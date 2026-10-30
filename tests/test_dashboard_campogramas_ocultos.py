"""Dashboard de Scouting tras la reunión con Pablo (13-10-2026): dos campogramas (chilenos y extranjeros) y vista
preliminar de los informes ocultos. Datos ficticios."""
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
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
HIDDEN_COUNTS = [dict(position='Delantero', players_count=1, reports_count=1)]
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

    calls = dict(summary=Mock(return_value=[]), hidden=Mock(return_value=[HIDDEN]),
                 hidden_counts=Mock(return_value=list(HIDDEN_COUNTS)), hidden_by_position=Mock(return_value=[HIDDEN]))
    monkeypatch.setattr(streamlit_app, 'get_connection', connection)
    monkeypatch.setattr(dashboard_service, 'get_hidden_position_counts', calls['hidden_counts'])
    monkeypatch.setattr(streamlit_app, 'fetch_hidden_reports_by_position', calls['hidden_by_position'])
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
    assert len(app.get('plotly_chart')) == 3, 'uno por grupo de nacionalidad y el de los informes ocultos'
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
    assert row['Valoración'] == '7', 'sin los decimales de sobra del tipo numeric'
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


# --- Campograma de los informes ocultos por posición (30-10-2026) -------------------------------------------------------------------------

HIDDEN_PITCH_TITLE = 'Mapa de posiciones · informes ocultos'


def captions_of(app):
    return ' '.join(c.value for c in app.caption)


def position_table(app):
    tables = [d.value for d in app.dataframe if 'Informes ocultos' in d.value.columns]
    assert len(tables) == 1, 'una sola tabla por posición junto al campograma'
    return tables[0]


def test_split_hidden_position_counts_never_loses_a_report():
    rows = [dict(position='Delantero', players_count=2, reports_count=3), dict(position='Libero', players_count=1, reports_count=1),
            dict(position=None, players_count=1, reports_count=2), dict(position='', players_count=1, reports_count=4),
            dict(position='Portero', players_count=1, reports_count=5)]
    out = dashboard_service.split_hidden_position_counts(rows, ['Delantero', 'Portero'])
    assert out['on_map'] == [rows[0], rows[4]]
    assert out['off_map'] == [rows[1]]
    assert out['no_position'] == dict(position=None, players_count=2, reports_count=6)
    counted = sum(r['reports_count'] for r in out['on_map'] + out['off_map']) + out['no_position']['reports_count']
    assert counted == sum(r['reports_count'] for r in rows) == 15


def test_split_hidden_position_counts_without_unplaceable_reports():
    out = dashboard_service.split_hidden_position_counts([dict(position='Portero', players_count=1, reports_count=2)], ['Portero'])
    assert out == dict(on_map=[dict(position='Portero', players_count=1, reports_count=2)], off_map=[], no_position=None)
    assert dashboard_service.split_hidden_position_counts([], ['Portero']) == dict(on_map=[], off_map=[], no_position=None)


@pytest.mark.parametrize('user', [ADMIN, SCOUT])
def test_dashboard_shows_the_hidden_reports_pitch_for_both_roles(dashboard, user):
    app = dashboard(user)
    assert not app.exception, [e.value for e in app.exception]
    assert not app.error, [e.value for e in app.error]
    assert HIDDEN_PITCH_TITLE in [s.value for s in app.subheader]
    dashboard.calls['hidden_counts'].assert_called_once()
    assert position_table(app).to_dict('records') == [{'Posición': 'Delantero', 'Jugadores': 1, 'Informes ocultos': 1}]
    dashboard.calls['hidden_by_position'].assert_not_called()   # sin posición elegida no se piden más informes
    assert 'dashboard_open_hidden_reports' in {b.key for b in app.button}, 'la vista preliminar sigue donde estaba'


def test_hidden_pitch_is_not_shown_without_hidden_reports(dashboard):
    dashboard.calls['hidden'].return_value = []
    app = dashboard(ADMIN)
    assert not app.exception and not app.error
    assert HIDDEN_PITCH_TITLE not in [s.value for s in app.subheader]
    dashboard.calls['hidden_counts'].assert_not_called()
    assert len(app.get('plotly_chart')) == 2, 'solo los dos campogramas por nacionalidad'


