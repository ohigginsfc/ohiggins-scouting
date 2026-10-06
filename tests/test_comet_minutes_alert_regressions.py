"""Alertas calculables a mano: minutos desconocidos no certifican una categoría ni una suma."""
import numpy as np
import pandas as pd
import pytest

from scouting.comet import alerts
from scouting.comet.pipeline import compute_all
from tests import comet_tiny


def promotion_history():
    """P2 juega U-14 en 2024/2025 y U-14/U-15 en 2026."""
    raw = comet_tiny.build()
    raw['sheet'] = raw['sheet'].astype({'played': object, 'minutesplayed': float})
    for year in (2024, 2025):
        match = raw['matches'].loc[raw['matches']['matchid'] == 4].copy()
        match['matchid'] = year
        match['competition_id'] = year
        match['season'] = str(year)
        match['matchdate'] = pd.Timestamp(f'{year}-03-08 11:00')
        sheet = raw['sheet'].loc[(raw['sheet']['matchid'] == 4) & (raw['sheet']['personid'] == 2)].copy()
        sheet['matchid'] = year
        sheet['competition_id'] = year
        raw['matches'] = pd.concat([raw['matches'], match], ignore_index=True)
        raw['sheet'] = pd.concat([raw['sheet'], sheet], ignore_index=True)
    return raw


def player_alerts(computed, key):
    found = alerts.evaluate_alerts(computed.ds, computed.cat, 2026)
    return found[(found['personid'] == '2') & (found['alert_key'] == key)]


def test_unknown_minutes_do_not_pick_another_category_or_invent_no_promotion():
    raw = promotion_history()
    mask = (raw['sheet']['matchid'] == 2) & (raw['sheet']['personid'] == 2)
    raw['sheet'].loc[mask, 'minutesplayed'] = np.nan
    computed = compute_all(raw)
    principal = computed.principal.query("personid == '2' and season_year == 2026")
    assert principal.empty, 'U-15 puede tener más minutos que U-14: la categoría principal no se conoce'
    assert player_alerts(computed, 'no_promotion').empty, 'no afirmar tres temporadas en U-14'
    assert set(computed.principal.query("personid == '2'")['season_year']) == {2024, 2025}
    assert not computed.principal.query("personid == '1' and season_year == 2026").empty


def test_unknown_historical_category_breaks_the_promotion_streak():
    raw = promotion_history()
    raw['sheet'] = raw['sheet'].loc[~((raw['sheet']['personid'] == 2) & (raw['sheet']['competition_id'] == 100))].copy()
    raw['sheet'].loc[raw['sheet']['matchid'] == 2025, 'minutesplayed'] = np.nan
    computed = compute_all(raw)
    assert computed.principal.query("personid == '2' and season_year == 2025").empty
    assert player_alerts(computed, 'no_promotion').empty, 'una temporada desconocida interrumpe la racha'


def test_complete_history_still_detects_three_seasons_without_promotion():
    raw = promotion_history()
    raw['sheet'] = raw['sheet'].loc[~((raw['sheet']['personid'] == 2) & (raw['sheet']['competition_id'] == 100))].copy()
    computed = compute_all(raw)
    found = player_alerts(computed, 'no_promotion')
    assert len(found) == 1 and found.iloc[0]['value'] == 3


@pytest.mark.parametrize('played,minutes', [(False, 80.0), (None, np.nan)])
def test_playing_up_counts_uncertain_rows_before_filtering_participation(played, minutes):
    raw = comet_tiny.build()
    raw['sheet'] = raw['sheet'].astype({'played': object, 'minutesplayed': float})
    mask = (raw['sheet']['matchid'] == 2) & (raw['sheet']['personid'] == 2)
    raw['sheet'].loc[mask, 'played'] = played
    raw['sheet'].loc[mask, 'minutesplayed'] = minutes
    computed = compute_all(raw)
    found = player_alerts(computed, 'playing_up')
    assert len(found) == 1, 'hay participación confirmada en otros partidos de U-15'
    assert pd.isna(found.iloc[0]['value'])
    assert 'minutos incompletos' in found.iloc[0]['detail']
    assert '110 min' not in found.iloc[0]['detail']


def test_unknown_minutes_in_own_category_do_not_erase_known_minutes_playing_up():
    raw = comet_tiny.build()
    raw['sheet']['minutesplayed'] = raw['sheet']['minutesplayed'].astype(float)
    raw['sheet'].loc[(raw['sheet']['matchid'] == 4) & (raw['sheet']['personid'] == 2), 'minutesplayed'] = np.nan
    found = player_alerts(compute_all(raw), 'playing_up')
    assert len(found) == 1 and found.iloc[0]['value'] == 190
