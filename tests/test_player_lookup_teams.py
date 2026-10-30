"""«Consultar jugador»: equipos de cada jugador (petición del 30-10-2026). Datos ficticios.

La lista debe mostrar el club de los jugadores cuya ficha de scouting no lo tiene (hasta ahora salía «—») usando el último
equipo de sus datos objetivos reales, y la ficha debe traer su historial de equipos por temporada. Nunca se muestran
equipos de datos demo ni se inventa un club.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.types.json import Json
from streamlit.testing.v1 import AppTest

from scouting.repositories import metrics_repository, players_repository
from scouting.services import players_service

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'app'
NONE_LABEL = '— Sin selección —'


# --- La etiqueta del club ----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize('player, expected', [
    (dict(current_team='Temuco'), 'Temuco'),
    (dict(current_team='  Temuco  ', previous_team='Colo-Colo', previous_team_season='2025'), 'Temuco'),   # la ficha manda
    (dict(current_team=None, previous_team='Colo-Colo', previous_team_season='2025'), 'Colo-Colo · 2025'),
    (dict(current_team='', previous_team='Colo-Colo', previous_team_season='2025'), 'Colo-Colo · 2025'),
    (dict(current_team='None', previous_team='Colo-Colo', previous_team_season='2025'), 'Colo-Colo · 2025'),
    (dict(current_team=None, previous_team='Colo-Colo', previous_team_season=None), 'Colo-Colo'),
    (dict(current_team=None, previous_team='Colo-Colo', previous_team_season='  '), 'Colo-Colo'),
    (dict(current_team=None, previous_team=None), '—'),
    (dict(current_team='—'), '—'),
    ({}, '—'),
])
def test_lookup_team_label(player, expected):
    assert players_service.lookup_team_label(player) == expected


def test_a_previous_team_never_replaces_the_one_on_the_card():
    player = dict(current_team='Temuco', previous_team='Colo-Colo', previous_team_season='2024')
    assert players_service.lookup_team_label(player) == 'Temuco'


# --- Quién necesita completar el equipo -----------------------------------------------------------------------------------------

def test_only_players_without_a_team_are_looked_up_and_the_card_is_never_changed(monkeypatch):
    players = [dict(id=1, full_name='Sin equipo', current_team=None), dict(id=2, full_name='Con equipo', current_team='Temuco'),
               dict(id=3, full_name='En blanco', current_team='  '), dict(id=4, full_name='Sin datos', current_team=None)]
    monkeypatch.setattr(players_repository, 'get_players_with_reports', lambda conn: [dict(p) for p in players])
    latest = Mock(return_value={1: dict(player_id=1, team_name='Colo-Colo', season='2025', competition='Primera'),
                                3: dict(player_id=3, team_name='  Huachipato ', season='2024', competition='Primera')})
    monkeypatch.setattr(metrics_repository, 'get_latest_objective_team_by_player', latest)
    out = players_service.list_players_for_lookup(object())
    latest.assert_called_once()
    assert latest.call_args.args[1] == [1, 3, 4], 'solo los jugadores cuya ficha no tiene equipo'
    by_id = {p['id']: p for p in out}
    assert by_id[1]['previous_team'] == 'Colo-Colo' and by_id[1]['previous_team_season'] == '2025'
    assert by_id[3]['previous_team'] == 'Huachipato'
    assert 'previous_team' not in by_id[2] and 'previous_team' not in by_id[4]
    assert [p['current_team'] for p in out] == [None, 'Temuco', '  ', None], 'la ficha no se toca'
    assert [players_service.lookup_team_label(p) for p in out] == ['Colo-Colo · 2025', 'Temuco', 'Huachipato · 2024', '—']


def test_no_query_when_every_player_already_has_a_team(monkeypatch):
    monkeypatch.setattr(players_repository, 'get_players_with_reports',
                        lambda conn: [dict(id=1, full_name='Uno', current_team='Temuco')])
    latest = Mock()
    monkeypatch.setattr(metrics_repository, 'get_latest_objective_team_by_player', latest)
    assert players_service.list_players_for_lookup(object())[0]['current_team'] == 'Temuco'
    latest.assert_not_called()


def test_the_team_history_is_read_through_the_service(monkeypatch):
    history = Mock(return_value=[dict(season='2025', competition='Primera', team_name='Colo-Colo')])
    monkeypatch.setattr(metrics_repository, 'get_player_team_history', history)
    conn = object()
    assert players_service.get_player_team_history(conn, 5) == [dict(season='2025', competition='Primera', team_name='Colo-Colo')]
    history.assert_called_once_with(conn, 5)


# --- Contra PostgreSQL ---------------------------------------------------------------------------------------------------------

@pytest.fixture
def scouting_db(monkeypatch):
    dsn = os.getenv('SCOUTING_TEST_DATABASE_URL')
    if not dsn:
        pytest.skip('Requires disposable local PostgreSQL via SCOUTING_TEST_DATABASE_URL')
    params = psycopg.conninfo.conninfo_to_dict(dsn)
    assert params.get('host') in {'localhost', '127.0.0.1', '::1'} and params.get('dbname') == 'scouting_test'
    monkeypatch.setenv('SOFASCORE_ACTIVE_SEASON', '2025')
    monkeypatch.delenv('PORTAL_MODE', raising=False)
    schema = 'lookup_test_' + uuid4().hex
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


def add_player(conn, name, team=None, report=True):
    player_id = conn.execute(
        'INSERT INTO players (full_name, normalized_name, current_team) VALUES (%s, %s, %s) RETURNING id',
        (name, name.lower(), team)).fetchone()[0]
    if report:
        conn.execute("INSERT INTO scouting_reports (player_id, source_type, scout_name, report_date, recommendation) "
                     "VALUES (%s, 'manual', 'Scout', '2026-10-01', 'Seguir monitorizando')", (player_id,))
    return player_id


def add_block(conn, player_id, season, competition, payload, *, rows=3, source_type='sofascore', batch=None):
    for index in range(rows):
        conn.execute(
            "INSERT INTO objective_metrics (player_id, source_name, season, competition, metric_name, metric_value, raw_payload, "
            "source_type, import_batch_id) VALUES (%s, 'Sofascore', %s, %s, %s, 1, %s, %s, %s)",
            (player_id, season, competition, f'metric_{index}', Json(payload), source_type, batch))


def add_batch(conn):
    return conn.execute(
        "INSERT INTO data_import_batches (provider, country, division, competition, season, source_file) "
        "VALUES ('Sofascore', 'Chile', 'Primera', 'Primera División Chile', '2022', 'synthetic.csv') RETURNING id").fetchone()[0]


@pytest.fixture
def squad(scouting_db):
    """Un jugador con historial, uno solo con datos demo, uno con equipo en la ficha y uno sin ningún dato."""
    conn = scouting_db
    ids = dict(
        history=add_player(conn, 'Jugador Con Historial'),
        demo=add_player(conn, 'Jugador Solo Demo'),
        card=add_player(conn, 'Jugador Con Equipo', team='Club Fijo'),
        nothing=add_player(conn, 'Jugador Sin Datos'),
        legacy=add_player(conn, 'Jugador Antiguo'),
        objective_only=add_player(conn, 'Jugador Solo Objetivo', report=False),
    )
    add_block(conn, ids['history'], '2024', 'Primera División Chile', {'team_name': 'Club Alfa'})
    add_block(conn, ids['history'], '2025', 'Primera División Chile', {'team_name': '  Club Beta  '}, rows=3)
    add_block(conn, ids['history'], '2025', 'Copa Chile', {'raw_row': {'team': 'Club Gamma'}}, rows=1)
    add_block(conn, ids['history'], '2023', 'Primera B', {})                                   # sin equipo en el dato
    add_block(conn, ids['history'], '2026', 'Liga Demo', {'team_name': 'Equipo Demo'}, source_type='demo')
    add_block(conn, ids['demo'], '2025', 'Liga Demo', {'team_name': 'Equipo Demo'}, source_type='demo')
    add_block(conn, ids['card'], '2025', 'Primera División Chile', {'team_name': 'Club Beta'})
    # Filas antiguas sin source_type: con lote de importación son Sofascore; sin lote, demo (misma norma que el resto del portal).
    add_block(conn, ids['legacy'], '2022', 'Primera División Chile', {'team_name': 'Club Antiguo'}, source_type=None,
              batch=add_batch(conn))
    add_block(conn, ids['legacy'], '2021', 'Liga Demo', {'team_name': 'Equipo Demo'}, source_type=None)
    add_block(conn, ids['objective_only'], '2025', 'Primera División Chile', {'team_name': 'Club Delta'})
    conn.commit()
    return ids


def test_team_history_is_newest_first_real_data_only(scouting_db, squad):
    history = metrics_repository.get_player_team_history(scouting_db, squad['history'])
    assert [(h['season'], h['competition'], h['team_name']) for h in history] == [
        ('2025', 'Primera División Chile', 'Club Beta'),     # a igualdad de temporada, la competición con más métricas
        ('2025', 'Copa Chile', 'Club Gamma'),                # el equipo puede venir de raw_row
        ('2024', 'Primera División Chile', 'Club Alfa'),
    ]
    teams = {h['team_name'] for h in history}
    assert 'Equipo Demo' not in teams, 'un equipo de datos demo no es un equipo anterior'
    assert not [h for h in history if h['season'] == '2023'], 'sin equipo en el dato no se inventa uno'


def test_team_history_is_empty_without_real_data(scouting_db, squad):
    assert metrics_repository.get_player_team_history(scouting_db, squad['demo']) == []
    assert metrics_repository.get_player_team_history(scouting_db, squad['nothing']) == []


def test_legacy_rows_follow_the_same_origin_rule_as_the_rest_of_the_portal(scouting_db, squad):
    history = metrics_repository.get_player_team_history(scouting_db, squad['legacy'])
    assert [(h['season'], h['team_name']) for h in history] == [('2022', 'Club Antiguo')]


def test_latest_team_is_the_most_recent_real_one(scouting_db, squad):
    latest = metrics_repository.get_latest_objective_team_by_player(scouting_db, list(squad.values()))
    assert latest[squad['history']]['team_name'] == 'Club Beta' and latest[squad['history']]['season'] == '2025'
    assert latest[squad['legacy']]['team_name'] == 'Club Antiguo'
    assert latest[squad['objective_only']]['team_name'] == 'Club Delta'
    assert squad['demo'] not in latest and squad['nothing'] not in latest
    assert metrics_repository.get_latest_objective_team_by_player(scouting_db, []) == {}
    only_one = metrics_repository.get_latest_objective_team_by_player(scouting_db, [squad['history']])
    assert list(only_one) == [squad['history']], 'solo los jugadores pedidos'


def test_lookup_completes_the_team_only_where_the_card_has_none(scouting_db, squad):
    players = {p['full_name']: p for p in players_service.list_players_for_lookup(scouting_db)}
    assert set(players) == {'Jugador Con Historial', 'Jugador Solo Demo', 'Jugador Con Equipo', 'Jugador Sin Datos',
                            'Jugador Antiguo'}, 'por defecto, solo los jugadores con informes'
    label = {name: players_service.lookup_team_label(p) for name, p in players.items()}
    assert label == {
        'Jugador Con Historial': 'Club Beta · 2025',
        'Jugador Solo Demo': '—',
        'Jugador Con Equipo': 'Club Fijo',          # la ficha manda aunque los datos objetivos digan otro club
        'Jugador Sin Datos': '—',
        'Jugador Antiguo': 'Club Antiguo · 2022',
    }
    assert players['Jugador Con Equipo']['current_team'] == 'Club Fijo'
    assert players['Jugador Con Historial']['current_team'] is None


def test_lookup_with_objective_only_players_also_shows_their_team(scouting_db, squad):
    players = {p['full_name']: p for p in players_service.list_players_for_lookup(scouting_db, include_objective_only=True)}
    assert players_service.lookup_team_label(players['Jugador Solo Objetivo']) == 'Club Delta · 2025'


# --- La pantalla ---------------------------------------------------------------------------------------------------------------------

PLAYERS = [
    dict(id=1, full_name='Aaron Astudillo', normalized_name='aaron astudillo', current_team=None, previous_team='Club Beta',
         previous_team_season='2025', position=None, nationality=None, birth_date=None, preferred_foot=None, height_cm=None,
         image_path=None, created_at=None),
    dict(id=2, full_name='FRANCO ORTEGA', normalized_name='franco ortega', current_team='TEMUCO', position='Delantero',
         nationality='Chile', birth_date=None, preferred_foot=None, height_cm=None, image_path=None, created_at=None),
    dict(id=3, full_name='Sin Datos', normalized_name='sin datos', current_team=None, position=None, nationality=None,
         birth_date=None, preferred_foot=None, height_cm=None, image_path=None, created_at=None),
]
HISTORY = {
    1: [dict(season='2025', competition='Primera División Chile', team_name='Club Beta'),
        dict(season='2024', competition='Primera B', team_name='Club Alfa')],
    2: [], 3: [],
}


@pytest.fixture
def lookup(monkeypatch):
    monkeypatch.syspath_prepend(str(APP))
    for key, value in [('DB_SCHEMA', 'scouting'), ('DISABLE_SOFASCORE_UPDATE', '1')]:
        monkeypatch.setenv(key, value)
    monkeypatch.delenv('PORTAL_MODE', raising=False)
    import streamlit_app

    @contextmanager
    def connection():
        yield object()

    shown = [dict(p) for p in PLAYERS]
    monkeypatch.setattr(streamlit_app, 'get_connection', connection)
    monkeypatch.setattr(players_service, 'list_players_for_lookup', lambda conn, include_objective_only=False: shown)
    monkeypatch.setattr(players_service, 'fetch_player', lambda conn, player_id: next(p for p in shown if p['id'] == player_id))
    monkeypatch.setattr(players_service, 'fetch_reports_for_player', lambda conn, player_id: [])
    monkeypatch.setattr(players_service, 'get_player_objective_data_status',
                        lambda conn, player_id: dict(has_objective_metrics=False, objective_metrics_count=0))
    monkeypatch.setattr(players_service, 'get_player_team_history', lambda conn, player_id: HISTORY[player_id])

    def run():
        return AppTest.from_string('import streamlit_app\nstreamlit_app._render_player_lookup()', default_timeout=30).run()

    run.players = shown
    return run


def test_lookup_list_shows_the_team_even_when_the_card_has_none(lookup):
    app = lookup()
    assert not app.exception, [e.value for e in app.exception]
    assert list(app.selectbox(key='player_lookup_selectbox').options) == [
        NONE_LABEL, 'Aaron Astudillo (Club Beta · 2025)', 'FRANCO ORTEGA (TEMUCO)', 'Sin Datos (—)']
    assert any('último que figura en los datos objetivos' in c.value for c in app.caption)


def test_lookup_list_has_no_explanation_when_every_team_comes_from_the_card(lookup):
    for player in lookup.players:
        player['current_team'] = player.get('current_team') or 'Club Fijo'
        player.pop('previous_team', None)
    app = lookup()
    assert not app.exception, [e.value for e in app.exception]
    assert not any('último que figura en los datos objetivos' in c.value for c in app.caption)


def test_lookup_ficha_lists_the_teams_of_each_season(lookup):
    app = lookup()
    app.selectbox(key='player_lookup_selectbox').select('Aaron Astudillo (Club Beta · 2025)').run()
    assert not app.exception, [e.value for e in app.exception]
    assert '##### Historial de equipos' in [m.value for m in app.markdown]
    table = next(d.value for d in app.dataframe if 'Equipo' in d.value.columns)
    assert table.to_dict('records') == [
        {'Temporada': '2025', 'Competición': 'Primera División Chile', 'Equipo': 'Club Beta'},
        {'Temporada': '2024', 'Competición': 'Primera B', 'Equipo': 'Club Alfa'}]
    assert any('Sofascore' in c.value and 'más reciente a la más antigua' in c.value for c in app.caption)


def test_lookup_ficha_without_history_says_why_instead_of_inventing_teams(lookup):
    app = lookup()
    app.selectbox(key='player_lookup_selectbox').select('Sin Datos (—)').run()
    assert not app.exception, [e.value for e in app.exception]
    assert '##### Historial de equipos' in [m.value for m in app.markdown]
    assert not [d for d in app.dataframe if 'Equipo' in d.value.columns]
    assert any('Sin historial de equipos' in c.value for c in app.caption)
