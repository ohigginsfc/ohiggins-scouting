"""Dashboard de Scouting tras la reunión con Pablo (13-10-2026): dos campogramas (chilenos y extranjeros) y vista
preliminar de los informes ocultos. Datos ficticios."""
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from unittest.mock import Mock
import os
import sys
from uuid import uuid4

import numpy as np
import psycopg
import pytest
from psycopg import sql
from streamlit.testing.v1 import AppTest

from scouting.repositories import dashboard_repository
from scouting.services import dashboard_service, nationality_service
from scouting.services.nationality_service import CHILEAN, FOREIGN, nationality_group, split_position_counts

ROOT = Path(__file__).resolve().parents[1]
ADMIN = dict(id='synthetic-admin', display_name='Admin', role='admin', active=True)
SCOUT = dict(id='synthetic-scout', display_name='Scout', role='scout', active=True)


# --- Chilenos y extranjeros ------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize('value, expected', [
    ('Chile', CHILEAN), ('chile', CHILEAN), ('  CHILE ', CHILEAN), ('Chilena', CHILEAN), ('chileno', CHILEAN),
    ('Chile / Argentina', CHILEAN), ('Argentina-Chilena', CHILEAN), ('chilena y española', CHILEAN), ('Chile, Italia', CHILEAN),
    ('Argentina', FOREIGN), ('Uruguay', FOREIGN), ('Venezuela', FOREIGN), ('Trinidad y Tobago', FOREIGN),
    ('Bosnia y Herzegovina', FOREIGN), ('Argentina / Uruguay', FOREIGN), ('Chilé', CHILEAN),   # las tildes no importan
    (None, None), ('', None), ('   ', None), ('—', None), ('Sin dato', None), (np.nan, None),
])
def test_nationality_groups(value, expected):
    assert nationality_group(value) == expected


def test_dual_nationality_with_chile_is_not_foreign_and_unknown_is_never_assumed():
    assert nationality_group('Colombia / Chile') == CHILEAN
    assert nationality_group(None) is None and nationality_group('') is None


def test_position_counts_are_split_by_group_without_duplicating_players_or_reports():
    rows = [
        dict(position='Delantero', nationality='Chile', players_count=3, reports_count=5),
        dict(position='Delantero', nationality='Chilena', players_count=1, reports_count=1),
        dict(position='Delantero', nationality='Argentina', players_count=2, reports_count=2),
        dict(position='Delantero', nationality=None, players_count=1, reports_count=1),
        dict(position='Portero', nationality='Uruguay', players_count=1, reports_count=3),
        dict(position=None, nationality='Chile', players_count=9, reports_count=9),
        dict(position='', nationality='Chile', players_count=9, reports_count=9),
    ]
    out = split_position_counts(rows)
    assert out[CHILEAN] == [dict(position='Delantero', players_count=4, reports_count=6)]
    assert out[FOREIGN] == [dict(position='Delantero', players_count=2, reports_count=2),
                            dict(position='Portero', players_count=1, reports_count=3)]
    assert out['unknown'] == [dict(position='Delantero', players_count=1, reports_count=1)]
    total = sum(r['players_count'] for group in out.values() for r in group)
    assert total == 8, 'cada jugador está en un solo grupo; las filas sin posición no se cuentan'


# --- Consultas contra PostgreSQL --------------------------------------------------------------------------------------------------

