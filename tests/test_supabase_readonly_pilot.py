"""The live-preview policy is tested with fakes and disposable loopback SQL only."""
from unittest.mock import Mock

import psycopg
import pytest

from scouting.portal import accounts, local_pilot, readonly_pilot, security
from tests.test_local_auth_pilot import configured, local_profiles, ADMIN, SCOUT, PASSWORD
from tests.test_portal_postgres import database

PROJECT = 'abcdefghijklmnopqrst'
KEYS = ('PORTAL_AUTH_DATABASE_URL', 'SCOUTING_DATABASE_URL', 'COMET_DATABASE_URL')


@pytest.fixture
def cloud_config(monkeypatch):
    monkeypatch.setenv('PORTAL_AUTH_PROVIDER', 'local_pilot')
    monkeypatch.setenv('PORTAL_PILOT_DATA_MODE', 'supabase_readonly')
    monkeypatch.setenv('PORTAL_PILOT_SUPABASE_PROJECT', PROJECT)
    for key, role in zip(KEYS, ('portal_runtime', 'scouting_runtime', 'comet_reader')):
        monkeypatch.setenv(key, f'host=aws-1-eu-central-1.pooler.supabase.com port=5432 '
                           f'user={role}.{PROJECT} dbname=postgres sslmode=require password=synthetic')


def test_live_mode_requires_explicit_opt_in_and_isolated_ssl_roles(cloud_config, monkeypatch):
    local_pilot.validate_environment()  # parsing only, no network
    monkeypatch.delenv('PORTAL_PILOT_DATA_MODE')
    with pytest.raises(RuntimeError, match='locales'):
        local_pilot.validate_environment()


@pytest.mark.parametrize('key', KEYS)
@pytest.mark.parametrize('suffix', [' sslmode=disable', ' user=postgres.abcdefghijklmnopqrst',
                                  ' hostaddr=192.0.2.1', ' service=production', ' port=6543',
                                  ' host=unrelated.invalid', ' dbname=other'])
def test_invalid_live_connections_rejected_before_network(cloud_config, monkeypatch, key, suffix):
    import os
    monkeypatch.setenv(key, os.environ[key] + suffix)
    connect = Mock(side_effect=AssertionError('must not connect'))
    monkeypatch.setattr(psycopg, 'connect', connect)
    with pytest.raises(RuntimeError):
        local_pilot.validate_environment()
    connect.assert_not_called()


def test_sessions_do_not_cross_synthetic_and_real_data_modes(configured, monkeypatch):
    synthetic = accounts.authenticate(ADMIN['username'], PASSWORD)
    monkeypatch.setenv('PORTAL_PILOT_DATA_MODE', 'supabase_readonly')
    monkeypatch.setattr(readonly_pilot, 'validate_environment', lambda: None)
    assert accounts.resolve_session(synthetic) is None
    live = accounts.authenticate(SCOUT['username'], PASSWORD)
    assert accounts.resolve_session(live)['role'] == 'scout'
    monkeypatch.delenv('PORTAL_PILOT_DATA_MODE')
    assert accounts.resolve_session(live) is None
    configured[2].assert_not_called()


@pytest.mark.parametrize('connection', ['portal', 'scouting', 'comet'])
def test_all_connection_paths_reject_sql_writes_even_after_commit(database, monkeypatch, connection):
    from pathlib import Path
    from scouting import db
    monkeypatch.setenv('PORTAL_AUTH_PROVIDER', 'local_pilot')
    monkeypatch.setenv('PORTAL_PILOT_DATA_MODE', 'supabase_readonly')
    # Cloud policy tested above; exercise the actual connection implementation on
    # scouting_test. The global pytest guard still forbids every external DSN.
    monkeypatch.setattr(local_pilot, 'validate_environment', lambda: None)
    monkeypatch.setenv('PORTAL_AUTH_DATABASE_URL', database)
    monkeypatch.setenv('SCOUTING_DATABASE_URL', database)
    monkeypatch.setenv('COMET_DATABASE_URL', database)
    monkeypatch.delenv('PORTAL_MODE', raising=False)
    monkeypatch.delenv('DB_SCHEMA', raising=False)
    if connection == 'portal':
        factory = accounts.connect
    elif connection == 'scouting':
        factory = db.get_connection
    else:
        monkeypatch.syspath_prepend(str(Path('app').resolve()))
        import comet_dashboard
        factory = comet_dashboard.get_db_connection
    with security.session_scope({}, verified_user=ADMIN):
        with factory() as conn:
            for boundary in ('commit', 'rollback'):
                row = conn.execute('SHOW transaction_read_only').fetchone()
                assert (row['transaction_read_only'] if isinstance(row, dict) else row[0]) == 'on'
                # Disposable local database only; never attempt this on Supabase.
                with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
                    conn.execute('CREATE TABLE should_never_exist(id int)')
                conn.rollback()
                getattr(conn, boundary)()
            row = conn.execute('SHOW default_transaction_read_only').fetchone()
            assert (row['default_transaction_read_only'] if isinstance(row, dict) else row[0]) == 'on'


