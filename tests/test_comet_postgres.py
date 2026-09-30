"""Consultas de COMET y migración 003 contra un PostgreSQL desechable (`scouting_test`, solo loopback).

El esquema COMET (`public`) es sintético: solo tiene las columnas que ya leen las pantallas actuales.
Se rellena con el mini-torneo de `tests/comet_tiny.py` y se comprueba que las consultas nuevas devuelven
exactamente esos datos y que coinciden con los cálculos ya existentes de `app/comet_dashboard.py`.
"""
import os
import threading
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

import pandas as pd
import psycopg
import pytest
import streamlit as st

from scouting.comet import alerts as alert_rules, config_store, metrics, queries
from scouting.comet.facts import build_dataset
from scouting.comet.ledger import PostgresLedger
from scouting.comet.rules import Rules
from scouting.portal import accounts, security
from tests import comet_tiny

CLUB = queries.OHIGGINS_CLUB_ID
RIVALS = {'Rival A': 1, 'Rival B': 2, 'Rival C': 3, 'Rival D': 4}
DDL = {
    'competiciones': 'id int, category text, name text, season text',
    'competidores': 'id int, clubid int',
    'equipos': 'clubid int, club text',
    # En COMET real el nacimiento llega como timestamp CON zona horaria (la revisión lo comprobó): el esquema sintético también.
    'jugadores': 'personid bigint, displayname text, dateofbirth timestamptz, nationality text, level text, status text, orgname text',
    'partidos': 'id int, matchid bigint, matchdate timestamptz, hometeam int, awayteam int',
    'partidos_fases': 'matchid bigint, phase text, homeresult int, awayresult int',
    'posiciones': 'id int, clubid int',
    'actuaciones_jugadores': ('id int, matchid bigint, personid bigint, clubid int, played boolean, startinglineup boolean, '
                              'minutesplayed int, goals int, singleyellow boolean, redcards int, goalkeeper boolean'),
    'actuaciones_arqueros': 'id int, matchid bigint, personid bigint, clubid int, played boolean, minutesplayed int, goalsconceded int',
}
ADMIN = dict(id='00000000-0000-0000-0000-000000000001', role='admin', active=True, revision=1, display_name='Admin')


def _dsn():
    dsn = os.environ.get('SCOUTING_TEST_DATABASE_URL')
    if not dsn:
        pytest.skip('Disposable PostgreSQL not configured')
    params = psycopg.conninfo.conninfo_to_dict(dsn)
    if params.get('host') not in ('localhost', '127.0.0.1') or params.get('dbname') != 'scouting_test':
        pytest.fail('COMET tests require loopback database scouting_test')
    return dsn


# Columnas que existen en algunas instalaciones de COMET (la revisión las comprobó con datos reales).
OPTIONAL_DDL = [
    'ALTER TABLE competiciones ADD COLUMN matchlength int',
    'ALTER TABLE partidos ADD COLUMN matchstatus text',
    'ALTER TABLE actuaciones_jugadores ADD COLUMN secondyellow boolean',
    'ALTER TABLE actuaciones_jugadores ADD COLUMN owngoals int',
    'ALTER TABLE jugadores ADD COLUMN datefrom timestamptz',
    'ALTER TABLE jugadores ADD COLUMN height numeric',
    'ALTER TABLE jugadores ADD COLUMN weight numeric',
]
OPTIONAL_DATA = [
    'UPDATE competiciones SET matchlength = CASE id WHEN 100 THEN 90 ELSE 70 END',
    "UPDATE partidos SET matchstatus = CASE matchid WHEN 3 THEN 'SUSPENDIDO' ELSE 'FINALIZADO' END WHERE matchid < 10",
    'UPDATE actuaciones_jugadores SET secondyellow = false, owngoals = 0 WHERE clubid = 40010',
    'UPDATE actuaciones_jugadores SET secondyellow = true WHERE matchid = 3 AND personid = 2',
    'UPDATE actuaciones_jugadores SET owngoals = 1 WHERE matchid = 3 AND personid = 3',
    "UPDATE jugadores SET datefrom = '2019-03-01 00:00:00+00' WHERE personid IN (1, 3)",
    'UPDATE jugadores SET height = 158, weight = 47.5 WHERE personid = 1',
]


def _create_comet_tables(conn, full=True):
    """Tablas COMET reales (en `public`, dentro de una transacción que se revierte)."""
    for table, columns in DDL.items():
        conn.execute(f'CREATE TABLE {table} ({columns})')
    if full:
        for statement in OPTIONAL_DDL:
            conn.execute(statement)


