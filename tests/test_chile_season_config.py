from scripts.run_all_sofascore_pipeline import LEAGUES
from scripts.seed_external_competitions import SOFASCORE_COMPETITIONS
from scouting.services.sofascore_incremental_runner import HISTORICAL_IMPORT_OPTIONS


def test_chile_season_ids_match_verified_browser_selector():
    leagues = {league.output_slug:league for league in LEAGUES}
    assert leagues['cl_primera_2025'].season_id == 71131
    assert leagues['cl_primera_2024'].season_id == 57883
    assert leagues['cl_primera_2024'].season_label == '2024'
    assert HISTORICAL_IMPORT_OPTIONS[0]['season_id'] == '57883'
    assert {row[4] for row in SOFASCORE_COMPETITIONS if row[0:2] == ('cl','primera')} == {71131,57883}
