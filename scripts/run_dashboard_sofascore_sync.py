#!/usr/bin/env python3
"""
Orquestador de sincronización Sofascore lanzado en segundo plano desde la UI.

Ejecuta los pasos del plan (histórica → activa, o incremental) de forma secuencial,
actualiza el estado en data/runtime/sofascore_update_ui_state.json y libera el lock.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from scouting.services import sofascore_incremental_runner as runner  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=["auto", "incremental", "resync", "historical"],
        default="auto",
        help="auto = plan según datos reales presentes",
    )
    parser.add_argument("--league-slug", default="cl_primera_2024")
    parser.add_argument("--season", default="")
    parser.add_argument(
        "--process-existing",
        action="store_true",
        help="Para histórico: usar checkpoint local si existe",
    )
    args = parser.parse_args()

    if args.mode == "historical":
        season = args.season or runner.get_active_season()
        # Prefer historical season from config when importing Chile 2024
        from scouting.config.sofascore_seasons import get_historical_season

        season = args.season.strip() or get_historical_season()
        result = runner.run_historical_import_for_ui(
            league_slug=args.league_slug,
            season=season,
            process_existing=args.process_existing,
        )
    elif args.mode == "resync":
        result = runner.run_resync_season_for_ui()
    elif args.mode == "incremental":
        result = runner.run_incremental_all_for_ui()
    else:
        result = runner.run_dashboard_sync_for_ui()

    print(f"RESULT status={result.status} ok={result.ok} headline={result.headline}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