def test_choosing_a_position_lists_its_hidden_reports(dashboard):
    dashboard.calls['hidden_counts'].return_value = [dict(position='Delantero', players_count=1, reports_count=1),
                                                     dict(position='Portero', players_count=2, reports_count=2)]
    app = dashboard(ADMIN, {'hidden_selected_position': 'Delantero'})
    assert not app.exception, [e.value for e in app.exception]
    dashboard.calls['hidden_by_position'].assert_called_once()
    call = dashboard.calls['hidden_by_position'].call_args
    assert call.args[1] == 'Delantero' and call.kwargs == {'limit': 200}
    assert 'Informes ocultos — Delantero' in ' '.join(m.value for m in app.markdown)
    listings = [d.value for d in app.dataframe if 'Resumen (inicio)' in d.value.columns]
    assert len(listings) == 2, 'la vista preliminar y los informes de la posición elegida'
    assert 'hidden_pitch_clear' in {b.key for b in app.button}


def test_a_position_without_hidden_reports_says_so_and_asks_nothing_more(dashboard):
    app = dashboard(ADMIN, {'hidden_selected_position': 'Portero'})
    assert not app.exception, [e.value for e in app.exception]
    dashboard.calls['hidden_by_position'].assert_not_called()
    assert 'No hay informes ocultos de esta posición.' in captions_of(app)


def test_clearing_the_hidden_pitch_filter_leaves_the_other_pitches_alone(dashboard):
    app = dashboard(ADMIN, {'hidden_selected_position': 'Delantero', 'dashboard_chile_selected_position': 'Delantero'})
    app.button(key='hidden_pitch_clear').click().run()
    assert not app.exception, [e.value for e in app.exception]
    assert 'hidden_selected_position' not in app.session_state
    assert app.session_state['dashboard_chile_selected_position'] == 'Delantero'


def test_reports_without_position_are_counted_in_the_table_not_lost(dashboard):
    dashboard.calls['hidden_counts'].return_value = [
        dict(position='Delantero', players_count=1, reports_count=1),
        dict(position='Libero', players_count=1, reports_count=3),
        dict(position=None, players_count=2, reports_count=5)]
    app = dashboard(ADMIN)
    assert not app.exception, [e.value for e in app.exception]
    rows = position_table(app).to_dict('records')
    assert {'Posición': 'Sin posición en la ficha', 'Jugadores': 2, 'Informes ocultos': 5} in rows
    assert {'Posición': 'Libero (no está en el campograma)', 'Jugadores': 1, 'Informes ocultos': 3} in rows
    assert sum(r['Informes ocultos'] for r in rows) == 9, 'ningún informe oculto desaparece de la cuenta'
    captions = captions_of(app)
    assert '2 jugador(es) con 5 informe(s) oculto(s) no tienen posición en su ficha' in captions
    assert 'posición que el campograma no reconoce (Libero)' in captions


def test_hidden_page_shows_the_pitch_and_filters_the_list_by_the_chosen_position(dashboard):
    app = dashboard(ADMIN, {'page': 'Informes ocultos'})
    assert not app.exception, [e.value for e in app.exception]
    assert not app.error, [e.value for e in app.error]
    assert HIDDEN_PITCH_TITLE in [s.value for s in app.subheader]
    dashboard.calls['hidden'].assert_called_once()
    assert dashboard.calls['hidden'].call_args.kwargs == {'limit': 200}
    dashboard.calls['hidden_by_position'].assert_not_called()

    filtered = dashboard(ADMIN, {'page': 'Informes ocultos', 'hidden_selected_position': 'Delantero'})
    assert not filtered.exception, [e.value for e in filtered.exception]
    dashboard.calls['hidden_by_position'].assert_called_once()
    assert dashboard.calls['hidden_by_position'].call_args.args[1] == 'Delantero'
    assert dashboard.calls['hidden'].call_count == 1, 'con una posición elegida se piden solo los de esa posición'
    assert 'Jugador de prueba' in filtered.selectbox(key='hidden_selected_report_label').value


def test_hidden_page_with_a_position_that_has_no_reports_explains_it(dashboard):
    dashboard.calls['hidden_by_position'].return_value = []
    app = dashboard(ADMIN, {'page': 'Informes ocultos', 'hidden_selected_position': 'Portero'})
    assert not app.exception, [e.value for e in app.exception]
    assert any('No hay informes ocultos de la posición Portero' in i.value for i in app.info)
    assert not [s for s in app.selectbox if s.key == 'hidden_selected_report_label']


def test_hidden_page_forgets_a_stale_position_when_no_hidden_report_is_left(dashboard):
    """Tras restaurar el último informe oculto no hay campograma ni «Limpiar filtro»: la posición elegida no puede quedar atrapada."""
    dashboard.calls['hidden'].return_value = []
    dashboard.calls['hidden_counts'].return_value = []
    app = dashboard(ADMIN, {'page': 'Informes ocultos', 'hidden_selected_position': 'Delantero'})
    assert not app.exception, [e.value for e in app.exception]
    assert 'hidden_selected_position' not in app.session_state
    dashboard.calls['hidden_by_position'].assert_not_called()
    assert not app.info, 'ningún mensaje que mande a un botón que no existe'


