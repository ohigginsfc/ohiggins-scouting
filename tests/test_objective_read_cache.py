from types import SimpleNamespace
from unittest.mock import MagicMock, Mock
import time

import pytest
from scouting import objective_cache as cache
from scouting.portal import accounts, security
from scouting.repositories import metrics_repository as metrics

USER = {'id': 'synthetic-scout', 'role': 'scout', 'active': True}


def connection(**changes):
    params = dict(host='127.0.0.1', port='5432', dbname='scouting_test',
                  user='scouting_test', options='-c search_path=scouting') | changes
    conn = MagicMock()
    conn.info = SimpleNamespace(get_parameters=lambda: params)
    return conn


@pytest.fixture(autouse=True)
def clean_cache():
    cache._reader().clear()
    yield
    cache._reader().clear()
    cache._reader.cache_clear()


def test_twenty_cohort_reads_run_one_query_and_worker_reads_are_fresh(monkeypatch):
    conn = connection()
    conn.cursor.return_value.__enter__.return_value.fetchall.return_value = [
        {'player_id': 1, 'raw_payload': {'sofascore_position': 'D'}},
        {'player_id': 2, 'raw_payload': {'sofascore_position': 'D'}},
        {'player_id': 3, 'raw_payload': {'sofascore_position': 'D'}},
    ]
    monkeypatch.setattr(metrics, '_cohort_origin_sql', lambda *a, **kw: '')
    args = (conn, 1, '2026', 'Synthetic League', 'Defensa', 'same_competition')
    with security.session_scope({}, verified_user=USER), cache.objective_read_scope():
        assert [metrics.count_objective_comparison_cohort(*args) for _ in range(20)] == [2] * 20
    assert conn.cursor.call_count == 1
    # Importers/CLI and tests outside portal read scope do not reuse UI results.
    metrics.count_objective_comparison_cohort(*args)
    metrics.count_objective_comparison_cohort(*args)
    assert conn.cursor.call_count == 3


def test_warm_cache_still_checks_the_current_session(monkeypatch):
    read = Mock(return_value=[{'value': 7}])
    @cache.cached_objective_read
    def query(conn, season):
        return read(season)
    resolve = Mock(return_value=USER)
    monkeypatch.setattr(accounts, 'resolve_session', resolve)
    with security.session_scope({'synthetic': True}), cache.objective_read_scope():
        query(connection(), '2026')
        query(connection(), '2026')
        resolve.return_value = None
        with pytest.raises(PermissionError):
            query(connection(), '2026')
    assert read.call_count == 1 and resolve.call_count == 3


@pytest.mark.parametrize('change', [dict(host='localhost'), dict(dbname='other_test'),
    dict(user='other_role'), dict(options='-c search_path=other_schema')])
def test_connection_scope_never_shares_results(change):
    read = Mock(return_value=[{'value': 7}])
    @cache.cached_objective_read
    def query(conn, **filters):
        return read(filters)
    with security.session_scope({}, verified_user=USER), cache.objective_read_scope():
        query(connection(), season='2026', competition='A', source_type='sofascore')
        query(connection(**change), season='2026', competition='A', source_type='sofascore')
    assert read.call_count == 2


def test_filters_and_operations_are_part_of_key_and_results_are_copies():
    read = Mock(return_value=[{'value': 7}])
    @cache.cached_objective_read
    def query(conn, **filters):
        return read(filters)
    @cache.cached_objective_read
    def different_query(conn, **filters):
        return [{'value': 99}]
    with security.session_scope({}, verified_user=USER), cache.objective_read_scope():
        conn = connection()
        original = query(conn, season='2026', competition='A', source_type='sofascore')
        original[0]['value'] = 0
        assert query(conn, season='2026', competition='A', source_type='sofascore') == [{'value': 7}]
        for kwargs in [dict(season='2025', competition='A', source_type='sofascore'),
                       dict(season='2026', competition='B', source_type='sofascore'),
                       dict(season='2026', competition='A', source_type='demo'),
                       dict(season='2026', cohort_seasons=['2025', '2026']),
                       dict(season='2026', peer_competitions=['A', 'B'])]:
            query(conn, **kwargs)
        assert different_query(conn, season='2026', competition='A', source_type='sofascore') == [{'value': 99}]
    assert read.call_count == 6


def test_expiry_clear_and_failures_do_not_preserve_stale_results(monkeypatch):
    monkeypatch.setattr(cache, 'TTL_SECONDS', 0.03)
    cache._reader.cache_clear()
    read = Mock(side_effect=[RuntimeError('synthetic'), 1, 2, 3])
    @cache.cached_objective_read
    def query(conn):
        return read()
    with security.session_scope({}, verified_user=USER), cache.objective_read_scope():
        conn = connection()
        with pytest.raises(RuntimeError):
            query(conn)
        assert query(conn) == query(conn) == 1
        time.sleep(0.05)
        assert query(conn) == 2
        cache._reader().clear()
        assert query(conn) == 3
