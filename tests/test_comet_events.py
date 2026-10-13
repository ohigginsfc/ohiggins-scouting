"""Cronología ficticia: marcadores calculados a mano, sin datos de jugadores reales."""
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from scouting.comet import events, queries
from scouting.comet.pipeline import compute_all
from tests import comet_tiny


def event(uid, kind, clock, person=None, second=None, side='for', phase='Segundo tiempo', **extra):
    return dict(uid=uid, matchid=1, personid=person, secondpersonid=second, matcheventtype=kind,
                displayminute=clock, phase=phase, stoppagetime=0, side=side, secondyellowcard=False, **extra)


def source():
    raw = comet_tiny.build()
    raw['matches']['nominal_duration'] = [80, 80, 80, 70]
    raw['sheet'].loc[(raw['sheet']['matchid'] == 1) & (raw['sheet']['personid'] == 1), 'minutesplayed'] = 50
    raw['events'] = pd.DataFrame([
        event(1, 'Gol', "15'", person=1, phase='Primer tiempo'),
        event(2, 'Gol', "30'", side='against', phase='Primer tiempo'),
        event(3, 'Sustitución', "50'", person=2, second=1),
        event(4, 'Gol', "65'", person=2),
    ])
    return raw


def results(raw=None):
    return compute_all(source() if raw is None else raw).onpitch.query("matchid == '1'").set_index('personid')


def test_full_timeline_entry_exit_and_goal_difference_are_separate_from_final():
    table = results()
    starter, sub, keeper, bench = (table.loc[str(pid)] for pid in (1, 2, 3, 4))
    assert (starter.onpitch_entry, starter.onpitch_exit) == ('Inicio', "50'")
    assert (starter.onpitch_score_entry, starter.onpitch_score_exit) == ('0-0', '1-1')
    assert starter.onpitch_changed == 'No' and starter.onpitch_state_exit == 'Empatando'
    assert (sub.onpitch_entry, sub.onpitch_exit) == ("50'", 'Final')
    assert (sub.onpitch_score_entry, sub.onpitch_score_exit) == ('1-1', '2-1')
    assert sub.onpitch_changed == 'Sí' and (sub.onpitch_for, sub.onpitch_against) == (1, 0)
    assert keeper.onpitch_status == 'Calculado' and keeper.onpitch_against == 1
    assert bench.onpitch_status == 'No participó' and pd.isna(bench.onpitch_score_exit)


def test_missing_opponent_goal_never_falls_back_to_final_result():
    raw = source()
    raw['events'] = raw['events'][raw['events']['side'] != 'against']
    table = results(raw)
    assert table.loc['1', 'onpitch_status'] == 'Cronología de goles incompleta'
    assert table['onpitch_score_exit'].isna().all()


@pytest.mark.parametrize('kind,side', [('Penal', 'for'), ('Autogol', 'against')])
def test_penalty_goal_and_opponent_own_goal_credit_our_team(kind, side):
    raw = source()
    raw['events'].loc[3, ['matcheventtype', 'side']] = [kind, side]
    assert results(raw).loc['2', 'onpitch_for'] == 1


def test_our_own_goal_credits_opponent_and_shootout_does_not_change_match_score():
    raw = source()
    raw['events'].loc[1, ['matcheventtype', 'side']] = ['Autogol', 'for']
    raw['events'] = pd.concat([raw['events'], pd.DataFrame([event(5, 'Tanda de penaltis', None, phase='Tanda de penaltis')])])
    assert results(raw).loc['3', 'onpitch_against'] == 1


@pytest.mark.parametrize('display,phase,added,want', [
    ("41'", 'Segundo tiempo', 0, (41, 0)), ("36'", 'Segundo tiempo', 0, (36, 0)),
    ("45'+2'", 'Primer tiempo', 2, (45, 2)), ('80+4', 'Segundo tiempo', 4, (80, 4)),
    ("90'+2'", 'Segundo tiempo', None, (90, 2)),
    ('', 'Segundo tiempo', 0, None), ("45'+2'", 'Primer tiempo', 3, None),
    ("1'", None, 0, None), ('-1', 'Primer tiempo', 0, None), ('12.5', 'Primer tiempo', 0, None),
])
def test_clock_uses_absolute_display_in_youth_and_added_time(display, phase, added, want):
    row = event(1, 'Gol', display, phase=phase)
    row['stoppagetime'] = added
    assert events.event_clock(row) == want


