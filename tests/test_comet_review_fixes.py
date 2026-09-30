"""Casos reproducidos en la revisión de la PR 13 (30-09-2026), uno por hallazgo."""
import threading
import smtplib
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from scouting.comet import alerts, categories, metrics, quality, queries
from scouting.comet.facts import build_dataset, civil_date, prepare_players
from scouting.comet.ledger import MemoryLedger
from scouting.comet.pipeline import compute_all
from scouting.comet.rules import Rules
from scripts import send_comet_weekly_digest as job
from tests import comet_tiny
from tests.comet_tiny import sheet_row
from tests.test_comet_ops import FakeSMTP, SMTP_ENV
from tests.test_comet_pages import ADMIN, SCRIPT


def dataset(rules=None, **extra):
    raw = comet_tiny.build(**extra)
    return build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers'], rules), raw


def summaries(ds, periods=None):
    comp = metrics.add_percentages(metrics.player_competition_summary(ds, periods))
    return comp, metrics.category_summary(comp)


def row(frame, personid, **where):
    picked = frame[frame['personid'] == str(personid)]
    for column, value in where.items():
        picked = picked[picked[column] == value]
    assert len(picked) == 1
    return picked.iloc[0]


# --- 1. Nacimientos con zona horaria: fecha civil y edad por aniversario ------------------------------------------

def test_civil_date_keeps_the_birthday_whatever_the_column_type():
    values = ['2011-06-10', None, '2012-02-29']
    utc = pd.Series(pd.to_datetime(values, utc=True))
    naive = pd.Series(pd.to_datetime(values))
    objects = pd.Series([date(2011, 6, 10), None, date(2012, 2, 29)], dtype=object)
    santiago_midnight = pd.Series(pd.to_datetime(['2011-06-10 00:00:00-04:00', None, '2012-02-29 00:00:00-03:00'], utc=True))
    for series in (utc, naive, objects, santiago_midnight):
        result = civil_date(series)
        assert result.dt.tz is None
        assert result.dt.strftime('%Y-%m-%d').tolist()[0] == '2011-06-10' and pd.isna(result.iloc[1])
        assert result.iloc[2] == pd.Timestamp('2012-02-29')
    session_in_santiago = pd.Series(pd.to_datetime(['2011-06-10'], utc=True)).dt.tz_convert('America/Santiago')
    assert civil_date(session_in_santiago).iloc[0] == pd.Timestamp('2011-06-10'), 'no retrocede un día por la zona de la sesión'


def test_ages_do_not_change_when_births_arrive_as_timestamptz():
    raw = comet_tiny.build()
    plain = build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers'])
    raw['players']['dateofbirth'] = pd.to_datetime(raw['players']['dateofbirth'], utc=True)
    with_zone = build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers'])
    assert with_zone.players['dateofbirth'].dt.tz is None
    pd.testing.assert_series_equal(plain.facts['age'], with_zone.facts['age'])
    assert plain.facts['age_category'].tolist() == with_zone.facts['age_category'].tolist()


def test_age_is_counted_by_anniversary_not_by_dividing_days():
    born = pd.Timestamp('2012-02-29')
    assert categories.age_on(born, date(2026, 2, 28)) == 13 and categories.age_on(born, date(2026, 3, 1)) == 14
    assert categories.age_on(pd.Timestamp('2011-06-10'), date(2026, 6, 9)) == 14
    assert categories.age_on(pd.Timestamp('2011-06-10'), date(2026, 6, 10)) == 15
    # Dividir por 365,25 se equivoca en las vísperas de un cumpleaños tras años bisiestos.
    assert categories.elapsed_years('2000-01-01', '2026-01-01') == 26.0
    assert categories.elapsed_years('2000-01-01', '2025-12-31') < 26.0
    assert categories.elapsed_years('2012-02-29', '2026-03-01') == pytest.approx(14.0)
    assert categories.elapsed_years('2026-05-01', '2026-04-01') is None and categories.elapsed_years(None, '2026-01-01') is None


