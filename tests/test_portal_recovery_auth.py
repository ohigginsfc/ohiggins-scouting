"""Server recovery is explicit, bounded, durable and read-only; no cloud in tests."""
import importlib
import json
import os
from pathlib import Path
from unittest.mock import Mock

import pytest

from scouting.portal import accounts, local_pilot, recovery_auth, readonly_pilot, security
from tests.test_local_auth_pilot import configured, local_profiles, ADMIN, SCOUT, PASSWORD
from tests.test_portal_postgres import database


@pytest.fixture
def state(monkeypatch, tmp_path):
    directory = tmp_path / 'state'
    monkeypatch.setenv('PORTAL_RECOVERY_STATE_DIR', str(directory))
    return directory


def test_five_attempts_survive_module_reload_and_expire(state, monkeypatch):
    now = 10000
    monkeypatch.setattr(recovery_auth, '_clock', lambda: now)
    for _ in range(5):
        assert recovery_auth.reserve_attempt('synthetic@example.test', 'secret')
    assert recovery_auth.reserve_attempt('synthetic@example.test', 'secret') is None
    importlib.reload(recovery_auth)
    monkeypatch.setattr(recovery_auth, '_clock', lambda: now)
    assert recovery_auth.reserve_attempt('synthetic@example.test', 'secret') is None
    monkeypatch.setattr(recovery_auth, '_clock', lambda: now + 901)
    assert recovery_auth.reserve_attempt('synthetic@example.test', 'secret')
    assert b'synthetic@example.test' not in (state / 'attempts.sqlite3').read_bytes()


def test_unknown_user_rotation_cannot_escape_global_limit(state):
    for n in range(60):
        assert recovery_auth.reserve_attempt(f'unknown{n}@example.test', 'secret')
    assert recovery_auth.reserve_attempt('other@example.test', 'secret') is None


def test_limiter_state_failure_never_allows_login(state, monkeypatch):
    state.write_text('not a directory')
    with pytest.raises(RuntimeError, match='privado'):
        recovery_auth.reserve_attempt('synthetic@example.test', 'secret')


def test_success_resets_only_user_counter_not_global(state):
    assert recovery_auth.reserve_attempt('synthetic@example.test', 'secret')
    recovery_auth.clear_user_attempts('synthetic@example.test', 'secret')
    with recovery_auth._connect() as db:
        assert db.execute('SELECT count(*) FROM attempts').fetchone()[0] == 1
        assert db.execute("SELECT count FROM attempts WHERE key='global'").fetchone()[0] == 1


def configure_recovery(monkeypatch, state):
    monkeypatch.setenv('PORTAL_AUTH_PROVIDER', 'local_recovery')
    monkeypatch.setenv('PORTAL_RECOVERY_CREDENTIALS', os.environ['PORTAL_PILOT_CREDENTIALS'])
    monkeypatch.setenv('PORTAL_RECOVERY_STATE_DIR', str(state))
    monkeypatch.setenv('PORTAL_RECOVERY_ENABLED', '1')
    monkeypatch.setattr(recovery_auth, 'validate_environment', lambda: None)


@pytest.mark.parametrize('profile', [ADMIN, SCOUT], ids=['admin', 'scout'])
def test_existing_profile_roles_and_revocation_without_auth_http(configured, state, monkeypatch, profile):
    configure_recovery(monkeypatch, state)
    token = accounts.authenticate(profile['username'], PASSWORD)
    assert token['provider'] == 'local_recovery' and 'access_token' not in token
    assert accounts.resolve_session(token) == profile
    with security.session_scope(token):
        if profile['role'] == 'scout':
            with pytest.raises(PermissionError):
                security.require_admin()
        else:
            assert security.require_admin()['role'] == 'admin'
        assert not security.can_edit({'is_hidden': True})
    configured[0][profile['id']]['revision'] += 1
    assert accounts.resolve_session(token) is None
    configured[2].assert_not_called()


def test_recovery_token_rejected_by_both_other_providers(configured, state, monkeypatch):
    configure_recovery(monkeypatch, state)
    token = accounts.authenticate(ADMIN['username'], PASSWORD)
    monkeypatch.setenv('PORTAL_AUTH_PROVIDER', 'local_pilot')
    assert accounts.resolve_session(token) is None
    monkeypatch.setenv('PORTAL_AUTH_PROVIDER', 'supabase')
    assert accounts.resolve_session(token) is None
    configured[2].assert_not_called()