def _santiago(value):
    return pd.Timestamp(value).tz_localize('America/Santiago').to_pydatetime()


def _utc(value):
    return pd.Timestamp(value).tz_localize('UTC').to_pydatetime()


def _fill_comet_tables(conn, full=True):
    """Vuelca el mini-torneo en las tablas COMET, más ruido que las consultas deben excluir."""
    raw = comet_tiny.build()
    m = raw['matches']
    conn.execute('INSERT INTO equipos VALUES (%s, %s)', (CLUB, "O'Higgins"))
    for name, club_id in RIVALS.items():
        conn.execute('INSERT INTO equipos VALUES (%s, %s)', (club_id, name))
    for comp, grp in m.groupby('competition_id'):
        first = grp.iloc[0]
        conn.execute('INSERT INTO competiciones VALUES (%s, %s, %s, %s)', (comp, first['category'], first['competition'], first['season']))
        conn.execute('INSERT INTO competidores VALUES (%s, %s)', (comp, CLUB))
    for r in m.itertuples():
        home, away = (CLUB, RIVALS[r.away_team]) if r.venue == 'Local' else (RIVALS[r.home_team], CLUB)
        conn.execute('INSERT INTO partidos VALUES (%s, %s, %s, %s, %s)', (r.competition_id, r.matchid, _santiago(r.matchdate), home, away))
        final_home, final_away = (r.goals_for, r.goals_against) if r.venue == 'Local' else (r.goals_against, r.goals_for)
        conn.execute("INSERT INTO partidos_fases VALUES (%s, 'Primer tiempo', 9, 9)", (r.matchid,))  # no debe usarse
        conn.execute("INSERT INTO partidos_fases VALUES (%s, 'Segundo tiempo', %s, %s)", (r.matchid, final_home, final_away))
    # Ruido: partido futuro de O'Higgins, partido ajeno y un jugador de otro club.
    conn.execute("INSERT INTO partidos VALUES (100, 90, now() + interval '7 days', %s, 1)", (CLUB,))
    conn.execute("INSERT INTO partidos VALUES (100, 91, now() - interval '3 days', 1, 2)")
    conn.execute("INSERT INTO partidos_fases VALUES (91, 'Segundo tiempo', 5, 5)")
    for p in raw['players'].itertuples():
        conn.execute('INSERT INTO jugadores (personid, displayname, dateofbirth, nationality, level, status, orgname) '
                     'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                     (p.personid, p.displayname, _utc(p.dateofbirth), p.nationality, p.level, p.status, p.orgname))
    conn.execute("INSERT INTO jugadores (personid, displayname, dateofbirth, nationality, level, status, orgname) "
                 "VALUES (9999, 'Jugador de otro club', '2010-01-01', 'Chile', 'F', 'ACTIVO', 'Rival A')")
    sheet_columns = ('(id, matchid, personid, clubid, played, startinglineup, minutesplayed, goals, singleyellow, '
                     'redcards, goalkeeper)')
    for s in raw['sheet'].itertuples():
        conn.execute(f'INSERT INTO actuaciones_jugadores {sheet_columns} VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                     (s.competition_id, s.matchid, s.personid, CLUB, s.played, s.startinglineup, s.minutesplayed,
                      s.goals, bool(s.yellow_cards), s.red_cards, s.goalkeeper))
    conn.execute(f'INSERT INTO actuaciones_jugadores {sheet_columns} '
                 'VALUES (100, 1, 9999, 1, true, true, 80, 0, false, 0, false)')  # rival
    for g in raw['goalkeepers'].itertuples():
        conn.execute('INSERT INTO actuaciones_arqueros VALUES (%s, %s, %s, %s, %s, %s, %s)',
                     (g.competition_id, g.matchid, g.personid, CLUB, g.played, g.minutesplayed, g.goalsconceded))
    conn.execute('INSERT INTO actuaciones_arqueros VALUES (100, 1, 9999, 1, true, 80, 2)')  # arquero rival
    if full:
        for statement in OPTIONAL_DATA:
            conn.execute(statement)
    return raw


@pytest.fixture
def comet_conn():
    """COMET con las columnas opcionales que la revisión encontró en los datos reales."""
    dsn = _dsn()
    with psycopg.connect(dsn) as conn:
        _create_comet_tables(conn, full=True)
        raw = _fill_comet_tables(conn, full=True)
        yield conn, raw
        conn.rollback()


@pytest.fixture
def comet_conn_base():
    """COMET solo con las columnas del dashboard antiguo (instalaciones sin las opcionales)."""
    dsn = _dsn()
    with psycopg.connect(dsn) as conn:
        _create_comet_tables(conn, full=False)
        raw = _fill_comet_tables(conn, full=False)
        yield conn, raw
        conn.rollback()


