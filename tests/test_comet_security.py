"""Admin ve las mejoras de COMET; Scout (o nadie) no llega a ellas ni a sus datos en caché."""
import re
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from scouting.comet import config_store
from scouting.portal import accounts, security
from scripts import comet_demo_data

ADMIN = dict(id='00000000-0000-0000-0000-000000000001', role='admin', active=True, revision=1,
             display_name='Admin', username='admin@example.test')
SCOUT = dict(id='00000000-0000-0000-0000-000000000002', role='scout', active=True, revision=1,
             display_name='Scout', username='scout@example.test')

NEW_SECTIONS = {
    'Partido semanal': ('comet_followup', 'page_weekly_match'),
    'Rankings por categoría': ('comet_followup', 'page_rankings'),
    'Ficha del jugador': ('comet_followup', 'page_player'),
    'Indicadores': ('comet_insights', 'page_indicators'),
    'Alertas': ('comet_insights', 'page_alerts'),
    'Jugadores adelantados': ('comet_insights', 'page_adelantados'),
    'Seguimiento y configuración': ('comet_insights', 'page_tracking'),
}


@pytest.fixture
def modules(monkeypatch):
    monkeypatch.syspath_prepend(str(Path('app').resolve()))
    for key, value in [('PORTAL_MODE', '1'), ('DB_SCHEMA', 'scouting'), ('DISABLE_SOFASCORE_UPDATE', '1')]:
        monkeypatch.setenv(key, value)
    import comet_context, comet_followup, comet_insights
    st.cache_data.clear()
    return dict(comet_context=comet_context, comet_followup=comet_followup, comet_insights=comet_insights)


GUARDED = [('comet_context', name) for name in ('load_raw', 'load_config', 'compute', 'context')] + \
          [(module, function) for module, function in NEW_SECTIONS.values()]


@pytest.mark.parametrize('module, function', GUARDED)
@pytest.mark.parametrize('user', [SCOUT, None], ids=['scout', 'sin-sesion'])
def test_every_new_entry_point_rejects_scout_and_anonymous(modules, monkeypatch, module, function, user):
    boom = Mock(side_effect=AssertionError('se abrió una conexión sin autorización'))
    monkeypatch.setattr(accounts, 'connect', boom)
    monkeypatch.setattr(modules['comet_context'].comet, 'get_db_connection', boom)
    monkeypatch.setattr(modules['comet_context'].comet.psycopg, 'connect', boom)
    call = getattr(modules[module], function)
    args = ({}, {}, pd.DataFrame()) if function == 'compute' else ()
    with security.session_scope({}, verified_user=user), pytest.raises(PermissionError):
        call(*args)
    boom.assert_not_called()


def test_cached_comet_data_is_not_served_to_scout(modules, monkeypatch):
    raw = comet_demo_data.build_raw()
    queries = Mock(side_effect=lambda sql, params=None: next(iter(raw.values())))
    monkeypatch.setattr(modules['comet_context'].comet, 'load_data', queries)
    context = modules['comet_context']
    with security.session_scope({}, verified_user=ADMIN):
        context.load_raw()
    served = queries.call_count
    assert served == 5, 'una consulta por tabla más la de columnas disponibles'
    with security.session_scope({}, verified_user=SCOUT), pytest.raises(PermissionError):
        context.load_raw()
    with security.session_scope({}, verified_user=ADMIN):
        context.load_raw()  # el administrador sí recibe la caché
    assert queries.call_count == served


def test_config_store_functions_require_admin_before_touching_the_database(monkeypatch):
    boom = Mock(side_effect=AssertionError('conexión abierta sin ser administrador'))
    monkeypatch.setattr(accounts, 'connect', boom)
    calls = [(config_store.load_all, ()), (config_store.save_setting, ('yellow_threshold', 4)),
             (config_store.set_mark, ('1', 'proyectado', True)),
             (config_store.add_period, ('1', 'mundial', pd.Timestamp('2026-01-01').date(), pd.Timestamp('2026-01-02').date())),
             (config_store.retire_period, (1,))]
    for user in (SCOUT, None):
        with security.session_scope({}, verified_user=user):
            for function, args in calls:
                with pytest.raises(PermissionError):
                    function(*args)
    boom.assert_not_called()


def test_config_store_validation_rejects_bad_input_before_connecting(monkeypatch):
    boom = Mock(side_effect=AssertionError('no debe conectar con datos inválidos'))
    monkeypatch.setattr(accounts, 'connect', boom)
    day = pd.Timestamp('2026-05-01').date()
    with security.session_scope({}, verified_user=ADMIN):
        for call in [
            lambda: config_store.save_setting('inexistente', 1),
            lambda: config_store.save_setting('yellow_threshold', 99),
            lambda: config_store.save_setting('alert_config', {'yellow_cards': {'enabled': True, 'color': 'Fucsia'}}),
            lambda: config_store.set_mark('1; DROP TABLE x', 'proyectado', True),
            lambda: config_store.set_mark('1', 'estrella', True),
            lambda: config_store.set_mark('1', 'proyectado', True, 'x' * 501),
            lambda: config_store.add_period('1', 'olimpiadas', day, day),
            lambda: config_store.add_period('1', 'mundial', day, day - timedelta(days=1)),
        ]:
            with pytest.raises(ValueError):
                call()
    boom.assert_not_called()


