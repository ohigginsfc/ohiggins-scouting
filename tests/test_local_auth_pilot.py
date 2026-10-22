import copy
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from itsdangerous import TimestampSigner
from scouting.portal import accounts, local_pilot as pilot, security

PASSWORD = 'synthetic-password-123'
ADMIN = dict(id='00000000-0000-0000-0000-000000000001', username='admin@pilot.test',
             display_name='Admin piloto', role='admin', active=True, revision=1)
SCOUT = dict(id='00000000-0000-0000-0000-000000000002', username='scout@pilot.test',
             display_name='Scout piloto', role='scout', active=True, revision=1)


@pytest.fixture
def configured(monkeypatch, tmp_path):
    monkeypatch.setenv('PORTAL_AUTH_PROVIDER', 'local_pilot')
    dsn = 'postgresql://synthetic@127.0.0.1/scouting_test'
    for key in ('PORTAL_AUTH_DATABASE_URL', 'SCOUTING_DATABASE_URL', 'COMET_DATABASE_URL'):
        monkeypatch.setenv(key, dsn)
    path = tmp_path / 'credentials.private.json'
    pilot.write_credentials(path, [(ADMIN, PASSWORD), (SCOUT, PASSWORD)])
    monkeypatch.setenv('PORTAL_PILOT_CREDENTIALS', str(path))
    profiles = {p['id']: copy.deepcopy(p) for p in (ADMIN, SCOUT)}
    monkeypatch.setattr(accounts, 'get_user', lambda uid: profiles.get(uid))
    auth = Mock(side_effect=RuntimeError('synthetic cloud HTTP 402'))
    monkeypatch.setattr(accounts, '_auth', auth)
    pilot._attempts.clear()
    yield profiles, path, auth
    pilot._attempts.clear()


@pytest.mark.parametrize('profile', [ADMIN, SCOUT], ids=['admin', 'scout'])
def test_login_preserves_existing_identity_and_role_with_cloud_unavailable(configured, profile):
    session = accounts.authenticate('  ' + profile['username'].upper() + ' ', PASSWORD)
    assert session['provider'] == 'local_pilot' and 'access_token' not in session
    user = accounts.resolve_session(session)
    assert user == profile
    with security.session_scope(session):
        assert security.require_user() == profile
        if profile['role'] == 'scout':
            with pytest.raises(PermissionError):
                security.require_admin()
        else:
            assert security.require_admin() == profile
    configured[2].assert_not_called()


def test_file_contains_no_plaintext_passwords_or_roles(configured):
    text = configured[1].read_text()
    assert PASSWORD not in text and '"role"' not in text
    assert text.count('$argon2id$') == 2


@pytest.mark.parametrize('field,value', [('active', False), ('revision', 2)])
def test_profile_changes_revoke_a_warm_session(configured, field, value):
    session = accounts.authenticate(ADMIN['username'], PASSWORD)
    assert accounts.resolve_session(session)
    configured[0][ADMIN['id']][field] = value
    assert accounts.resolve_session(session) is None


def test_role_is_read_from_database_not_session(configured):
    session = accounts.authenticate(ADMIN['username'], PASSWORD)
    session['role'] = 'admin'
    configured[0][ADMIN['id']]['role'] = 'scout'
    with security.session_scope(session):
        assert security.require_user()['role'] == 'scout'
        with pytest.raises(PermissionError):
            security.require_admin()


@pytest.mark.parametrize('field,value', [('id', SCOUT['id']), ('revision', 2),
    ('expires', 0), ('expires', float('inf')), ('expires', 'tomorrow'),
    ('provider', 'supabase'), ('local_token', 'forged')])
def test_invalid_or_tampered_session_is_rejected(configured, field, value):
    session = accounts.authenticate(ADMIN['username'], PASSWORD)
    session[field] = value
    assert accounts.resolve_session(session) is None


