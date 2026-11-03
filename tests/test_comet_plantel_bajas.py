"""Plantel vigente y bajas de jugadores: COMET no borra a quien deja el club, así que el portal decide quién cuenta.

Todo con datos ficticios. Lo que toca PostgreSQL vive en `test_comet_plantel_postgres.py`.
"""
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from scouting.comet import alerts as alert_rules, config_store, roster
from scouting.comet.pipeline import compute_all
from scouting.comet.rules import RULES_BY_KEY, STATUS_PENDING, Rules
from scouting.portal import security
from tests import comet_tiny

TODAY = pd.Timestamp('2026-10-30')
ADMIN = dict(id='00000000-0000-0000-0000-000000000001', role='admin', active=True, revision=1,
             display_name='Admin', username='admin@example.test')
SCOUT = dict(ADMIN, role='scout')


def person(pid, name, category, age, last_match=None, datefrom=None, nationality='Chile'):
    return dict(personid=pid, displayname=name, age=age, age_category=category, nationality=nationality,
                level='Formativo', status='ACTIVO', last_match=last_match, datefrom=datefrom,
                dateofbirth=pd.Timestamp('2000-01-01'))


def squad_frame(*people):
    return pd.DataFrame(list(people))


def bajas_frame(*rows):
    return pd.DataFrame([dict(personid=p, active=a, reason=r, effective_on=d, note='', updated_at=pd.Timestamp('2026-10-01'))
                         for p, a, r, d in rows], columns=roster.BAJA_COLUMNS)


def states(frame):
    return dict(zip(frame['personid'], frame['state']))


# --- Regla automática -------------------------------------------------------------------------------------------------

def test_a_player_on_a_recent_sheet_counts_and_one_with_an_old_sheet_does_not():
    squad = squad_frame(
        person(1, 'Actual', 'Primer Equipo', 27, last_match=pd.Timestamp('2026-10-10 15:00')),
        person(2, 'Antiguo', 'Primer Equipo', 31, last_match=pd.Timestamp('2024-05-01 15:00')))
    done = roster.classify(squad, TODAY, 365)
    assert states(done) == {'1': roster.STATE_CURRENT, '2': roster.STATE_INACTIVE}
    reasons = dict(zip(done['personid'], done['reason']))
    assert reasons['1'] == 'Última planilla: 10-10-2026 (hace 20 días)'
    assert reasons['2'].startswith('Última planilla: 01-05-2024') and 'fuera de los 365 días' in reasons['2']
    assert list(roster.current(done)['personid']) == ['1'], 'nadie se borra: el antiguo sigue en `classified`, solo no cuenta'
    assert len(done) == 2


def test_the_window_edge_counts_the_last_day_and_not_the_next():
    limit = TODAY - timedelta(days=365)
    squad = squad_frame(person(1, 'En el borde', 'U-15', 14, last_match=limit + timedelta(hours=18)),
                        person(2, 'Un día fuera', 'U-15', 14, last_match=limit - timedelta(days=1)))
    assert states(roster.classify(squad, TODAY, 365)) == {'1': roster.STATE_CURRENT, '2': roster.STATE_INACTIVE}
    assert states(roster.classify(squad, TODAY, 366))['2'] == roster.STATE_CURRENT, 'el plazo es el que dice la regla'


def test_a_player_without_sheets_is_inactive_unless_the_profile_has_a_recent_datefrom():
    squad = squad_frame(
        person(1, 'Nunca jugó', 'U-16', 15),
        person(2, 'Alta reciente', 'U-16', 15, datefrom=pd.Timestamp('2026-08-15', tz='UTC')),
        person(3, 'Alta antigua', 'U-16', 15, datefrom=pd.Timestamp('2019-03-01', tz='UTC')),
        person(4, 'Alta futura', 'U-16', 15, datefrom=pd.Timestamp('2027-01-10', tz='UTC')))
    done = roster.classify(squad, TODAY, 365)
    assert states(done) == {'1': roster.STATE_INACTIVE, '2': roster.STATE_CURRENT, '3': roster.STATE_INACTIVE,
                            '4': roster.STATE_INACTIVE}
    reasons = dict(zip(done['personid'], done['reason']))
    assert reasons['1'] == 'Nunca figuró en una planilla de O’Higgins'
    assert reasons['2'] == 'Alta reciente: datefrom 15-08-2026, todavía sin planilla'