@pytest.fixture
def scouting_db():
    dsn = os.getenv('SCOUTING_TEST_DATABASE_URL')
    if not dsn:
        pytest.skip('Requires disposable local PostgreSQL via SCOUTING_TEST_DATABASE_URL')
    params = psycopg.conninfo.conninfo_to_dict(dsn)
    assert params.get('host') in {'localhost', '127.0.0.1', '::1'} and params.get('dbname') == 'scouting_test'
    schema = 'campograma_test_' + uuid4().hex
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    conn = psycopg.connect(dsn, options=f'-c search_path={schema}')
    try:
        conn.execute((ROOT / 'db/init.sql').read_text(encoding='utf-8'))
        for path in sorted((ROOT / 'db/migrations').glob('*.sql')):
            conn.execute(path.read_text(encoding='utf-8'))
        conn.commit()
        yield conn
    finally:
        conn.close()
        with psycopg.connect(dsn, autocommit=True) as admin:
            admin.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def add_player(conn, name, nationality, position, reports=1, hidden=0):
    player_id = conn.execute(
        'INSERT INTO players (full_name, normalized_name, nationality, position) VALUES (%s, %s, %s, %s) RETURNING id',
        (name, name.lower(), nationality, position)).fetchone()[0]
    for index in range(reports + hidden):
        conn.execute(
            "INSERT INTO scouting_reports (player_id, source_type, scout_name, report_date, recommendation, rating, is_hidden) "
            "VALUES (%s, 'manual', 'Scout', %s, 'Seguir monitorizando', 7, %s)",
            (player_id, date(2026, 10, 1 + index), index >= reports))
    return player_id


def test_position_counts_by_nationality_group_visible_reports_only(scouting_db):
    conn = scouting_db
    add_player(conn, 'Chileno Uno', 'Chile', 'Delantero', reports=2)
    add_player(conn, 'Chilena Dos', 'Chilena', 'Delantero')
    add_player(conn, 'Argentino Tres', 'Argentina', 'Delantero', reports=3)
    add_player(conn, 'Uruguayo Cuatro', 'Uruguay', 'Portero')
    add_player(conn, 'Sin nacionalidad', None, 'Delantero')
    add_player(conn, 'Solo oculto', 'Chile', 'Portero', reports=0, hidden=2)      # sus informes ocultos no cuentan
    add_player(conn, 'Sin posición', 'Chile', None)
    conn.commit()
    by_origin = dashboard_service.get_position_counts_by_origin(conn)
    assert by_origin[CHILEAN] == [dict(position='Delantero', players_count=2, reports_count=3)]
    assert by_origin[FOREIGN] == [dict(position='Delantero', players_count=1, reports_count=3),
                                  dict(position='Portero', players_count=1, reports_count=1)]
    assert by_origin['unknown'] == [dict(position='Delantero', players_count=1, reports_count=1)]
    # El conteo total anterior no cambia: la suma de los tres grupos es el conteo por posición de siempre.
    old = {r['position']: (r['players_count'], r['reports_count']) for r in dashboard_service.get_position_counts(conn)}
    new = {}
    for rows in by_origin.values():
        for r in rows:
            players, reports = new.get(r['position'], (0, 0))
            new[r['position']] = (players + r['players_count'], reports + r['reports_count'])
    assert new == old == {'Delantero': (4, 7), 'Portero': (1, 1)}


def test_position_summary_can_be_limited_to_one_group(scouting_db):
    conn = scouting_db
    add_player(conn, 'Chileno Uno', 'Chile', 'Delantero')
    add_player(conn, 'Argentino Dos', 'Argentina', 'Delantero')
    add_player(conn, 'Sin nacionalidad', None, 'Delantero')
    conn.commit()
    names = lambda origin: sorted(r['full_name'] for r in dashboard_service.get_position_summary(conn, 'Delantero', origin=origin))
    assert names(None) == ['Argentino Dos', 'Chileno Uno', 'Sin nacionalidad']
    assert names(CHILEAN) == ['Chileno Uno'] and names(FOREIGN) == ['Argentino Dos']


# --- Pantalla del Dashboard ---------------------------------------------------------------------------------------------------------

HIDDEN = dict(
    id=7, player_full_name='Jugador de prueba', player_position='Delantero', scout_name='Scout', report_date=date(2026, 10, 1),
    is_hidden=True, hidden_at=datetime(2026, 10, 2, 9, 30), hidden_by='Admin', rating=7, recommendation='Interesante',
    summary='Resumen de prueba ' + 'muy largo ' * 40, strengths='Fortaleza de prueba', weaknesses='Aspecto de prueba',
    match_observed='Partido', minutes_observed=60, raw_payload=None)
