from unittest.mock import MagicMock, patch
import pytest
from scouting.services import sofascore_incremental_runner as runner
from scouting.repositories import metrics_repository as metrics
from tests.test_sofascore_pipeline_post_download import _load_incremental


def valid_summary():
    return {'ok': True, 'leagues': [{'slug': 'cl_primera_2025', 'errors': 0, 'pending_total': 0, 'total_calendar': 10}]}


@pytest.mark.parametrize('payload', [None, [], {}, {'ok': True, 'leagues': []},
    {'ok': False, 'leagues': []}, {'ok': True, 'leagues': [{}]}])
def test_missing_or_invalid_summary_is_not_success(payload):
    assert runner._summary_error(payload)


def test_summary_with_league_errors_is_not_success():
    payload = valid_summary()
    payload['leagues'][0]['errors'] = 1
    assert runner._summary_error(payload)
    assert runner._summary_error(valid_summary()) is None


def test_downloaded_pending_import_is_selected_for_update():
    inc = _load_incremental()
    result = inc.LeagueIncrementalResult(league=inc.LEAGUES[0], pending_import=3)
    payload = {'leagues': [inc.result_to_json(result)]}
    assert payload['leagues'][0]['pending_total'] == 3
    assert len(runner._leagues_with_pending(payload)) == 1


def percentile_rows(peer_values, metric='goals_per90', target=3, seasons=None):
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    cur.fetchall.side_effect = [
        [{'metric_name': metric, 'metric_value': target, 'metric_unit': 'per90'}],
        [dict(player_id=pid, player_name=str(pid), player_position='MF', raw_payload={},
              metric_name=metric, metric_value=value, metric_unit='per90', season=season,
              competition='Synthetic') for pid, season, value in peer_values],
    ]
    with patch.object(metrics, 'count_objective_comparison_cohort', return_value=10), \
         patch.object(metrics, '_cohort_origin_sql', return_value=''), \
         patch.object(metrics, '_objective_position_from_row', return_value='MF'):
        return metrics.get_player_vs_position_percentiles(conn, player_id=1, season='2025',
            competition='Synthetic', position_group='MF', metric_names=[metric], cohort_seasons=seasons)[0]


@pytest.mark.parametrize('metric,target,rank', [('goals_per90',3,1), ('goals_per90',0,3),
    ('foulsCommited_per90',3,3), ('foulsCommited_per90',0,1), ('goals_per90',2,1)])
def test_rank_direction_and_denominator(metric, target, rank):
    row = percentile_rows([(2,'2025',1),(3,'2025',2)],metric,target)[0]
    assert row['cohort_rank'] == rank
    assert row['rank_population'] == 3
    assert row['players_count'] == 2


def test_duplicate_rows_do_not_inflate_cohort():
    row = percentile_rows([(2,'2025',1),(2,'2025',1),(3,'2025',2)])[0]
    assert row['cohort_observations'] == 2
    assert row['rank_population'] == 3


def test_multiple_seasons_have_consistent_observation_rank():
    row = percentile_rows([(2,'2024',1),(2,'2025',2),(3,'2025',4)], seasons=['2024','2025'])[0]
    assert row['cohort_rank'] == 2
    assert row['rank_population'] == 4
    assert row['players_count'] == 2


def test_conflicting_duplicate_is_not_arbitrarily_selected():
    assert percentile_rows([(2,'2025',1),(2,'2025',9),(3,'2025',2)]) == []


def test_one_peer_multiple_seasons_does_not_meet_minimum_peers():
    assert percentile_rows([(2,'2024',1),(2,'2025',2)], seasons=['2024','2025']) == []



@pytest.mark.parametrize('empty', [False, True])
def test_dry_run_does_not_bootstrap_processed_events(tmp_path, empty):
    inc = _load_incremental()
    conn = MagicMock()
    driver = MagicMock()
    stats = dict(total_calendar=1, already_processed=0, new_events=1, updated_events=0,
                 pending_events=0, skipped_events=0, already_downloaded=0)
    with patch.object(inc, 'scraper_config_for_league', return_value=MagicMock()), \
         patch.object(inc, 'build_driver', return_value=driver), \
         patch.object(inc, 'init_fetch_context'), \
         patch.object(inc, 'get_all_events', return_value=[] if empty else [{'id':1}]), \
         patch.object(inc, 'get_connection', return_value=conn), \
         patch.object(inc, 'bootstrap_ingestion_if_needed') as bootstrap, \
         patch.object(inc, 'classify_events', return_value=([],stats)), \
         patch.object(inc.ingestion_repo, 'list_events_for_scope', return_value=[]):
        result = inc.process_league_incremental(tmp_path, inc.LEAGUES[0], '2025', dry_run=True,
            since=None, force_event_ids=None, no_headless=False, skip_import=False, use_replace=True)
    bootstrap.assert_not_called()
    driver.quit.assert_called_once()
    assert result.errors == (1 if empty else 0)


def test_partial_calendar_fetch_failure_is_not_success(monkeypatch):
    import importlib.util
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / 'web_scraping_sofascore'
    monkeypatch.syspath_prepend(str(root))
    spec = importlib.util.spec_from_file_location('calendar_regression_scraper', root / 'sofascore_scraper.py')
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, mod)
    spec.loader.exec_module(mod)
    with patch.object(mod, 'fetch_json', side_effect=[{'events':[{'id':1}], 'hasNextPage':True}, None]), \
         patch.object(mod.time, 'sleep'):
        with pytest.raises(RuntimeError, match='page 1'):
            mod.get_all_events(None, 1, 1, delay_events=0)

from tests.test_atomic_sofascore_import import db


def test_rank_query_against_postgresql(db):
    with db() as conn:
        ids = []
        for name, value in [('target',3),('peer_a',1),('peer_b',2)]:
            pid = conn.execute("INSERT INTO players(full_name,normalized_name,position) VALUES (%s,%s,'MF') RETURNING id", (name,name)).fetchone()[0]
            ids.append(pid)
            conn.execute("""INSERT INTO objective_metrics(player_id,source_name,source_type,season,competition,metric_name,metric_value,metric_unit,raw_payload)
                VALUES (%s,'Sofascore','sofascore','2025','Synthetic','goals_per90',%s,'per90','{"sofascore_position":"M"}')""", (pid,value))
        rows, _ = metrics.get_player_vs_position_percentiles(conn, ids[0], '2025', 'Synthetic', 'Mediocampo', ['goals_per90'], source_type='sofascore')
        assert len(rows) == 1
        assert rows[0]['cohort_rank'] == 1
        assert rows[0]['rank_population'] == 3