def _loader(conn):
    return lambda sql, params=None: pd.read_sql_query(sql, conn, params=params)


def test_queries_return_only_oh_higgins_data_in_the_expected_shape(comet_conn):
    conn, tiny = comet_conn
    raw = queries.fetch_raw(_loader(conn))
    assert list(raw['sheet'].columns) == ['matchid', 'competition_id', 'personid', 'played', 'startinglineup',
                                          'minutesplayed', 'goals', 'yellow_cards', 'red_cards', 'goalkeeper',
                                          'second_yellows', 'own_goals']
    assert {'nominal_duration', 'matchstatus'} <= set(raw['matches'].columns)
    assert {'datefrom', 'height', 'weight'} <= set(raw['players'].columns)
    assert len(raw['sheet']) == len(tiny['sheet']) and 9999 not in raw['sheet']['personid'].tolist(), 'sin filas del rival'
    assert sorted(raw['matches']['matchid']) == [1, 2, 3, 4], 'sin partido futuro ni ajeno'
    assert sorted(raw['players']['personid']) == [1, 2, 3, 4, 5], 'solo jugadores de las planillas de O\'Higgins'
    assert raw['goalkeepers']['personid'].tolist() == [3, 3] and 9999 not in raw['goalkeepers']['personid'].tolist()
    by_match = raw['matches'].set_index('matchid').sort_index()
    assert by_match['result'].tolist() == ['Victoria', 'Empate', 'Derrota', 'Victoria']
    assert by_match['goals_for'].tolist() == [2, 0, 0, 1] and by_match['goals_against'].tolist() == [1, 0, 3, 0]
    assert by_match['venue'].tolist() == ['Local', 'Visita', 'Local', 'Local']
    assert by_match.loc[2, 'home_team'] == 'Rival B' and by_match.loc[2, 'away_team'] == "O'Higgins"


def test_database_round_trip_gives_the_same_calculations_as_the_source_frames(comet_conn):
    conn, tiny = comet_conn
    from_db = queries.fetch_raw(_loader(conn))
    a = build_dataset(from_db['sheet'], from_db['matches'], from_db['players'], from_db['goalkeepers'])
    b = build_dataset(tiny['sheet'], tiny['matches'], tiny['players'], tiny['goalkeepers'])
    for name in ('matches', 'facts'):
        left = getattr(a, name).sort_values(['matchid', 'personid'] if name == 'facts' else ['matchid']).reset_index(drop=True)
        right = getattr(b, name).sort_values(['matchid', 'personid'] if name == 'facts' else ['matchid']).reset_index(drop=True)
        columns = ['matchid', 'competition_id', 'category', 'season_year', 'matchdate', 'venue', 'rival', 'result',
                   'goals_for', 'goals_against', 'duration'] if name == 'matches' else \
                  ['matchid', 'personid', 'role', 'participated', 'minutes', 'goals', 'yellow_cards', 'red_cards',
                   'age', 'age_category', 'steps_ahead']
        pd.testing.assert_frame_equal(left[columns], right[columns], check_dtype=False)
    optional = ['second_yellows', 'own_goals']    # solo la base de datos los trae: el resto debe coincidir exactamente
    summary_a = metrics.add_percentages(metrics.player_competition_summary(a)).sort_values(['personid', 'competition_id'])
    summary_b = metrics.add_percentages(metrics.player_competition_summary(b)).sort_values(['personid', 'competition_id'])
    pd.testing.assert_frame_equal(summary_a.drop(columns=optional).reset_index(drop=True),
                                  summary_b.drop(columns=optional).reset_index(drop=True), check_dtype=False)
    assert alert_rules.evaluate_alerts(a, metrics.category_summary(summary_a), 2026)['personid'].tolist() == ['4', '2']


