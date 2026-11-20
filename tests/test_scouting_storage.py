import pytest

from scouting.storage_measure import compare, measure
from tests.test_atomic_sofascore_import import db  # noqa: F401


def test_comparison_reports_growth_in_bytes_including_indexes():
    before = dict(database_bytes=1000, schema_bytes=600,
                  tables=[dict(table_name='objective_metrics', total_bytes=400)])
    after = dict(database_bytes=1300, schema_bytes=850,
                 tables=[dict(table_name='objective_metrics', total_bytes=650)])
    result = compare(before, after)
    assert result['database_delta_bytes'] == 300 and result['schema_delta_bytes'] == 250
    assert result['database_growth_percent'] == 30
    assert result['table_delta_bytes']['objective_metrics'] == 250


def test_negative_delta_is_not_hidden():
    before = dict(database_bytes=1000, schema_bytes=600, tables=[])
    after = dict(database_bytes=900, schema_bytes=550, tables=[])
    assert compare(before, after)['database_delta_bytes'] == -100


def test_invalid_baseline_is_rejected():
    with pytest.raises((KeyError, ValueError)):
        compare({}, dict(database_bytes=1000, schema_bytes=600, tables=[]))


def test_measurement_uses_a_read_only_transaction_and_only_returns_aggregates(db):
    with db() as conn:
        result = measure(conn)
        assert conn.execute('SHOW transaction_read_only').fetchone()[0] == 'on'
        assert result['database_bytes'] > 0
        assert result['schema_bytes'] == sum(t['total_bytes'] for t in result['tables'])
        assert {'objective_metrics', 'players'} <= {t['table_name'] for t in result['tables']}
        assert result['scopes'] == []
