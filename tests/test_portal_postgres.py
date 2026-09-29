"""Exercise private role storage against a disposable PostgreSQL only."""
import os
from pathlib import Path
from uuid import uuid4
from unittest.mock import Mock

import psycopg
import pytest

from scouting.portal import accounts, security


@pytest.fixture
def database(monkeypatch):
    dsn = os.environ.get('SCOUTING_TEST_DATABASE_URL')
    if not dsn:
        pytest.skip('Disposable PostgreSQL not configured')
    params = psycopg.conninfo.conninfo_to_dict(dsn)
    if params.get('host') not in ('localhost', '127.0.0.1') or params.get('dbname') != 'scouting_test':
        pytest.fail('Portal tests require loopback database scouting_test')
    with psycopg.connect(dsn, autocommit=True) as db:
        db.execute('CREATE SCHEMA IF NOT EXISTS auth')
        db.execute('CREATE TABLE IF NOT EXISTS auth.users(id uuid PRIMARY KEY)')
        for role in ['anon', 'authenticated']:
            if not db.execute('SELECT 1 FROM pg_roles WHERE rolname=%s', (role,)).fetchone():
                db.execute(psycopg.sql.SQL('CREATE ROLE {}').format(psycopg.sql.Identifier(role)))
        db.execute(Path('db/portal/001_accounts.sql').read_text())
    monkeypatch.setenv('PORTAL_AUTH_DATABASE_URL', dsn)
    def auth(method, path, **kwargs):
        if method == 'POST':
            uid = str(uuid4())
            with psycopg.connect(dsn) as db:
                db.execute('INSERT INTO auth.users VALUES(%s)', (uid,))
            return {'id': uid}
        return {}
    monkeypatch.setattr(accounts, '_auth', auth)
    yield dsn
    with psycopg.connect(dsn, autocommit=True) as db:
        db.execute('DROP SCHEMA portal CASCADE')
        db.execute('DROP SCHEMA auth CASCADE')


def test_accounts_roles_last_admin_and_rls(database):
    admin_id = accounts.bootstrap_admin('admin@example.test', 'Admin', 'synthetic-password-123')
    admin = accounts.get_user(admin_id)
    with security.session_scope({}, verified_user=admin):
        scout_id = accounts.save_user(username='scout@example.test', name='Scout', password='synthetic-password-456')
        with pytest.raises(ValueError, match='último'):
            accounts.save_user(user_id=admin_id, name='Admin', role='scout')
        accounts.save_user(user_id=scout_id, name='Scout', role='scout', active=False)
    assert not accounts.get_user(scout_id)['active']
    assert accounts.get_user(scout_id)['revision'] == 2
    with security.session_scope({}, verified_user=accounts.get_user(scout_id)), pytest.raises(PermissionError):
        accounts.list_users()
    with psycopg.connect(database, autocommit=True) as db:
        db.execute('SET ROLE authenticated')
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute('SELECT * FROM portal.accounts')
        db.execute('RESET ROLE')
        db.execute('SET ROLE portal_runtime')
        assert db.execute('SELECT count(*) FROM portal.accounts').fetchone()[0] == 2


def test_second_bootstrap_cannot_create_another_admin(database):
    accounts.bootstrap_admin('admin@example.test', 'Admin', 'synthetic-password-123')
    with pytest.raises(ValueError, match='Ya existen'):
        accounts.bootstrap_admin('other@example.test', 'Other', 'synthetic-password-123')