def test_births_as_timestamptz_and_optional_columns_survive_the_real_database(comet_conn):
    conn, _ = comet_conn
    raw = queries.fetch_raw(_loader(conn))
    assert str(raw['players']['dateofbirth'].dtype).startswith('datetime64[ns, '), 'nacimiento con zona horaria, como en COMET real'
    ds = build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers'])
    players = ds.players.set_index('personid')
    assert players.loc['1', 'dateofbirth'] == pd.Timestamp('2011-06-10') and players['dateofbirth'].dt.tz is None
    assert players.loc['1', 'datefrom'] == pd.Timestamp('2019-03-01') and pd.isna(players.loc['2', 'datefrom'])
    assert players.loc['1', 'height'] == 158 and players.loc['1', 'weight'] == 47.5 and pd.isna(players.loc['3', 'height'])
    matches = ds.matches.set_index('matchid')
    assert matches.loc['1', 'nominal_duration'] == 90 and matches.loc['4', 'nominal_duration'] == 70
    assert matches.loc['3', 'matchstatus'] == 'SUSPENDIDO' and matches.loc['1', 'matchstatus'] == 'FINALIZADO'
    f = ds.facts.set_index(['matchid', 'personid'])
    assert f.loc[('3', '2'), 'second_yellows'] == 1 and f.loc[('3', '3'), 'own_goals'] == 1
    assert (f.loc[('1', '1'), ['second_yellows', 'own_goals']] == 0).all()


def test_columns_that_do_not_exist_arrive_as_missing_not_as_errors(comet_conn_base):
    conn, _ = comet_conn_base
    assert queries.available_columns(_loader(conn)) >= {('jugadores', 'personid'), ('partidos', 'matchid')}
    assert ('jugadores', 'datefrom') not in queries.available_columns(_loader(conn))
    raw = queries.fetch_raw(_loader(conn))
    assert raw['sheet'][['second_yellows', 'own_goals']].isna().all().all()
    assert raw['matches'][['nominal_duration', 'matchstatus']].isna().all().all()
    assert raw['players'][['datefrom', 'height', 'weight']].isna().all().all()
    ds = build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers'])
    comp = metrics.add_percentages(metrics.player_competition_summary(ds))
    assert comp['possible_minutes'].notna().all(), 'la duración registrada sigue funcionando sin la nominal'


def test_available_columns_lists_only_the_public_tables_the_portal_reads(comet_conn):
    conn, _ = comet_conn
    conn.execute('CREATE TABLE tabla_privada_ajena (secreto text)')
    columns = queries.available_columns(_loader(conn))
    assert ('actuaciones_jugadores', 'secondyellow') in columns and ('jugadores', 'weight') in columns
    assert not any(table == 'tabla_privada_ajena' for table, _ in columns), 'solo las tablas que el portal usa'


def test_new_calculations_agree_with_the_existing_comet_dashboard(comet_conn, monkeypatch):
    """Minutos, goles, tarjetas, titularidades y goles recibidos = lo que ya muestra COMET."""
    conn, _ = comet_conn
    monkeypatch.syspath_prepend(str(Path('app').resolve()))
    import comet_dashboard as dashboard
    monkeypatch.setattr(dashboard, 'load_data', _loader(conn))
    st.cache_data.clear()
    with security.session_scope({}, verified_user=ADMIN):
        old_players = dashboard.get_player_stats_by_category(None)
        old_keepers = dashboard.get_goalkeeper_stats_by_category(None)
        old_results = dashboard.get_match_results_by_category(None)
    raw = queries.fetch_raw(_loader(conn))
    ds = build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers'])
    mine = metrics.category_summary(metrics.add_percentages(metrics.player_competition_summary(ds)))

    old = old_players.assign(personid=old_players['personid'].astype(str)).set_index(['personid', 'category'])
    field = mine[~mine['personid'].isin(['3'])].set_index(['personid', 'category'])
    for key in old.index:
        assert field.loc[key, 'minutes'] == old.loc[key, 'minutes'], key
        assert field.loc[key, 'played'] == old.loc[key, 'matches'], key
        assert field.loc[key, 'started'] == old.loc[key, 'starts'], key
        assert field.loc[key, 'goals'] == old.loc[key, 'goals'], key
        assert field.loc[key, 'yellow_cards'] == old.loc[key, 'yellow_cards'], key
        assert field.loc[key, 'red_cards'] == old.loc[key, 'red_cards'], key
    keeper = old_keepers.iloc[0]
    conceded = metrics.goalkeeper_conceded(ds)
    assert conceded['goalsconceded'].sum() == keeper['goals_conceded'] and len(conceded) == keeper['matches']

    old_by_match = old_results.assign(matchid=old_results['matchid'].astype(str)).set_index('matchid')
    new_by_match = ds.matches.set_index('matchid')
    for matchid in ds.matches['matchid']:
        assert new_by_match.loc[matchid, 'result'] == old_by_match.loc[matchid, 'result'] or \
            (pd.isna(new_by_match.loc[matchid, 'result']) and pd.isna(old_by_match.loc[matchid, 'result']))
        assert new_by_match.loc[matchid, 'goals_for'] == old_by_match.loc[matchid, 'goals_for']
        assert new_by_match.loc[matchid, 'goals_against'] == old_by_match.loc[matchid, 'goals_against']
        assert new_by_match.loc[matchid, 'venue'] == old_by_match.loc[matchid, 'venue']