def test_missing_optional_columns_leave_the_player_without_activity_instead_of_failing():
    squad = pd.DataFrame([dict(personid=1, displayname='Sin columnas', age=20, age_category='U-20')])
    assert states(roster.classify(squad, TODAY, 365)) == {'1': roster.STATE_INACTIVE}
    assert roster.classify(squad.iloc[0:0], TODAY, 365).empty


def test_sheet_dates_use_the_santiago_day_not_the_utc_day():
    """Un partido del sábado 7 de marzo a las 22:30 en Santiago es el domingo 8 a la 01:30 UTC: el día es el 7."""
    squad = squad_frame(person(1, 'Noche', 'U-15', 14, last_match=pd.Timestamp('2026-03-08 01:30', tz='UTC')))
    assert roster.classify(squad, TODAY, 365)['last_sheet'].iloc[0] == pd.Timestamp('2026-03-07')


def test_identifiers_match_whatever_type_each_source_uses():
    squad = squad_frame(person(12.0, 'Float', 'U-15', 14, last_match=pd.Timestamp('2026-10-01')))
    bajas = bajas_frame(('12', True, 'dejo_club', date(2026, 10, 20)))
    assert states(roster.classify(squad, TODAY, 365, bajas)) == {'12': roster.STATE_BAJA}
    assert roster.active_baja_ids(bajas) == frozenset({'12'})


# --- Bajas ------------------------------------------------------------------------------------------------------------------

def test_a_baja_removes_a_current_player_and_reincorporating_brings_them_back_without_deleting_anything():
    squad = squad_frame(person(1, 'Se va', 'U-15', 14, last_match=pd.Timestamp('2026-10-10')),
                        person(2, 'Se queda', 'U-15', 14, last_match=pd.Timestamp('2026-10-10')))
    active = bajas_frame(('1', True, 'cedido', date(2026, 10, 20)))
    done = roster.classify(squad, TODAY, 365, active)
    assert states(done) == {'1': roster.STATE_BAJA, '2': roster.STATE_CURRENT}
    assert dict(zip(done['personid'], done['reason']))['1'] == 'Cedido a otro club · desde 20-10-2026'
    assert len(done) == 2 and list(roster.current(done)['personid']) == ['2']
    undone = bajas_frame(('1', False, 'cedido', date(2026, 10, 20)))
    assert states(roster.classify(squad, TODAY, 365, undone)) == {'1': roster.STATE_CURRENT, '2': roster.STATE_CURRENT}
    assert roster.active_baja_ids(undone) == frozenset() and roster.active_baja_ids(None) == frozenset()
    assert roster.active_baja_ids(roster.EMPTY_BAJAS) == frozenset()


def test_a_baja_stays_in_force_but_warns_when_the_player_shows_up_on_a_later_sheet():
    squad = squad_frame(person(1, 'Volvió', 'U-15', 14, last_match=pd.Timestamp('2026-10-10 15:00')),
                        person(2, 'Mismo día', 'U-15', 14, last_match=pd.Timestamp('2026-10-10 15:00')),
                        person(3, 'Antes', 'U-15', 14, last_match=pd.Timestamp('2026-10-10 15:00')))
    bajas = bajas_frame(('1', True, 'cedido', date(2026, 10, 1)), ('2', True, 'cedido', date(2026, 10, 10)),
                        ('3', True, 'cedido', date(2026, 10, 20)))
    done = roster.classify(squad, TODAY, 365, bajas)
    reasons = dict(zip(done['personid'], done['reason']))
    assert set(done['state']) == {roster.STATE_BAJA}, 'la baja manda; el aviso solo informa al administrador'
    assert reasons['1'] == 'Cedido a otro club · desde 01-10-2026 · atención: figura en una planilla posterior (10-10-2026)'
    assert reasons['2'] == 'Cedido a otro club · desde 10-10-2026' and reasons['3'] == 'Cedido a otro club · desde 20-10-2026'