def test_same_minute_goal_is_inside_and_added_time_is_ordered():
    raw = source()
    raw['events'].loc[2, 'displayminute'] = "40'+1'"
    raw['events'].loc[2, 'stoppagetime'] = 1
    raw['events'].loc[2, 'phase'] = 'Primer tiempo'
    raw['events'].loc[3, 'displayminute'] = "40'+2'"
    raw['events'].loc[3, 'stoppagetime'] = 2
    raw['events'].loc[3, 'phase'] = 'Primer tiempo'
    raw['sheet'].loc[(raw['sheet']['matchid'] == 1) & (raw['sheet']['personid'] == 1), 'minutesplayed'] = 40
    raw['sheet'].loc[(raw['sheet']['matchid'] == 1) & (raw['sheet']['personid'] == 2), 'minutesplayed'] = 40
    assert results(raw).loc['1', 'onpitch_score_exit'] == '1-1'
    raw['events'].loc[3, 'displayminute'] = "40'+1'"
    raw['events'].loc[3, 'stoppagetime'] = 1
    assert results(raw).loc['1', 'onpitch_score_exit'] == '2-1'
    assert results(raw).loc['2', 'onpitch_for'] == 1


@pytest.mark.parametrize('mutation,reason', [
    ('clock', 'Cambio sin minuto válido'), ('missing', 'Entrada o reentrada sin intervalo único'),
    ('reentry', 'Entrada o reentrada sin intervalo único'), ('duplicate', 'Eventos contradictorios'),
    ('goalclock', 'Gol sin minuto o equipo válido'), ('team', 'Gol sin minuto o equipo válido'),
])
def test_incomplete_or_conflicting_events_stay_unknown(mutation, reason):
    raw = source()
    if mutation == 'clock':
        raw['events'].loc[2, 'displayminute'] = None
    elif mutation == 'missing':
        raw['events'] = raw['events'].drop(index=2)
    elif mutation == 'reentry':
        raw['events'] = pd.concat([raw['events'], pd.DataFrame([event(5, 'Sustitución', "70'", person=2, second=3)])])
    elif mutation == 'duplicate':
        other = raw['events'].iloc[[2]].copy()
        other['displayminute'] = "51'"
        raw['events'] = pd.concat([raw['events'], other])
    elif mutation == 'goalclock':
        raw['events'].loc[3, 'displayminute'] = None
    elif mutation == 'team':
        raw['events'].loc[3, 'side'] = pd.NA
    assert results(raw).loc['2', 'onpitch_status'] == reason
    assert pd.isna(results(raw).loc['2', 'onpitch_score_exit'])


def test_identical_uid_duplicate_is_not_a_second_goal():
    raw = source()
    raw['events'] = pd.concat([raw['events'], raw['events'].iloc[[3]]])
    assert results(raw).loc['3', 'onpitch_status'] == 'Calculado'


@pytest.mark.parametrize('kind', ['Tarjeta roja', 'Expulsión', 'Tarjeta amarilla'])
def test_dismissal_ends_stint_but_card_after_exit_does_not(kind):
    raw = source()
    card = event(5, kind, "60'", person=3)
    card['secondyellowcard'] = kind == 'Tarjeta amarilla'
    raw['events'] = pd.concat([raw['events'], pd.DataFrame([card, event(6, 'Tarjeta roja', "70'", person=1)])])
    raw['sheet'].loc[(raw['sheet']['matchid'] == 1) & (raw['sheet']['personid'] == 3), 'minutesplayed'] = 60
    table = results(raw)
    assert (table.loc['3', 'onpitch_exit'], table.loc['3', 'onpitch_score_exit']) == ("60'", '1-1')
    assert table.loc['1', 'onpitch_exit'] == "50'"