def test_recovery_requires_readonly_opt_in_and_three_isolated_roles(state, monkeypatch):
    monkeypatch.setenv('PORTAL_AUTH_PROVIDER', 'local_recovery')
    with pytest.raises(RuntimeError, match='lectura'):
        recovery_auth.validate_environment()
    monkeypatch.setenv('PORTAL_RECOVERY_ENABLED', '1')
    monkeypatch.setenv('PORTAL_RECOVERY_SUPABASE_PROJECT', 'abcdefghijklmnopqrst')
    for key, role in zip(('PORTAL_AUTH_DATABASE_URL', 'SCOUTING_DATABASE_URL', 'COMET_DATABASE_URL'),
                         ('portal_runtime', 'scouting_runtime', 'comet_reader')):
        monkeypatch.setenv(key, f'host=aws-1-eu-central-1.pooler.supabase.com user={role}.abcdefghijklmnopqrst '
                           'dbname=postgres port=5432 sslmode=require')
    recovery_auth.validate_environment()  # parse only; no connection
    monkeypatch.setenv('SCOUTING_DATABASE_URL', 'host=127.0.0.1 dbname=postgres user=postgres')
    with pytest.raises(RuntimeError):
        recovery_auth.validate_environment()


def test_corrupt_credentials_never_reveal_values_or_contact_auth(configured, state, monkeypatch):
    configure_recovery(monkeypatch, state)
    configured[1].write_text('{"secret":"private-value"}')
    with pytest.raises(RuntimeError) as error:
        accounts.authenticate(ADMIN['username'], PASSWORD)
    assert 'private-value' not in str(error.value)
    configured[2].assert_not_called()


@pytest.mark.parametrize('profile', [ADMIN, SCOUT], ids=['admin', 'scout'])
def test_server_login_on_public_container_listener_retains_role_router(local_profiles, state, monkeypatch, profile):
    from streamlit.testing.v1 import AppTest
    configure_recovery(monkeypatch, state)
    monkeypatch.syspath_prepend(str(Path('app').resolve()))
    import portal
    original_option = portal.st.get_option
    monkeypatch.setattr(portal.st, 'get_option', lambda name: '0.0.0.0' if name == 'server.address' else original_option(name))
    monkeypatch.setattr(portal, 'render_scouting', lambda user: portal.st.write('Scouting recovery'))
    monkeypatch.setattr(portal, 'render_comet', lambda: security.require_admin())
    app = AppTest.from_string('import portal\nportal.main()', default_timeout=30).run()
    app.text_input(key='portal_username').input(profile['username'])
    app.text_input[1].input(PASSWORD)
    app.button[0].click().run()
    assert not app.error and not app.exception
    assert app.session_state['portal_session']['provider'] == 'local_recovery'
    expected = ['Inicio', 'COMET', 'Scouting', 'Administración'] if profile['role'] == 'admin' else ['Scouting']
    assert app.radio(key='portal_module').options == expected
    if profile['role'] == 'admin':
        app.radio(key='portal_module').set_value('COMET').run()
    else:
        token = app.session_state['portal_session']
        app = AppTest.from_string('import portal\nportal.main()', default_timeout=30)
        app.session_state['portal_session'] = token
        app.session_state['portal_module'] = 'COMET'
        app.run()
    assert not app.error and not app.exception
    assert app.radio(key='portal_module').value == ('COMET' if profile['role'] == 'admin' else 'Scouting')
    app.button(key='portal_logout').click().run()
    assert app.text_input(key='portal_username') and len(app.radio) == 0
    local_profiles.assert_not_called()


def test_recovery_compose_uses_private_mount_persistent_limiter_and_no_auth_or_mail_keys():
    from scripts.check_compose_db_credentials import load_compose_config
    env = dict(os.environ, PORTAL_RECOVERY_SUPABASE_PROJECT='abcdefghijklmnopqrst',
               PORTAL_AUTH_DATABASE_URL='synthetic', SCOUTING_DATABASE_URL='synthetic',
               COMET_DATABASE_URL='synthetic', COMPOSE_PROFILES='setup')
    config = load_compose_config(Path('docker-compose.portal-recovery.yml').resolve(), env=env)
    portal = config['services']['portal']
    env = portal['environment']
    assert env['PORTAL_AUTH_PROVIDER'] == 'local_recovery' and env['PORTAL_RECOVERY_ENABLED'] == '1'
    assert not any('SUPABASE_SECRET' in k or 'SMTP' in k for k in env)
    credential_mount = portal['volumes'][0]
    # Compose versions may omit false fields when normalizing to JSON.
    assert credential_mount['read_only']
    assert credential_mount.get('bind', {}).get('create_host_path', False) is False
    assert any(v.get('source') == 'portal_recovery_state' and v['target'] == '/var/lib/ohiggins-auth'
               for v in portal['volumes'])
    assert portal['build']['args']['INSTALL_ARGON2'] == '1'
    assert config['services']['provision-recovery']['profiles'] == ['setup']