def test_a_baja_wins_over_a_recent_sheet_and_the_summary_and_calibration_agree_with_the_classification():
    people = [person(i, f'P{i}', 'Primer Equipo', 25, last_match=pd.Timestamp('2026-09-01')) for i in range(1, 4)]
    people += [person(10 + i, f'A{i}', 'Primer Equipo', 30, last_match=pd.Timestamp('2023-01-01')) for i in range(5)]
    people += [person(20, 'Joven', 'U-15', 14, last_match=pd.Timestamp('2026-10-01')),
               person(21, 'Joven ido', 'U-15', 14, last_match=pd.Timestamp('2025-01-01'))]
    squad = squad_frame(*people)
    bajas = bajas_frame(('1', True, 'dejo_club', date(2026, 10, 1)))
    done = roster.classify(squad, TODAY, 365, bajas)
    summary = roster.summary_by_category(done, ['Primer Equipo', 'U-15']).set_index('Categoría')
    assert summary.loc['Primer Equipo'].to_dict() == {'Vigentes': 2, roster.STATE_INACTIVE: 5, roster.STATE_BAJA: 1,
                                                      'Registrados en COMET': 8}
    assert summary.loc['U-15'].to_dict() == {'Vigentes': 1, roster.STATE_INACTIVE: 1, roster.STATE_BAJA: 0,
                                             'Registrados en COMET': 2}
    table = roster.calibration(squad, TODAY, bajas, windows=(90, 365, 2000)).set_index('Días sin planilla')
    assert table.loc[365, 'Vigentes'] == len(roster.current(done)) == 3
    assert table.loc[365, 'Primer Equipo'] == 2 and table.loc[365, 'Categorías menores'] == 1
    assert table['Vigentes'].is_monotonic_increasing and table.loc[2000, 'Vigentes'] == len(squad) - 1, 'la baja no depende del plazo'


def test_the_squad_rule_is_an_assumption_pending_with_a_question_for_pablo():
    rules = Rules()
    rule = RULES_BY_KEY['squad_activity_days']
    assert rules.value('squad_activity_days') == 365 and rules.status('squad_activity_days') == STATUS_PENDING
    assert rule.question and 'datefrom' in rule.question and rule.minimum <= 365 <= rule.maximum
    with pytest.raises(ValueError):
        config_store.clean_setting('squad_activity_days', 5)
    assert config_store.clean_setting('squad_activity_days', 120) == 120


# --- Validación de bajas -------------------------------------------------------------------------------------------------

def test_baja_validation_rejects_unknown_reasons_bad_dates_ids_and_long_notes():
    today = date(2026, 10, 30)
    ok = config_store.clean_baja(' 15 ', 'cedido', date(2026, 10, 1), '  se fue a préstamo ', today=today)
    assert ok == ('15', 'cedido', date(2026, 10, 1), 'se fue a préstamo')
    assert config_store.clean_baja('15', 'dejo_club', datetime(2026, 10, 1, 8), today=today)[2] == date(2026, 10, 1)
    assert config_store.clean_baja('15', 'otro', today + timedelta(days=1), today=today)[2] == today + timedelta(days=1), \
        'mañana se acepta por la diferencia de huso horario'
    for bad in [dict(personid='1; DROP TABLE x', reason='cedido', effective_on=today),
                dict(personid='', reason='cedido', effective_on=today),
                dict(personid='1', reason='despedido', effective_on=today),
                dict(personid='1', reason='cedido', effective_on=today + timedelta(days=2)),
                dict(personid='1', reason='cedido', effective_on=date(1999, 12, 31)),
                dict(personid='1', reason='cedido', effective_on='2026-10-01'),
                dict(personid='1', reason='cedido', effective_on=today, note='x' * 501)]:
        with pytest.raises(ValueError):
            config_store.clean_baja(today=today, **bad)


