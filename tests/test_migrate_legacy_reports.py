"""Distinguish club reports from seeded demo records before any writes."""
from unittest.mock import MagicMock

import pytest

from scripts import migrate_legacy_reports as migration


def test_prepare_excludes_seeded_reports_and_their_ratings(monkeypatch):
    source, target = object(), MagicMock()
    source_rows = {
        'players': [dict(id=1, normalized_name='demo'), dict(id=2, normalized_name='club')],
        'scouting_reports': [
            dict(id=10, player_id=1, source_type='manual', raw_payload={'loader': 'scripts/seed_demo_data.py'}),
            dict(id=11, player_id=2, source_type='manual', raw_payload=None),
        ],
        'report_attribute_ratings': [dict(id=20, report_id=10), dict(id=21, report_id=11)],
    }
    monkeypatch.setattr(migration, 'rows', lambda conn, table: source_rows[table] if conn is source else [])
    monkeypatch.setattr(migration, 'columns', lambda conn, table: set(source_rows[table][0]))
    target.execute.return_value.fetchone.return_value = (0,)
    tables, players, _, plan = migration.prepare(source, target)
    assert [r['id'] for r in tables['scouting_reports']] == [11]
    assert [r['id'] for r in tables['report_attribute_ratings']] == [21]
    assert set(players) == {'club'}
    assert plan['seed_demo_excluded'] == 1


def test_prepare_rejects_seed_only_source(monkeypatch):
    source, target = object(), MagicMock()
    source_rows = {
        'players': [dict(id=1, normalized_name='demo')],
        'scouting_reports': [dict(id=10, player_id=1, source_type='manual',
                                  raw_payload={'loader': 'scripts/seed_demo_data.py'})],
        'report_attribute_ratings': [],
    }
    monkeypatch.setattr(migration, 'rows', lambda conn, table: source_rows[table] if conn is source else [])
    with pytest.raises(ValueError, match='no scouting reports'):
        migration.prepare(source, target)