def test_write_actions_stop_before_database_or_email(cloud_config, monkeypatch):
    from datetime import date
    from scouting.comet import config_store
    connect = Mock(side_effect=AssertionError('write opened database'))
    monkeypatch.setattr(accounts, 'connect', connect)
    actions = [lambda: config_store.save_setting('x', 1),
               lambda: config_store.set_mark('1', 'proyectado', True),
               lambda: config_store.add_period('1', 'microciclo', date.today(), date.today()),
               lambda: config_store.retire_period(1),
               lambda: config_store.reserve_delivery_for_job(date.today(), 'test@example.test'),
               lambda: config_store.finish_delivery_for_job(date.today(), 'test@example.test', sent=True),
               lambda: security.require_report_management(None, 1)]
    for action in actions:
        with pytest.raises(PermissionError, match='consultar'):
            action()
    assert not security.can_edit({'is_hidden': True})
    connect.assert_not_called()


def test_readonly_hidden_report_ui_has_no_write_controls(cloud_config, monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    monkeypatch.syspath_prepend(str(Path('app').resolve()))
    import portal
    import streamlit_app as scouting
    monkeypatch.setattr(scouting, '_render_dashboard', lambda: portal.st.write('Read only dashboard'))
    # No coverage queries on the hidden-report route. Test it with synthetic rows.
    from contextlib import nullcontext
    monkeypatch.setattr(scouting, 'get_connection', lambda: nullcontext(None))
    monkeypatch.setattr(scouting, 'fetch_hidden_reports', lambda *a, **k: [
        dict(id=1, player_full_name='Synthetic player', is_hidden=True, summary='Synthetic report')])
    monkeypatch.setattr(scouting.attribute_ratings_service, 'get_report_attribute_ratings', lambda *a: [])
    monkeypatch.setattr(security, 'require_user', lambda: SCOUT)
    monkeypatch.setenv('PORTAL_MODE', '1')
    app = AppTest.from_string('from streamlit_app import _render_hidden_reports_page\n_render_hidden_reports_page()').run()
    assert not app.exception and not app.error
    assert len(app.button) == 0 and len(app.text_area) == 0 and len(app.dataframe) == 1


def test_readonly_router_omits_creation_and_comet_configuration(cloud_config, monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    monkeypatch.syspath_prepend(str(Path('app').resolve()))
    import portal
    import comet_dashboard
    import streamlit_app as scouting
    monkeypatch.setattr(scouting, '_handle_page_navigation', lambda page: False)
    monkeypatch.setattr(scouting, '_render_hidden_reports_page', lambda: portal.st.write('Hidden reports read only'))
    app = AppTest.from_string('import portal\nportal.st.session_state["page"]="Informes ocultos"\nportal.render_scouting({})').run()
    assert not app.exception and not app.error
    assert 'Nuevo informe' not in [button.label for button in app.button]
    assert 'Informes ocultos' in [button.label for button in app.button]
    monkeypatch.setattr(comet_dashboard, 'page_executive_summary', lambda: portal.st.write('COMET read only'))
    monkeypatch.setattr(portal, 'require_admin', lambda: ADMIN)
    app = AppTest.from_string('import portal\nportal.render_comet()').run()
    assert not app.exception and not app.error
    assert 'Seguimiento y configuración' not in app.selectbox[0].options


def test_launcher_environment_drops_cloud_auth_mail_and_inherited_connections():
    from scripts.run_supabase_readonly_pilot import clean_from
    source = dict(PORTAL_SUPABASE_SECRET_KEY='secret', SMTP_PASSWORD='secret', GOOGLE_SV_B64='secret',
                  DATABASE_URL='secret', SESSION_URL='secret', PGOPTIONS='unsafe', PATH='safe')
    assert clean_from(source) == {'PATH': 'safe'}