def test_bajas_are_admin_only_and_blocked_in_read_only_mode(monkeypatch):
    calls = [lambda: config_store.set_bajas(['1'], 'cedido', date(2026, 10, 1)),
             lambda: config_store.reinstate_bajas(['1']), config_store.load_bajas, config_store.load_roster_config]
    for call in calls:
        with pytest.raises(PermissionError):  # sin sesión
            call()
        with security.session_scope({}, verified_user=SCOUT), pytest.raises(PermissionError, match='administrador'):
            call()
    monkeypatch.setenv('PORTAL_AUTH_PROVIDER', 'local_recovery')
    with security.session_scope({}, verified_user=ADMIN):
        for write in (lambda: config_store.set_bajas(['1'], 'cedido', date(2026, 10, 1)),
                      lambda: config_store.reinstate_bajas(['1'])):
            with pytest.raises(PermissionError, match='solo permite consultar'):
                write()


def test_set_bajas_validates_before_opening_any_connection(monkeypatch):
    def no_connection():
        raise AssertionError('no debe conectarse con datos no válidos')
    monkeypatch.setattr(config_store.accounts, 'connect', no_connection)
    with security.session_scope({}, verified_user=ADMIN):
        for args in [([], 'cedido', date(2026, 10, 1)), (['1'], 'despedido', date(2026, 10, 1)),
                     (['x y'], 'cedido', date(2026, 10, 1)), ([str(i) for i in range(201)], 'cedido', date(2026, 10, 1))]:
            with pytest.raises(ValueError):
                config_store.set_bajas(*args)


def test_missing_005_is_reported_by_name_without_leaking_details(monkeypatch):
    import psycopg

    class Broken:
        def __enter__(self):
            raise psycopg.errors.UndefinedTable('relation "portal.comet_player_bajas" does not exist')

        def __exit__(self, *exc):
            return False
    monkeypatch.setattr(config_store.accounts, 'connect', lambda: Broken())
    with security.session_scope({}, verified_user=ADMIN):
        with pytest.raises(config_store.StoreUnavailable, match='005_comet_player_bajas.sql') as failure:
            config_store.load_bajas()
        assert 'relation' not in str(failure.value)
        with pytest.raises(config_store.StoreUnavailable, match='003_comet_followup.sql'):
            config_store.load_roster_config()


# --- Alertas y resumen semanal ------------------------------------------------------------------------------------------------

def tiny_alerts(**kwargs):
    computed = compute_all(comet_tiny.build(), {'yellow_threshold': {'value': 1, 'confirmed': True}},
                           pd.DataFrame(columns=['id', 'personid', 'kind', 'starts_on', 'ends_on', 'note', 'active', 'start', 'end']))
    return computed, alert_rules.evaluate_alerts(computed.ds, computed.cat, 2026, **kwargs)


def test_alerts_skip_players_with_a_baja_and_keep_everyone_else():
    _, everyone = tiny_alerts()
    flagged = set(everyone['personid'])
    assert {'1', '2'} <= flagged, 'P1 y P2 tienen amarillas con el umbral en 1'
    _, without_first = tiny_alerts(exclude=frozenset({'1'}))
    assert '1' not in set(without_first['personid']) and set(without_first['personid']) == flagged - {'1'}
    assert len(tiny_alerts(exclude=frozenset())[1]) == len(everyone) and len(tiny_alerts(exclude=None)[1]) == len(everyone)


def test_context_applies_bajas_only_to_the_season_in_progress():
    import sys
    sys.path.insert(0, str(Path('app').resolve()))
    try:
        import comet_context
    finally:
        sys.path.remove(str(Path('app').resolve()))
    ctx = comet_context.Context(computed=None, alert_config={}, marks=comet_context.EMPTY_MARKS, periods=comet_context.EMPTY_PERIODS,
                                store_error=None, today=TODAY, season=2026,
                                bajas=bajas_frame(('1', True, 'dejo_club', date(2026, 10, 1)), ('2', False, 'cedido', date(2026, 9, 1))))
    assert ctx.alert_exclusions(2026) == frozenset({'1'})
    assert ctx.alert_exclusions(2025) == frozenset() and ctx.alert_exclusions(None) == frozenset()
    assert comet_context.Context(computed=None, alert_config={}, marks=None, periods=None, store_error=None,
                                 today=TODAY, season=2026).bajas.empty