@pytest.fixture
def screen_env(monkeypatch):
    monkeypatch.syspath_prepend(str(Path('app').resolve()))
    for key, value in [('PORTAL_MODE', '1'), ('DB_SCHEMA', 'scouting'), ('DISABLE_SOFASCORE_UPDATE', '1')]:
        monkeypatch.setenv(key, value)
    import comet_context

    def install(raw, periods=None):
        monkeypatch.setattr(comet_context, 'load_raw', lambda: raw)
        monkeypatch.setattr(comet_context, 'load_config', lambda: (
            {}, comet_context.EMPTY_MARKS, comet_context.EMPTY_PERIODS if periods is None else periods, 'sin configuración'))
        monkeypatch.setattr(comet_context, 'now', lambda: comet_tiny.TODAY)
    return install


def render(module, function):
    return AppTest.from_string(SCRIPT.format(module=module, function=function, admin=ADMIN), default_timeout=90).run()


def test_player_screen_renders_with_births_as_utc_timestamps(screen_env):
    """Reproducción de la revisión: la ficha fallaba con `datetime64[ns, UTC]` al restar `ctx.today`."""
    raw = comet_tiny.build()
    raw['players']['dateofbirth'] = pd.to_datetime(raw['players']['dateofbirth'], utc=True)
    raw['players']['datefrom'] = pd.to_datetime(['2019-03-01', '2018-01-15', None, '2020-05-05', '2021-09-09'], utc=True)
    raw['players']['height'] = [158.0, 151.0, 160.0, None, 149.0]
    raw['players']['weight'] = [47.0, 42.5, None, None, 41.0]
    screen_env(raw)
    app = AppTest.from_string(SCRIPT.format(module='comet_followup', function='page_player', admin=ADMIN), default_timeout=90).run()
    assert not app.exception, [e.value for e in app.exception]
    app.selectbox(key='cp_player').set_value('1').run()
    assert not app.exception, [e.value for e in app.exception]
    page = ' '.join(m.value for m in app.markdown) + ' ' + ' '.join(c.value for c in app.caption)
    assert 'Nacimiento 10-06-2011 · 15 años' in page, 'nació el 10-06-2011: el 30-09-2026 tiene 15 años cumplidos'
    assert 'datefrom: 01-03-2019' in page and 'estatura: 158' in page and 'peso: 47' in page
    app.selectbox(key='cp_player').set_value('4').run()
    assert 'estatura: —' in ' '.join(c.value for c in app.caption), 'lo que falta se ve como «—»'


# --- 2. Filas repetidas por jugador y partido ------------------------------------------------------------------------

def test_identical_repeated_rows_are_counted_once():
    base, _ = dataset()
    copies = [sheet_row(1, 1, True, True, 80, goals=1, yellow=1)] * 4          # cuatro copias exactas del renglón de P1
    ds, raw = dataset(extra_sheet=copies)
    assert (ds.duplicates['resolucion'].str.startswith('idénticas')).all() and ds.duplicates['filas'].tolist() == [5]
    a, b = summaries(base)[0], summaries(ds)[0]
    for column in ('cited', 'started', 'sub_in', 'only_called', 'played', 'minutes', 'goals', 'yellow_cards', 'possible_minutes'):
        assert row(a, 1, competition_id='100')[column] == row(b, 1, competition_id='100')[column], column
    assert not ds.facts['conflict'].any() and ds.blocked_players().empty
    report = quality.data_quality(ds, raw['sheet'], raw['matches']).set_index('control')
    assert report.loc['Filas repetidas idénticas (jugador y partido)', 'cantidad'] == 1
    assert report.loc['Filas repetidas contradictorias (jugador y partido)', 'nivel'] == 'Correcto'


