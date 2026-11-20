"""Competition isolation: adding Primera B must preserve existing Primera checkpoints and publications."""
from unittest.mock import MagicMock

import pytest

from scouting import manual_sync as manual
from scouting.sofascore_leagues import DEFAULT_LEAGUE, LEAGUES
from scouting import sync_scheduler
from datetime import datetime, timezone
import pandas as pd
from tests.test_manual_sync import candidate, event, fake_players  # noqa: F401

B = LEAGUES['cl_primera_b']


def b_event(eid=1):
    e = event(eid)
    e['season']['id'] = B.season_id
    e['tournament']['uniqueTournament']['id'] = B.tournament_id
    return e


def b_candidate():
    state = candidate([b_event()])
    state.update(season_id=B.season_id, tournament_id=B.tournament_id, league_key=B.key)
    return state


def test_catalog_identifies_separate_verified_leagues_and_folders():
    assert DEFAULT_LEAGUE.tournament_id == 11653 and DEFAULT_LEAGUE.season_id == 88493
    assert B.tournament_id == 1240 and B.season_id == 89007
    assert B.folder != DEFAULT_LEAGUE.folder and B.scope['division'] == 'primera_b'


def test_old_primera_checkpoint_remains_valid(fake_players):
    assert not manual.validate(candidate([event()])).empty


def test_primera_b_validates_only_in_its_own_scope(fake_players):
    state = b_candidate()
    assert not manual.validate(state, league=B).empty
    with pytest.raises(ValueError):
        manual.validate(state)
    with pytest.raises(ValueError):
        manual.validate(candidate([event()]), league=B)


def test_primera_b_checkpoint_must_not_omit_its_tournament_identity(fake_players):
    state = b_candidate()
    state.pop('tournament_id')
    with pytest.raises(ValueError, match='scope'):
        manual.validate(state, league=B)


def test_forged_league_key_is_rejected(fake_players):
    state = b_candidate()
    state['league_key'] = DEFAULT_LEAGUE.key
    with pytest.raises(ValueError, match='scope'):
        manual.validate(state, league=B)


def test_collect_uses_primera_b_url_and_persists_scope(tmp_path, fake_players):
    urls = []

    def fetch(url):
        urls.append(url)
        return {'events': [b_event()], 'hasNextPage': False}

    state, frame = manual.collect(tmp_path, fetch, league=B)
    assert urls == [manual.r.scraper.BASE_URL + '/unique-tournament/1240/season/89007/events/last/0']
    assert state['league_key'] == B.key and state['tournament_id'] == 1240
    assert not frame.empty


def test_primera_checkpoint_cannot_be_overwritten_with_primera_b(tmp_path, fake_players):
    old = candidate([event()])
    manual.save(tmp_path / 'candidate.json', old)
    with pytest.raises(ValueError):
        manual.collect(tmp_path, lambda _: pytest.fail('foreign cache must fail before HTTP'), league=B)
    assert manual.read(tmp_path / 'candidate.json') == old


def test_publication_guard_is_restricted_to_the_selected_competition():
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = [(1,)]
    conn.execute.return_value.fetchone.return_value = (None,)
    manual.guard_existing(conn, b_candidate(), league=B)
    assert all(call.args[1] == ('cl', 'primera_b', B.competition, '2026')
               for call in conn.execute.call_args_list)


def test_probe_rejects_first_division_response_when_primera_b_was_requested():
    with pytest.raises(ValueError):
        manual.probe(lambda _: {'events': [event()], 'hasNextPage': False}, league=B)


def test_primera_b_schedule_is_staggered_and_persisted_separately(tmp_path):
    now = datetime(2026, 11, 16, 10, tzinfo=timezone.utc)
    result = sync_scheduler.tick(tmp_path, now, lambda: pytest.fail('startup download'), league=B)
    assert result['league_key'] == B.key
    assert result['next_run_at'] == '2026-11-17T07:15:00+00:00'
    with pytest.raises(ValueError, match='scope'):
        sync_scheduler.tick(tmp_path, now, lambda: None)


def test_both_leagues_share_the_same_provider_lock():
    first = sync_scheduler.worker_command(DEFAULT_LEAGUE.folder)
    second = sync_scheduler.worker_command(B.folder, league=B)
    assert first[4] == second[4]
    assert ['--league', B.key] == second[second.index('--league'):second.index('--league') + 2]


def test_old_primera_scheduler_file_remains_compatible(tmp_path):
    manual.save(tmp_path / 'scheduler-state.json', dict(version=1, status='waiting', next_run_at='2099-01-01T00:00:00+00:00'))
    sync_scheduler.tick(tmp_path, datetime.now(timezone.utc), lambda: pytest.fail('early execution'))
    with pytest.raises(ValueError, match='scope'):
        sync_scheduler.tick(tmp_path, datetime.now(timezone.utc), lambda: None, league=B)


def test_basic_league_statistics_do_not_invent_advanced_zeros():
    from scouting.services.sofascore_import_service import convert_row_to_metrics
    entries = {1: [dict(player=dict(id=1, name='Synthetic player'), team=dict(id=1, name='Synthetic team'),
                       statistics=dict(minutesPlayed=90, goals=0, totalShots=1))]}
    row = pd.Series(manual.r.scraper.aggregate(entries, {})[0])
    metrics = convert_row_to_metrics(row, season=B.season, competition=B.competition)
    names = {metric['metric_name'] for metric in metrics}
    assert not names & {'avg_rating', 'totalPass_per90', 'expectedGoals_per90', 'goalAssist_per90'}
    goals = next(metric for metric in metrics if metric['metric_name'] == 'goals_per90')
    assert goals['metric_value'] == 0  # an explicit observed zero remains a true zero