COUNTS = {
    CHILEAN: [dict(position='Delantero', players_count=2, reports_count=3)],
    FOREIGN: [dict(position='Portero', players_count=1, reports_count=1)],
    'unknown': [dict(position='Delantero', players_count=2, reports_count=4)],
}
SNAPSHOT = dict(player_count=3, report_count=8, hidden_report_count=49, scout_count=2, metric_count=0, metrics_are_demo=False,
                recent_reports=[], hybrid_player_count=0, demo_metric_count=0, sofascore_metric_count=0,
                total_players_in_db=3, metrics_label='Métricas objetivas')


@pytest.fixture
def dashboard(monkeypatch):
    monkeypatch.syspath_prepend(str(Path('app').resolve()))
    for key, value in [('PORTAL_MODE', '1'), ('DB_SCHEMA', 'scouting'), ('DISABLE_SOFASCORE_UPDATE', '1')]:
        monkeypatch.setenv(key, value)
    import portal
    import scouting.db
    import streamlit_app
    from scouting.repositories import sofascore_event_ingestion_repository as ingestion

    @contextmanager
    def connection():
        yield object()

    calls = dict(summary=Mock(return_value=[]), hidden=Mock(return_value=[HIDDEN]))
    monkeypatch.setattr(streamlit_app, 'get_connection', connection)
    monkeypatch.setattr(scouting.db, 'get_connection', connection)
    monkeypatch.setattr(ingestion, 'list_incomplete_coverage', lambda conn: [])
    monkeypatch.setattr(dashboard_service, 'get_dashboard_snapshot', lambda conn, recent_reports_limit=5: dict(SNAPSHOT))
    monkeypatch.setattr(dashboard_service, 'get_position_counts_by_origin', lambda conn: COUNTS)
    monkeypatch.setattr(dashboard_service, 'get_position_summary', calls['summary'])
    monkeypatch.setattr(streamlit_app, 'fetch_visible_reports', lambda conn, limit=50: [])
    monkeypatch.setattr(streamlit_app, 'fetch_hidden_reports', calls['hidden'])
    monkeypatch.setattr(streamlit_app.attribute_ratings_service, 'get_report_attribute_ratings', lambda conn, report_id: [])

    def run(user, state=None):
        monkeypatch.setattr(portal.accounts, 'resolve_session', lambda token: user)
        app = AppTest.from_string('import portal\nportal.main()', default_timeout=30)
        app.session_state['portal_session'] = {'synthetic': True}
        app.session_state['portal_module'] = 'Scouting'
        app.session_state['_portal_previous_module'] = 'Scouting'
        app.session_state['page'] = 'Dashboard'
        for key, value in (state or {}).items():
            app.session_state[key] = value
        return app.run()

    run.calls = calls
    return run


@pytest.mark.parametrize('user', [ADMIN, SCOUT])
def test_dashboard_shows_one_pitch_per_nationality_group(dashboard, user):
    app = dashboard(user)
    assert not app.exception, [e.value for e in app.exception]
    assert not app.error, [e.value for e in app.error]
    headings = [s.value for s in app.subheader]
    assert 'Mapa de posiciones · jugadores chilenos' in headings and 'Mapa de posiciones · jugadores extranjeros' in headings
    assert len(app.get('plotly_chart')) == 2, 'dos campogramas, no uno'
    captions = ' '.join(c.value for c in app.caption)
    assert '2 jugador(es) con 4 informe(s) no tienen nacionalidad en su ficha' in captions
    assert 'no aparecen en ninguno de los dos campogramas' in captions


def test_each_pitch_keeps_its_own_selection_and_filters_its_own_group(dashboard):
    app = dashboard(ADMIN, {'dashboard_chile_selected_position': 'Delantero'})
    assert not app.exception, [e.value for e in app.exception]
    dashboard.calls['summary'].assert_called_once()
    assert dashboard.calls['summary'].call_args.args[1] == 'Delantero' and dashboard.calls['summary'].call_args.kwargs == {'origin': CHILEAN}
    headings = ' '.join(m.value for m in app.markdown)
    assert 'Jugadores e informes — Delantero · jugadores chilenos' in headings and 'jugadores extranjeros' not in headings.split('Jugadores e informes')[-1]
    keys = {b.key for b in app.button}
    assert 'dashboard_chile_pitch_clear' in keys and 'dashboard_foreign_pitch_clear' not in keys

    both = dashboard(ADMIN, {'dashboard_chile_selected_position': 'Delantero', 'dashboard_foreign_selected_position': 'Portero'})
    assert not both.exception
    last_two = {(call.args[1], call.kwargs['origin']) for call in dashboard.calls['summary'].call_args_list[-2:]}
    assert last_two == {('Delantero', CHILEAN), ('Portero', FOREIGN)}


