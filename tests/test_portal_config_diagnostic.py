from unittest.mock import MagicMock, Mock
from scripts.check_portal_config import REQUIRED, check_config
import requests


def environment():
    return {key: 'synthetic-private' for key in REQUIRED} | {'PORTAL_SUPABASE_URL': 'https://example.supabase.co'}


def test_missing_values_fail_without_network():
    get = Mock()
    results = check_config({}, get=get)
    assert not any(ok for _, ok, _ in results)
    get.assert_not_called()


def test_auth_and_db_failures_identify_stage_without_secrets():
    get = Mock(side_effect=[Mock(status_code=401), requests.ConnectionError('synthetic-private secret')])
    connect = Mock(side_effect=RuntimeError('synthetic-private database secret'))
    results = check_config(environment(), get=get, connect=connect)
    assert len([r for r in results if not r[1]]) == 5
    assert 'synthetic-private' not in repr(results)


def test_queries_are_read_only():
    connection = MagicMock()
    connect = Mock(return_value=connection)
    results = check_config(environment(), get=Mock(return_value=Mock(status_code=200)), connect=connect)
    assert all(ok for _, ok, _ in results)
    assert connect.call_count == 3
    queries = [call.args[0] for call in connection.__enter__.return_value.execute.call_args_list]
    assert queries.count('SET TRANSACTION READ ONLY') == 3
    assert not any('INSERT' in query or 'UPDATE' in query for query in queries)
