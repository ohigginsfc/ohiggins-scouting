"""Ficha del jugador editable desde «Gestión de informes»: posición, equipo de procedencia y nacionalidad (Pablo, 20-11-2026).

* Se puede **cambiar** (pisar) lo que hubiera, o dejar sin dato (NULL); solo se escribe lo que se pide y lo que de verdad cambia.
* La nacionalidad decide en qué campograma sale el jugador (chilenos o extranjeros) y la posición, en qué punto del campo.
* Permisos: los mismos que editar el informe (Admin, todos; Scout, sus informes visibles y los ocultos; solo lectura, nadie).

Datos ficticios. La pantalla se prueba en `test_dashboard_campogramas_ocultos.py`.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.types.json import Json

from scouting.portal import readonly_pilot, security
from scouting.repositories import players_repository, reports_repository
from scouting.services import dashboard_service, nationality_service, reports_service

ROOT = Path(__file__).resolve().parents[1]

ADMIN = dict(id='synthetic-admin', display_name='Admin', role='admin', active=True)
SCOUT = dict(id='synthetic-scout', display_name='Scout', role='scout', active=True)
OTHER_SCOUT = dict(id='synthetic-other-scout', display_name='Otro scout', role='scout', active=True)


# --- Texto libre de la ficha ---------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize('value, expected', [
    (None, None), ('', None), ('   ', None), ('—', None), ('-', None), ('–', None), ('Sin dato', None), ('N/A', None),
    ('Chile', 'Chile'), ('  Chile  ', 'Chile'), ('Chile  /  Argentina', 'Chile / Argentina'),
    ('Colo\tColo\n', 'Colo Colo'), ('Colo\x00Colo', 'Colo Colo'),
    ('Ñublense', 'Ñublense'), ("O'Higgins", "O'Higgins"), ('Universidad de Concepción', 'Universidad de Concepción'),
])
def test_ficha_text_is_cleaned_and_a_dash_means_no_data(value, expected):
    assert reports_service.clean_profile_text(value, label='equipo') == expected


def test_ficha_text_too_long_is_rejected_not_cut_silently():
    limit = reports_service.PROFILE_TEXT_MAX_LENGTH
    assert reports_service.clean_profile_text('x' * limit, label='equipo') == 'x' * limit
    with pytest.raises(ValueError, match=f'Equipo de procedencia: máximo {limit} caracteres'):
        reports_service.clean_profile_text('x' * (limit + 1), label='equipo de procedencia')


# --- El servicio, sin base de datos --------------------------------------------------------------------------------------------------

FICHA = dict(id=7, player_id=3, is_hidden=False, raw_payload=None,
             player_position='Delantero', player_current_team='Club de prueba', player_nationality='Argentina')


@pytest.fixture
def writes(monkeypatch):
    """Fuera del portal: el informe 7 es del jugador 3, cuya ficha trae datos. Devuelve el «UPDATE» simulado."""
    monkeypatch.delenv('PORTAL_MODE', raising=False)
    state = dict(report=dict(FICHA))
    monkeypatch.setattr(reports_repository, 'get_report_by_id', lambda conn, report_id: state['report'])
    update = Mock(return_value=True)
    monkeypatch.setattr(players_repository, 'update_player_profile', update)
    update.state = state
    return update


def test_only_the_given_field_is_written_and_the_change_is_reported(writes):
    conn = Mock()
    changed = reports_service.update_player_profile(conn, 7, nationality='Chile')
    writes.assert_called_once_with(conn, 3, {'nationality': 'Chile'}, commit=False)
    assert changed == {'nationality': ('Argentina', 'Chile')}
    conn.commit.assert_called_once()
    conn.rollback.assert_not_called()


def test_position_team_and_nationality_can_change_together(writes):
    conn = Mock()
    changed = reports_service.update_player_profile(
        conn, 7, position='Portero', current_team='Otro club', nationality='Chile / Argentina')
    writes.assert_called_once_with(
        conn, 3, {'position': 'Portero', 'current_team': 'Otro club', 'nationality': 'Chile / Argentina'}, commit=False)
    assert changed == {'position': ('Delantero', 'Portero'), 'current_team': ('Club de prueba', 'Otro club'),
                       'nationality': ('Argentina', 'Chile / Argentina')}
    conn.commit.assert_called_once()


def test_a_field_that_is_not_given_is_neither_read_nor_written(writes):
    reports_service.update_player_profile(Mock(), 7, current_team='Otro club')
    assert writes.call_args.args[2] == {'current_team': 'Otro club'}


def test_nothing_to_change_writes_nothing(writes):
    conn = Mock()
    for kwargs in [dict(), dict(position='Delantero'), dict(current_team='  Club de prueba '), dict(nationality='Argentina'),
                   dict(position='Delantero', current_team='Club de prueba', nationality='Argentina')]:
        assert reports_service.update_player_profile(conn, 7, **kwargs) == {}
    writes.assert_not_called()
    conn.commit.assert_not_called()
    conn.rollback.assert_not_called()


@pytest.mark.parametrize('blank', [None, '', '   ', '—', '-', 'sin dato'])
@pytest.mark.parametrize('field', ['current_team', 'nationality'])
def test_blank_or_a_dash_leaves_the_field_without_data(writes, field, blank):
    changed = reports_service.update_player_profile(Mock(), 7, **{field: blank})
    assert writes.call_args.args[2] == {field: None}, 'sin dato es NULL, no un texto vacío ni un «—» guardado'
    assert changed[field][1] is None


@pytest.mark.parametrize('blank', [None, '', '   '])
def test_the_position_can_be_left_without_data(writes, blank):
    changed = reports_service.update_player_profile(Mock(), 7, position=blank)
    assert writes.call_args.args[2] == {'position': None}
    assert changed == {'position': ('Delantero', None)}


def test_a_field_that_had_no_data_is_reported_as_no_data(writes):
    writes.state['report'] = {**FICHA, 'player_nationality': None, 'player_current_team': '   '}
    changed = reports_service.update_player_profile(Mock(), 7, nationality='Chile', current_team='Otro club')
    assert changed == {'nationality': (None, 'Chile'), 'current_team': (None, 'Otro club')}


@pytest.mark.parametrize('position', ['Libero', 'delantero', 'Mediapunta', '—'])
def test_a_position_outside_the_campograma_is_rejected_before_anything_is_written(writes, position):
    with pytest.raises(ValueError, match='Posición no válida'):
        reports_service.update_player_profile(Mock(), 7, position=position, nationality='Chile')
    writes.assert_not_called()


def test_a_ficha_position_the_campograma_does_not_know_is_only_validated_when_it_changes(writes):
    writes.state['report'] = {**FICHA, 'player_position': 'Libero'}
    conn = Mock()
    assert reports_service.update_player_profile(conn, 7, position='Libero') == {}
    writes.assert_not_called()
    reports_service.update_player_profile(conn, 7, nationality='Chile')
    assert writes.call_args.args[2] == {'nationality': 'Chile'}, 'la posición rara que ya traía la ficha no se toca'
    reports_service.update_player_profile(conn, 7, position='Portero')
    assert writes.call_args.args[2] == {'position': 'Portero'}
    with pytest.raises(ValueError, match='Posición no válida'):
        reports_service.update_player_profile(conn, 7, position='Mediapunta')


def test_too_long_text_is_rejected_before_anything_is_written(writes):
    limit = reports_service.PROFILE_TEXT_MAX_LENGTH
    with pytest.raises(ValueError, match=f'Nacionalidad: máximo {limit}'):
        reports_service.update_player_profile(Mock(), 7, nationality='x' * (limit + 1))
    with pytest.raises(ValueError, match=f'Equipo de procedencia: máximo {limit}'):
        reports_service.update_player_profile(Mock(), 7, current_team='x' * (limit + 1), nationality='Chile')
    writes.assert_not_called()
    reports_service.update_player_profile(Mock(), 7, nationality='x' * limit)
    writes.assert_called_once()


def test_a_missing_report_is_reported_not_ignored(monkeypatch):
    monkeypatch.delenv('PORTAL_MODE', raising=False)
    monkeypatch.setattr(reports_repository, 'get_report_by_id', lambda conn, report_id: None)
    update = Mock()
    monkeypatch.setattr(players_repository, 'update_player_profile', update)
    with pytest.raises(ValueError, match='no encontrado'):
        reports_service.update_player_profile(object(), 7, nationality='Chile')
    update.assert_not_called()


def test_a_player_that_no_longer_exists_is_reported_and_nothing_is_confirmed(writes):
    writes.return_value = False
    conn = Mock()
    with pytest.raises(ValueError, match='Jugador no encontrado'):
        reports_service.update_player_profile(conn, 7, nationality='Chile')
    conn.rollback.assert_called_once()
    conn.commit.assert_not_called()


def test_a_failure_while_writing_rolls_back(writes):
    writes.side_effect = RuntimeError('base de datos caída')
    conn = Mock()
    with pytest.raises(RuntimeError, match='caída'):
        reports_service.update_player_profile(conn, 7, nationality='Chile')
    conn.rollback.assert_called_once()
    conn.commit.assert_not_called()


def test_the_repository_refuses_columns_outside_the_ficha_and_builds_no_sql_from_them():
    conn = Mock()
    for bad in ({'full_name': 'X'}, {'position': 'Delantero', 'normalized_name': 'x'}, {'position = NULL; --': 'x'}, {'id': 1}):
        with pytest.raises(ValueError, match='no válidos'):
            players_repository.update_player_profile(conn, 3, bad)
    conn.cursor.assert_not_called()
    assert players_repository.update_player_profile(conn, 3, {}) is False
    assert set(players_repository.EDITABLE_PROFILE_COLUMNS) == {'position', 'current_team', 'nationality'}


# --- Permisos del portal: los mismos que editar un informe -------------------------------------------------------------------------

OWN = {**FICHA, 'raw_payload': {'portal_owner_id': SCOUT['id']}}
OF_ANOTHER = {**FICHA, 'raw_payload': {'portal_owner_id': ADMIN['id']}}
HIDDEN_OF_ANOTHER = {**OF_ANOTHER, 'is_hidden': True}


@pytest.mark.parametrize('user, report, allowed', [
    (SCOUT, OWN, True),
    (SCOUT, OF_ANOTHER, False),
    (SCOUT, HIDDEN_OF_ANOTHER, True),       # los scouts también gestionan los informes ocultos
    (OTHER_SCOUT, OWN, False),
    (ADMIN, OWN, True),
    (ADMIN, OF_ANOTHER, True),
    (ADMIN, HIDDEN_OF_ANOTHER, True),
])
def test_portal_update_follows_the_same_rules_as_editing_a_report(monkeypatch, user, report, allowed):
    monkeypatch.setenv('PORTAL_MODE', '1')
    monkeypatch.setattr(reports_repository, 'get_report_by_id', lambda *args: report)
    update = Mock(return_value=True)
    monkeypatch.setattr(players_repository, 'update_player_profile', update)
    with security.session_scope({}, verified_user=user):
        if allowed:
            reports_service.update_player_profile(Mock(), 7, nationality='Chile')
            update.assert_called_once()
        else:
            with pytest.raises(PermissionError):
                reports_service.update_player_profile(Mock(), 7, nationality='Chile')
            update.assert_not_called()


@pytest.mark.parametrize('user', [None, {**SCOUT, 'active': False}])
def test_portal_update_needs_a_valid_session(monkeypatch, user):
    from scouting.portal import accounts
    monkeypatch.setenv('PORTAL_MODE', '1')
    monkeypatch.setattr(accounts, 'resolve_session', lambda token: user)
    monkeypatch.setattr(reports_repository, 'get_report_by_id', lambda *args: OWN)
    update = Mock()
    monkeypatch.setattr(players_repository, 'update_player_profile', update)
    with security.session_scope({}, verified_user=user), pytest.raises(PermissionError):
        reports_service.update_player_profile(object(), 7, nationality='Chile')
    update.assert_not_called()


def test_the_readonly_pilot_cannot_edit_a_ficha_even_as_admin(monkeypatch):
    monkeypatch.setenv('PORTAL_MODE', '1')
    monkeypatch.setattr(readonly_pilot, 'scouting_readonly', lambda: True)
    monkeypatch.setattr(reports_repository, 'get_report_by_id', lambda *args: OWN)
    update = Mock()
    monkeypatch.setattr(players_repository, 'update_player_profile', update)
    with security.session_scope({}, verified_user=ADMIN), pytest.raises(PermissionError):
        reports_service.update_player_profile(object(), 7, nationality='Chile')
    update.assert_not_called()


def test_a_denied_user_does_not_learn_whether_the_values_are_valid(monkeypatch):
    """Primero se comprueba el permiso: quien no puede editar el informe no averigua nada con valores de prueba."""
    monkeypatch.setenv('PORTAL_MODE', '1')
    monkeypatch.setattr(reports_repository, 'get_report_by_id', lambda *args: OF_ANOTHER)
    with security.session_scope({}, verified_user=SCOUT), pytest.raises(PermissionError):
        reports_service.update_player_profile(object(), 7, position='Libero')


# --- Contra PostgreSQL ---------------------------------------------------------------------------------------------------------------

@pytest.fixture
def scouting_db():
    dsn = os.getenv('SCOUTING_TEST_DATABASE_URL')
    if not dsn:
        pytest.skip('Requires disposable local PostgreSQL via SCOUTING_TEST_DATABASE_URL')
    params = psycopg.conninfo.conninfo_to_dict(dsn)
    assert params.get('host') in {'localhost', '127.0.0.1', '::1'} and params.get('dbname') == 'scouting_test'
    schema = 'profile_test_' + uuid4().hex
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


def add_player(conn, name, nationality=None, position=None, team=None, *, reports=1, hidden=0, owner=None):
    """Un jugador con su ficha y `reports` informes visibles + `hidden` ocultos. Devuelve (id del jugador, [ids de informes])."""
    player_id = conn.execute(
        'INSERT INTO players (full_name, normalized_name, nationality, position, current_team) VALUES (%s, %s, %s, %s, %s) RETURNING id',
        (name, name.lower(), nationality, position, team)).fetchone()[0]
    report_ids = []
    for index in range(reports + hidden):
        report_ids.append(conn.execute(
            "INSERT INTO scouting_reports (player_id, source_type, scout_name, report_date, recommendation, rating, is_hidden, raw_payload) "
            "VALUES (%s, 'manual', 'Scout', %s, 'Seguir monitorizando', 7, %s, %s) RETURNING id",
            (player_id, date(2026, 10, 1 + index), index >= reports, Json({'portal_owner_id': owner}) if owner else None)).fetchone()[0])
    conn.commit()
    return player_id, report_ids


def ficha(conn, player_id):
    return conn.execute('SELECT position, current_team, nationality FROM players WHERE id = %s', (player_id,)).fetchone()


def ficha_from_another_connection(conn, player_id):
    """Lo que ve otra sesión: solo lo que ya está confirmado (commit)."""
    dsn = os.environ['SCOUTING_TEST_DATABASE_URL']
    search_path = conn.execute('SHOW search_path').fetchone()[0]
    with psycopg.connect(dsn, options=f'-c search_path={search_path}') as other:
        return ficha(other, player_id)


@pytest.fixture
def outside_portal(monkeypatch):
    monkeypatch.delenv('PORTAL_MODE', raising=False)


def test_postgres_the_edit_replaces_what_the_ficha_had_and_touches_nothing_else(scouting_db, outside_portal):
    conn = scouting_db
    player_id, (report_id,) = add_player(conn, 'Jugador Uno', 'Argentina', 'Delantero', 'Club A')
    other_id, _ = add_player(conn, 'Jugador Dos', 'Argentina', 'Delantero', 'Club A')
    before = conn.execute('SELECT full_name, normalized_name, birth_date, preferred_foot, height_cm FROM players WHERE id = %s',
                          (player_id,)).fetchone()
    report_before = conn.execute('SELECT rating, recommendation, position_observed, summary FROM scouting_reports WHERE id = %s',
                                 (report_id,)).fetchone()
    changed = reports_service.update_player_profile(
        conn, report_id, position='Portero', current_team='Club B', nationality='Chile')
    assert ficha(conn, player_id) == ('Portero', 'Club B', 'Chile')
    assert changed == {'position': ('Delantero', 'Portero'), 'current_team': ('Club A', 'Club B'), 'nationality': ('Argentina', 'Chile')}
    assert ficha(conn, other_id) == ('Delantero', 'Club A', 'Argentina'), 'otro jugador no cambia'
    assert conn.execute('SELECT full_name, normalized_name, birth_date, preferred_foot, height_cm FROM players WHERE id = %s',
                        (player_id,)).fetchone() == before, 'el resto de la ficha no cambia'
    assert conn.execute('SELECT rating, recommendation, position_observed, summary FROM scouting_reports WHERE id = %s',
                        (report_id,)).fetchone() == report_before, 'el informe no cambia'


def test_postgres_a_blank_field_is_stored_as_null_not_as_empty_text_or_a_dash(scouting_db, outside_portal):
    conn = scouting_db
    player_id, (report_id,) = add_player(conn, 'Jugador Tres', 'Chile', 'Delantero', 'Club A')
    reports_service.update_player_profile(conn, report_id, position=None, current_team='   ', nationality='—')
    assert ficha(conn, player_id) == (None, None, None)


def test_postgres_a_field_that_is_not_given_keeps_what_another_person_saved_meanwhile(scouting_db, outside_portal):
    """Dos personas abren la misma ficha; la segunda no pisa lo que la primera cambió en un campo que no tocó."""
    conn = scouting_db
    player_id, (report_id,) = add_player(conn, 'Jugador Cuatro', 'Argentina', 'Delantero', 'Club A')
    reports_service.update_player_profile(conn, report_id, current_team='Club B')            # la primera persona
    reports_service.update_player_profile(conn, report_id, nationality='Chile')              # la segunda: solo lo suyo
    assert ficha(conn, player_id) == ('Delantero', 'Club B', 'Chile')


def test_postgres_the_edit_is_committed_for_other_sessions(scouting_db, outside_portal):
    conn = scouting_db
    player_id, (report_id,) = add_player(conn, 'Jugador Cinco', None, None, None)
    reports_service.update_player_profile(conn, report_id, position='Delantero', current_team='Club A', nationality='Chile')
    assert ficha_from_another_connection(conn, player_id) == ('Delantero', 'Club A', 'Chile')


def test_postgres_changing_nationality_and_position_moves_the_player_between_the_campogramas(scouting_db, outside_portal):
    conn = scouting_db
    _, (report_id, _second) = add_player(conn, 'Jugador Seis', None, None, None, reports=2)
    by_origin = lambda: dashboard_service.get_position_counts_by_origin(conn)  # noqa: E731
    chilean, foreign, unknown = nationality_service.CHILEAN, nationality_service.FOREIGN, 'unknown'

    assert by_origin() == {chilean: [], foreign: [], unknown: []}, 'sin posición ni nacionalidad no sale en ningún campograma'
    reports_service.update_player_profile(conn, report_id, position='Delantero')
    assert by_origin()[unknown] == [dict(position='Delantero', players_count=1, reports_count=2)], 'con posición pero sin nacionalidad'
    reports_service.update_player_profile(conn, report_id, nationality='Chilena')
    assert by_origin() == {chilean: [dict(position='Delantero', players_count=1, reports_count=2)], foreign: [], unknown: []}
    reports_service.update_player_profile(conn, report_id, nationality='Argentina')
    assert by_origin() == {chilean: [], foreign: [dict(position='Delantero', players_count=1, reports_count=2)], unknown: []}
    reports_service.update_player_profile(conn, report_id, position='Portero', nationality='Argentina / Chile')
    assert by_origin() == {chilean: [dict(position='Portero', players_count=1, reports_count=2)], foreign: [], unknown: []}, \
        'doble nacionalidad con Chile cuenta como chileno'
    reports_service.update_player_profile(conn, report_id, nationality=None)
    assert by_origin()[unknown] == [dict(position='Portero', players_count=1, reports_count=2)] and not by_origin()[chilean]


def test_postgres_every_report_of_the_player_shows_the_new_ficha(scouting_db, outside_portal):
    conn = scouting_db
    player_id, (first, second) = add_player(conn, 'Jugador Siete', 'Argentina', 'Delantero', 'Club A', reports=2)
    reports_service.update_player_profile(conn, first, current_team='Club B', nationality='Chile', position='Extremo derecho')
    for report_id in (first, second):
        report = reports_service.get_report(conn, report_id)
        assert (report['player_position'], report['player_current_team'], report['player_nationality']) == (
            'Extremo derecho', 'Club B', 'Chile')
    visible = {r['id']: r for r in reports_service.fetch_visible_reports(conn)}
    assert {visible[i]['player_nationality'] for i in (first, second)} == {'Chile'}


def test_postgres_the_report_listings_carry_the_ficha_the_editor_starts_from(scouting_db, outside_portal):
    conn = scouting_db
    add_player(conn, 'Visible', 'Chile', 'Delantero', 'Club A', reports=1)
    add_player(conn, 'Oculto', 'Uruguay', 'Portero', 'Club B', reports=0, hidden=1)
    conn.commit()
    visible = reports_service.fetch_visible_reports(conn)[0]
    hidden = reports_service.fetch_hidden_reports(conn)[0]
    by_position = reports_service.fetch_hidden_reports_by_position(conn, 'Portero')[0]
    assert (visible['player_position'], visible['player_current_team'], visible['player_nationality']) == ('Delantero', 'Club A', 'Chile')
    for report in (hidden, by_position):
        assert (report['player_position'], report['player_current_team'], report['player_nationality']) == ('Portero', 'Club B', 'Uruguay')


def test_postgres_a_failed_validation_leaves_the_ficha_untouched(scouting_db, outside_portal):
    conn = scouting_db
    player_id, (report_id,) = add_player(conn, 'Jugador Ocho', 'Chile', 'Delantero', 'Club A')
    with pytest.raises(ValueError, match='Posición no válida'):
        reports_service.update_player_profile(conn, report_id, position='Libero', current_team='Club B', nationality='Argentina')
    with pytest.raises(ValueError, match='máximo'):
        reports_service.update_player_profile(conn, report_id, current_team='x' * 500, nationality='Argentina')
    assert ficha(conn, player_id) == ('Delantero', 'Club A', 'Chile')
    assert ficha_from_another_connection(conn, player_id) == ('Delantero', 'Club A', 'Chile')


def test_postgres_a_failure_after_the_write_undoes_it(scouting_db, outside_portal, monkeypatch):
    conn = scouting_db
    player_id, (report_id,) = add_player(conn, 'Jugador Nueve', 'Chile', 'Delantero', 'Club A')
    original = players_repository.update_player_profile

    def writes_then_fails(conn, player_id, changes, *, commit=True):
        original(conn, player_id, changes, commit=commit)
        raise RuntimeError('fallo simulado antes de confirmar')

    monkeypatch.setattr(players_repository, 'update_player_profile', writes_then_fails)
    with pytest.raises(RuntimeError, match='simulado'):
        reports_service.update_player_profile(conn, report_id, position='Portero', nationality='Argentina')
    assert ficha(conn, player_id) == ('Delantero', 'Club A', 'Chile')
    assert ficha_from_another_connection(conn, player_id) == ('Delantero', 'Club A', 'Chile')


def test_postgres_permissions_follow_the_report_in_the_portal(scouting_db, monkeypatch):
    monkeypatch.setenv('PORTAL_MODE', '1')
    conn = scouting_db
    player_id, (visible_of_admin, hidden_of_admin) = add_player(
        conn, 'Jugador Diez', 'Argentina', 'Delantero', 'Club A', reports=1, hidden=1, owner=ADMIN['id'])
    own_id, (own_report,) = add_player(conn, 'Jugador Once', 'Argentina', 'Delantero', 'Club A', owner=SCOUT['id'])

    with security.session_scope({}, verified_user=SCOUT):
        with pytest.raises(PermissionError):
            reports_service.update_player_profile(conn, visible_of_admin, nationality='Chile')
        assert ficha(conn, player_id) == ('Delantero', 'Club A', 'Argentina'), 'el scout no toca la ficha por un informe ajeno'
        reports_service.update_player_profile(conn, own_report, nationality='Chile')
        assert ficha(conn, own_id)[2] == 'Chile', 'sí por un informe propio'
        reports_service.update_player_profile(conn, hidden_of_admin, current_team='Club B')
        assert ficha(conn, player_id)[1] == 'Club B', 'sí por un informe oculto, que los scouts gestionan'
    with security.session_scope({}, verified_user=OTHER_SCOUT), pytest.raises(PermissionError):
        reports_service.update_player_profile(conn, own_report, nationality='Brasil')
    assert ficha(conn, own_id)[2] == 'Chile'
    with security.session_scope({}, verified_user=ADMIN):
        reports_service.update_player_profile(conn, own_report, nationality='Brasil')
    assert ficha(conn, own_id)[2] == 'Brasil'


def test_postgres_automatic_fills_never_overwrite_a_manual_edit(scouting_db, outside_portal):
    """Una importación o un informe nuevo solo completan lo que está vacío: lo corregido a mano se conserva."""
    conn = scouting_db
    player_id, (report_id,) = add_player(conn, 'Jugador Doce', 'Argentina', 'Delantero', 'Club A')
    reports_service.update_player_profile(conn, report_id, position='Portero', current_team='Club B', nationality='Chile')
    players_repository.merge_player_empty_fields(
        conn, player_id, nationality='Brazil', position='Delantero', current_team='Club C')
    same_id, created = players_repository.get_or_create_player(
        conn, 'Jugador Doce', nationality='Brazil', position='Delantero', current_team='Club C')
    assert (same_id, created) == (player_id, False)
    assert ficha(conn, player_id) == ('Portero', 'Club B', 'Chile')


def test_postgres_a_field_left_empty_on_purpose_can_be_filled_in_again_by_an_automatic_source(scouting_db, outside_portal):
    """Dejar vacío no bloquea el dato: es «sin dato», y lo que solo completa vacíos puede volver a rellenarlo."""
    conn = scouting_db
    player_id, (report_id,) = add_player(conn, 'Jugador Trece', 'Argentina', 'Delantero', 'Club A')
    reports_service.update_player_profile(conn, report_id, nationality=None)
    players_repository.merge_player_empty_fields(conn, player_id, nationality='Brazil')
    assert ficha(conn, player_id)[2] == 'Brazil'
