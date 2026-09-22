#!/usr/bin/env python3
"""Carga/actualiza las 6 competiciones Sofascore en external_competitions."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from scouting.db import get_connection
from scouting.repositories import external_competitions_repository

SOFASCORE_COMPETITIONS = (
    ("cl", "primera", "Primera División Chile", 11653, 71131),
    ("cl", "segunda", "Liga de Ascenso Chile", 1240, 89007),
    ("ar", "primera", "Liga Profesional Argentina", 155, 87913),
    ("ar", "segunda", "Primera Nacional Argentina", 703, 87940),
    ("uy", "primera", "Liga AUF Uruguay", 278, 89288),
    ("uy", "segunda", "Segunda División Uruguay", 1908, 91195),
    # Histórica: temporada natural 2024, verificada en el selector de Sofascore.
    ("cl", "primera", "Primera División Chile", 11653, 57883),
)


def main() -> None:
    with get_connection() as conn:
        for country, division, competition, tournament_id, season_id in SOFASCORE_COMPETITIONS:
            external_competitions_repository.upsert_external_competition(
                conn,
                provider="sofascore",
                country=country,
                division=division,
                competition=competition,
                tournament_id=tournament_id,
                season_id=season_id,
                is_active=True,
            )
            print(f"  {country}/{division}: {competition} ({tournament_id}/{season_id})")
    print(f"\nUpserted {len(SOFASCORE_COMPETITIONS)} competitions.")


if __name__ == "__main__":
    main()