def test_signed_session_expires_even_if_outer_expiry_is_extended(configured, monkeypatch):
    monkeypatch.setattr(TimestampSigner, 'get_timestamp', lambda self: 1000)
    session = accounts.authenticate(ADMIN['username'], PASSWORD)
    monkeypatch.setattr(TimestampSigner, 'get_timestamp', lambda self: 1000 + pilot.LIFETIME + 1)
    assert accounts.resolve_session(session) is None


@pytest.mark.parametrize('change', ['password', 'secret', 'remove'])
def test_credential_change_or_removal_revokes_sessions(configured, change):
    session = accounts.authenticate(ADMIN['username'], PASSWORD)
    config = json.loads(configured[1].read_text())
    if change == 'password':
        config['accounts'][0]['password_hash'] = pilot._hasher.hash('new-synthetic-password')
    elif change == 'secret':
        config['secret'] = 'another-synthetic-signing-secret-' * 3
    else:
        config['accounts'] = config['accounts'][1:]
    configured[1].write_text(json.dumps(config))
    assert accounts.resolve_session(session) is None


def test_bad_password_and_unknown_user_are_generic_and_throttled(configured, monkeypatch):
    for name in (ADMIN['username'], 'unknown@pilot.test'):
        for _ in range(pilot.MAX_ATTEMPTS):
            assert accounts.authenticate(name, 'incorrect-synthetic-password') is None
    assert accounts.authenticate(ADMIN['username'], PASSWORD) is None
    now = pilot._clock()
    monkeypatch.setattr(pilot, '_clock', lambda: now + pilot.WINDOW + 1)
    assert accounts.authenticate(ADMIN['username'], PASSWORD)


def test_no_silent_fallback_when_supabase_is_the_selected_provider(configured, monkeypatch):
    session = accounts.authenticate(ADMIN['username'], PASSWORD)
    monkeypatch.delenv('PORTAL_AUTH_PROVIDER')
    assert accounts.provider() == 'supabase'
    with pytest.raises(RuntimeError, match='402'):
        accounts.authenticate(ADMIN['username'], PASSWORD)
    assert accounts.resolve_session(session) is None


@pytest.mark.parametrize('function,args,kwargs', [
    (accounts.bootstrap_admin, ('admin@pilot.test', 'Admin', PASSWORD), {}),
    (accounts.save_user, (), dict(name='New', role='admin')),
])
def test_account_writes_are_disabled_in_the_pilot(configured, monkeypatch, function, args, kwargs):
    connect = Mock(side_effect=AssertionError('unexpected write connection'))
    monkeypatch.setattr(accounts, 'connect', connect)
    with pytest.raises(RuntimeError, match='piloto'):
        function(*args, **kwargs)
    connect.assert_not_called()


@pytest.mark.parametrize('key', ['PORTAL_AUTH_DATABASE_URL', 'SCOUTING_DATABASE_URL', 'COMET_DATABASE_URL'])
def test_cloud_connections_are_rejected_before_auth_or_sql(configured, monkeypatch, key):
    monkeypatch.setenv(key, 'postgresql://synthetic@db.example.invalid/postgres')
    with pytest.raises(RuntimeError, match='locales desechables'):
        accounts.authenticate(ADMIN['username'], PASSWORD)
    configured[2].assert_not_called()


def test_misconfigured_file_and_unknown_provider_fail_closed(configured, monkeypatch):
    configured[1].write_text('{"secret":"synthetic-private"}')
    with pytest.raises(RuntimeError) as error:
        accounts.authenticate(ADMIN['username'], PASSWORD)
    assert 'synthetic-private' not in str(error.value)
    monkeypatch.setenv('PORTAL_AUTH_PROVIDER', 'unknown')
    with pytest.raises(RuntimeError, match='Proveedor'):
        accounts.authenticate(ADMIN['username'], PASSWORD)


@pytest.mark.parametrize('dsn', ['postgresql://synthetic@db.example.invalid/portal_pilot',
                               'postgresql://synthetic@127.0.0.1/postgres',
                               'host=localhost dbname=portal_pilot hostaddr=192.0.2.1'])