def test_hidden_page_without_hidden_reports_keeps_its_empty_state(dashboard):
    dashboard.calls['hidden'].return_value = []
    dashboard.calls['hidden_counts'].return_value = []
    app = dashboard(ADMIN, {'page': 'Informes ocultos'})
    assert not app.exception and not app.error
    assert HIDDEN_PITCH_TITLE not in [s.value for s in app.subheader]
    assert not app.info


def test_leaving_the_page_forgets_the_hidden_pitch_selection(dashboard):
    sys.path.insert(0, str(ROOT / 'app'))
    import streamlit_app
    assert 'hidden_selected_position' in streamlit_app.UI_SELECTION_KEYS


# --- Posición y valoración en «Actividad reciente» y el botón «Actualizar» (30-10-2026) -----------------------------------------------------

def recent(**changes):
    row = dict(id=1, report_date=date(2026, 10, 1), player_full_name='Jugador Uno', player_position='Delantero', position_observed=None,
               scout_name='Scout', competition='Primera', rating=Decimal('6.000000'), recommendation='Interesante')
    row.update(changes)
    return row


def test_recent_activity_never_shows_none_as_a_position(dashboard, monkeypatch):
    rows = [recent(id=1, player_position=None, position_observed=None, rating=None),
            recent(id=2, player_full_name='Jugador Dos', player_position=None, position_observed='Extremo derecho'),
            recent(id=3, player_full_name='Jugador Tres', player_position='Portero', position_observed='Delantero')]
    monkeypatch.setattr(dashboard_service, 'get_dashboard_snapshot',
                        lambda conn, recent_reports_limit=5: {**SNAPSHOT, 'recent_reports': rows})
    app = dashboard(ADMIN)
    assert not app.exception, [e.value for e in app.exception]
    table = next(d.value for d in app.dataframe if 'Fecha' in d.value.columns and 'Posición' in d.value.columns)
    assert list(table['Posición']) == ['—', 'Extremo derecho', 'Portero']
    assert 'None' not in ' '.join(str(v) for v in table['Posición'])
    assert 'significa que no hay dato' in captions_of(app)


def test_tables_show_a_dash_where_there_is_no_data_never_none_or_a_filled_in_rating(dashboard, monkeypatch):
    """Una celda vacía de una columna numérica se vería «None»: la valoración va como texto, «—» sin dato y sin decimales de sobra."""
    rows = [recent(id=1, rating=None, scout_name=None, competition=None, recommendation=None),
            recent(id=2, rating=Decimal('6.000000')),
            recent(id=3, rating=Decimal('7.500000')),
            recent(id=4, rating=Decimal('0'))]
    monkeypatch.setattr(dashboard_service, 'get_dashboard_snapshot',
                        lambda conn, recent_reports_limit=5: {**SNAPSHOT, 'recent_reports': rows})
    dashboard.calls['hidden'].return_value = [{**HIDDEN, 'rating': None, 'scout_name': None}]
    app = dashboard(ADMIN)
    assert not app.exception, [e.value for e in app.exception]
    activity = next(d.value for d in app.dataframe if 'Fecha' in d.value.columns and 'Competición' in d.value.columns)
    assert list(activity['Valoración']) == ['—', '6', '7.5', '0'], 'un 0 real se ve 0; la falta de dato, «—»'
    assert list(activity.iloc[0][['Scout', 'Competición', 'Recomendación']]) == ['—', '—', '—']
    preview = next(d.value for d in app.dataframe if 'Resumen (inicio)' in d.value.columns)
    assert preview.iloc[0]['Valoración'] == '—' and preview.iloc[0]['Scout'] == '—'
    for table in (activity, preview):
        assert not table.isna().any().any() and 'None' not in table.astype(str).to_numpy()


def test_refresh_button_reads_the_reports_again(dashboard, monkeypatch):
    snapshot = Mock(side_effect=lambda conn, recent_reports_limit=5: {**SNAPSHOT, 'recent_reports': [recent()]})
    monkeypatch.setattr(dashboard_service, 'get_dashboard_snapshot', snapshot)
    app = dashboard(ADMIN)
    assert snapshot.call_count == 1
    app.button(key='dashboard_refresh_recent').click().run()
    assert not app.exception, [e.value for e in app.exception]
    assert snapshot.call_count == 2, 'el botón vuelve a leer los informes de la base de datos'