def test_weekly_digest_leaves_out_players_with_a_baja(capsys):
    from scripts import send_comet_weekly_digest as digest_job
    raw = comet_tiny.build()
    stored = ({'yellow_threshold': {'value': 1, 'confirmed': True}}, digest_job.NO_PERIODS, None)
    args = ['--week-of', '2026-03-09']

    def alerts_section(bajas=None):
        lines = []
        digest_job.run(args, env={}, load_raw=lambda: raw, stored=stored, now='2026-03-30', out=lines.append, bajas=bajas)
        text = '\n'.join(lines)
        return text, text.split('ALERTAS VIGENTES')[1].split('NOTAS')[0]

    whole, alerts = alerts_section()
    assert 'Jugador Uno' in alerts and 'Jugador Dos' in alerts
    # La semana está en la temporada en curso (la de `now`): con una baja vigente, P1 deja de aparecer en las alertas.
    # El partido de esa semana es historia y conserva sus amarillas.
    whole, alerts = alerts_section(bajas_frame(('1', True, 'dejo_club', date(2026, 3, 25))))
    assert 'Jugador Uno' not in alerts and 'Jugador Dos' in alerts
    assert 'Amarillas: Jugador Uno' in whole
    # Una baja reincorporada no quita nada.
    assert 'Jugador Uno' in alerts_section(bajas_frame(('1', False, 'dejo_club', date(2026, 3, 25))))[1]


def test_digest_job_reads_bajas_from_the_private_connection_and_warns_when_it_cannot(monkeypatch):
    from scripts import send_comet_weekly_digest as digest_job
    assert digest_job.load_bajas({})[1] == 'PORTAL_AUTH_DATABASE_URL no está definida'
    monkeypatch.setattr(config_store, 'load_bajas_for_job', lambda: (_ for _ in ()).throw(
        config_store.StoreUnavailable('Falta aplicar db/portal/005_comet_player_bajas.sql en Supabase.')))
    frame, warning = digest_job.load_bajas({'PORTAL_AUTH_DATABASE_URL': 'postgresql://example.invalid/x'})
    assert frame.empty and '005_comet_player_bajas.sql' in warning
    expected = bajas_frame(('7', True, 'otro', date(2026, 1, 1)))
    monkeypatch.setattr(config_store, 'load_bajas_for_job', lambda: expected)
    assert digest_job.load_bajas({'PORTAL_AUTH_DATABASE_URL': 'postgresql://example.invalid/x'}) == (expected, None)


# --- Pantallas ---------------------------------------------------------------------------------------------------------------------

SQUAD = squad_frame(
    person(101, 'Delantero Actual', 'Primer Equipo', 26, last_match=pd.Timestamp('2026-10-20 18:00')),
    person(102, 'Portero Actual', 'Primer Equipo', 29, last_match=pd.Timestamp('2026-10-05 18:00')),
    person(103, 'Ex Jugador Uno', 'Primer Equipo', 33, last_match=pd.Timestamp('2022-04-01 18:00')),
    person(104, 'Ex Jugador Dos', 'Primer Equipo', 35),
    person(105, 'Ex Jugador Tres', 'Primer Equipo', 30, last_match=pd.Timestamp('2023-06-01 18:00')),
    person(201, 'Sub Quince Uno', 'U-15', 14, last_match=pd.Timestamp('2026-10-18 11:00')),
    person(202, 'Sub Quince Dos', 'U-15', 14, last_match=pd.Timestamp('2026-10-18 11:00')),
    person(203, 'Sub Quince Ido', 'U-15', 15, last_match=pd.Timestamp('2025-03-02 11:00')),
    person(301, 'Sub Veinte Uno', 'U-20', 19, last_match=pd.Timestamp('2026-10-19 11:00')))