def test_contradictory_repeated_rows_are_not_guessed_and_block_the_metrics():
    extra = [sheet_row(1, 1, True, True, 90, goals=2), sheet_row(2, 2, True, False, 30)]   # P1 en el 1 y P2 en el 2: versiones distintas
    ds, raw = dataset(extra_sheet=extra)
    conflicts = ds.duplicates[ds.duplicates['resolucion'].str.startswith('contradictorias')]
    assert sorted(zip(conflicts['matchid'], conflicts['personid'])) == [('1', '1'), ('2', '2')]
    f = ds.facts
    bad = f[f['conflict']].set_index(['matchid', 'personid'])
    assert bad['role'].tolist() == ['Sin dato', 'Sin dato'] and bad['minutes'].isna().all() and bad['goals'].isna().all()
    assert not bad['participated'].any(), 'no se afirma que jugó ni que no jugó'
    comp, cat = summaries(ds)
    p1 = row(comp, 1, competition_id='100')
    assert p1.incomplete == 1 and p1.minutes == 60, 'solo suma lo que no está en duda (el partido 2)'
    assert row(comp, 3, competition_id='100').incomplete == 0, 'otros jugadores no se ven afectados'
    # Rankings: los incompletos no entran y se listan aparte.
    ranked = metrics.ranking(cat, 'Minutos jugados', category='U-15', season_year=2026)
    assert not {'1', '2'} & set(ranked['personid']) and set(ranked['personid']) == {'3'}
    listed = metrics.incomplete_players(cat, category='U-15', season_year=2026)
    assert set(listed['personid']) == {'1', '2'}
    assert {'1', '2'} <= set(metrics.ranking(cat, 'Minutos jugados', category='U-15', season_year=2026,
                                             include_incomplete=True)['personid'])
    # Alertas: no se evalúan; se informan como bloqueados.
    strict = Rules({'participation_threshold': {'value': 100}, 'yellow_threshold': {'value': 1}})
    ds2, _ = dataset(strict, extra_sheet=extra)
    found = alerts.evaluate_alerts(ds2, summaries(ds2)[1], 2026)
    assert not {'1', '2'} & set(found['personid']), 'un jugador con planillas contradictorias no genera alertas'
    assert set(ds2.blocked_players(2026)['personid']) == {'1', '2'}
    report = quality.data_quality(ds, raw['sheet'], raw['matches']).set_index('control')
    assert report.loc['Filas repetidas contradictorias (jugador y partido)', ['nivel', 'cantidad']].tolist() == ['Error', 2]
    # La planilla del partido las muestra, sin números inventados.
    sheet = metrics.match_sheet(ds, '1')
    assert '1' in set(sheet['personid']) and sheet.loc[sheet['personid'] == '1', 'role'].iloc[0] == 'Sin dato'


def test_repeated_goalkeeper_rows_follow_the_same_policy():
    raw = comet_tiny.build()
    raw['goalkeepers'] = pd.concat([raw['goalkeepers'], raw['goalkeepers'].iloc[[0]]], ignore_index=True)   # copia exacta
    identical = build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers'])
    assert metrics.goalkeeper_conceded(identical)['goalsconceded'].sum() == 4, 'no se cuenta dos veces'
    clash = raw['goalkeepers'].iloc[[0]].assign(goalsconceded=5)
    raw['goalkeepers'] = pd.concat([raw['goalkeepers'], clash], ignore_index=True)
    contradictory = build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers'])
    shown = metrics.goalkeeper_conceded(contradictory, '1')
    assert len(shown) == 1 and pd.isna(shown['goalsconceded'].iloc[0]), 'el arquero figura, sus goles quedan sin dato'


def test_screens_warn_about_contradictory_rows(screen_env):
    raw = comet_tiny.build(extra_sheet=[sheet_row(3, 2, True, True, 70)])   # el partido 3 es el de la última semana
    screen_env(raw)
    weekly = render('comet_followup', 'page_weekly_match')
    assert not weekly.exception
    assert any('filas repetidas con valores distintos' in w.value for w in weekly.warning)
    ranking = render('comet_followup', 'page_rankings')
    assert not ranking.exception and any('no entran en los rankings' in w.value for w in ranking.warning)
    quality_tab = render('comet_insights', 'page_tracking')
    assert not quality_tab.exception
    assert any('Filas repetidas por jugador y partido' in m.value for m in quality_tab.markdown)