PAGES = ['page_weekly_match', 'page_rankings', 'page_player', 'page_indicators', 'page_alerts', 'page_adelantados', 'page_tracking']


@pytest.mark.parametrize('page', PAGES)
def test_every_screen_renders_with_the_types_postgres_really_returns(comet_conn, monkeypatch, page):
    """Fechas date, horas con zona, booleanos y None reales: también pasan por el hash de la caché de Streamlit."""
    from streamlit.testing.v1 import AppTest
    conn, _ = comet_conn
    monkeypatch.syspath_prepend(str(Path('app').resolve()))
    for key, value in [('PORTAL_MODE', '1'), ('DB_SCHEMA', 'scouting'), ('DISABLE_SOFASCORE_UPDATE', '1')]:
        monkeypatch.setenv(key, value)
    import comet_context
    real = queries.fetch_raw(_loader(conn))
    assert isinstance(real['players']['dateofbirth'].iloc[0], object) and real['matches']['matchdate'].dt.tz is not None
    monkeypatch.setattr(comet_context, 'load_raw', lambda: real)
    monkeypatch.setattr(comet_context, 'load_config', lambda: (
        {}, comet_context.EMPTY_MARKS, comet_context.EMPTY_PERIODS, 'sin configuración'))
    module = 'comet_followup' if page in PAGES[:3] else 'comet_insights'
    script = (f'import {module}\nfrom scouting.portal import security\n'
              f'with security.session_scope({{}}, verified_user={ADMIN!r}):\n    {module}.{page}()\n')
    app = AppTest.from_string(script, default_timeout=90).run()
    assert not app.exception, [e.value for e in app.exception]
    assert not app.error, [e.value for e in app.error]


def test_match_without_final_score_has_no_result_instead_of_a_defeat(comet_conn):
    conn, _ = comet_conn
    conn.execute("INSERT INTO partidos VALUES (100, 50, now() - interval '2 days', %s, 1)", (CLUB,))
    conn.execute("INSERT INTO partidos_fases VALUES (50, 'Primer tiempo', 1, 0)")
    raw = queries.fetch_raw(_loader(conn))
    unfinished = raw['matches'].set_index('matchid').loc[50]
    assert pd.isna(unfinished['result']) and pd.isna(unfinished['goals_for'])


def test_comet_reader_role_can_run_every_new_query_and_cannot_write():
    dsn = _dsn()
    with psycopg.connect(dsn) as conn:
        _create_comet_tables(conn, full=True)
        _fill_comet_tables(conn, full=True)
        for table in DDL:
            conn.execute(f'ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY')
        source = Path('db/portal/002_comet_reader.sql').read_text(encoding='utf8')
        conn.execute(source.replace('BEGIN;', '').replace('COMMIT;', ''))
        conn.execute('SET LOCAL ROLE comet_reader')
        assert {('jugadores', 'datefrom'), ('actuaciones_jugadores', 'secondyellow'), ('competiciones', 'matchlength'),
                ('partidos', 'matchstatus')} <= queries.available_columns(_loader(conn)), 'el lector ve las columnas opcionales'
        raw = queries.fetch_raw(_loader(conn))
        assert len(raw['sheet']) and len(raw['matches']) == 4 and len(raw['players']) == 5 and len(raw['goalkeepers']) == 2
        assert raw['players']['datefrom'].notna().sum() == 2 and raw['sheet']['second_yellows'].sum() == 1
        for table in DDL:
            assert not conn.execute('SELECT has_table_privilege(current_user, %s, %s)', (f'public.{table}', 'INSERT')).fetchone()[0]
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute('INSERT INTO public.jugadores(personid) VALUES (1)')
        conn.rollback()


# --- Migración 003 y persistencia ------------------------------------------------------------------------------

@pytest.fixture
def portal_db(monkeypatch):
    dsn = _dsn()
    with psycopg.connect(dsn, autocommit=True) as db:
        db.execute('CREATE SCHEMA IF NOT EXISTS auth')
        db.execute('CREATE TABLE IF NOT EXISTS auth.users(id uuid PRIMARY KEY)')
        for role in ['anon', 'authenticated']:
            if not db.execute('SELECT 1 FROM pg_roles WHERE rolname=%s', (role,)).fetchone():
                db.execute(psycopg.sql.SQL('CREATE ROLE {}').format(psycopg.sql.Identifier(role)))
        db.execute(Path('db/portal/001_accounts.sql').read_text(encoding='utf8'))
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


