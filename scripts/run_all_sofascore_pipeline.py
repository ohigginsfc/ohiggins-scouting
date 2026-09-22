#!/usr/bin/env python3
"""
Pipeline completo Sofascore: Docker → schema → seed → scrape → stage → import.

Ejecutar desde la raíz del repositorio scouting-platform.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

STAGED_DIR_RE = re.compile(r"^STAGED_DIR=(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class LeagueConfig:
    country: str
    division: str
    competition: str
    tournament_id: int
    season_id: int
    output_slug: str
    season: str = ""
    season_label: str = ""


LEAGUES: tuple[LeagueConfig, ...] = (
    LeagueConfig("cl", "primera", "Primera División Chile", 11653, 71131, "cl_primera_2025"),
    LeagueConfig("cl", "segunda", "Liga de Ascenso Chile", 1240, 89007, "cl_segunda_2025"),
    LeagueConfig("ar", "primera", "Liga Profesional Argentina", 155, 87913, "ar_primera_2025"),
    LeagueConfig("ar", "segunda", "Primera Nacional Argentina", 703, 87940, "ar_segunda_2025"),
    LeagueConfig("uy", "primera", "Liga AUF Uruguay", 278, 89288, "uy_primera_2025"),
    LeagueConfig("uy", "segunda", "Segunda División Uruguay", 1908, 91195, "uy_segunda_2025"),
    LeagueConfig(
        "cl",
        "primera",
        "Primera División Chile",
        11653,
        57883,
        "cl_primera_2024",
        season="2024",
        season_label="2024",
    ),
)


def league_staging_season(league: LeagueConfig, cli_season: str) -> str:
    if league.season:
        return league.season
    suffix = league.output_slug.rsplit("_", 1)[-1]
    if suffix.isdigit():
        return suffix
    return cli_season


@dataclass
class LeagueResult:
    league: LeagueConfig
    scrape: str = "skipped"
    staging_path: str = ""
    import_status: str = "skipped"
    error: str = ""


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def run_command(
    cmd: list[str] | str,
    *,
    cwd: Path | None = None,
    check: bool = True,
    dry_run: bool = False,
) -> int:
    if isinstance(cmd, list):
        display = " ".join(_quote_arg(a) for a in cmd)
    else:
        display = cmd
    cwd_str = str(cwd) if cwd else None
    prefix = f"[cwd={cwd_str}] " if cwd_str else ""
    print(f"\n$ {prefix}{display}")

    if dry_run:
        return 0

    result = subprocess.run(
        cmd,
        cwd=cwd_str,
        shell=isinstance(cmd, str),
        text=True,
    )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd)
    return result.returncode


def _quote_arg(arg: str) -> str:
    if not arg or any(c in arg for c in " \t\"'"):
        return f'"{arg}"'
    return arg


def filter_leagues(only: list[str] | None) -> list[LeagueConfig]:
    if not only:
        return list(LEAGUES)
    slugs = {s.strip() for s in only}
    unknown = slugs - {lg.output_slug for lg in LEAGUES}
    if unknown:
        print(f"ERROR: unknown output_slug(s): {', '.join(sorted(unknown))}", file=sys.stderr)
        print(f"Valid: {', '.join(lg.output_slug for lg in LEAGUES)}", file=sys.stderr)
        sys.exit(1)
    return [lg for lg in LEAGUES if lg.output_slug in slugs]


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sofascore_output_root(root: Path) -> Path:
    return root / "web_scraping_sofascore" / "sofascore_output"


def league_output_dir(root: Path, league: LeagueConfig) -> Path:
    return sofascore_output_root(root) / league.output_slug


def reaggregate_script_path(root: Path) -> Path:
    return root / "scripts" / "reaggregate_sofascore_outputs.py"


def reaggregate_league_from_checkpoint(
    root: Path,
    league: LeagueConfig,
    *,
    dry_run: bool,
    backup: bool,
) -> tuple[bool, str]:
    """Re-agrega player_stats desde checkpoint_raw.json (sin Sofascore)."""
    league_dir = league_output_dir(root, league)
    checkpoint = league_dir / "checkpoint_raw.json"
    if not checkpoint.is_file():
        return False, f"missing checkpoint_raw.json at {league_dir}"

    script = reaggregate_script_path(root)
    if not script.is_file():
        return (
            False,
            f"Script de reagregación no encontrado: {script}. "
            "Debe existir scripts/reaggregate_sofascore_outputs.py en el repositorio.",
        )

    cmd = [
        sys.executable,
        str(script),
        "--only",
        league.output_slug,
    ]
    if dry_run:
        cmd.append("--dry-run")
    if backup:
        cmd.append("--backup")

    if dry_run:
        run_command(cmd, cwd=root, dry_run=True)
        return True, "dry-run"

    proc = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
    print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    if proc.returncode != 0:
        return False, proc.stderr.strip() or f"reaggregate exit {proc.returncode}"
    return True, "ok"


def validate_sofascore_output(output_dir: Path) -> tuple[bool, str]:
    """
    Comprueba que un directorio de scrape Sofascore está completo y usable.
    """
    required_files = (
        "player_stats.csv",
        "player_stats.json",
        "events.json",
        "teams.json",
    )
    if not output_dir.is_dir():
        return False, f"Output directory does not exist: {output_dir}"

    for name in required_files:
        if not (output_dir / name).is_file():
            return False, f"Missing {name}"

    csv_path = output_dir / "player_stats.csv"
    try:
        lines = csv_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return False, f"Cannot read player_stats.csv: {exc}"

    non_empty_lines = [ln for ln in lines if ln.strip()]
    if len(non_empty_lines) <= 1:
        return False, "player_stats.csv has no data rows (header only or empty)"

    return True, "ok"


def _cleanup_failed_temp(temp_dir: Path, *, keep_failed_temp: bool) -> None:
    if not temp_dir.exists():
        return
    if keep_failed_temp:
        print(f"Keeping failed temp dir for inspection: {temp_dir}")
        return
    try:
        entries = list(temp_dir.iterdir())
    except OSError:
        print(f"Leaving temp dir (cannot list): {temp_dir}")
        return
    if not entries:
        temp_dir.rmdir()
        print(f"Removed empty temp dir: {temp_dir}")
    else:
        print(f"Leaving non-empty temp dir: {temp_dir}")


def _promote_temp_to_final(
    root: Path,
    league: LeagueConfig,
    temp_dir: Path,
    *,
    dry_run: bool,
) -> tuple[bool, str]:
    ok, reason = validate_sofascore_output(temp_dir)
    if not ok:
        return False, reason

    final_dir = league_output_dir(root, league)
    base = sofascore_output_root(root)

    if dry_run:
        print(
            f"DRY RUN: would promote {temp_dir.name} → {final_dir.name} "
            f"(backup previous snapshot if present)"
        )
        return True, reason

    if final_dir.exists():
        backup_dir = base / f"_backup_{league.output_slug}_{utc_timestamp()}"
        shutil.move(str(final_dir), str(backup_dir))
        print(f"Backed up previous snapshot → {backup_dir}")

    shutil.move(str(temp_dir), str(final_dir))
    print(f"Promoted new snapshot → {final_dir}")
    return True, reason


def setup_docker(root: Path, *, skip_docker_up: bool, dry_run: bool) -> None:
    if not skip_docker_up:
        run_command(["docker", "compose", "up", "-d"], cwd=root, dry_run=dry_run)

    run_command(
        ["docker", "compose", "exec", "app", "python", "scripts/apply_migrations.py"],
        cwd=root,
        dry_run=dry_run,
    )
    run_command(
        ["docker", "compose", "exec", "app", "python", "scripts/seed_external_competitions.py"],
        cwd=root,
        dry_run=dry_run,
    )


def scrape_league(
    root: Path,
    league: LeagueConfig,
    *,
    no_headless: bool,
    dry_run: bool,
    keep_failed_temp: bool,
) -> tuple[bool, str]:
    """
    Scrape en carpeta temporal; solo reemplaza snapshot válido si la salida pasa validación.
    """
    scraper_dir = root / "web_scraping_sofascore"
    base = sofascore_output_root(root)
    base.mkdir(parents=True, exist_ok=True)

    ts = utc_timestamp()
    temp_name = f"_tmp_{league.output_slug}_{ts}"
    temp_dir = base / temp_name
    temp_rel = Path("sofascore_output") / temp_name
    final_dir = league_output_dir(root, league)

    print(f"Scrape target (temp): {temp_dir}")
    if final_dir.is_dir():
        ok_prev, _ = validate_sofascore_output(final_dir)
        if ok_prev:
            print(f"Previous valid snapshot kept until promotion: {final_dir}")
        else:
            print(f"Previous output exists but incomplete; will not overwrite: {final_dir}")

    if dry_run:
        cmd = [
            "python3",
            "sofascore_scraper.py",
            "--tournament-id",
            str(league.tournament_id),
            "--season-id",
            str(league.season_id),
            "--output-dir",
            str(temp_rel),
        ]
        if no_headless:
            cmd.append("--no-headless")
        run_command(cmd, cwd=scraper_dir, dry_run=True)
        _promote_temp_to_final(root, league, temp_dir, dry_run=True)
        return True, "dry-run"

    temp_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "python3",
        "sofascore_scraper.py",
        "--tournament-id",
        str(league.tournament_id),
        "--season-id",
        str(league.season_id),
        "--output-dir",
        str(temp_rel),
    ]
    if no_headless:
        cmd.append("--no-headless")

    try:
        run_command(cmd, cwd=scraper_dir, dry_run=False)
    except subprocess.CalledProcessError as exc:
        print(
            "Scrape failed or incomplete; keeping previous snapshot untouched.",
            file=sys.stderr,
        )
        print(f"Reason: scraper exited with code {exc.returncode}", file=sys.stderr)
        print(f"Temp dir: {temp_dir}", file=sys.stderr)
        _cleanup_failed_temp(temp_dir, keep_failed_temp=keep_failed_temp)
        return False, f"scraper exit code {exc.returncode}"

    ok, reason = validate_sofascore_output(temp_dir)
    if not ok:
        print(
            "Scrape failed or incomplete; keeping previous snapshot untouched.",
            file=sys.stderr,
        )
        print(f"Reason: {reason}", file=sys.stderr)
        print(f"Temp dir: {temp_dir}", file=sys.stderr)
        _cleanup_failed_temp(temp_dir, keep_failed_temp=keep_failed_temp)
        return False, reason

    promoted, promote_reason = _promote_temp_to_final(
        root, league, temp_dir, dry_run=False
    )
    if not promoted:
        print(
            "Scrape failed or incomplete; keeping previous snapshot untouched.",
            file=sys.stderr,
        )
        print(f"Reason: {promote_reason}", file=sys.stderr)
        print(f"Temp dir: {temp_dir}", file=sys.stderr)
        _cleanup_failed_temp(temp_dir, keep_failed_temp=keep_failed_temp)
        return False, promote_reason

    return True, "ok"


def stage_league(
    root: Path,
    league: LeagueConfig,
    season: str,
    *,
    dry_run: bool,
) -> Path | None:
    source = root / "web_scraping_sofascore" / "sofascore_output" / league.output_slug
    cmd = [
        sys.executable,
        str(root / "scripts" / "stage_sofascore_output.py"),
        "--source-dir",
        str(source),
        "--country",
        league.country,
        "--division",
        league.division,
        "--season",
        season,
        "--competition",
        league.competition,
        "--tournament-id",
        str(league.tournament_id),
        "--season-id",
        str(league.season_id),
    ]
    if dry_run:
        run_command(cmd, cwd=root, dry_run=True)
        return root / "data" / "staging" / "sofascore" / league.country / league.division / season / "DRY_RUN"

    proc = subprocess.run(
        cmd,
        cwd=root,
        capture_output=True,
        text=True,
    )
    print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd)

    match = STAGED_DIR_RE.search(proc.stdout)
    if match:
        return Path(match.group(1).strip())

    return find_latest_staging_dir(root, league, season)


def find_latest_staging_dir(root: Path, league: LeagueConfig, season: str) -> Path | None:
    base = root / "data" / "staging" / "sofascore" / league.country / league.division / season
    if not base.is_dir():
        return None
    candidates = [p for p in base.iterdir() if p.is_dir()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.name)


def import_league(
    root: Path,
    league: LeagueConfig,
    season: str,
    staging_dir: Path,
    *,
    use_replace: bool,
    dry_run: bool,
) -> None:
    csv_path = (
        root
        / "data"
        / "staging"
        / "sofascore"
        / league.country
        / league.division
        / season
        / staging_dir.name
        / "player_stats.csv"
    )
    import_mode = os.environ.get("SOFASCORE_IMPORT_MODE", "docker").strip().lower()

    if import_mode == "direct":
        cmd = [
            sys.executable,
            "-m",
            "scouting.ingestion.import_sofascore_player_stats_csv",
            str(csv_path),
            "--country",
            league.country,
            "--division",
            league.division,
            "--season",
            season,
            "--competition",
            league.competition,
        ]
        if use_replace:
            cmd.append("--replace")
        run_command(cmd, cwd=root, dry_run=dry_run)
        return

    csv_in_container = (
        f"/app/data/staging/sofascore/{league.country}/{league.division}/"
        f"{season}/{staging_dir.name}/player_stats.csv"
    )
    cmd = [
        "docker",
        "compose",
        "exec",
        "app",
        "python",
        "-m",
        "scouting.ingestion.import_sofascore_player_stats_csv",
        csv_in_container,
        "--country",
        league.country,
        "--division",
        league.division,
        "--season",
        season,
        "--competition",
        league.competition,
    ]
    if use_replace:
        cmd.append("--replace")

    run_command(cmd, cwd=root, dry_run=dry_run)


def print_summary(results: list[LeagueResult]) -> None:
    print("\n" + "=" * 72)
    print("RESUMEN PIPELINE SOFASCORE")
    print("=" * 72)
    headers = ("liga", "scrape", "staging", "import", "notas")
    rows = []
    for r in results:
        notes = r.error[:40] + "…" if r.error and len(r.error) > 40 else r.error
        staging = r.staging_path or "-"
        if len(staging) > 48:
            staging = "…" + staging[-45:]
        rows.append(
            (
                r.league.output_slug,
                r.scrape,
                staging,
                r.import_status,
                notes,
            )
        )

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    def fmt_row(cells: tuple[str, ...]) -> str:
        return "  ".join(str(c).ljust(widths[i]) for i, c in enumerate(cells))

    print(fmt_row(headers))
    print("-" * (sum(widths) + 2 * (len(widths) - 1)))
    for row in rows:
        print(fmt_row(row))
    print("=" * 72)


def _require_valid_output(root: Path, league: LeagueConfig, *, dry_run: bool) -> Path:
    out = league_output_dir(root, league)
    if dry_run:
        return out
    ok, reason = validate_sofascore_output(out)
    if not ok:
        raise FileNotFoundError(f"Invalid Sofascore output at {out}: {reason}")
    return out


def process_league(
    root: Path,
    league: LeagueConfig,
    season: str,
    *,
    skip_scrape: bool,
    reaggregate_from_checkpoint: bool,
    reaggregate_backup: bool,
    skip_import: bool,
    no_headless: bool,
    use_replace: bool,
    dry_run: bool,
    keep_failed_temp: bool,
) -> LeagueResult:
    result = LeagueResult(league=league)

    if skip_scrape and reaggregate_from_checkpoint:
        ok, reason = reaggregate_league_from_checkpoint(
            root,
            league,
            dry_run=dry_run,
            backup=reaggregate_backup,
        )
        if not ok:
            raise RuntimeError(reason)
        result.scrape = "reaggregated"
        _require_valid_output(root, league, dry_run=dry_run)
    elif skip_scrape:
        result.scrape = "skipped"
        _require_valid_output(root, league, dry_run=dry_run)
    else:
        scrape_ok, scrape_reason = scrape_league(
            root,
            league,
            no_headless=no_headless,
            dry_run=dry_run,
            keep_failed_temp=keep_failed_temp,
        )
        if not scrape_ok:
            raise RuntimeError(scrape_reason)
        result.scrape = "ok"

    if not dry_run:
        _require_valid_output(root, league, dry_run=False)

    staging_dir = stage_league(root, league, season, dry_run=dry_run)
    if staging_dir:
        result.staging_path = str(staging_dir)

    if skip_import:
        result.import_status = "skipped"
    else:
        if staging_dir is None:
            raise RuntimeError("No staging directory for import")
        import_league(
            root,
            league,
            season,
            staging_dir,
            use_replace=use_replace,
            dry_run=dry_run,
        )
        result.import_status = "ok"

    return result


def process_league_safe(
    root: Path,
    league: LeagueConfig,
    season: str,
    *,
    skip_scrape: bool,
    reaggregate_from_checkpoint: bool,
    reaggregate_backup: bool,
    skip_import: bool,
    no_headless: bool,
    use_replace: bool,
    dry_run: bool,
    keep_failed_temp: bool,
) -> LeagueResult:
    result = LeagueResult(league=league)
    phase = "scrape"
    try:
        if skip_scrape and reaggregate_from_checkpoint:
            ok, reason = reaggregate_league_from_checkpoint(
                root,
                league,
                dry_run=dry_run,
                backup=reaggregate_backup,
            )
            if not ok:
                result.scrape = "error"
                result.error = reason
                return result
            result.scrape = "reaggregated"
            _require_valid_output(root, league, dry_run=dry_run)
        elif skip_scrape:
            result.scrape = "skipped"
            _require_valid_output(root, league, dry_run=dry_run)
        else:
            scrape_ok, scrape_reason = scrape_league(
                root,
                league,
                no_headless=no_headless,
                dry_run=dry_run,
                keep_failed_temp=keep_failed_temp,
            )
            if not scrape_ok:
                result.scrape = "error"
                result.error = scrape_reason
                return result
            result.scrape = "ok"

        if not dry_run:
            _require_valid_output(root, league, dry_run=False)

        phase = "staging"
        staging_dir = stage_league(root, league, season, dry_run=dry_run)
        if staging_dir:
            result.staging_path = str(staging_dir)

        if skip_import:
            result.import_status = "skipped"
        else:
            phase = "import"
            if staging_dir is None:
                raise RuntimeError("No staging directory for import")
            import_league(
                root,
                league,
                season,
                staging_dir,
                use_replace=use_replace,
                dry_run=dry_run,
            )
            result.import_status = "ok"

    except (subprocess.CalledProcessError, OSError, RuntimeError, FileNotFoundError) as exc:
        result.error = str(exc)
        if phase == "scrape" and not skip_scrape:
            result.scrape = "error"
        elif phase == "import" and not skip_import:
            result.import_status = "error"
        elif phase == "staging":
            if not skip_scrape:
                result.scrape = result.scrape or "ok"
            result.import_status = "error" if not skip_import else "skipped"

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full Sofascore scrape → stage → import pipeline.")
    parser.add_argument("--season", default="2025", help="Season label for staging/import")
    parser.add_argument(
        "--only",
        nargs="+",
        default=None,
        metavar="OUTPUT_SLUG",
        help="Run only these leagues (e.g. cl_primera_2025)",
    )
    parser.add_argument(
        "--skip-scrape",
        action="store_true",
        help=(
            "Reuse existing scraper output (NO recupera equipos si los CSV viejos "
            "no tienen team_name; re-scrape obligatorio)"
        ),
    )
    parser.add_argument(
        "--reaggregate-from-checkpoint",
        action="store_true",
        help=(
            "Con --skip-scrape: re-agrega player_stats.csv/json desde checkpoint_raw.json "
            "(aliases actuales, sin llamar a Sofascore) y luego stage + import"
        ),
    )
    parser.add_argument(
        "--reaggregate-backup",
        action="store_true",
        help="Con --reaggregate-from-checkpoint: backup de player_stats antes de sobrescribir",
    )
    parser.add_argument("--skip-import", action="store_true", help="Scrape and stage only")
    parser.add_argument("--skip-docker-up", action="store_true", help="Do not run docker compose up -d")
    parser.add_argument("--no-headless", action="store_true", help="Pass --no-headless to scraper")
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue with next league if one fails",
    )
    parser.add_argument(
        "--no-replace",
        action="store_true",
        help="Do not pass --replace to importer (default is replace)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    parser.add_argument(
        "--keep-failed-temp",
        action="store_true",
        help="Keep _tmp_* dirs after failed scrapes (for inspection)",
    )
    args = parser.parse_args()

    if args.reaggregate_from_checkpoint and not args.skip_scrape:
        print(
            "ERROR: --reaggregate-from-checkpoint requiere --skip-scrape",
            file=sys.stderr,
        )
        sys.exit(1)

    root = project_root()
    leagues = filter_leagues(args.only)
    use_replace = not args.no_replace

    print(f"Project root: {root}")
    print(f"Leagues: {', '.join(lg.output_slug for lg in leagues)}")
    if args.skip_scrape and args.reaggregate_from_checkpoint:
        print(
            "\nModo re-agregación: checkpoint_raw.json → player_stats (aliases actuales) "
            "→ stage → import. Sin scrape Sofascore.\n"
        )
    elif args.skip_scrape:
        print(
            "\nAVISO: --skip-scrape activo. Si los CSV en sofascore_output/ no tienen "
            "team_name, los equipos seguirán vacíos en la BD. Para equipos correctos, "
            "ejecuta sin --skip-scrape (re-scrapea en carpeta temporal y promueve solo si OK).\n"
        )
    else:
        print(
            "\nPipeline seguro: no borra snapshots válidos si Sofascore falla. "
            "Scrape en _tmp_<liga>_<timestamp>; promoción solo si player_stats.csv es válido.\n"
        )
    if args.dry_run:
        print("DRY RUN — no commands will be executed")

    try:
        setup_docker(
            root,
            skip_docker_up=args.skip_docker_up,
            dry_run=args.dry_run,
        )
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: Docker setup failed: {exc}", file=sys.stderr)
        sys.exit(1)

    results: list[LeagueResult] = []
    failures = 0

    for league in leagues:
        season = league_staging_season(league, args.season)
        print("\n" + "=" * 72)
        print(f"LIGA: {league.output_slug} ({league.competition}) · temporada {season}")
        print("=" * 72)

        if args.continue_on_error:
            result = process_league_safe(
                root,
                league,
                season,
                skip_scrape=args.skip_scrape,
                reaggregate_from_checkpoint=args.reaggregate_from_checkpoint,
                reaggregate_backup=args.reaggregate_backup,
                skip_import=args.skip_import,
                no_headless=args.no_headless,
                use_replace=use_replace,
                dry_run=args.dry_run,
                keep_failed_temp=args.keep_failed_temp,
            )
            if result.error:
                failures += 1
                print(f"ERROR ({league.output_slug}): {result.error}", file=sys.stderr)
            results.append(result)
        else:
            try:
                result = process_league(
                    root,
                    league,
                    season,
                    skip_scrape=args.skip_scrape,
                    reaggregate_from_checkpoint=args.reaggregate_from_checkpoint,
                    reaggregate_backup=args.reaggregate_backup,
                    skip_import=args.skip_import,
                    no_headless=args.no_headless,
                    use_replace=use_replace,
                    dry_run=args.dry_run,
                    keep_failed_temp=args.keep_failed_temp,
                )
            except (subprocess.CalledProcessError, OSError, RuntimeError, FileNotFoundError) as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                sys.exit(1)
            results.append(result)

    print_summary(results)

    if failures:
        sys.exit(2)


if __name__ == "__main__":
    main()