# --- 3. Umbral de participación: sin redondeo antes de comparar -------------------------------------------------------

def participation_frame(minutes, possible):
    return metrics._percentages(pd.DataFrame([dict(
        personid='9', displayname='X', season_year=2026, category='U-15', category_rank=15, minutes=float(minutes),
        counted_minutes=float(minutes), possible_minutes=float(possible), results_with=0, wins_with=0, cited=75, played=75,
        started=75, sub_in=0, only_called=0, draws_with=0, losses_with=0, possible_matches=75, ahead_minutes=0.0,
        yellow_cards=0.0, red_cards=0.0, goals=0.0, age=15, age_category='U-15', incomplete=0)]))


@pytest.mark.parametrize('minutes, alerted', [(1199, True), (1200, False), (1201, False), (1000, True), (0, True)])
def test_low_participation_alert_compares_the_exact_ratio(minutes, alerted):
    frame = participation_frame(minutes, 6000)
    found = alerts._low_participation(frame, 2026, 20)
    assert (len(found) == 1) is alerted, f'{minutes}/6000 = {minutes / 6000 * 100:.4f} %'
    if alerted and minutes == 1199:
        assert found['detail'].iloc[0].startswith('19.98 %'), 'nunca se muestra «20,0 %» bajo un umbral de 20 %'
        assert found['value'].iloc[0] == pytest.approx(1199 / 60)


def test_stored_percentages_are_not_rounded():
    frame = participation_frame(1199, 6000)
    assert frame['participation_pct'].iloc[0] == 1199 / 6000 * 100 != 20.0


def test_alert_without_minutes_is_not_evaluated_as_zero():
    frame = participation_frame(0, 6000).assign(counted_minutes=np.nan, minutes=np.nan)
    assert alerts._low_participation(frame, 2026, 20).empty, 'minutos sin dato no son 0 minutos'


# --- 5. Resumen semanal: mismo cálculo que la pantalla, y una entrega por semana y destinatario ---------------------------

STORED = {'digest_recipients': {'value': ['a@example.test', 'B@Example.test'], 'confirmed': True}}
WEEK = ['--week-of', '2026-03-16', '--send']


def run_job(stored=None, ledger=None, smtp=FakeSMTP, env=None, argv=WEEK, periods=None, raw=None):
    lines = []
    code = job.run(argv, env=SMTP_ENV if env is None else env, load_raw=lambda: raw or comet_tiny.build(),
                   stored=(STORED if stored is None else stored, job.NO_PERIODS if periods is None else periods, None),
                   now=comet_tiny.TODAY, smtp_factory=smtp, ledger=ledger, out=lines.append)
    return code, '\n'.join(lines)


@pytest.fixture(autouse=True)
def fresh_smtp():
    FakeSMTP.instances.clear()


def sent_messages():
    return [m['To'] for s in FakeSMTP.instances for m in s.sent]


def test_two_runs_of_the_same_week_send_each_recipient_once():
    ledger = MemoryLedger()
    first = run_job(ledger=ledger)
    second = run_job(ledger=ledger)
    assert first[0] == 0 and second[0] == 0
    assert sorted(sent_messages()) == ['a@example.test', 'b@example.test'], 'un mensaje por destinatario (sin repetir mayúsculas)'
    assert 'ya enviados antes (omitidos): 2' in second[1]
    run_job(ledger=ledger, argv=['--week-of', '2026-03-23', '--send'])
    assert len(sent_messages()) == 4, 'otra semana sí se envía'


class FlakySMTP(FakeSMTP):
    failing = True

    def send_message(self, message):
        if FlakySMTP.failing:
            raise smtplib.SMTPDataError(451, b'boom con datos: smtp.example.test password=secreto')
        super().send_message(message)