def test_scouting_write_opt_in_never_unlocks_comet_or_accounts(configured, state, monkeypatch):
    configure_recovery(monkeypatch, state)
    assert readonly_pilot.scouting_readonly()
    monkeypatch.setenv('PORTAL_RECOVERY_SCOUTING_WRITES', '1')
    assert readonly_pilot.scouting_writes() and not readonly_pilot.scouting_readonly()
    assert 'default_transaction_read_only=off' in readonly_pilot.connection_options('scouting')
    for schema in ('public', 'portal'):
        assert 'default_transaction_read_only=on' in readonly_pilot.connection_options(schema)
    with security.session_scope({}, verified_user=ADMIN):
        with pytest.raises(PermissionError):
            readonly_pilot.require_writable()  # COMET settings stay protected
        with pytest.raises(RuntimeError):
            accounts.save_user(name='Forbidden', role='admin')
    configured[2].assert_not_called()


def test_create_edit_and_permission_boundaries_on_disposable_sql(local_profiles, state, monkeypatch):
    """Full service operations, independent SQL role, synthetic records, no cloud."""
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict, make_conninfo
    from scripts.create_local_auth_pilot import _migration
    from scouting.db import get_connection
    from scouting.services import reports_service as reports
    configure_recovery(monkeypatch, state)
    monkeypatch.setenv('PORTAL_RECOVERY_SCOUTING_WRITES', '1')
    monkeypatch.setenv('PORTAL_MODE', '1')
    monkeypatch.setenv('DB_SCHEMA', 'scouting')
    dsn = os.environ['SCOUTING_TEST_DATABASE_URL']
    with psycopg.connect(dsn) as owner:
        owner.execute('CREATE SCHEMA scouting; SET LOCAL search_path=scouting')
        _migration(owner, Path('db/init.sql'))
        for path in sorted(Path('db/migrations').glob('*.sql')):
            _migration(owner, path)
        owner.execute("CREATE ROLE recovery_report_writer LOGIN PASSWORD 'synthetic-writer-only'")
        owner.execute('GRANT USAGE ON SCHEMA scouting TO recovery_report_writer; '
                      'GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA scouting TO recovery_report_writer; '
                      'GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA scouting TO recovery_report_writer')
    params = conninfo_to_dict(dsn)
    params.update(user='recovery_report_writer', password='synthetic-writer-only')
    monkeypatch.setenv('SCOUTING_DATABASE_URL', make_conninfo(**params))
    try:
        admin_token = accounts.authenticate(ADMIN['username'], PASSWORD)
        scout_token = accounts.authenticate(SCOUT['username'], PASSWORD)
        with security.session_scope(admin_token):
            with get_connection() as conn:
                assert conn.execute('SHOW transaction_read_only').fetchone()[0] == 'off'
                admin_report, _, _ = reports.create_scouting_report_from_dict(conn, {
                    'player_name': 'Synthetic admin player', 'summary': 'Before', 'rating': 6,
                    'recommendation': 'Interesante'})
                reports.update_report(conn, admin_report, summary='Admin edited')
                assert reports.get_report(conn, admin_report)['summary'] == 'Admin edited'
        with security.session_scope(scout_token):
            with get_connection() as conn:
                scout_report, _, _ = reports.create_scouting_report_from_dict(conn, {
                    'player_name': 'Synthetic scout player', 'summary': 'Before',
                    'raw_payload': {'portal_owner_id': ADMIN['id']}})
                reports.update_report(conn, scout_report, summary='Scout edited')
                saved = reports.get_report(conn, scout_report)
                assert saved['summary'] == 'Scout edited'
                assert saved['raw_payload']['portal_owner_id'] == SCOUT['id']
                with pytest.raises(PermissionError):
                    reports.update_report(conn, admin_report, summary='Forbidden')
                with pytest.raises(PermissionError):
                    security.require_admin()
                assert not conn.execute("SELECT has_schema_privilege(current_user,'portal','USAGE')").fetchone()[0]
        with security.session_scope(admin_token):
            with get_connection() as conn:
                reports.hide_report(conn, admin_report)
        with security.session_scope(scout_token):
            with get_connection() as conn:
                reports.update_report(conn, admin_report, summary='Hidden report edited by scout')
                reports.restore_report(conn, admin_report)
                assert not reports.get_report(conn, admin_report)['is_hidden']
                with pytest.raises(PermissionError):
                    reports.update_report(conn, admin_report, summary='Forbidden again')
        local_profiles.assert_not_called()
    finally:
        with psycopg.connect(dsn) as owner:
            owner.execute('DROP SCHEMA scouting CASCADE')
            owner.execute('DROP OWNED BY recovery_report_writer')
            owner.execute('DROP ROLE recovery_report_writer')