STATS = pd.DataFrame([
    dict(personid=201, displayname='Sub Quince Uno', age=14, nationality='Chile', level='Formativo', category='U-15',
         season_year=2026, matches=9, minutes=700, starts=8, goals=5, yellow_cards=1, red_cards=0),
    dict(personid=203, displayname='Sub Quince Ido', age=15, nationality='Chile', level='Formativo', category='U-15',
         season_year=2026, matches=20, minutes=1500, starts=19, goals=12, yellow_cards=2, red_cards=0)])
OVERVIEW = pd.DataFrame([dict(category='U-15', total_competitions=1, total_matches=9, season='2026')])

SCRIPT = '''
import comet_dashboard
from scouting.portal import security
with security.session_scope({{}}, verified_user={admin!r}):
    comet_dashboard.{function}()
'''


@pytest.fixture
def screen(monkeypatch):
    monkeypatch.syspath_prepend(str(Path('app').resolve()))
    for key, value in [('PORTAL_MODE', '1'), ('DB_SCHEMA', 'scouting'), ('DISABLE_SOFASCORE_UPDATE', '1')]:
        monkeypatch.setenv(key, value)
    monkeypatch.delenv('PORTAL_AUTH_PROVIDER', raising=False)
    import comet_context
    import comet_dashboard
    monkeypatch.setattr(comet_context, 'now', lambda: TODAY)
    monkeypatch.setattr(comet_dashboard, 'get_squad_by_age_category', lambda: SQUAD.copy())
    monkeypatch.setattr(comet_dashboard, 'get_categories_overview', lambda: OVERVIEW.copy())
    monkeypatch.setattr(comet_dashboard, 'get_player_stats_by_year', lambda category=None: STATS.copy())
    monkeypatch.setattr(comet_dashboard, 'get_goalkeeper_stats_by_year', lambda category=None: pd.DataFrame())
    state = dict(bajas=roster.EMPTY_BAJAS, error=None, writes=[], reinstated=[], reinstated_count=None)
    monkeypatch.setattr(config_store, 'load_roster_config', lambda: ({}, state['bajas'], state['error']))

    def set_bajas(ids, reason, day, note=''):
        state['writes'].append((sorted(ids), reason, day, note))
        return len(ids)

    def reinstate_bajas(ids):
        state['reinstated'].append(sorted(ids))
        return len(ids) if state['reinstated_count'] is None else state['reinstated_count']
    monkeypatch.setattr(config_store, 'set_bajas', set_bajas)
    monkeypatch.setattr(config_store, 'reinstate_bajas', reinstate_bajas)
    return state


def render(function, *, admin=ADMIN):
    return AppTest.from_string(SCRIPT.format(function=function, admin=admin), default_timeout=90).run()


def metric(app, label):
    return next(m.value for m in app.metric if m.label == label)


def text(app):
    return ' '.join(m.value for m in app.markdown) + ' ' + ' '.join(c.value for c in app.caption)


def test_executive_summary_counts_the_current_squad_not_every_registration(screen):
    app = render('page_executive_summary')
    assert not app.exception, [e.value for e in app.exception]
    assert metric(app, 'Jugadores Activos') == '5', '9 registrados, 4 sin planilla reciente'
    assert 'Plantel vigente: 5 de 9 jugadores' in text(app) and '4 no cuentan' in text(app)
    assert 'últimos 365 días' in text(app)
    assert 'Criterios provisionales' in text(app) and 'Plantel vigente: días sin planilla' in text(app), 'es un supuesto y se dice'


