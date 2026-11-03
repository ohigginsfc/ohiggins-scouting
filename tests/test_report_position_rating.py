"""Posición y valoración de los informes de Scouting (petición del 30-10-2026). Datos ficticios.

* En el Dashboard la posición no puede salir como «None» y la valoración no puede ser un 6 por defecto.
* «Actualizar informe» corrige la posición y la valoración en el momento, con las mismas reglas de permisos de siempre.
"""
from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from streamlit.testing.v1 import AppTest

from scouting.portal import accounts, security
from scouting.repositories import players_repository, reports_repository
from scouting.services import reports_service

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'app'
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

from ui.presentation import format_rating_for_ui, report_position_for_ui  # noqa: E402

ADMIN = dict(id='synthetic-admin', display_name='Admin', role='admin', active=True)
SCOUT = dict(id='synthetic-scout', display_name='Scout', role='scout', active=True)
OTHER_SCOUT = dict(id='synthetic-other-scout', display_name='Otro scout', role='scout', active=True)


# --- Cómo se muestran la posición y la valoración ------------------------------------------------------------------------------

@pytest.mark.parametrize('report, expected', [
    ({'player_position': 'Delantero', 'position_observed': 'Extremo derecho'}, 'Delantero'),
    ({'player_position': None, 'position_observed': 'Extremo derecho'}, 'Extremo derecho'),
    ({'player_position': '', 'position_observed': '  Carril izquierdo  '}, 'Carril izquierdo'),
    ({'player_position': '   ', 'position_observed': None}, '—'),
    ({'player_position': None, 'position_observed': None}, '—'),
    ({'player_position': 'None', 'position_observed': 'nan'}, '—'),      # lo que deja una conversión a texto
    ({'player_position': float('nan'), 'position_observed': None}, '—'),
    ({}, '—'),
])
def test_report_position_never_shows_none(report, expected):
    assert report_position_for_ui(report) == expected


def test_ficha_position_wins_over_the_one_observed_in_the_match():
    report = {'player_position': 'Mediocentro', 'position_observed': 'Delantero'}
    assert report_position_for_ui(report) == 'Mediocentro'


@pytest.mark.parametrize('value, expected', [
    (None, '—'), (float('nan'), '—'), ('', '—'), ('sin dato', '—'),
    (Decimal('6.000000'), '6'), (Decimal('6.5'), '6.5'), (7, '7'), (7.25, '7.25'), ('8.5', '8.5'),
])
def test_rating_shows_a_dash_when_there_is_no_value_and_no_extra_decimals(value, expected):
    assert format_rating_for_ui(value) == expected


def test_a_real_zero_is_a_value_not_a_missing_rating():
    assert format_rating_for_ui(0) == '0' and format_rating_for_ui(Decimal('0')) == '0'


@pytest.mark.parametrize('with_recommendation', [False, True])
def test_report_table_keeps_ratings_numeric_for_sorting_and_formats_missing_values(with_recommendation):
    import pandas as pd
    from streamlit_app import _style_recommendation_dataframe

    rows = [{'Valoración': value, 'Scout': None} for value in [Decimal('1'), Decimal('2'), Decimal('10'), None, Decimal('6.5'), 0]]
    if with_recommendation:
        for row in rows:
            row['Recomendación'] = 'Interesante'
    styled = _style_recommendation_dataframe(rows)
    data = styled if isinstance(styled, pd.DataFrame) else styled.data
    assert pd.api.types.is_numeric_dtype(data['Valoración']), 'sorting must use scores rather than their text labels'
    ordered = data.sort_values('Valoración', ascending=False)['Valoración'].tolist()
    assert ordered[:-1] == [10, 6.5, 2, 1, 0] and pd.isna(ordered[-1])
    assert pd.isna(data.loc[3, 'Valoración']), 'a missing score stays missing in the underlying data'
    assert data['Scout'].tolist() == ['—'] * len(rows)
    html = styled.to_html()
    assert '>—</td>' in html and '>6.5</td>' in html and '>10</td>' in html
    assert '>nan</td>' not in html and '>10.000000</td>' not in html


# --- «Actualizar informe»: reglas del servicio, sin base de datos ---------------------------------------------------------------