def test_failed_delivery_is_retried_next_run_then_gives_up():
    ledger = MemoryLedger()
    FlakySMTP.failing = True
    code, out = run_job(ledger=ledger, smtp=FlakySMTP, stored={'digest_recipients': {'value': ['a@example.test'], 'confirmed': True}})
    assert code == 1 and 'Fallaron 1' in out and sent_messages() == []
    assert ledger.status(date(2026, 3, 16), 'a@example.test') == ('fallido', 1)
    assert 'secreto' not in str(ledger._rows), 'el motivo no guarda el texto del servidor'
    FlakySMTP.failing = False
    code, out = run_job(ledger=ledger, smtp=FlakySMTP, stored={'digest_recipients': {'value': ['a@example.test'], 'confirmed': True}})
    assert code == 0 and sent_messages() == ['a@example.test']
    assert ledger.status(date(2026, 3, 16), 'a@example.test') == ('enviado', 2)
    FlakySMTP.failing = True
    exhausted = MemoryLedger()
    for _ in range(3):
        run_job(ledger=exhausted, smtp=FlakySMTP, stored={'digest_recipients': {'value': ['z@example.test'], 'confirmed': True}})
    assert exhausted.status(date(2026, 3, 16), 'z@example.test') == ('fallido', 3)
    FlakySMTP.failing = False
    before = len(sent_messages())
    code, out = run_job(ledger=exhausted, smtp=FlakySMTP, stored={'digest_recipients': {'value': ['z@example.test'], 'confirmed': True}})
    assert code == 1 and 'Sin más intentos' in out and len(sent_messages()) == before, 'agotados los intentos no se insiste'


def test_reservation_left_open_is_never_resent_automatically():
    ledger = MemoryLedger()
    assert ledger.reserve(date(2026, 3, 16), 'a@example.test')          # un proceso reservó y murió antes de cerrar
    code, out = run_job(ledger=ledger, stored={'digest_recipients': {'value': ['a@example.test'], 'confirmed': True}})
    assert code == 1 and 'En duda' in out and sent_messages() == [], 'pudo haber salido: se confirma a mano'


class FailingClose(MemoryLedger):
    def finish(self, *args, **kwargs):
        raise RuntimeError('registro caído')


def test_if_the_ledger_cannot_be_closed_the_message_is_not_marked_failed_or_resent():
    ledger = FailingClose()
    stored = {'digest_recipients': {'value': ['a@example.test'], 'confirmed': True}}
    code, out = run_job(ledger=ledger, stored=stored)
    assert code == 1 and sent_messages() == ['a@example.test'] and 'En duda' in out
    run_job(ledger=ledger, stored=stored)
    assert sent_messages() == ['a@example.test'], 'la reserva abierta impide el reenvío'