def test_squad_structure_counts_the_current_squad_and_audits_the_rest(screen):
    app = render('page_squad_structure')
    assert not app.exception, [e.value for e in app.exception]
    assert metric(app, 'Total jugadores') == '5'
    assert 'Revisión del plantel' in ' '.join(s.value for s in app.subheader)
    view = app.selectbox(key='squad_audit_view')
    assert view.value.startswith('Sin actividad reciente')
    shown = [t for t in app.dataframe][-1].value
    assert set(shown['Jugador']) == {'Ex Jugador Uno', 'Ex Jugador Dos', 'Ex Jugador Tres', 'Sub Quince Ido'}
    assert dict(zip(shown['Jugador'], shown['Detalle']))['Ex Jugador Dos'] == 'Nunca figuró en una planilla de O’Higgins'
    complete, summary, calibration = (app.dataframe[i].value for i in range(3))
    assert set(complete['Jugador']) == {'Delantero Actual', 'Portero Actual', 'Sub Quince Uno', 'Sub Quince Dos', 'Sub Veinte Uno'}
    by_category = summary.set_index('Categoría')
    assert by_category.loc['Primer Equipo'].to_dict() == {'Vigentes (cuentan)': 2, 'Sin actividad reciente': 3, 'Baja registrada': 0,
                                                          'Registrados en COMET': 5}
    assert by_category.loc['U-15', 'Registrados en COMET'] == 3 and by_category.loc['U-15', 'Vigentes (cuentan)'] == 2
    assert calibration['Días sin planilla'].tolist() == [90, 180, 365, 730, 1095]
    assert not [b for b in app.button if b.label == 'Reincorporar'], 'sin bajas no hay nada que reincorporar'


def test_youth_development_lists_only_current_players_and_can_include_former_ones(screen):
    app = render('page_youth_development')
    assert not app.exception, [e.value for e in app.exception]
    app.selectbox(key='youth_cat').select('U-15').run()
    assert metric(app, 'Jugadores en Categoría') == '2', 'Sub Quince Ido ya no está'
    tab_tables = [d.value for d in app.dataframe]
    assert tab_tables and all('Sub Quince Ido' not in set(t.get('Jugador', [])) for t in tab_tables)
    assert app.checkbox(key='youth_include_former').value is False
    app.checkbox(key='youth_include_former').check().run()
    assert any('Sub Quince Ido' in set(d.value.get('Jugador', [])) for d in app.dataframe), 'el histórico vuelve si se pide'


def test_a_baja_needs_players_and_confirmation_and_then_reaches_the_store(screen):
    app = render('page_youth_development')
    app.selectbox(key='youth_cat').select('U-15').run()
    submit = next(b for b in app.button if b.label == 'Dar de baja')
    submit.click().run()
    assert any('al menos un jugador' in w.value for w in app.warning) and not screen['writes']
    pick = app.multiselect(key='baja_pick_U-15')
    assert pick.options == ['Sub Quince Dos · 14 años', 'Sub Quince Uno · 14 años'], 'solo el plantel vigente de esa categoría'
    pick.select('201')   # AppTest recibe el valor (el identificador), no la etiqueta
    next(b for b in app.button if b.label == 'Dar de baja').click().run()
    assert any('Marca la confirmación' in w.value for w in app.warning) and not screen['writes']
    app.selectbox(key='baja_reason_U-15').select('cedido')
    app.text_input(key='baja_note_U-15').input('Préstamo a Club Ficticio')
    app.checkbox(key='baja_confirm_U-15').check()
    next(b for b in app.button if b.label == 'Dar de baja').click().run()
    assert not app.exception, [e.value for e in app.exception]
    assert screen['writes'] == [(['201'], 'cedido', TODAY.date(), 'Préstamo a Club Ficticio')], screen['writes']
    assert any('Se registró la baja de 1 jugador' in s.value for s in app.success), 'el aviso sobrevive al rerun'