@pytest.fixture
def writes(monkeypatch):
    monkeypatch.delenv('PORTAL_MODE', raising=False)
    monkeypatch.setattr(reports_repository, 'get_report_by_id', lambda conn, report_id: {'id': report_id, 'player_id': 3})
    update = Mock()
    fill = Mock(return_value=True)
    monkeypatch.setattr(reports_repository, 'update_report_fields', update)
    monkeypatch.setattr(players_repository, 'set_player_position_if_missing', fill)
    return update, fill


@pytest.mark.parametrize('bad', [-0.5, 10.5, 11, float('nan'), float('inf'), float('-inf'), 'abc'])
def test_invalid_rating_is_rejected_before_anything_is_written(writes, bad):
    update, fill = writes
    with pytest.raises(ValueError, match='entre 0 y 10'):
        reports_service.update_report_position_and_rating(
            object(), 7, position_observed='Extremo', rating=bad, player_position='Delantero')
    update.assert_not_called()
    fill.assert_not_called()


def test_unknown_ficha_position_is_rejected_before_anything_is_written(writes):
    update, fill = writes
    with pytest.raises(ValueError, match='Posición no válida'):
        reports_service.update_report_position_and_rating(
            object(), 7, position_observed='Extremo', rating=Decimal('7'), player_position='Libero')
    update.assert_not_called()
    fill.assert_not_called()


def test_missing_report_is_reported_not_ignored(monkeypatch):
    monkeypatch.delenv('PORTAL_MODE', raising=False)
    monkeypatch.setattr(reports_repository, 'get_report_by_id', lambda conn, report_id: None)
    update = Mock()
    monkeypatch.setattr(reports_repository, 'update_report_fields', update)
    with pytest.raises(ValueError, match='no encontrado'):
        reports_service.update_report_position_and_rating(object(), 7, position_observed='X', rating=None)
    update.assert_not_called()


def test_no_rating_is_saved_as_no_rating_and_blank_position_as_no_position(writes):
    update, fill = writes
    conn = Mock()
    reports_service.update_report_position_and_rating(conn, 7, position_observed='   ', rating=None)
    update.assert_called_once_with(conn, 7, position_observed=None, rating=None, commit=False)
    fill.assert_not_called()
    conn.commit.assert_called_once()


@pytest.mark.parametrize('value', [0, 10, '0', 6.5, Decimal('9.5')])
def test_valid_ratings_including_the_two_ends_of_the_scale_are_saved(writes, value):
    update, _ = writes
    reports_service.update_report_position_and_rating(Mock(), 7, position_observed=' Extremo ', rating=value)
    kwargs = update.call_args.kwargs
    assert kwargs['position_observed'] == 'Extremo' and kwargs['rating'] == Decimal(str(value))


def test_ficha_position_is_completed_only_when_one_is_chosen(writes):
    update, fill = writes
    conn = Mock()
    reports_service.update_report_position_and_rating(
        conn, 7, position_observed=None, rating=None, player_position='Delantero')
    fill.assert_called_once_with(conn, 3, 'Delantero', commit=False)


def test_report_and_ficha_are_written_in_one_transaction(writes):
    """Las dos escrituras no confirman por separado: una sola confirmación al final."""
    update, fill = writes
    conn = Mock()
    reports_service.update_report_position_and_rating(
        conn, 7, position_observed='Extremo', rating=Decimal('7'), player_position='Delantero')
    assert update.call_args.kwargs['commit'] is False and fill.call_args.kwargs['commit'] is False
    conn.commit.assert_called_once()
    conn.rollback.assert_not_called()


def test_a_failure_while_writing_rolls_everything_back(writes):
    update, fill = writes
    fill.side_effect = RuntimeError('base de datos caída')
    conn = Mock()
    with pytest.raises(RuntimeError, match='caída'):
        reports_service.update_report_position_and_rating(
            conn, 7, position_observed='Extremo', rating=Decimal('7'), player_position='Delantero')
    update.assert_called_once()
    conn.rollback.assert_called_once()
    conn.commit.assert_not_called()


# --- Permisos del portal: los mismos que editar un informe -------------------------------------------------------------------

OWN = dict(id=7, player_id=3, is_hidden=False, raw_payload={'portal_owner_id': SCOUT['id']})
OF_ANOTHER = dict(id=7, player_id=3, is_hidden=False, raw_payload={'portal_owner_id': ADMIN['id']})
HIDDEN_OF_ANOTHER = {**OF_ANOTHER, 'is_hidden': True}