@pytest.fixture
def visible_report(dashboard, monkeypatch):
    import streamlit_app
    report = recent(id=7, player_position=None, position_observed='Extremo derecho', rating=Decimal('6'), raw_payload=None,
                    is_hidden=False, summary='Resumen', strengths='Fortaleza', weaknesses='Debilidad')
    monkeypatch.setattr(streamlit_app, 'fetch_visible_reports', lambda conn, limit=50: [report])
    update = Mock()
    monkeypatch.setattr(streamlit_app, 'update_report_position_and_rating', update)
    dashboard.update = update
    return dashboard


def test_update_report_panel_sends_the_chosen_position_and_rating(visible_report):
    app = visible_report(ADMIN)
    assert not app.exception, [e.value for e in app.exception]
    assert app.button(key='dashboard_update_report_7').label.endswith('Actualizar informe')
    app.selectbox(key='dashboard_player_pos_7').select('Delantero')
    app.text_input(key='dashboard_pos_obs_7').set_value('Extremo izquierdo')
    app.slider(key='dashboard_rating_7').set_value(8.5)
    app.button(key='dashboard_update_report_7').click().run()
    assert not app.exception, [e.value for e in app.exception]
    visible_report.update.assert_called_once()
    call = visible_report.update.call_args
    assert call.args[1] == 7
    assert call.kwargs == dict(position_observed='Extremo izquierdo', rating=8.5, player_position='Delantero')
    assert any('Informe de Jugador Uno actualizado.' in s.value for s in app.success)


def test_update_report_panel_can_leave_the_report_without_rating(visible_report):
    app = visible_report(ADMIN)
    app.checkbox(key='dashboard_has_rating_7').uncheck().run()
    app.button(key='dashboard_update_report_7').click().run()
    assert not app.exception, [e.value for e in app.exception]
    call = visible_report.update.call_args
    assert call.kwargs['rating'] is None, 'sin valoración: nunca un 0 ni un 6 de relleno'
    assert call.kwargs['player_position'] is None, 'sin elegir posición no se toca la ficha'


def test_update_report_panel_only_offers_the_ficha_position_when_it_is_missing(dashboard, monkeypatch):
    import streamlit_app
    report = recent(id=7, player_position='Portero', rating=None, raw_payload=None, is_hidden=False)
    monkeypatch.setattr(streamlit_app, 'fetch_visible_reports', lambda conn, limit=50: [report])
    app = dashboard(ADMIN)
    assert not app.exception, [e.value for e in app.exception]
    assert not [s for s in app.selectbox if s.key == 'dashboard_player_pos_7'], 'una posición que ya existe no se pisa'
    assert app.checkbox(key='dashboard_has_rating_7').value is False, 'un informe sin valoración empieza sin valoración'


def test_update_report_panel_reports_a_failure_instead_of_hiding_it(visible_report):
    visible_report.update.side_effect = ValueError('La valoración general debe estar entre 0 y 10.')
    app = visible_report(ADMIN)
    app.button(key='dashboard_update_report_7').click().run()
    assert not app.exception, [e.value for e in app.exception]
    assert any('No se pudo actualizar: La valoración general debe estar entre 0 y 10.' in e.value for e in app.error)


def test_hidden_page_offers_the_same_update_panel(dashboard, monkeypatch):
    import streamlit_app
    update = Mock()
    monkeypatch.setattr(streamlit_app, 'update_report_position_and_rating', update)
    app = dashboard(SCOUT, {'page': 'Informes ocultos'})
    assert not app.exception, [e.value for e in app.exception]
    app.slider(key='hidden_rating_7').set_value(9.0)
    app.button(key='hidden_update_report_7').click().run()
    assert not app.exception, [e.value for e in app.exception]
    update.assert_called_once()
    assert update.call_args.args[1] == 7
    # El texto vacío viaja tal cual: es el servicio quien lo guarda como «sin posición observada» (probado en test_report_position_rating).
    assert update.call_args.kwargs == dict(position_observed='', rating=9.0, player_position=None)


# --- Informes ocultos por posición en PostgreSQL ------------------------------------------------------------------------------------------

