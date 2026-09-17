#!/usr/bin/env python3
"""
Re-agrega player_stats.csv/json desde checkpoint_raw.json existente (sin llamar a Sofascore).

Aplica STAT_ALIASES y aggregate() actuales del scraper. No modifica teams.json ni events.json.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SCRAPER_DIR = _ROOT / "web_scraping_sofascore"
if str(_SCRAPER_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRAPER_DIR))

from sofascore_scraper import aggregate, save_csv, save_json  # noqa: E402

KNOWN_SLUGS = (
    "cl_primera_2025",
    "cl_segunda_2025",
    "ar_primera_2025",
    "ar_segunda_2025",
    "uy_primera_2025",
    "uy_segunda_2025",
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--output-root",
        type=Path,
        default=_ROOT / "web_scraping_sofascore" / "sofascore_output",
        help="Carpeta sofascore_output",
    )
    p.add_argument(
        "--only",
        nargs="+",
        default=None,
        metavar="OUTPUT_SLUG",
        help="Solo estas ligas (p. ej. cl_primera_2025)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostrar acciones sin escribir player_stats",
    )
    p.add_argument(
        "--backup",
        action="store_true",
        help="Copiar player_stats.csv/json previos a _backup_reagg_<timestamp>/",
    )
    return p.parse_args()


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_league_dirs(output_root: Path, only: list[str] | None) -> list[Path]:
    if only:
        unknown = set(only) - set(KNOWN_SLUGS)
        if unknown:
            print(
                f"AVISO: slug(s) no estándar: {', '.join(sorted(unknown))}",
                file=sys.stderr,
            )
        candidates = [output_root / slug for slug in only]
    else:
        candidates = sorted(
            p
            for p in output_root.iterdir()
            if p.is_dir() and not p.name.startswith("_")
        )

    out: list[Path] = []
    for league_dir in candidates:
        if (league_dir / "checkpoint_raw.json").is_file():
            out.append(league_dir)
        elif only and league_dir.name in set(only):
            print(f"OMITIDO {league_dir.name}: sin checkpoint_raw.json", file=sys.stderr)
    return out


def load_raw_stats(checkpoint_path: Path) -> dict[int, list]:
    data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Formato inesperado en {checkpoint_path}")
    raw: dict[int, list] = {}
    for key, matches in data.items():
        if not isinstance(matches, list):
            continue
        raw[int(key)] = matches
    return raw


def details_cache_from_player_stats(json_path: Path) -> dict[int, dict]:
    """Preserva name_ar, país, etc. del player_stats.json anterior si existe."""
    if not json_path.is_file():
        return {}
    rows = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        return {}
    cache: dict[int, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        pid = row.get("player_id")
        if pid is None:
            continue
        cache[int(pid)] = {
            "name_ar": row.get("player_name_ar") or "",
            "country": row.get("country") or "",
            "country_alpha2": row.get("country_alpha2") or "",
            "country_alpha3": row.get("country_alpha3") or "",
            "date_of_birth": row.get("date_of_birth"),
            "height": row.get("height"),
            "preferred_foot": row.get("preferred_foot") or "",
            "market_value": row.get("market_value"),
            "market_value_currency": row.get("market_value_currency") or "EUR",
        }
    return cache


def backup_player_stats(league_dir: Path, *, dry_run: bool) -> Path | None:
    ts = utc_timestamp()
    backup_dir = league_dir / f"_backup_reagg_{ts}"
    copied: list[str] = []
    for name in ("player_stats.csv", "player_stats.json"):
        src = league_dir / name
        if src.is_file():
            copied.append(name)
    if not copied:
        return None
    if dry_run:
        print(f"  DRY RUN: backup → {backup_dir.name}/ ({', '.join(copied)})")
        return backup_dir
    backup_dir.mkdir(parents=True, exist_ok=True)
    for name in copied:
        shutil.copy2(league_dir / name, backup_dir / name)
    print(f"  Backup: {backup_dir} ({', '.join(copied)})")
    return backup_dir


def validate_aggregated(league_dir: Path, rows: list[dict]) -> tuple[bool, str]:
    if not rows:
        return False, "aggregate() devolvió 0 jugadores"
    with_team = sum(1 for r in rows if r.get("team_name") or r.get("team_id"))
    with_fouls = sum(1 for r in rows if "foulsCommited" in r)
    print(
        f"  Jugadores: {len(rows)} · con equipo: {with_team} · "
        f"con foulsCommited: {with_fouls}"
    )
    return True, "ok"


def reaggregate_league(league_dir: Path, *, dry_run: bool, backup: bool) -> tuple[bool, str]:
    slug = league_dir.name
    checkpoint = league_dir / "checkpoint_raw.json"
    print(f"\n=== {slug} ===")
    print(f"  Checkpoint: {checkpoint}")

    if backup:
        backup_player_stats(league_dir, dry_run=dry_run)

    try:
        raw_stats = load_raw_stats(checkpoint)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return False, f"no se pudo leer checkpoint: {exc}"

    n_players = len(raw_stats)
    n_matches = sum(len(m) for m in raw_stats.values())
    print(f"  Raw: {n_players} jugadores · {n_matches} entradas partido")

    if n_players == 0:
        return False, "checkpoint sin jugadores"

    details_cache = details_cache_from_player_stats(league_dir / "player_stats.json")
    if details_cache:
        print(f"  Detalles jugador reutilizados: {len(details_cache)} (player_stats.json previo)")

    if dry_run:
        print("  DRY RUN: omitiendo aggregate() y escritura")
        return True, "dry-run"

    aggregated = aggregate(raw_stats, details_cache)
    ok, reason = validate_aggregated(league_dir, aggregated)
    if not ok:
        return False, reason

    save_json(aggregated, league_dir / "player_stats.json")
    save_csv(aggregated, league_dir / "player_stats.csv")
    print(f"  Escrito: player_stats.json, player_stats.csv")
    return True, "ok"


def main() -> int:
    args = parse_args()
    output_root = args.output_root.resolve()
    if not output_root.is_dir():
        print(f"ERROR: no existe {output_root}", file=sys.stderr)
        return 1

    league_dirs = resolve_league_dirs(output_root, args.only)
    if not league_dirs:
        print(f"No hay ligas con checkpoint_raw.json bajo {output_root}", file=sys.stderr)
        return 1

    print(f"Re-agregación desde checkpoint (sin Sofascore)")
    print(f"Output root: {output_root}")
    print(f"Ligas: {', '.join(d.name for d in league_dirs)}")
    if args.dry_run:
        print("Modo: DRY RUN")

    ok_n = 0
    fail_n = 0
    for league_dir in league_dirs:
        ok, reason = reaggregate_league(
            league_dir,
            dry_run=args.dry_run,
            backup=args.backup,
        )
        if ok:
            ok_n += 1
        else:
            fail_n += 1
            print(f"  ERROR: {reason}", file=sys.stderr)

    print(f"\nResumen: {ok_n} OK · {fail_n} error(es)")
    return 0 if fail_n == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