def test_concurrent_runs_cannot_reserve_the_same_delivery():
    ledger, wins = MemoryLedger(), []
    barrier = threading.Barrier(8)

    def attempt():
        barrier.wait()
        wins.append(ledger.reserve(date(2026, 3, 16), 'a@example.test'))
    threads = [threading.Thread(target=attempt) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert wins.count(True) == 1


def test_sending_needs_a_ledger_and_never_falls_back_to_unrecorded_sends():
    lines = []
    code = job.run(WEEK, env=SMTP_ENV, load_raw=lambda: comet_tiny.build(), stored=(STORED, job.NO_PERIODS, None),
                   now=comet_tiny.TODAY, smtp_factory=FakeSMTP, out=lines.append)
    assert code == 2 and 'registro de entregas' in '\n'.join(lines) and sent_messages() == []


def test_job_and_screens_use_the_same_periods_and_alerts():
    """El correo debe mostrar las mismas alertas que la pantalla cuando hay períodos de selección."""
    rules = {'participation_threshold': {'value': 60}, 'exclude_selection_periods': {'value': True}}
    period = pd.DataFrame([dict(id=1, personid='1', kind='microciclo', starts_on=date(2026, 3, 21), ends_on=date(2026, 3, 22),
                                note='', active=True, start=pd.Timestamp('2026-03-21'), end=pd.Timestamp('2026-03-22'))])
    stored = {**rules, 'digest_recipients': {'value': ['a@example.test'], 'confirmed': True}}

    def alert_names(periods):
        lines = []
        job.run(['--week-of', '2026-03-16'], env={}, load_raw=lambda: comet_tiny.build(),
                stored=(stored, periods, None), now=comet_tiny.TODAY, out=lines.append)
        return [line for line in '\n'.join(lines).splitlines() if 'Menos del 60 %' in line or 'Jugador Uno' in line]

    without = alert_names(job.NO_PERIODS)          # P1: 140 de 240 = 58,3 % < 60 %: alerta
    with_period = alert_names(period)              # P1 no jugó el partido 3, en período de selección: 140 de 160 = 87,5 %: sin alerta
    assert any('Jugador Uno' in line for line in without)
    assert not any('Jugador Uno' in line for line in with_period)
    computed = compute_all(comet_tiny.build(), rules, period)
    ui_alerts = alerts.evaluate_alerts(computed.ds, computed.cat, 2026)
    assert '1' not in set(ui_alerts.loc[ui_alerts['alert_key'] == 'low_participation', 'personid'])


# --- 6. Datos que COMET sí tiene ------------------------------------------------------------------------------------------

ALL_COLUMNS = {('actuaciones_jugadores', 'secondyellow'), ('actuaciones_jugadores', 'owngoals'),
               ('competiciones', 'matchlength'), ('partidos', 'matchstatus'), ('jugadores', 'datefrom'),
               ('jugadores', 'altura'), ('jugadores', 'peso')}


def test_queries_only_ask_for_optional_columns_that_exist():
    full_sheet, empty_sheet = queries.sheet_sql(ALL_COLUMNS), queries.sheet_sql(set())
    assert 'a.secondyellow::int AS second_yellows' in full_sheet and 'a.owngoals::int AS own_goals' in full_sheet
    assert 'secondyellow' not in empty_sheet and 'NULL::int AS second_yellows' in empty_sheet
    assert 'c.matchlength AS nominal_duration' in queries.matches_sql(ALL_COLUMNS) and 'p.matchstatus AS matchstatus' in queries.matches_sql(ALL_COLUMNS)
    assert 'matchlength' not in queries.matches_sql(set())
    players = queries.players_sql(ALL_COLUMNS)
    assert 'j.datefrom AS datefrom' in players and 'j.altura AS height' in players and 'j.peso AS weight' in players
    assert 'NULL AS height' in queries.players_sql({('jugadores', 'datefrom')})
    for sql in (full_sheet, queries.matches_sql(ALL_COLUMNS), players, queries.COLUMNS_SQL):
        assert not any(word in sql.upper() for word in ('INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'GRANT'))


def test_fetch_raw_tolerates_an_unreadable_information_schema():
    asked = []

    def load(sql, params):
        asked.append(sql)
        if 'information_schema' in sql:
            raise RuntimeError('sin permiso')
        return pd.DataFrame()
    raw = queries.fetch_raw(load)
    assert set(raw) == {'sheet', 'matches', 'players', 'goalkeepers'} and len(asked) == 5
    assert 'NULL::int AS second_yellows' in asked[1], 'sin metadatos se piden solo las columnas base'


def test_duration_source_rule_uses_recorded_or_nominal_minutes_without_switching_silently():
    raw = comet_tiny.build()
    raw['matches']['nominal_duration'] = [90, 90, np.nan, 70]
    recorded = build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers'])
    nominal = build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers'],
                            Rules({'duration_source': {'value': 'nominal'}}))
    assert row(summaries(recorded)[0], 1, competition_id='100').possible_minutes == 240
    p1 = row(summaries(nominal)[0], 1, competition_id='100')
    assert p1.possible_minutes == 180, 'partidos 1 y 2 a 90; el 3 no tiene duración nominal y no cuenta (no se usa la registrada)'
    assert p1.counted_minutes == 140, 'los minutos del partido excluido tampoco cuentan: mismo conjunto en ambos lados'
    assert p1.participation_pct == pytest.approx(140 / 180 * 100)
    report = quality.data_quality(recorded, raw['sheet'], raw['matches']).set_index('control')
    assert report.loc['Duración registrada distinta de la nominal', 'cantidad'] == 2, 'partidos 1 (80 vs 90) y 2 (80 vs 90)'


def test_match_status_rule_excludes_states_from_possible_minutes():
    raw = comet_tiny.build()
    raw['matches']['matchstatus'] = ['FINALIZADO', 'Suspendido', 'FINALIZADO', 'FINALIZADO']
    default = build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers'])
    excluding = build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers'],
                              Rules({'excluded_match_statuses': {'value': ['suspendido']}}))
    assert row(summaries(default)[0], 1, competition_id='100').possible_minutes == 240
    p1 = row(summaries(excluding)[0], 1, competition_id='100')
    assert p1.possible_minutes == 160 and p1.counted_minutes == 80, 'el partido suspendido sale del numerador y del denominador'
    report = quality.data_quality(default, raw['sheet'], raw['matches']).set_index('control')
    assert 'Suspendido: 1' in report.loc['Partidos por estado (matchstatus)', 'detalle']
    assert report.loc['Partidos por estado (matchstatus)', 'nivel'] == 'Información'


def test_second_yellows_and_own_goals_are_shown_but_not_added_to_the_counts():
    raw = comet_tiny.build()
    raw['sheet']['second_yellows'] = 0
    raw['sheet']['own_goals'] = 0
    raw['sheet'].loc[(raw['sheet']['matchid'] == 3) & (raw['sheet']['personid'] == 2), 'second_yellows'] = 1
    raw['sheet'].loc[(raw['sheet']['matchid'] == 3) & (raw['sheet']['personid'] == 3), 'own_goals'] = 1
    ds = build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers'],
                       Rules({'yellow_threshold': {'value': 1}}))
    comp, cat = summaries(ds)
    p2, gk = row(comp, 2, competition_id='100'), row(comp, 3, competition_id='100')
    assert p2.second_yellows == 1 and p2.yellow_cards == 1, 'la segunda amarilla no se suma a las amarillas'
    assert gk.own_goals == 1 and gk.goals == 0, 'el autogol no es un gol a favor'
    found = alerts.evaluate_alerts(ds, cat, 2026)
    detail = found.loc[(found['alert_key'] == 'yellow_cards') & (found['personid'] == '2'), 'detail'].iloc[0]
    assert '(+1 segunda amarilla, no sumada)' in detail