def _apply_003(dsn):
    with psycopg.connect(dsn, autocommit=True) as db:
        db.execute(Path('db/portal/003_comet_followup.sql').read_text(encoding='utf8'))


def test_migration_003_is_idempotent_private_and_without_delete(portal_db):
    _apply_003(portal_db)
    _apply_003(portal_db)  # se puede volver a aplicar
    tables = ['comet_settings', 'comet_player_marks', 'comet_selection_periods', 'comet_digest_deliveries']
    with psycopg.connect(portal_db, autocommit=True) as db:
        for table in tables:
            assert db.execute("SELECT relrowsecurity FROM pg_class WHERE oid = %s::regclass", (f'portal.{table}',)).fetchone()[0]
            grants = db.execute("SELECT grantee, privilege_type FROM information_schema.role_table_grants "
                                "WHERE table_schema='portal' AND table_name=%s", (table,)).fetchall()
            owner = db.execute("SELECT tableowner FROM pg_tables WHERE schemaname='portal' AND tablename=%s",
                               (table,)).fetchone()[0]  # el dueño varía: postgres en local, scouting_test en CI
            assert {g for g, _ in grants} <= {'portal_runtime', owner}, f'{table}: permisos inesperados {grants}'
            assert 'DELETE' not in {p for g, p in grants if g == 'portal_runtime'}
        db.execute('SET ROLE authenticated')
        for table in tables:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                db.execute(f'SELECT * FROM portal.{table}')
        db.execute('RESET ROLE')
        db.execute('SET ROLE anon')
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute('SELECT * FROM portal.comet_settings')


def test_portal_runtime_can_read_and_write_but_constraints_hold(portal_db):
    _apply_003(portal_db)
    admin_id = accounts.bootstrap_admin('admin@example.test', 'Admin', 'synthetic-password-123')
    with psycopg.connect(portal_db, autocommit=True) as db:
        db.execute('SET ROLE portal_runtime')
        db.execute("INSERT INTO portal.comet_settings(key, value, updated_by) VALUES ('yellow_threshold', '3', %s)", (admin_id,))
        db.execute("INSERT INTO portal.comet_player_marks(personid, mark, updated_by) VALUES ('1', 'proyectado', %s)", (admin_id,))
        db.execute("INSERT INTO portal.comet_selection_periods(personid, kind, starts_on, ends_on, created_by) "
                   "VALUES ('1', 'mundial', '2026-05-01', '2026-05-10', %s)", (admin_id,))
        assert db.execute('SELECT count(*) FROM portal.comet_settings').fetchone()[0] == 1
        db.execute("UPDATE portal.comet_player_marks SET active = false WHERE personid = '1'")
        for table in ('comet_settings', 'comet_player_marks', 'comet_selection_periods'):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                db.execute(f'DELETE FROM portal.{table}')
        bad = [
            ("INSERT INTO portal.comet_player_marks(personid, mark, updated_by) VALUES ('1', 'estrella', %s)", psycopg.errors.CheckViolation),
            ("INSERT INTO portal.comet_selection_periods(personid, kind, starts_on, ends_on, created_by) VALUES ('1', 'mundial', '2026-05-10', '2026-05-01', %s)", psycopg.errors.CheckViolation),
            ("INSERT INTO portal.comet_selection_periods(personid, kind, starts_on, ends_on, created_by) VALUES ('1', 'olimpiadas', '2026-05-01', '2026-05-02', %s)", psycopg.errors.CheckViolation),
            ("INSERT INTO portal.comet_player_marks(personid, mark, note, updated_by) VALUES ('2', 'proyectado', repeat('x', 501), %s)", psycopg.errors.CheckViolation),
            ("INSERT INTO portal.comet_player_marks(personid, mark, updated_by) VALUES ('', 'proyectado', %s)", psycopg.errors.CheckViolation),
            ("INSERT INTO portal.comet_settings(key, value, updated_by) VALUES ('x', '1', %s)", psycopg.errors.ForeignKeyViolation),
        ]
        for statement, error in bad:
            with pytest.raises(error):
                db.execute(statement, (str(uuid4()) if error is psycopg.errors.ForeignKeyViolation else admin_id,))