@pytest.mark.parametrize('user, report, allowed', [
    (SCOUT, OWN, True),
    (SCOUT, OF_ANOTHER, False),
    (SCOUT, HIDDEN_OF_ANOTHER, True),       # los scouts también gestionan los informes ocultos
    (OTHER_SCOUT, OWN, False),
    (ADMIN, OWN, True),
    (ADMIN, OF_ANOTHER, True),
])
def test_portal_update_follows_the_same_rules_as_editing_a_report(monkeypatch, user, report, allowed):
    monkeypatch.setenv('PORTAL_MODE', '1')
    monkeypatch.setattr(reports_repository, 'get_report_by_id', lambda *args: report)
    update, fill = Mock(), Mock()
    monkeypatch.setattr(reports_repository, 'update_report_fields', update)
    monkeypatch.setattr(players_repository, 'set_player_position_if_missing', fill)

    def act():
        reports_service.update_report_position_and_rating(
            Mock(), 7, position_observed='Extremo', rating=Decimal('7'), player_position='Delantero')

    with security.session_scope({}, verified_user=user):
        if allowed:
            act()
            update.assert_called_once()
            fill.assert_called_once()
        else:
            with pytest.raises(PermissionError):
                act()
            update.assert_not_called()
            fill.assert_not_called()


@pytest.mark.parametrize('user', [None, {**SCOUT, 'active': False}])
def test_portal_update_needs_a_valid_session(monkeypatch, user):
    monkeypatch.setenv('PORTAL_MODE', '1')
    monkeypatch.setattr(accounts, 'resolve_session', lambda token: user)
    monkeypatch.setattr(reports_repository, 'get_report_by_id', lambda *args: OWN)
    update = Mock()
    monkeypatch.setattr(reports_repository, 'update_report_fields', update)
    with security.session_scope({}, verified_user=user), pytest.raises(PermissionError):
        reports_service.update_report_position_and_rating(object(), 7, position_observed='X', rating=None)
    update.assert_not_called()


def test_an_invalid_value_does_not_leak_through_a_denied_report(monkeypatch):
    """Primero se comprueba el permiso: quien no puede editar el informe no averigua nada de él."""
    monkeypatch.setenv('PORTAL_MODE', '1')
    monkeypatch.setattr(reports_repository, 'get_report_by_id', lambda *args: OF_ANOTHER)
    with security.session_scope({}, verified_user=SCOUT), pytest.raises(PermissionError):
        reports_service.update_report_position_and_rating(object(), 7, position_observed='X', rating=99)


# --- Contra PostgreSQL ---------------------------------------------------------------------------------------------------------

@pytest.fixture
def scouting_db():
    dsn = os.getenv('SCOUTING_TEST_DATABASE_URL')
    if not dsn:
        pytest.skip('Requires disposable local PostgreSQL via SCOUTING_TEST_DATABASE_URL')
    params = psycopg.conninfo.conninfo_to_dict(dsn)
    assert params.get('host') in {'localhost', '127.0.0.1', '::1'} and params.get('dbname') == 'scouting_test'
    schema = 'report_test_' + uuid4().hex
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


def add_report(conn, name, position, rating=Decimal('6'), observed=None):
    player_id = conn.execute(
        'INSERT INTO players (full_name, normalized_name, position) VALUES (%s, %s, %s) RETURNING id',
        (name, name.lower(), position)).fetchone()[0]
    report_id = conn.execute(
        "INSERT INTO scouting_reports (player_id, source_type, scout_name, report_date, recommendation, rating, position_observed) "
        "VALUES (%s, 'manual', 'Scout', '2026-10-01', 'Seguir monitorizando', %s, %s) RETURNING id",
        (player_id, rating, observed)).fetchone()[0]
    conn.commit()
    return player_id, report_id


def read(conn, report_id):
    return conn.execute(
        'SELECT sr.rating, sr.position_observed, p.position FROM scouting_reports sr JOIN players p ON p.id = sr.player_id '
        'WHERE sr.id = %s', (report_id,)).fetchone()