def test_seniority_can_come_from_datefrom_and_missing_stays_missing():
    from scouting.comet import indicators
    raw = comet_tiny.build()
    raw['players']['datefrom'] = pd.to_datetime(['2019-03-01', None, '2021-09-30', '2020-10-01', None], utc=True)
    first = build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers'])
    dated = build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers'],
                          Rules({'seniority_rule': {'value': 'datefrom'}}))
    assert indicators.seniority_years(first, comet_tiny.TODAY)['2'] > 0
    years = indicators.seniority_years(dated, comet_tiny.TODAY)
    assert years['1'] == pytest.approx(7 + 213 / 365, abs=0.01) and years['3'] == 5.0
    assert pd.isna(years['2']) and pd.isna(years['5']), 'sin datefrom queda sin dato: no se reemplaza por el primer partido'
    ind = indicators.category_indicators(dated, summaries(dated)[1], 2026, comet_tiny.TODAY).set_index('category')
    assert ind.loc['U-15', 'antiguedad_promedio'] == pytest.approx((years['1'] + years['3'] + years['4']) / 3, abs=0.06)


def test_players_expose_height_weight_and_datefrom_with_missing_values():
    raw = comet_tiny.build()
    raw['players']['height'] = ['158', 'x', None, 150, 149.5]
    raw['players']['weight'] = [47, None, None, None, None]
    players = prepare_players(raw['players'])
    assert players['height'].tolist()[0] == 158.0 and pd.isna(players['height'].iloc[1]) and pd.isna(players['height'].iloc[2])
    assert players['weight'].notna().sum() == 1 and 'datefrom' in players.columns and players['datefrom'].isna().all()