def test_clearing_one_pitch_does_not_clear_the_other(dashboard):
    app = dashboard(ADMIN, {'dashboard_chile_selected_position': 'Delantero', 'dashboard_foreign_selected_position': 'Portero'})
    app.button(key='dashboard_chile_pitch_clear').click().run()
    assert not app.exception
    assert 'dashboard_chile_selected_position' not in app.session_state
    assert app.session_state['dashboard_foreign_selected_position'] == 'Portero'


# --- Vista preliminar de los informes ocultos -----------------------------------------------------------------------------------------

@pytest.mark.parametrize('user', [ADMIN, SCOUT])
def test_dashboard_previews_hidden_reports_for_both_roles(dashboard, user):
    app = dashboard(user)
    assert not app.exception and not app.error
    dashboard.calls['hidden'].assert_called_once()
    assert dashboard.calls['hidden'].call_args.kwargs == {'limit': 5}, 'solo los más recientes'
    previews = [d.value for d in app.dataframe if 'Resumen (inicio)' in d.value.columns]
    assert len(previews) == 1
    row = previews[0].iloc[0]
    assert row['Jugador'] == 'Jugador de prueba' and row['Ocultado por'] == 'Admin' and row['Recomendación'] == 'Interesante'
    assert row['Valoración'] == 7.0, 'sin los decimales de sobra del tipo numeric'
    assert row['Resumen (inicio)'].startswith('Resumen de prueba') and row['Resumen (inicio)'].endswith('…')
    assert len(row['Resumen (inicio)']) <= 140
    captions = ' '.join(c.value for c in app.caption)
    assert 'Se muestran los 1 más recientes de 49 informes ocultos.' in captions
    assert app.button(key='dashboard_open_hidden_reports')


def test_hidden_preview_opens_the_management_page(dashboard):
    app = dashboard(SCOUT)
    app.button(key='dashboard_open_hidden_reports').click().run()
    assert not app.exception, [e.value for e in app.exception]
    assert app.session_state['page'] == 'Informes ocultos'
    assert 'Jugador de prueba' in app.selectbox(key='hidden_selected_report_label').value


def test_hidden_preview_without_hidden_reports_says_so(dashboard):
    dashboard.calls['hidden'].return_value = []
    app = dashboard(ADMIN)
    assert not app.exception and not app.error
    assert not [d for d in app.dataframe if 'Resumen (inicio)' in d.value.columns]
    assert not [b for b in app.button if b.key == 'dashboard_open_hidden_reports']


# --- El campograma sigue siendo el mismo componente -----------------------------------------------------------------------------------------

def test_pitch_helpers_keep_the_original_keys_by_default_and_separate_the_new_ones():
    sys.path.insert(0, str(ROOT / 'app'))
    from ui import pitch_map
    assert pitch_map.selection_state_key() == 'dashboard_selected_position' and pitch_map.chart_key() == 'dashboard_pitch_chart'
    assert pitch_map.selection_state_key('dashboard_chile') != pitch_map.selection_state_key('dashboard_foreign')
    labels = {p: p[:3] for p in pitch_map.PITCH_COORDS}
    one = pitch_map.build_pitch_figure(short_labels=labels, counts={}, selected=None, uirevision='a')
    two = pitch_map.build_pitch_figure(short_labels=labels, counts={}, selected=None, uirevision='b')
    assert one.layout.uirevision == 'a' and two.layout.uirevision == 'b' and one is not two
    default = pitch_map.build_pitch_figure(short_labels=labels, counts={}, selected=None)
    assert default.layout.uirevision == 'dashboard_pitch_stable' and default.layout.height == 540
    assert pitch_map.build_pitch_figure(short_labels=labels, counts={}, selected=None, height=440).layout.height == 440