def test_postgres_clearing_the_rating_stores_null_and_not_zero(scouting_db, monkeypatch):
    monkeypatch.delenv('PORTAL_MODE', raising=False)
    _, report_id = add_report(scouting_db, 'Jugador Uno', 'Delantero', rating=Decimal('6'))
    reports_service.update_report_position_and_rating(scouting_db, report_id, position_observed=None, rating=None)
    assert read(scouting_db, report_id)[0] is None
    reports_service.update_report_position_and_rating(scouting_db, report_id, position_observed=None, rating=0)
    assert read(scouting_db, report_id)[0] == 0, 'un 0 elegido a propósito sí es un valor'


def test_postgres_observed_position_is_trimmed_and_can_be_erased(scouting_db, monkeypatch):
    monkeypatch.delenv('PORTAL_MODE', raising=False)
    _, report_id = add_report(scouting_db, 'Jugador Dos', 'Delantero', observed='Banda')
    reports_service.update_report_position_and_rating(
        scouting_db, report_id, position_observed='  Extremo derecho  ', rating=Decimal('8.5'))
    assert read(scouting_db, report_id)[:2] == (Decimal('8.5'), 'Extremo derecho')
    reports_service.update_report_position_and_rating(scouting_db, report_id, position_observed='', rating=Decimal('8.5'))
    assert read(scouting_db, report_id)[1] is None


def test_postgres_ficha_position_is_filled_only_when_missing(scouting_db, monkeypatch):
    monkeypatch.delenv('PORTAL_MODE', raising=False)
    _, without = add_report(scouting_db, 'Sin posición', None)
    _, blank = add_report(scouting_db, 'Posición en blanco', '   ')
    _, with_position = add_report(scouting_db, 'Con posición', 'Delantero')
    for report_id in (without, blank, with_position):
        reports_service.update_report_position_and_rating(
            scouting_db, report_id, position_observed=None, rating=Decimal('7'), player_position='Portero')
    assert read(scouting_db, without)[2] == 'Portero'
    assert read(scouting_db, blank)[2] == 'Portero'
    assert read(scouting_db, with_position)[2] == 'Delantero', 'nunca pisa una posición que ya existe'


def read_from_another_connection(conn, report_id):
    """Lo que ve otra sesión: solo lo que ya está confirmado (commit)."""
    dsn = os.environ['SCOUTING_TEST_DATABASE_URL']
    search_path = conn.execute('SHOW search_path').fetchone()[0]
    with psycopg.connect(dsn, options=f'-c search_path={search_path}') as other:
        return read(other, report_id)


def test_postgres_the_update_is_committed_for_other_sessions(scouting_db, monkeypatch):
    monkeypatch.delenv('PORTAL_MODE', raising=False)
    _, report_id = add_report(scouting_db, 'Jugador Cinco', None, rating=Decimal('6'))
    reports_service.update_report_position_and_rating(
        scouting_db, report_id, position_observed='Extremo', rating=None, player_position='Delantero')
    assert read_from_another_connection(scouting_db, report_id) == (None, 'Extremo', 'Delantero')


def test_postgres_a_failure_after_the_first_write_undoes_both(scouting_db, monkeypatch):
    monkeypatch.delenv('PORTAL_MODE', raising=False)
    _, report_id = add_report(scouting_db, 'Jugador Seis', None, rating=Decimal('6'), observed='Banda')
    original = players_repository.set_player_position_if_missing

    def writes_then_fails(conn, player_id, position, *, commit=True):
        original(conn, player_id, position, commit=commit)
        raise RuntimeError('fallo simulado antes de confirmar')

    monkeypatch.setattr(players_repository, 'set_player_position_if_missing', writes_then_fails)
    with pytest.raises(RuntimeError, match='simulado'):
        reports_service.update_report_position_and_rating(
            scouting_db, report_id, position_observed='Nueva', rating=Decimal('9'), player_position='Portero')
    assert read(scouting_db, report_id) == (Decimal('6'), 'Banda', None), 'ni el informe ni la ficha cambian a medias'
    assert read_from_another_connection(scouting_db, report_id) == (Decimal('6'), 'Banda', None)


def test_postgres_a_failed_validation_leaves_the_report_untouched(scouting_db, monkeypatch):
    monkeypatch.delenv('PORTAL_MODE', raising=False)
    player_id, report_id = add_report(scouting_db, 'Jugador Tres', None, rating=Decimal('5'), observed='Banda')
    with pytest.raises(ValueError):
        reports_service.update_report_position_and_rating(
            scouting_db, report_id, position_observed='Nueva', rating=Decimal('11'), player_position='Portero')
    with pytest.raises(ValueError):
        reports_service.update_report_position_and_rating(
            scouting_db, report_id, position_observed='Nueva', rating=Decimal('7'), player_position='Libero')
    assert read(scouting_db, report_id) == (Decimal('5'), 'Banda', None)