def test_config_store_end_to_end_with_real_database(portal_db):
    _apply_003(portal_db)
    admin_id = accounts.bootstrap_admin('admin@example.test', 'Admin', 'synthetic-password-123')
    admin = accounts.get_user(admin_id)
    day = pd.Timestamp('2026-05-01').date()
    with security.session_scope({}, verified_user=admin):
        settings, marks, periods = config_store.load_all()
        assert settings == {} and marks.empty and periods.empty
        config_store.save_setting('yellow_threshold', 3, confirmed=False)
        config_store.save_setting('card_cycle', 'temporada', confirmed=True)
        config_store.save_setting('yellow_threshold', 5, confirmed=True)  # actualiza, no duplica
        config_store.save_setting('roster_rule', 'ignorado', confirmed=True)  # regla informativa: solo su confirmación
        config_store.save_setting(config_store.ALERT_CONFIG_KEY, {'playing_up': {'enabled': False, 'color': 'Verde'}})
        config_store.set_mark('1', 'proyectado', True, 'nota <b>uno</b>')
        config_store.set_mark('1', 'seleccion', True)
        config_store.set_mark('1', 'seleccion', False)
        config_store.add_period('1', 'sudamericano', day, day + timedelta(days=9), 'Sub-17')
        settings, marks, periods = config_store.load_all()
        rules = Rules({k: v for k, v in settings.items() if k != config_store.ALERT_CONFIG_KEY})
        assert rules.value('yellow_threshold') == 5 and rules.confirmed('yellow_threshold')
        assert rules.value('card_cycle') == 'temporada' and rules.status('card_cycle').startswith('Confirmada')
        assert rules.value('roster_rule') == 'planillas' and rules.confirmed('roster_rule')
        assert alert_rules.resolve_config(settings[config_store.ALERT_CONFIG_KEY]['value'])['playing_up'] == {'enabled': False, 'color': 'Verde'}
        active = marks[marks['active']]
        assert active['mark'].tolist() == ['proyectado'] and active['note'].iloc[0] == 'nota <b>uno</b>'
        assert set(marks['mark']) == {'proyectado', 'seleccion'}, 'la marca retirada se conserva como inactiva'
        assert len(periods) == 1 and periods.loc[0, 'kind'] == 'sudamericano' and bool(periods.loc[0, 'active'])
        assert pd.Timestamp(periods.loc[0, 'end']) == pd.Timestamp('2026-05-10')
        config_store.retire_period(int(periods.loc[0, 'id']))
        _, _, after = config_store.load_all()
        assert len(after) == 1 and not bool(after.loc[0, 'active']), 'el período se retira, no se borra'
        assert set(after.columns) >= {'id', 'personid', 'kind', 'start', 'end', 'note', 'active'}
        # Lo guardado tiene autoría: quien lo cambió queda registrado.
        with psycopg.connect(portal_db) as db:
            assert db.execute('SELECT DISTINCT updated_by::text FROM portal.comet_settings').fetchall() == [(admin_id,)]
            retired = db.execute('SELECT retired_by::text, retired_at IS NOT NULL, created_by::text '
                                 'FROM portal.comet_selection_periods').fetchall()
            assert retired == [(admin_id, True, admin_id)], 'queda quién retiró el período y cuándo'


# --- Registro de entregas del resumen semanal ------------------------------------------------------------------

WEEK = date(2026, 3, 16)


def test_delivery_table_constraints_and_grants(portal_db):
    _apply_003(portal_db)
    with psycopg.connect(portal_db, autocommit=True) as db:
        db.execute('SET ROLE portal_runtime')
        db.execute("INSERT INTO portal.comet_digest_deliveries(week_start, recipient, status) VALUES ('2026-03-16', 'a@example.test', 'reservado')")
        with pytest.raises(psycopg.errors.UniqueViolation):
            db.execute("INSERT INTO portal.comet_digest_deliveries(week_start, recipient, status) VALUES ('2026-03-16', 'a@example.test', 'reservado')")
        for bad in ("('2026-03-16', 'sin-arroba', 'reservado')", "('2026-03-16', 'b@example.test', 'quizás')"):
            with pytest.raises(psycopg.errors.CheckViolation):
                db.execute(f'INSERT INTO portal.comet_digest_deliveries(week_start, recipient, status) VALUES {bad}')
        with pytest.raises(psycopg.errors.CheckViolation):
            db.execute("UPDATE portal.comet_digest_deliveries SET attempts = 21")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute('DELETE FROM portal.comet_digest_deliveries')
        db.execute('RESET ROLE')
        db.execute('SET ROLE authenticated')
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute('SELECT * FROM portal.comet_digest_deliveries')