def test_hidden_position_counts_only_count_hidden_reports_and_keep_the_unplaceable_ones(scouting_db, monkeypatch):
    monkeypatch.delenv('PORTAL_MODE', raising=False)
    conn = scouting_db
    add_player(conn, 'Delantero A', 'Chile', 'Delantero', reports=1, hidden=2)
    add_player(conn, 'Delantero B', 'Chile', 'Delantero', reports=0, hidden=1)
    add_player(conn, 'Portero C', 'Argentina', 'Portero', reports=3, hidden=0)     # sin informes ocultos: no cuenta
    add_player(conn, 'Sin posición D', 'Chile', None, reports=0, hidden=2)
    add_player(conn, 'En blanco E', 'Chile', '  ', reports=0, hidden=1)
    add_player(conn, 'Rara F', 'Chile', 'Libero', reports=0, hidden=1)
    conn.commit()
    rows = dashboard_service.get_hidden_position_counts(conn)
    assert {r['position']: (r['players_count'], r['reports_count']) for r in rows} == {
        'Delantero': (2, 3), 'Libero': (1, 1), None: (2, 3)}
    assert rows[-1]['position'] is None, 'los jugadores sin posición van al final'
    hidden_in_db = conn.execute('SELECT count(*) FROM scouting_reports WHERE is_hidden').fetchone()[0]
    assert sum(r['reports_count'] for r in rows) == hidden_in_db == 7, 'todos los informes ocultos están contados'


def test_hidden_position_counts_are_empty_without_hidden_reports(scouting_db, monkeypatch):
    monkeypatch.delenv('PORTAL_MODE', raising=False)
    add_player(scouting_db, 'Jugador visible', 'Chile', 'Delantero', reports=2)
    scouting_db.commit()
    assert dashboard_service.get_hidden_position_counts(scouting_db) == []


def test_hidden_reports_by_position_return_only_hidden_ones_newest_first(scouting_db, monkeypatch):
    monkeypatch.delenv('PORTAL_MODE', raising=False)
    from scouting.services import reports_service
    conn = scouting_db
    first = add_player(conn, 'Delantero A', 'Chile', 'Delantero', reports=1, hidden=1)
    second = add_player(conn, 'Delantero B', 'Chile', 'Delantero', reports=0, hidden=1)
    add_player(conn, 'Portero C', 'Chile', 'Portero', reports=0, hidden=1)
    conn.execute("UPDATE scouting_reports SET hidden_at = '2026-10-02' WHERE player_id = %s AND is_hidden", (first,))
    conn.execute("UPDATE scouting_reports SET hidden_at = '2026-10-05' WHERE player_id = %s AND is_hidden", (second,))
    conn.commit()
    rows = reports_service.fetch_hidden_reports_by_position(conn, 'Delantero')
    assert [r['player_full_name'] for r in rows] == ['Delantero B', 'Delantero A']
    assert all(r['is_hidden'] and r['player_position'] == 'Delantero' for r in rows), 'los visibles no entran'
    assert [r['player_full_name'] for r in reports_service.fetch_hidden_reports_by_position(conn, 'Delantero', limit=1)] == ['Delantero B']
    assert reports_service.fetch_hidden_reports_by_position(conn, 'Lateral derecho') == []


def test_hidden_reports_without_position_can_be_listed(scouting_db, monkeypatch):
    monkeypatch.delenv('PORTAL_MODE', raising=False)
    from scouting.services import reports_service
    conn = scouting_db
    add_player(conn, 'Sin posición', 'Chile', None, reports=0, hidden=1)
    add_player(conn, 'En blanco', 'Chile', '   ', reports=0, hidden=1)
    add_player(conn, 'Con posición', 'Chile', 'Delantero', reports=0, hidden=1)
    conn.commit()
    names = sorted(r['player_full_name'] for r in reports_service.fetch_hidden_reports_by_position(conn, None))
    assert names == ['En blanco', 'Sin posición']


@pytest.mark.parametrize('user', [None, {**SCOUT, 'active': False}])
def test_hidden_position_reads_need_a_valid_session(monkeypatch, user):
    from scouting.portal import accounts, security
    from scouting.repositories import reports_repository
    from scouting.services import reports_service
    monkeypatch.setenv('PORTAL_MODE', '1')
    monkeypatch.setattr(accounts, 'resolve_session', lambda token: user)
    counts, listing = Mock(), Mock()
    monkeypatch.setattr(dashboard_repository, 'get_hidden_position_counts', counts)
    monkeypatch.setattr(reports_repository, 'get_hidden_reports_by_position', listing)
    with security.session_scope({}, verified_user=user):
        with pytest.raises(PermissionError):
            dashboard_service.get_hidden_position_counts(object())
        with pytest.raises(PermissionError):
            reports_service.fetch_hidden_reports_by_position(object(), 'Delantero')
    counts.assert_not_called()
    listing.assert_not_called()