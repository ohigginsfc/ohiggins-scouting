#!/usr/bin/env python3
"""
Actualización incremental Sofascore por event_id.

Descarga solo partidos nuevos o modificados, fusiona checkpoint_raw.json,
re-agrega, stage e importa con --replace de la competición afectada.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _ROOT / "scripts"
_SCRAPER_DIR = _ROOT / "web_scraping_sofascore"
_SRC_DIR = _ROOT / "src"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
if str(_SCRAPER_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRAPER_DIR))
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from run_all_sofascore_pipeline import (  # noqa: E402
    LEAGUES,
    LeagueConfig,
    filter_leagues,
    import_league,
    league_output_dir,
    project_root,
    reaggregate_league_from_checkpoint,
    stage_league,
    validate_sofascore_output,
)
from scouting.db import get_connection  # noqa: E402
from scouting.repositories import sofascore_event_ingestion_repository as ingestion_repo  # noqa: E402
from sofascore_scraper import (  # noqa: E402
    DEFAULT_DELAY_DETAILS,
    DEFAULT_DELAY_EVENTS,
    DEFAULT_DELAY_FALLBACK,
    DEFAULT_DELAY_INCIDENTS,
    DEFAULT_DELAY_LINEUP,
    ScraperConfig,
    build_driver,
    compute_event_checksum,
    event_datetime_utc,
    get_all_events,
    init_fetch_context,
    is_event_finished,
    load_checkpoint,
    merge_events_by_id,
    process_finished_event,
    remove_event_from_checkpoint,
    append_entries_to_checkpoint,
    save_json,
)

SOURCE_NAME = ingestion_repo.SOURCE_NAME


def scraper_config_for_league(league: LeagueConfig, *, no_headless: bool) -> ScraperConfig:
    return ScraperConfig(
        tournament_id=league.tournament_id,
        season_id=league.season_id,
        output_dir=Path("sofascore_output") / league.output_slug,
        headless=not no_headless,
        delay_lineup=DEFAULT_DELAY_LINEUP,
        delay_fallback=DEFAULT_DELAY_FALLBACK,
        delay_details=DEFAULT_DELAY_DETAILS,
        delay_events=DEFAULT_DELAY_EVENTS,
        delay_incidents=DEFAULT_DELAY_INCIDENTS,
    )


@dataclass
class EventClassification:
    event: dict
    event_id: int
    checksum: str
    kind: str  # new | updated | pending | skipped | force


@dataclass
class LeagueIncrementalResult:
    league: LeagueConfig
    total_calendar: int = 0
    already_processed: int = 0
    new_events: int = 0
    updated_events: int = 0
    pending_events: int = 0
    pending_import: int = 0
    skipped_events: int = 0
    downloaded: int = 0
    errors: int = 0
    players_updated: int = 0
    metrics_imported: int | None = None
    error_messages: list[str] = field(default_factory=list)
    dry_run: bool = False
    mode: str = "incremental"
    tournament_id: int | None = None
    season_id: int | None = None
    force_all_finished: bool = False


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group()
    group.add_argument(
        "--only",
        nargs="+",
        metavar="OUTPUT_SLUG",
        help="Solo estas ligas (p. ej. cl_primera_2025)",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Todas las ligas configuradas (opcionalmente filtradas con --season)",
    )
    p.add_argument(
        "--season",
        default=None,
        metavar="YEAR",
        help=(
            "Con --all: solo ligas cuyo slug termina en _YEAR (p. ej. 2025). "
            "También etiqueta staging/import; si se omite, se infiere del slug de cada liga."
        ),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostrar candidatos sin descargar lineups ni importar",
    )
    p.add_argument(
        "--since",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="Solo eventos con fecha >= YYYY-MM-DD",
    )
    p.add_argument(
        "--force-event",
        type=int,
        action="append",
        default=None,
        metavar="EVENT_ID",
        help="Forzar descarga de event_id(s) concretos",
    )
    p.add_argument(
        "--no-headless",
        action="store_true",
        help="Chrome visible (útil para depurar bloqueos WAF)",
    )
    p.add_argument(
        "--skip-import",
        action="store_true",
        help="Scrape + reaggregate + stage, sin importar a PostgreSQL",
    )
    p.add_argument(
        "--no-replace",
        action="store_true",
        help="Import sin --replace (append)",
    )
    p.add_argument(
        "--json-summary",
        action="store_true",
        help="Imprimir resumen JSON parseable al final (SOFASCORE_INCREMENTAL_JSON=...)",
    )
    p.add_argument(
        "--force-backfill",
        action="store_true",
        help=(
            "Forzar descarga de todos los partidos finalizados de la temporada "
            "(sincronización inicial cuando solo hay datos demo o sync incompleta)."
        ),
    )
    p.add_argument(
        "--resync-season",
        action="store_true",
        help=(
            "Resincronizar toda la temporada activa: descarga de nuevo todos los "
            "eventos finalizados, re-agrega e importa (upsert/replace)."
        ),
    )
    p.add_argument(
        "--process-existing-output",
        action="store_true",
        help=(
            "No descargar partidos: reagregar + stage + importar desde "
            "checkpoint_raw.json ya existente (reutiliza scrapes previos)."
        ),
    )
    p.add_argument(
        "--skip-download-if-checkpoint-exists",
        action="store_true",
        help=(
            "Alias de --process-existing-output: procesa checkpoints existentes "
            "sin scraping."
        ),
    )
    return p.parse_args()


def season_year_from_league(league: LeagueConfig) -> int:
    suffix = league.output_slug.rsplit("_", 1)[-1]
    return int(suffix)


def league_season_label(league: LeagueConfig) -> str:
    if league.season:
        return league.season
    return league.output_slug.rsplit("_", 1)[-1]


def filter_leagues_by_season(
    leagues: list[LeagueConfig],
    season: str,
) -> tuple[list[LeagueConfig], list[LeagueConfig]]:
    """Devuelve (ligas de la temporada, ligas históricas omitidas)."""
    active: list[LeagueConfig] = []
    skipped: list[LeagueConfig] = []
    season_str = str(season)
    for league in leagues:
        if league_season_label(league) == season_str:
            active.append(league)
        else:
            skipped.append(league)
    return active, skipped


def staging_season_for_league(league: LeagueConfig, season_arg: str | None) -> str:
    if season_arg:
        return season_arg
    return league_season_label(league)


def parse_since(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def project_scripts(root: Path) -> dict[str, Path]:
    return {
        "reaggregate": root / "scripts" / "reaggregate_sofascore_outputs.py",
        "stage": root / "scripts" / "stage_sofascore_output.py",
    }


def preflight_pipeline(
    root: Path,
    *,
    require_browser: bool,
    require_db: bool,
) -> None:
    """Valida componentes obligatorios ANTES de descargar ligas."""
    errors: list[str] = []
    scripts = project_scripts(root)
    for name, path in scripts.items():
        if not path.is_file():
            errors.append(f"Falta script {name}: {path}")

    import_mod = root / "src" / "scouting" / "ingestion" / "import_sofascore_player_stats_csv.py"
    if not import_mod.is_file():
        errors.append(f"Falta módulo de importación: {import_mod}")

    out_root = root / "web_scraping_sofascore" / "sofascore_output"
    out_root.mkdir(parents=True, exist_ok=True)

    if require_browser:
        chrome = (os.environ.get("CHROME_BINARY") or os.environ.get("CHROME_BIN") or "").strip()
        driver = (os.environ.get("CHROMEDRIVER_PATH") or "").strip()
        if chrome and not Path(chrome).is_file():
            errors.append(f"Chromium no encontrado en {chrome}")
        if driver and not Path(driver).is_file():
            errors.append(f"ChromeDriver no encontrado en {driver}")
        try:
            import selenium  # noqa: F401
        except ImportError:
            errors.append("Selenium no está instalado en este Python")

    if require_db:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Conexión PostgreSQL fallida: {exc}")

    if errors:
        print("PREFLIGHT FALLIDO — no se iniciará la descarga:", file=sys.stderr)
        for err in errors:
            print(f"  · {err}", file=sys.stderr)
        raise SystemExit(2)
    print("Preflight OK: scripts, salida, runtime y BD verificados.")


def finalize_league_from_checkpoint(
    root: Path,
    league: LeagueConfig,
    season: str,
    result: LeagueIncrementalResult,
    *,
    skip_import: bool,
    use_replace: bool,
    backup: bool = True,
) -> LeagueIncrementalResult:
    """checkpoint_raw → teams.json → reagregar → validar → stage → import PostgreSQL."""
    from scouting.services.sofascore_teams_rebuild import ensure_teams_json

    league_dir = league_output_dir(root, league)
    checkpoint = league_dir / "checkpoint_raw.json"
    if not checkpoint.is_file():
        msg = f"No hay checkpoint_raw.json en {league_dir}"
        result.errors += 1
        result.error_messages.append(msg)
        print(f"  ERROR: {msg}", file=sys.stderr)
        return result

    try:
        checkpoint_bytes = checkpoint.read_bytes()
        checkpoint_hash = hashlib.sha256(checkpoint_bytes).hexdigest()
        checkpoint_data = json.loads(checkpoint_bytes)
        if not isinstance(checkpoint_data, dict) or not checkpoint_data:
            raise ValueError("Checkpoint vacío o inválido")
        event_ids_set: set[int] = set()
        for entries in checkpoint_data.values():
            if not isinstance(entries, list):
                raise ValueError("Entradas de checkpoint inválidas")
            for entry in entries:
                event_id = entry.get("event_id") if isinstance(entry, dict) else None
                if type(event_id) is not int or event_id <= 0:
                    raise ValueError("Checkpoint sin event_id válido; no se puede publicar su cobertura")
                event_ids_set.add(event_id)
        if not event_ids_set:
            raise ValueError("Checkpoint sin partidos")
        event_ids = sorted(event_ids_set)
    except (OSError, ValueError) as exc:
        result.errors += 1
        result.error_messages.append(f"checkpoint: {exc}")
        return result

    print(f"  Procesando checkpoint existente: {checkpoint}")

    # teams.json no lo genera el incremental (solo el scraper completo vía get_teams).
    # Regenerar desde events/checkpoint/player_stats antes de validar/staging.
    teams_ok, teams_reason, teams_n = ensure_teams_json(league_dir, overwrite=False)
    print(f"  teams.json: {teams_reason}")
    if not teams_ok:
        result.error_messages.append(f"teams.json: {teams_reason}")
        result.errors += 1
        _mark_scope_import_outcome(
            league,
            season_year_from_league(league),
            event_ids=event_ids,
            ok=False,
            error_message=f"validate/teams: {teams_reason}",
        )
        return result

    ok, reason = reaggregate_league_from_checkpoint(
        root, league, dry_run=False, backup=backup
    )
    if not ok:
        result.error_messages.append(f"reaggregate: {reason}")
        result.errors += 1
        print(
            "  ERROR de reagregación: no se marcará la importación como completada.",
            file=sys.stderr,
        )
        _mark_scope_import_outcome(
            league,
            season_year_from_league(league),
            event_ids=event_ids,
            ok=False,
            error_message=f"reaggregate: {reason}",
        )
        return result

    # Re-asegurar teams tras reagregación (por si se regeneró player_stats).
    ensure_teams_json(league_dir, overwrite=False)

    ok, reason = validate_sofascore_output(league_dir)
    if not ok:
        result.error_messages.append(f"validate: {reason}")
        result.errors += 1
        _mark_scope_import_outcome(
            league,
            season_year_from_league(league),
            event_ids=event_ids,
            ok=False,
            error_message=f"validate: {reason}",
        )
        return result

    try:
        staging_dir = stage_league(root, league, season, dry_run=False)
    except Exception as exc:  # noqa: BLE001
        result.error_messages.append(f"staging: {exc}")
        result.errors += 1
        _mark_scope_import_outcome(
            league,
            season_year_from_league(league),
            event_ids=event_ids,
            ok=False,
            error_message=f"staging: {exc}",
        )
        return result
    if staging_dir is None:
        result.error_messages.append("staging: no staging dir")
        result.errors += 1
        _mark_scope_import_outcome(
            league,
            season_year_from_league(league),
            event_ids=event_ids,
            ok=False,
            error_message="staging: no staging dir",
        )
        return result

    if skip_import:
        print("  skip-import: stage listo, sin PostgreSQL")
        return result

    try:
        if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != checkpoint_hash:
            raise ValueError("El checkpoint cambió durante la preparación; repetir la importación")
        import_league(
            root,
            league,
            season,
            staging_dir,
            use_replace=use_replace,
            dry_run=False,
        )
    except Exception as exc:  # noqa: BLE001
        result.error_messages.append(f"import: {exc}")
        result.errors += 1
        print(
            "  ERROR de importación: rollback/lote fallido gestionado por el importer.",
            file=sys.stderr,
        )
        _mark_scope_import_outcome(
            league,
            season_year_from_league(league),
            event_ids=event_ids,
            ok=False,
            error_message=f"import: {exc}",
        )
        return result

    csv_path = staging_dir / "player_stats.csv"
    if csv_path.is_file():
        lines = csv_path.read_text(encoding="utf-8").strip().splitlines()
        result.metrics_imported = max(0, len(lines) - 1)
    print(f"  Importación OK · filas CSV: {result.metrics_imported} · equipos: {teams_n}")
    _mark_scope_import_outcome(
        league,
        season_year_from_league(league),
        event_ids=event_ids,
        ok=True,
        error_message=None,
    )
    return result


def _mark_scope_import_outcome(
    league: LeagueConfig,
    season_year: int,
    *,
    ok: bool,
    error_message: str | None,
    event_ids: list[int],
) -> None:
    """Tras import: downloaded→processed. Ante fallo: dejar downloaded con error."""
    try:
        with get_connection() as conn:
            if ok:
                n = ingestion_repo.update_events_status_for_scope(
                    conn,
                    country=league.country,
                    division=league.division,
                    competition=league.competition,
                    season=season_year,
                    event_ids=event_ids,
                    from_statuses={"downloaded"},
                    to_status="processed",
                    error_message=None,
                )
                print(f"  Eventos marcados processed: {n}")
            else:
                n = ingestion_repo.update_events_status_for_scope(
                    conn,
                    country=league.country,
                    division=league.division,
                    competition=league.competition,
                    season=season_year,
                    event_ids=event_ids,
                    from_statuses={"downloaded"},
                    to_status="downloaded",
                    error_message=error_message,
                )
                print(
                    f"  Eventos dejados en downloaded (import incompleta): {n}"
                    + (f" · {error_message}" if error_message else "")
                )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("No se pudo confirmar el estado de los partidos importados") from exc


def _repair_premature_processed_events(league: LeagueConfig, season_year: int) -> None:
    """Si hay processed sin métricas Sofascore reales del ámbito, demover a downloaded."""
    from scouting.services.sofascore_sync_assessment import has_real_sofascore_metrics_for_scope

    try:
        with get_connection() as conn:
            if has_real_sofascore_metrics_for_scope(
                conn, competition=league.competition, season=season_year
            ):
                return
            n = ingestion_repo.demote_processed_without_import(
                conn,
                country=league.country,
                division=league.division,
                competition=league.competition,
                season=season_year,
                error_message=(
                    "Reparado: marcado processed sin lote/métricas reales "
                    "(p. ej. falló validate teams.json)."
                ),
            )
            if n:
                print(
                    f"  Reparación: {n} eventos {league.output_slug} "
                    f"pasaron de processed → downloaded"
                )
    except Exception as exc:  # noqa: BLE001
        print(f"  AVISO reparación ingestion: {exc}", file=sys.stderr)


def load_existing_events(league_dir: Path) -> list[dict]:
    path = league_dir / "events.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def bootstrap_ingestion_if_needed(
    conn,
    league: LeagueConfig,
    season_year: int,
    league_dir: Path,
    fetched_events: list[dict],
) -> None:
    """
    Solo marca eventos como processed si YA existen métricas Sofascore reales
    para esa competición/temporada. Nunca bootstrap a partir de solo checkpoint
    en disco cuando la BD solo tiene demo o está vacía.
    """
    from scouting.services.sofascore_sync_assessment import (
        has_real_sofascore_metrics_for_scope,
    )

    existing = ingestion_repo.list_events_for_scope(
        conn,
        country=league.country,
        division=league.division,
        competition=league.competition,
        season=season_year,
    )
    if existing:
        return

    if not has_real_sofascore_metrics_for_scope(
        conn, competition=league.competition, season=season_year
    ):
        print(
            "  Bootstrap omitido: no hay métricas Sofascore reales para este "
            "ámbito; los eventos se tratarán como pendientes de descarga."
        )
        return

    checkpoint = league_dir / "checkpoint_raw.json"
    events_source = fetched_events or load_existing_events(league_dir)
    if not checkpoint.is_file() or not events_source:
        return

    print(
        f"  Bootstrap: marcando {len(events_source)} eventos como processed "
        "(checkpoint existente + métricas reales, tabla vacía)."
    )
    enriched = []
    for event in events_source:
        if not is_event_finished(event):
            continue
        copy = dict(event)
        copy["_bootstrap_checksum"] = compute_event_checksum(event)
        enriched.append(copy)
    n = ingestion_repo.seed_processed_events(
        conn,
        country=league.country,
        division=league.division,
        competition=league.competition,
        season=season_year,
        events=enriched,
    )
    print(f"  Bootstrap insertados: {n}")


def classify_events(
    events: list[dict],
    known: dict[int, dict[str, Any]],
    *,
    force_event_ids: set[int] | None,
    since: date | None,
    force_all_finished: bool = False,
) -> tuple[list[EventClassification], dict[str, int]]:
    force_event_ids = force_event_ids or set()
    stats = {
        "total_calendar": 0,
        "already_processed": 0,
        "already_downloaded": 0,
        "new_events": 0,
        "updated_events": 0,
        "pending_events": 0,
        "skipped_events": 0,
    }
    candidates: list[EventClassification] = []

    for event in events:
        if not is_event_finished(event):
            continue

        event_id = int(event["id"])
        stats["total_calendar"] += 1

        ev_dt = event_datetime_utc(event)
        if since and ev_dt and ev_dt.date() < since:
            stats["skipped_events"] += 1
            continue

        checksum = compute_event_checksum(event)
        row = known.get(event_id)

        if force_all_finished or event_id in force_event_ids:
            candidates.append(
                EventClassification(event=event, event_id=event_id, checksum=checksum, kind="force")
            )
            if row and row.get("processing_status") == "processed":
                stats["updated_events"] += 1
            else:
                stats["new_events"] += 1
            continue

        if not row:
            candidates.append(
                EventClassification(event=event, event_id=event_id, checksum=checksum, kind="new")
            )
            stats["new_events"] += 1
            continue

        status = row.get("processing_status")
        stored_checksum = row.get("checksum")

        if status == "processed" and stored_checksum == checksum:
            stats["already_processed"] += 1
            stats["skipped_events"] += 1
            continue

        # Descargado a checkpoint pero aún no importado: no re-scrapear.
        if status == "downloaded" and stored_checksum == checksum:
            stats["already_downloaded"] = stats.get("already_downloaded", 0) + 1
            stats["skipped_events"] += 1
            continue

        if status != "processed":
            kind = "pending"
            stats["pending_events"] += 1
        elif stored_checksum != checksum:
            kind = "updated"
            stats["updated_events"] += 1
        else:
            kind = "pending"
            stats["pending_events"] += 1

        candidates.append(
            EventClassification(event=event, event_id=event_id, checksum=checksum, kind=kind)
        )

    return candidates, stats


def print_league_dry_run(league: LeagueConfig, stats: dict[str, int]) -> None:
    print(f"\nLiga: {league.output_slug}")
    print(f"  Eventos totales en calendario: {stats['total_calendar']}")
    print(f"  Eventos ya procesados: {stats['already_processed']}")
    print(f"  Eventos nuevos: {stats['new_events']}")
    print(f"  Eventos actualizados: {stats['updated_events']}")
    print(f"  Eventos pendientes: {stats['pending_events']}")
    pending_total = stats["new_events"] + stats["updated_events"] + stats["pending_events"]
    print(f"  → A descargar: {pending_total}")


def scrape_candidates(
    league: LeagueConfig,
    league_dir: Path,
    candidates: list[EventClassification],
    *,
    no_headless: bool,
    conn,
    season_year: int,
) -> tuple[set[int], int, list[str]]:
    config = scraper_config_for_league(league, no_headless=no_headless)

    checkpoint_path = league_dir / "checkpoint_raw.json"
    raw_stats = load_checkpoint(checkpoint_path)
    players_touched: set[int] = set()
    downloaded = 0
    errors: list[str] = []

    driver = None if os.environ.get("SOFASCORE_FETCH_MODE") == "http" else build_driver(headless=config.headless)
    init_fetch_context(debug_fetch=False, driver=driver)

    try:
        for idx, item in enumerate(candidates, 1):
            event = item.event
            event_id = item.event_id
            home = (event.get("homeTeam") or {}).get("name", "?")
            away = (event.get("awayTeam") or {}).get("name", "?")
            print(f"  [{idx}/{len(candidates)}] #{event_id} {home} vs {away} ({item.kind})")

            try:
                entries, _diag = process_finished_event(
                    driver,
                    event,
                    delay_lineup=config.delay_lineup,
                    delay_fallback=config.delay_fallback,
                    delay_incidents=config.delay_incidents,
                )
                if not entries:
                    msg = f"event {event_id}: sin lineup"
                    errors.append(msg)
                    ingestion_repo.upsert_event(
                        conn,
                        country=league.country,
                        division=league.division,
                        competition=league.competition,
                        season=season_year,
                        event_id=event_id,
                        home_team=home,
                        away_team=away,
                        event_date=event_datetime_utc(event),
                        status=(event.get("status") or {}).get("type"),
                        has_lineups=event.get("hasLineups"),
                        has_xg=event.get("hasXg"),
                        checksum=item.checksum,
                        processing_status="skipped",
                        error_message=msg,
                    )
                    continue

                raw_stats = remove_event_from_checkpoint(raw_stats, event_id)
                raw_stats = append_entries_to_checkpoint(raw_stats, entries)
                for entry in entries:
                    pid = (entry.get("player") or {}).get("id")
                    if pid:
                        players_touched.add(int(pid))

                downloaded += 1
                ingestion_repo.upsert_event(
                    conn,
                    country=league.country,
                    division=league.division,
                    competition=league.competition,
                    season=season_year,
                    event_id=event_id,
                    home_team=home,
                    away_team=away,
                    event_date=event_datetime_utc(event),
                    status=(event.get("status") or {}).get("type"),
                    has_lineups=event.get("hasLineups"),
                    has_xg=event.get("hasXg"),
                    checksum=item.checksum,
                        processing_status="downloaded",
                        scraped_at=datetime.now(timezone.utc),
                        error_message=None,
                    )
            except Exception as exc:  # noqa: BLE001
                msg = f"event {event_id}: {exc}"
                errors.append(msg)
                print(f"    ERROR: {exc}", file=sys.stderr)
                ingestion_repo.upsert_event(
                    conn,
                    country=league.country,
                    division=league.division,
                    competition=league.competition,
                    season=season_year,
                    event_id=event_id,
                    home_team=home,
                    away_team=away,
                    event_date=event_datetime_utc(event),
                    status=(event.get("status") or {}).get("type"),
                    has_lineups=event.get("hasLineups"),
                    has_xg=event.get("hasXg"),
                    checksum=item.checksum,
                    processing_status="failed",
                    error_message=str(exc),
                )

        save_json(raw_stats, checkpoint_path)
    finally:
        if driver is not None:
            driver.quit()

    return players_touched, downloaded, errors


def process_league_incremental(
    root: Path,
    league: LeagueConfig,
    season: str,
    *,
    dry_run: bool,
    since: date | None,
    force_event_ids: set[int] | None,
    no_headless: bool,
    skip_import: bool,
    use_replace: bool,
    force_all_finished: bool = False,
    mode: str = "incremental",
    process_existing: bool = False,
) -> LeagueIncrementalResult:
    result = LeagueIncrementalResult(
        league=league,
        dry_run=dry_run,
        mode=mode,
        tournament_id=league.tournament_id,
        season_id=league.season_id,
        force_all_finished=force_all_finished,
    )
    season_year = season_year_from_league(league)
    league_dir = league_output_dir(root, league)
    league_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"Incremental: {league.output_slug} (mode={mode})")
    print(f"  tournament_id={league.tournament_id} season_id={league.season_id}")
    print(f"{'=' * 60}")

    if process_existing:
        if dry_run:
            checkpoint = league_dir / "checkpoint_raw.json"
            print(f"  DRY RUN process-existing: checkpoint={'OK' if checkpoint.is_file() else 'MISSING'}")
            return result
        # Reparar eventos marcados processed sin métricas reales (import fallida previa).
        _repair_premature_processed_events(league, season_year)
        return finalize_league_from_checkpoint(
            root,
            league,
            season,
            result,
            skip_import=skip_import,
            use_replace=use_replace,
            backup=True,
        )

    # Fetch current calendar (lightweight vs full season scrape)
    config = scraper_config_for_league(league, no_headless=no_headless)
    driver = None if os.environ.get("SOFASCORE_FETCH_MODE") == "http" else build_driver(headless=config.headless)
    init_fetch_context(debug_fetch=False, driver=driver)
    try:
        fetched = get_all_events(
            driver,
            league.tournament_id,
            league.season_id,
            delay_events=config.delay_events,
        )
    finally:
        if driver is not None:
            driver.quit()

    if not fetched:
        msg = (
            f"Calendario vacío o no disponible para tournament_id={league.tournament_id} "
            f"season_id={league.season_id}"
        )
        print(f"  ERROR: {msg}", file=sys.stderr)
        result.errors = 1
        result.error_messages = [msg]
        return result

    existing_events = load_existing_events(league_dir)
    merged_events = merge_events_by_id(existing_events, fetched)
    if not dry_run:
        save_json(merged_events, league_dir / "events.json")
        from scouting.services.sofascore_teams_rebuild import ensure_teams_json

        teams_ok, teams_reason, teams_n = ensure_teams_json(league_dir, overwrite=False)
        print(f"  {teams_reason}" + (f" ({teams_n})" if teams_ok else ""))

    with get_connection() as conn:
        if not force_all_finished and not dry_run:
            bootstrap_ingestion_if_needed(
                conn, league, season_year, league_dir, merged_events
            )
        known = ingestion_repo.list_events_for_scope(
            conn,
            country=league.country,
            division=league.division,
            competition=league.competition,
            season=season_year,
        )

        candidates, stats = classify_events(
            merged_events,
            known,
            force_event_ids=force_event_ids,
            since=since,
            force_all_finished=force_all_finished,
        )

        result.total_calendar = stats["total_calendar"]
        result.already_processed = stats["already_processed"]
        result.new_events = stats["new_events"]
        result.updated_events = stats["updated_events"]
        result.pending_events = stats["pending_events"]
        result.pending_import = int(stats.get("already_downloaded") or 0)
        result.skipped_events = stats["skipped_events"]

        print_league_dry_run(league, stats)
        if stats.get("already_downloaded"):
            print(f"  Eventos descargados pendientes de importar: {stats['already_downloaded']}")

        if dry_run:
            return result

        if not candidates:
            print("  Nada que descargar.")
            checkpoint = league_dir / "checkpoint_raw.json"
            downloaded_pending = int(stats.get("already_downloaded") or 0)
            if downloaded_pending > 0 and not checkpoint.is_file():
                result.errors = 1
                result.error_messages = ["Hay importaciones pendientes pero falta checkpoint_raw.json; recuperar el checkpoint o ejecutar una recarga explícita."]
                return result
            if checkpoint.is_file() and (downloaded_pending > 0 or force_all_finished):
                print("  Continuando con reagregación/importación del checkpoint…")
                return finalize_league_from_checkpoint(
                    root,
                    league,
                    season,
                    result,
                    skip_import=skip_import,
                    use_replace=use_replace,
                    backup=True,
                )
            return result

        players_touched, downloaded, errors = scrape_candidates(
            league,
            league_dir,
            candidates,
            no_headless=no_headless,
            conn=conn,
            season_year=season_year,
        )
        result.downloaded = downloaded
        result.errors = len(errors)
        result.error_messages = errors
        result.players_updated = len(players_touched)

    checkpoint = league_dir / "checkpoint_raw.json"
    if result.downloaded == 0 and not force_event_ids and not force_all_finished:
        if checkpoint.is_file() and not skip_import:
            print(
                "  Sin eventos nuevos; hay checkpoint — "
                "usa --process-existing-output para importar sin re-descargar."
            )
        else:
            print("  Sin cambios en checkpoint; omitiendo reaggregate/import.")
        return result

    if result.downloaded == 0 and force_all_finished and not checkpoint.is_file():
        msg = (
            "force-backfill/resync sin descargas ni checkpoint: "
            "no se importarán métricas."
        )
        print(f"  ERROR: {msg}", file=sys.stderr)
        result.errors += 1
        result.error_messages.append(msg)
        return result

    if result.downloaded == 0 and force_all_finished and checkpoint.is_file():
        print("  Sin descargas nuevas; reagregando/importando checkpoint existente.")

    return finalize_league_from_checkpoint(
        root,
        league,
        season,
        result,
        skip_import=skip_import,
        use_replace=use_replace,
        backup=True,
    )


def print_final_summary(results: list[LeagueIncrementalResult]) -> None:
    print("\n" + "=" * 72)
    print("RESUMEN ACTUALIZACIÓN INCREMENTAL SOFASCORE")
    print("=" * 72)
    for r in results:
        print(f"\n{r.league.output_slug}")
        print(f"  eventos nuevos:      {r.new_events}")
        print(f"  eventos actualizados:{r.updated_events}")
        print(f"  eventos omitidos:    {r.skipped_events}")
        print(f"  descargados:         {r.downloaded}")
        print(f"  errores:             {r.errors}")
        print(f"  jugadores actualiz.: {r.players_updated}")
        if r.metrics_imported is not None:
            print(f"  métricas importadas: {r.metrics_imported}")
        if r.error_messages:
            for msg in r.error_messages[:5]:
                print(f"    · {msg}")
    print("=" * 72)


def result_to_json(r: LeagueIncrementalResult) -> dict:
    pending = r.new_events + r.updated_events + r.pending_events + r.pending_import
    return {
        "slug": r.league.output_slug,
        "competition": r.league.competition,
        "tournament_id": r.tournament_id or r.league.tournament_id,
        "season_id": r.season_id or r.league.season_id,
        "mode": r.mode,
        "total_calendar": r.total_calendar,
        "new_events": r.new_events,
        "updated_events": r.updated_events,
        "pending_events": r.pending_events,
        "pending_import": r.pending_import,
        "pending_total": pending,
        "skipped_events": r.skipped_events,
        "downloaded": r.downloaded,
        "errors": r.errors,
        "dry_run": r.dry_run,
        "players_updated": r.players_updated,
        "metrics_imported": r.metrics_imported,
        "error_messages": r.error_messages,
        "force_all_finished": r.force_all_finished,
    }


def emit_json_summary(
    results: list[LeagueIncrementalResult],
    *,
    active_season: str | None,
    leagues_checked: list[str],
    historical_leagues_skipped: int,
) -> None:
    payload = {
        "ok": all(r.errors == 0 for r in results),
        "active_season": active_season,
        "leagues_checked": leagues_checked,
        "historical_leagues_skipped": historical_leagues_skipped,
        "leagues": [result_to_json(r) for r in results],
    }
    print("\nSOFASCORE_INCREMENTAL_JSON=" + json.dumps(payload, ensure_ascii=False))


def main() -> int:
    args = parse_args()
    root = project_root()

    all_configured = list(LEAGUES)
    historical_skipped = 0
    active_season: str | None = None

    if args.all:
        if args.season:
            active_season = str(args.season)
            leagues, skipped_leagues = filter_leagues_by_season(all_configured, active_season)
            historical_skipped = len(skipped_leagues)
            if skipped_leagues:
                skipped_slugs = ", ".join(lg.output_slug for lg in skipped_leagues)
                print(
                    f"Temporada activa {active_season}: omitiendo {historical_skipped} "
                    f"liga(s) histórica(s): {skipped_slugs}"
                )
            if not leagues:
                print(
                    f"ERROR: ninguna liga configurada para temporada {active_season}",
                    file=sys.stderr,
                )
                return 1
        else:
            leagues = all_configured
    elif args.only:
        leagues = filter_leagues(args.only)
    else:
        print("ERROR: indica --only <slug> o --all", file=sys.stderr)
        return 1

    since = parse_since(args.since)
    force_ids = set(args.force_event or [])
    force_all = bool(args.force_backfill or args.resync_season)
    process_existing = bool(
        args.process_existing_output or args.skip_download_if_checkpoint_exists
    )
    mode = (
        "process_existing"
        if process_existing
        else ("resync" if args.resync_season else ("backfill" if args.force_backfill else "incremental"))
    )
    if force_all and not process_existing:
        print(f"Modo {mode}: se forzarán todos los partidos finalizados de la temporada.")
    if process_existing:
        print(
            "Modo process-existing: reagregar/importar desde checkpoint_raw.json "
            "sin descargar partidos."
        )

    require_browser = (not process_existing) and (not args.dry_run)
    preflight_pipeline(
        root,
        require_browser=require_browser,
        require_db=not args.dry_run,
    )

    results: list[LeagueIncrementalResult] = []
    for league in leagues:
        staging_season = staging_season_for_league(league, args.season)
        try:
            res = process_league_incremental(
                root,
                league,
                staging_season,
                dry_run=args.dry_run,
                since=since,
                force_event_ids=force_ids,
                no_headless=args.no_headless,
                skip_import=args.skip_import,
                use_replace=not args.no_replace,
                force_all_finished=force_all,
                mode=mode,
                process_existing=process_existing,
            )
            results.append(res)
        except Exception as exc:  # noqa: BLE001
            import traceback

            print(f"ERROR {league.output_slug}: {exc}", file=sys.stderr)
            traceback.print_exc()
            err = LeagueIncrementalResult(
                league=league,
                dry_run=args.dry_run,
                mode=mode,
                tournament_id=league.tournament_id,
                season_id=league.season_id,
            )
            err.errors = 1
            err.error_messages = [f"{exc}\n{traceback.format_exc()}"]
            results.append(err)

    leagues_checked = [r.league.output_slug for r in results]
    print_final_summary(results)
    if args.json_summary:
        emit_json_summary(
            results,
            active_season=active_season,
            leagues_checked=leagues_checked,
            historical_leagues_skipped=historical_skipped,
        )
    return 0 if all(r.errors == 0 for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
