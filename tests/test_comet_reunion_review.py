"""Club decisions cannot turn incomplete minutes or another rule into certainty."""
import numpy as np
import pytest

from scouting.comet.rules import Rules, STATUS_PENDING
from tests.test_comet_reunion_pablo import cards_dataset, yellow_alerts
from scouting.comet.pipeline import compute_all


def test_yellow_alert_retains_card_count_without_inventing_principal_category():
    raw = cards_dataset()
    raw['sheet']['minutesplayed'] = raw['sheet']['minutesplayed'].astype(float)
    raw['sheet'].loc[raw['sheet']['personid'] == 51, 'minutesplayed'] = np.nan
    found = yellow_alerts(raw)
    assert found.loc['51', 'value'] == 4
    assert found.loc['51', 'category'] == 'Sin dato'


@pytest.mark.parametrize('value', ['competicion', 'temporada'])
def test_club_decision_does_not_confirm_another_stored_card_cycle(value):
    rules = Rules({'card_cycle': {'value': value}})
    assert rules.value('card_cycle') == value
    assert not rules.confirmed('card_cycle')
    assert rules.status('card_cycle') == STATUS_PENDING


def test_admin_can_explicitly_confirm_or_unconfirm_a_stored_cycle():
    assert Rules({'card_cycle': {'value': 'competicion', 'confirmed': True}}).confirmed('card_cycle')
    assert not Rules({'card_cycle': {'value': 'mixto', 'confirmed': False}}).confirmed('card_cycle')
    assert Rules({'card_cycle': {'value': 'mixto'}}).confirmed('card_cycle')


def test_extra_data_category_does_not_replace_an_official_age_section():
    raw = cards_dataset()
    raw['players'].loc[raw['players']['personid'] == 51, 'dateofbirth'] = '2007-01-01'
    raw['matches'].loc[raw['matches']['matchid'] == 42, 'category'] = 'U-19'
    computed = compute_all(raw)
    mine = computed.ds.facts[computed.ds.facts['personid'] == '51']
    assert set(mine['age_category']) == {'U-20'}
    assert 'U-19' in computed.ds.ladder, 'keep the actual data category for display and comparisons'