def test_players_with_a_baja_leave_the_counts_and_can_be_reincorporated(screen):
    screen['bajas'] = bajas_frame(('201', True, 'dejo_club', date(2026, 10, 20)))
    app = render('page_youth_development')
    app.selectbox(key='youth_cat').select('U-15').run()
    assert metric(app, 'Jugadores en Categoría') == '1'
    assert 'Bajas registradas en U-15' in text(app)
    back = app.multiselect(key='reinstate_pick_U-15')
    assert back.options == ['Sub Quince Uno · 14 años']
    back.select('201')
    next(b for b in app.button if b.label == 'Reincorporar').click().run()
    assert screen['reinstated'] == [['201']]
    assert any('Se reincorporó a 1 jugador' in s.value for s in app.success)


def test_reincorporating_someone_already_reincorporated_says_so_instead_of_claiming_success(screen):
    screen['bajas'] = bajas_frame(('201', True, 'dejo_club', date(2026, 10, 20)))
    screen['reinstated_count'] = 0   # otra persona ya lo había reincorporado
    app = render('page_youth_development')
    app.selectbox(key='youth_cat').select('U-15').run()
    app.multiselect(key='reinstate_pick_U-15').select('201')
    next(b for b in app.button if b.label == 'Reincorporar').click().run()
    assert not any('Se reincorporó' in s.value for s in app.success)
    assert any('ya no tenían una baja vigente' in i.value for i in app.info)


def test_the_audit_can_reincorporate_from_estructura_del_plantel(screen):
    screen['bajas'] = bajas_frame(('101', True, 'transferido', date(2026, 10, 20)))
    app = render('page_squad_structure')
    assert metric(app, 'Total jugadores') == '4'
    app.selectbox(key='squad_audit_view').select('Con baja registrada').run()
    shown = [t for t in app.dataframe][-1].value
    assert shown['Jugador'].tolist() == ['Delantero Actual'] and shown['Detalle'].tolist() == ['Transferido · desde 20-10-2026']
    app.multiselect(key='reinstate_pick_audit').select('101')
    next(b for b in app.button if b.label == 'Reincorporar').click().run()
    assert screen['reinstated'] == [['101']]


def test_without_migration_005_the_rule_still_applies_and_bajas_are_disabled_with_the_reason(screen):
    screen['error'] = 'Falta aplicar db/portal/005_comet_player_bajas.sql en Supabase.'
    app = render('page_youth_development')
    app.selectbox(key='youth_cat').select('U-15').run()
    assert not app.exception, [e.value for e in app.exception]
    assert metric(app, 'Jugadores en Categoría') == '2', 'la regla automática sigue funcionando'
    assert any('005_comet_player_bajas.sql' in w.value for w in app.warning)
    assert next(b for b in app.button if b.label == 'Dar de baja').disabled
    assert app.multiselect(key='baja_pick_U-15').disabled


def test_read_only_mode_shows_the_squad_but_does_not_allow_bajas(screen, monkeypatch):
    monkeypatch.setenv('PORTAL_AUTH_PROVIDER', 'local_recovery')
    app = render('page_youth_development')
    app.selectbox(key='youth_cat').select('U-15').run()
    assert any('solo lectura' in i.value for i in app.info)
    assert next(b for b in app.button if b.label == 'Dar de baja').disabled and not screen['writes']


def test_player_analysis_hides_former_players_by_default(screen):
    app = render('page_player_analysis')
    assert not app.exception, [e.value for e in app.exception]
    names = set(app.dataframe[0].value['Jugador'])
    assert names == {'Sub Quince Uno'}
    app.checkbox(key='analysis_include_former').check().run()
    assert set(app.dataframe[0].value['Jugador']) == {'Sub Quince Uno', 'Sub Quince Ido'}


def test_every_squad_screen_requires_an_administrator(screen):
    for function in ('page_executive_summary', 'page_youth_development', 'page_squad_structure', 'page_player_analysis'):
        app = render(function, admin=SCOUT)
        assert app.exception and 'administrador' in app.exception[0].value, function


def test_squad_module_is_listed_among_the_guarded_comet_modules():
    source = Path('app/comet_squad.py').read_text(encoding='utf8')
    for name in ('load_roster', 'render_notice', 'exclude_former', 'render_baja_panel', 'render_audit'):
        assert f'@admin_only\ndef {name}(' in source, name