def test_postgres_scout_cannot_touch_the_report_of_another_user(scouting_db, monkeypatch):
    monkeypatch.setenv('PORTAL_MODE', '1')
    _, report_id = add_report(scouting_db, 'Jugador Cuatro', None, rating=Decimal('5'))
    scouting_db.execute(
        "UPDATE scouting_reports SET raw_payload = '{\"portal_owner_id\": \"synthetic-admin\"}'::jsonb WHERE id = %s",
        (report_id,))
    scouting_db.commit()
    with security.session_scope({}, verified_user=SCOUT), pytest.raises(PermissionError):
        reports_service.update_report_position_and_rating(
            scouting_db, report_id, position_observed='X', rating=Decimal('9'), player_position='Portero')
    assert read(scouting_db, report_id) == (Decimal('5'), None, None)
    with security.session_scope({}, verified_user=ADMIN):
        reports_service.update_report_position_and_rating(
            scouting_db, report_id, position_observed='X', rating=Decimal('9'), player_position='Portero')
    assert read(scouting_db, report_id) == (Decimal('9'), 'X', 'Portero')


# --- Alta manual: sin valoración salvo que el scout la pida ---------------------------------------------------------------------

@pytest.fixture
def manual_form(monkeypatch):
    monkeypatch.syspath_prepend(str(APP))
    for key, value in [('DB_SCHEMA', 'scouting'), ('DISABLE_SOFASCORE_UPDATE', '1')]:
        monkeypatch.setenv(key, value)
    monkeypatch.delenv('PORTAL_MODE', raising=False)
    import streamlit_app

    saved: list[dict] = []

    @contextmanager
    def connection():
        yield object()

    def create(conn, payload):
        saved.append(payload)
        return 1, True, 1

    monkeypatch.setattr(streamlit_app, 'get_connection', connection)
    monkeypatch.setattr(streamlit_app, 'create_scouting_report_from_dict', create)
    monkeypatch.setattr(streamlit_app.attribute_ratings_service, 'save_attribute_ratings_for_report', lambda *a, **k: None)
    app = AppTest.from_string('import streamlit_app\nstreamlit_app._render_new_report()', default_timeout=30).run()
    assert not app.exception, [e.value for e in app.exception]
    return SimpleNamespace(app=app, saved=saved)


def fill_required(app):
    app.text_input(key='mr_player_name').set_value('Jugador de prueba')
    app.text_input(key='mr_scout_name').set_value('Scout de prueba')


def test_manual_form_does_not_pre_fill_a_rating(manual_form):
    app = manual_form.app
    assert app.checkbox(key='mr_rate_report').value is False
    assert not [s for s in app.slider if s.key == 'mr_rating_scout'], 'sin pedirlo no hay valor que enviar'


def test_manual_report_is_saved_without_rating_unless_the_scout_asks_for_one(manual_form):
    app, saved = manual_form.app, manual_form.saved
    fill_required(app)
    app.button(key='mr_submit').click().run()
    assert not app.exception, [e.value for e in app.exception]
    assert len(saved) == 1 and saved[0]['rating'] is None, 'el 6 inicial del control ya no se guarda solo'


def test_manual_report_keeps_the_rating_the_scout_chose(manual_form):
    app, saved = manual_form.app, manual_form.saved
    fill_required(app)
    app.checkbox(key='mr_rate_report').check().run()
    app.slider(key='mr_rating_scout').set_value(7.5)
    app.button(key='mr_submit').click().run()
    assert not app.exception, [e.value for e in app.exception]
    assert len(saved) == 1 and saved[0]['rating'] == 7.5


def test_manual_form_is_back_to_no_rating_after_saving(manual_form):
    app, saved = manual_form.app, manual_form.saved
    fill_required(app)
    app.checkbox(key='mr_rate_report').check().run()
    app.button(key='mr_submit').click().run()
    assert not app.exception, [e.value for e in app.exception]
    assert saved[0]['rating'] == 6.0, 'quien marca la casilla y no mueve el control elige ese valor a propósito'
    assert app.checkbox(key='mr_rate_report').value is False
