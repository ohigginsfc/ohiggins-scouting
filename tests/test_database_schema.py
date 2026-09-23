import pytest
from unittest.mock import MagicMock,patch
from scouting.config.database import get_db_connection_params
from scouting.db import get_connection


def test_explicit_scouting_url_and_schema_override_local_settings(monkeypatch):
    monkeypatch.setenv('SCOUTING_DATABASE_URL','postgresql://runtime:synthetic@localhost/remote?sslmode=require')
    monkeypatch.setenv('DB_SCHEMA','scouting')
    params=get_db_connection_params()
    assert params['dbname']=='remote' and params['user']=='runtime'
    assert params['sslmode']=='require'
    assert params['options']=='-c search_path=scouting'
    assert 'public' not in params['options']


def test_schema_injection_is_rejected(monkeypatch):
    monkeypatch.setenv('SCOUTING_DATABASE_URL','postgresql://localhost/test')
    monkeypatch.setenv('DB_SCHEMA','scouting -c search_path=public')
    with pytest.raises(ValueError,match='DB_SCHEMA'):get_db_connection_params()


def test_missing_schema_fails_closed_and_closes_connection(monkeypatch):
    monkeypatch.setenv('DB_SCHEMA','scouting')
    conn=MagicMock();conn.execute.return_value.fetchone.return_value=(None,)
    with patch('scouting.db.psycopg.connect',return_value=conn):
        with pytest.raises(ValueError,match='absent'):get_connection()
    conn.close.assert_called_once()