def test_demo_setup_cannot_target_production(dsn):
    from scripts.create_local_auth_pilot import validate_setup_dsn
    with pytest.raises(ValueError, match='BD local'):
        validate_setup_dsn(dsn)


@pytest.fixture
def local_profiles(database, monkeypatch, tmp_path):
    """Real identity/role SQL in the existing disposable portal fixture."""
    import psycopg
    dsn = database
    with psycopg.connect(dsn) as db:
        for profile in (ADMIN, SCOUT):
            db.execute('INSERT INTO auth.users(id) VALUES(%s)', (profile['id'],))
            db.execute('INSERT INTO portal.accounts(id,email,display_name,role) VALUES(%s,%s,%s,%s)',
                       (profile['id'], profile['username'], profile['display_name'], profile['role']))
    for key in ('PORTAL_AUTH_DATABASE_URL', 'SCOUTING_DATABASE_URL', 'COMET_DATABASE_URL'):
        monkeypatch.setenv(key, dsn)
    path = tmp_path / 'local-users.private.json'
    pilot.write_credentials(path, [(ADMIN, PASSWORD), (SCOUT, PASSWORD)])
    monkeypatch.setenv('PORTAL_PILOT_CREDENTIALS', str(path))
    monkeypatch.setenv('PORTAL_AUTH_PROVIDER', 'local_pilot')
    cloud = Mock(side_effect=AssertionError('pilot contacted Supabase Auth'))
    monkeypatch.setattr(accounts, '_auth', cloud)
    pilot._attempts.clear()
    yield cloud
    pilot._attempts.clear()


from tests.test_portal_postgres import database  # disposable-local fixture only


@pytest.mark.parametrize('profile', [ADMIN, SCOUT], ids=['admin', 'scout'])
def test_real_login_form_and_role_router_with_local_postgres(local_profiles, monkeypatch, profile):
    from streamlit.testing.v1 import AppTest
    monkeypatch.syspath_prepend(str(Path('app').resolve()))
    import portal
    original_option = portal.st.get_option
    monkeypatch.setattr(portal.st, 'get_option', lambda name: '127.0.0.1' if name == 'server.address' else original_option(name))
    monkeypatch.setattr(portal, 'render_scouting', lambda user: portal.st.write('Scouting local autorizado'))
    def comet():
        security.require_admin()
        portal.st.write('COMET local autorizado')
    monkeypatch.setattr(portal, 'render_comet', comet)
    app = AppTest.from_string('import portal\nportal.main()', default_timeout=30).run()
    app.text_input(key='portal_username').input(profile['username'])
    app.text_input[1].input(PASSWORD)
    app.button[0].click().run()
    assert not app.exception and not app.error
    assert app.session_state['portal_session']['id'] == profile['id']
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
    assert not app.exception and not app.error
    if profile['role'] == 'admin':
        assert 'COMET local autorizado' in [x.value for x in app.markdown]
    else:
        assert app.radio(key='portal_module').value == 'Scouting'
        assert 'COMET local autorizado' not in [x.value for x in app.markdown]
    local_profiles.assert_not_called()
    app.button(key='portal_logout').click().run()
    assert not app.exception
    assert app.text_input(key='portal_username') and len(app.radio) == 0


def test_pilot_refuses_a_public_listener_before_any_profile_read(local_profiles, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.syspath_prepend(str(Path('app').resolve()))
    import portal
    read = Mock(side_effect=AssertionError('profile read before bind check'))
    monkeypatch.setattr(accounts, 'connect', read)
    original_option = portal.st.get_option
    monkeypatch.setattr(portal.st, 'get_option', lambda name: '0.0.0.0' if name == 'server.address' else original_option(name))
    monkeypatch.setenv('PORTAL_AUTH_PROVIDER', 'local_pilot ')
    app = AppTest.from_string('import portal\nportal.main()', default_timeout=30).run()
    assert not app.exception
    assert any('localhost' in error.value for error in app.error)
    read.assert_not_called()