def test_postgres_ledger_reserves_once_retries_failures_and_never_retakes_open_reservations(portal_db):
    _apply_003(portal_db)
    ledger = PostgresLedger()
    assert ledger.status(WEEK, 'a@example.test') is None
    assert ledger.reserve(WEEK, 'A@Example.test') is True, 'se normaliza a minúsculas'
    assert ledger.reserve(WEEK, 'a@example.test') is False, 'ya reservada'
    assert ledger.status(WEEK, 'a@example.test') == ('reservado', 1)
    ledger.finish(WEEK, 'a@example.test', sent=False, error='SMTPServerDisconnected')
    assert ledger.status(WEEK, 'a@example.test') == ('fallido', 1)
    assert ledger.reserve(WEEK, 'a@example.test') is True and ledger.status(WEEK, 'a@example.test') == ('reservado', 2)
    ledger.finish(WEEK, 'a@example.test', sent=True)
    assert ledger.status(WEEK, 'a@example.test') == ('enviado', 2)
    assert ledger.reserve(WEEK, 'a@example.test') is False, 'lo enviado no se reserva de nuevo'
    ledger.finish(WEEK, 'a@example.test', sent=False, error='tardío')     # cerrar dos veces no reabre nada
    assert ledger.status(WEEK, 'a@example.test') == ('enviado', 2)
    # Agota los intentos.
    for attempt in (1, 2, 3):
        assert ledger.reserve(WEEK, 'b@example.test') is True
        ledger.finish(WEEK, 'b@example.test', sent=False, error='x' * 500)
    assert ledger.status(WEEK, 'b@example.test') == ('fallido', 3) and ledger.reserve(WEEK, 'b@example.test') is False
    # Otra semana es otra entrega.
    assert ledger.reserve(date(2026, 3, 23), 'a@example.test') is True
    with psycopg.connect(portal_db) as db:
        assert db.execute("SELECT length(last_error) FROM portal.comet_digest_deliveries WHERE recipient = 'b@example.test'").fetchone()[0] == 200


def test_concurrent_processes_cannot_reserve_the_same_delivery_in_postgres(portal_db):
    _apply_003(portal_db)
    barrier, wins, errors = threading.Barrier(8), [], []

    def attempt():
        try:
            barrier.wait()
            wins.append(PostgresLedger().reserve(WEEK, 'a@example.test'))
        except Exception as exc:  # pragma: no cover - solo si el registro falla
            errors.append(exc)
    threads = [threading.Thread(target=attempt) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors and wins.count(True) == 1 and len(wins) == 8


def test_two_full_runs_of_the_job_against_postgres_send_once(portal_db, monkeypatch):
    _apply_003(portal_db)
    from scripts import send_comet_weekly_digest as job
    from tests.test_comet_ops import FakeSMTP, SMTP_ENV
    FakeSMTP.instances.clear()
    stored = {'digest_recipients': {'value': ['a@example.test'], 'confirmed': True}}
    env = {**SMTP_ENV, 'PORTAL_AUTH_DATABASE_URL': portal_db}
    codes = []
    for _ in range(2):
        codes.append(job.run(['--week-of', '2026-03-16', '--send'], env=env, load_raw=lambda: comet_tiny.build(),
                             stored=(stored, job.NO_PERIODS, None), now=comet_tiny.TODAY, smtp_factory=FakeSMTP, out=lambda *_: None))
    assert codes == [0, 0] and sum(len(s.sent) for s in FakeSMTP.instances) == 1


def test_job_refuses_to_send_when_the_delivery_table_is_missing(portal_db):
    from scripts import send_comet_weekly_digest as job
    from tests.test_comet_ops import FakeSMTP, SMTP_ENV
    FakeSMTP.instances.clear()
    lines = []
    code = job.run(['--week-of', '2026-03-16', '--send'], env={**SMTP_ENV, 'PORTAL_AUTH_DATABASE_URL': portal_db},
                   load_raw=lambda: comet_tiny.build(),
                   stored=({'digest_recipients': {'value': ['a@example.test'], 'confirmed': True}}, job.NO_PERIODS, None),
                   now=comet_tiny.TODAY, smtp_factory=FakeSMTP, out=lines.append)
    assert code == 2 and 'registro de entregas no está disponible' in '\n'.join(lines)
    assert sum(len(s.sent) for s in FakeSMTP.instances) == 0


def test_store_reports_missing_migration_without_leaking_details(portal_db):
    admin = accounts.get_user(accounts.bootstrap_admin('admin@example.test', 'Admin', 'synthetic-password-123'))
    with security.session_scope({}, verified_user=admin):
        with pytest.raises(config_store.StoreUnavailable, match='003_comet_followup.sql'):
            config_store.load_all()
        with pytest.raises(config_store.StoreUnavailable):
            config_store.set_mark('1', 'proyectado', True)