def test_missing_exit_or_contradictory_minutes_are_not_end_of_match():
    raw = source()
    raw['sheet'].loc[(raw['sheet']['matchid'] == 1) & (raw['sheet']['personid'] == 3), 'minutesplayed'] = 60
    assert results(raw).loc['3', 'onpitch_status'] == 'Salida no confirmada por la planilla'
    raw['sheet'].loc[(raw['sheet']['matchid'] == 1) & (raw['sheet']['personid'] == 1), 'minutesplayed'] = 80
    assert results(raw).loc['1', 'onpitch_status'] == 'Minutos incompatibles con los cambios'


def test_zero_zero_requires_events_to_distinguish_absent_export_from_empty_timeline():
    raw = source()
    assert compute_all(raw).onpitch.query("matchid == '2' and personid == '2'").iloc[0].onpitch_status == 'Sin eventos del partido'
    card = event(6, 'Tarjeta amarilla', "60'", person=2)
    card['matchid'] = 2
    raw['events'] = pd.concat([raw['events'], pd.DataFrame([card])])
    row = compute_all(raw).onpitch.query("matchid == '2' and personid == '2'").iloc[0]
    assert row.onpitch_score_exit == '0-0' and row.onpitch_changed == 'No'


def test_without_event_permissions_dataset_remains_available():
    raw = source()
    del raw['events']
    computed = compute_all(raw)
    assert len(computed.ds.facts) == 14
    assert computed.onpitch.query("personid == '1' and matchid == '1'").iloc[0].onpitch_status == 'Eventos no disponibles'
    assert queries.events_sql(set()) is None
    cols = {('eventos_partido', name) for name in queries.EVENT_REQUIRED}
    sql = queries.events_sql(cols)
    assert 'NULL::boolean' in sql and 'e.teamid IN (p.hometeam, p.awayteam)' in sql
    assert 'WHERE e.teamid' not in sql


def test_admin_event_calculation_cache_is_not_served_to_scout(monkeypatch):
    monkeypatch.syspath_prepend(str(Path('app').resolve()))
    import comet_context
    from scouting.portal import security
    from tests.test_comet_security import ADMIN, SCOUT
    raw = source()
    with security.session_scope({}, verified_user=ADMIN):
        assert comet_context.compute(raw, {}, pd.DataFrame()).onpitch['onpitch_status'].eq('Calculado').any()
    with security.session_scope({}, verified_user=SCOUT), pytest.raises(PermissionError):
        comet_context.compute(raw, {}, pd.DataFrame())


@pytest.mark.parametrize('page', ['Partido semanal', 'Ficha del jugador'])
def test_portal_renders_real_entry_and_exit_without_changing_final(page, monkeypatch):
    monkeypatch.syspath_prepend(str(Path('app').resolve()))
    import comet_context
    from tests.test_comet_pages import ADMIN, SCRIPT, PAGES
    monkeypatch.setattr(comet_context, 'load_raw', source)
    monkeypatch.setattr(comet_context, 'load_config', lambda: ({}, comet_context.EMPTY_MARKS, comet_context.EMPTY_PERIODS, None))
    monkeypatch.setattr(comet_context, 'now', lambda: comet_tiny.TODAY)
    module, function = PAGES[page]
    app = AppTest.from_string(SCRIPT.format(module=module, function=function, admin=ADMIN), default_timeout=90)
    if page == 'Partido semanal':
        app.session_state['cw_week'] = pd.Timestamp('2026-03-02')
        app.session_state['cw_match'] = '1'
    else:
        app.session_state['cp_player'] = '1'
    app.run()
    assert not app.exception, [e.value for e in app.exception]
    tables = [df.value for df in app.dataframe if 'Marcador al salir' in df.value.columns]
    assert tables, 'las columnas del resultado real deben estar en el portal'
    assert any('1-1' in set(t['Marcador al salir'].dropna()) for t in tables)