def test_store_unavailable_when_connection_or_migration_is_missing(monkeypatch):
    def unreachable():
        raise RuntimeError('Falta configurar la conexión privada de cuentas.')
    monkeypatch.setattr(accounts, 'connect', unreachable)
    with security.session_scope({}, verified_user=ADMIN), pytest.raises(config_store.StoreUnavailable) as failure:
        config_store.load_all()
    assert 'postgres' not in str(failure.value).lower() and 'password' not in str(failure.value).lower()


# --- Enrutamiento real del portal ---------------------------------------------------------------------------

def _routed_app(monkeypatch, user, section):
    monkeypatch.syspath_prepend(str(Path('app').resolve()))
    for key, value in [('PORTAL_MODE', '1'), ('DB_SCHEMA', 'scouting'), ('DISABLE_SOFASCORE_UPDATE', '1')]:
        monkeypatch.setenv(key, value)
    import portal, comet_followup, comet_insights
    monkeypatch.setattr(portal.accounts, 'resolve_session', lambda token: user)
    monkeypatch.setattr(portal, 'render_scouting', lambda u: portal.st.write('Scouting autorizado'))
    reached = []
    for label, (module, function) in NEW_SECTIONS.items():
        target = {'comet_followup': comet_followup, 'comet_insights': comet_insights}[module]
        monkeypatch.setattr(target, function, lambda label=label: reached.append(label) or portal.st.write(f'Sección {label}'))
    app = AppTest.from_string('import portal\nportal.main()', default_timeout=60)
    app.session_state['portal_session'] = {'synthetic': True}
    app.session_state['portal_module'] = 'COMET'
    app.session_state['_portal_previous_module'] = 'COMET'
    app.session_state['comet_section'] = section
    return app.run(), reached


@pytest.mark.parametrize('section', list(NEW_SECTIONS))
def test_scout_cannot_route_to_any_new_comet_section(monkeypatch, section):
    app, reached = _routed_app(monkeypatch, dict(SCOUT), section)
    assert reached == [], 'un scout no debe ejecutar ninguna pantalla nueva de COMET'
    assert app.radio(key='portal_module').options == ['Scouting'] and app.radio(key='portal_module').value == 'Scouting'
    assert not app.exception and not app.error
    assert 'comet_section' not in app.session_state


@pytest.mark.parametrize('section', list(NEW_SECTIONS))
def test_admin_reaches_every_new_comet_section_from_the_portal_menu(monkeypatch, section):
    app, reached = _routed_app(monkeypatch, dict(ADMIN), section)
    assert reached == [section]
    assert not app.exception and not app.error
    options = app.selectbox(key='comet_section').options
    assert list(NEW_SECTIONS) == [o for o in options if o in NEW_SECTIONS]
    assert {'Resumen ejecutivo', 'Desarrollo juvenil', 'Rendimiento competitivo', 'Análisis de jugadores',
            'Estructura del plantel'} <= set(options), 'se conservan las cinco pantallas actuales'


# --- Solo lectura sobre COMET y sin secretos ----------------------------------------------------------------

def test_new_comet_queries_are_read_only_and_parameterised():
    from scouting.comet import queries
    for sql in (queries.SHEET_SQL, queries.MATCHES_SQL, queries.PLAYERS_SQL, queries.GOALKEEPERS_SQL):
        assert re.match(r'\s*(SELECT|WITH)\b', sql)
        assert not re.search(r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT)\b', sql, re.I)
        assert set(re.findall(r'%\(?\w*\)?[sd]?', sql)) <= {'%(club)s'}, 'solo el parámetro del club'
    assert 'a.clubid = %(club)s' in queries.PLAYERS_SQL, 'solo se piden los jugadores de las planillas de O\'Higgins'


def test_club_id_matches_the_existing_dashboard(modules):
    import comet_dashboard
    from scouting.comet import queries
    assert queries.OHIGGINS_CLUB_ID == comet_dashboard.OHIGGINS_CLUB_ID


def test_migration_003_stays_in_private_portal_schema_and_grants_nothing_public():
    sql = Path('db/portal/003_comet_followup.sql').read_text(encoding='utf8')
    code = '\n'.join(line for line in sql.splitlines() if not line.strip().startswith('--'))
    assert 'public.' not in code and 'comet_reader' not in code and 'scouting_runtime' not in code
    assert not re.search(r'GRANT[^;]*\b(anon|authenticated|PUBLIC)\b', code, re.I | re.S)
    assert not re.search(r'GRANT[^;]*\bDELETE\b', code, re.I | re.S), 'nada se borra: solo se desactiva'
    assert code.count('ENABLE ROW LEVEL SECURITY') == 4
    for table in ('comet_settings', 'comet_player_marks', 'comet_selection_periods', 'comet_digest_deliveries'):
        assert f'portal.{table}' in code


def test_new_files_contain_no_connection_strings_or_keys():
    root = Path('.')
    files = list((root / 'src/scouting/comet').glob('*.py')) + [root / 'app/comet_context.py', root / 'app/comet_followup.py',
            root / 'app/comet_insights.py', root / 'app/ui/comet_widgets.py', root / 'db/portal/003_comet_followup.sql',
            root / 'scripts/comet_demo_data.py', root / 'scripts/comet_demo_store.py', root / 'scripts/demo_comet_followup.py']
    forbidden = re.compile(r'postgres(ql)?://\w+:[^@\s]+@|eyJ[A-Za-z0-9_-]{20,}|sb_secret_|password\s*=\s*[\'"][^\'"]{4,}[\'"]', re.I)
    for path in files:
        assert not forbidden.search(path.read_text(encoding='utf8')), f'{path} parece contener una credencial'
