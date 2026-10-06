"""Un partido jugado sin minutos registrados no es un 0 ni una suma parcial: el total queda sin dato.

Todos los casos salen del mini-torneo de `tests/comet_tiny.py` (cifras comprobables a mano). La planilla de
O'Higgins U-15 (competición 100) tiene tres partidos de 80 minutos; P1 jugó el 1 (80') y el 2 (60'), P2 jugó
30', 80' y 80', P3 jugó 80' y 80' y P4 solo estuvo en el banco.
"""
import numpy as np
import pandas as pd
import pytest

from scouting.comet import adelantados, alerts, indicators, metrics
from scouting.comet.pipeline import compute_all
from tests import comet_tiny
from tests.test_comet_review_fixes import render, row, screen_env  # noqa: F401  (fixture de pantallas)


def raw_with(changes):
    """Datos del mini-torneo con cambios `{(partido, jugador): {columna: valor}}` en la planilla."""
    raw = comet_tiny.build()
    sheet = raw['sheet'].astype({'played': object, 'startinglineup': object, 'minutesplayed': float})
    for (matchid, personid), values in changes.items():
        mask = (sheet['matchid'] == matchid) & (sheet['personid'] == personid)
        assert mask.sum() == 1
        for column, value in values.items():
            sheet.loc[mask, column] = value
    raw['sheet'] = sheet
    return raw


P1_WITHOUT_MINUTES_IN_MATCH_2 = {(2, 1): {'minutesplayed': np.nan}}   # jugó (titular) pero COMET no trae sus minutos


def cat_row(computed, personid, category='U-15'):
    return row(computed.cat, personid, category=category)


# --- Antes: P1 mostraba 80 minutos y 33,3 % de participación; jugó los partidos 1 y 2 y sus minutos del 2 no se conocen --------------

def test_played_without_minutes_blanks_the_totals_instead_of_a_partial_sum():
    computed = compute_all(raw_with(P1_WITHOUT_MINUTES_IN_MATCH_2))
    p1 = cat_row(computed, 1)
    assert p1.played == 2 and p1.cited == 3, 'las apariciones sí se conocen'
    assert p1.minutes_missing == 1
    assert pd.isna(p1.minutes) and pd.isna(p1.counted_minutes) and pd.isna(p1.participation_pct) and pd.isna(p1.ahead_minutes)
    assert p1.possible_minutes == 240, 'los minutos posibles no dependen de este dato'
    assert p1.goals == 1 and p1.yellow_cards == 2, 'goles y tarjetas del jugador no se pierden'
    comp = row(computed.comp, 1, competition_id='100')
    assert pd.isna(comp.minutes) and pd.isna(comp.participation_pct) and comp.minutes_missing == 1


def test_players_with_every_minute_known_keep_exactly_the_same_figures():
    computed = compute_all(raw_with(P1_WITHOUT_MINUTES_IN_MATCH_2))
    for personid, minutes in (('2', 190), ('3', 160), ('4', 0)):
        player = cat_row(computed, personid)
        assert player.minutes_missing == 0 and player.minutes == minutes
        assert player.participation_pct == pytest.approx(minutes / 240 * 100)


# --- Alertas: «menos del 20 %» no se dispara con una suma parcial --------------------------------------------------------------

def test_low_participation_alert_is_not_raised_from_a_partial_sum():
    """P1 jugó los 3 partidos, pero solo se conocen 10 minutos del primero: 10/240 = 4,2 % era una alerta falsa."""
    changes = {(1, 1): {'minutesplayed': 10.0}, (2, 1): {'minutesplayed': np.nan},
               (3, 1): {'played': True, 'startinglineup': False, 'minutesplayed': np.nan}}
    computed = compute_all(raw_with(changes))
    found = alerts.evaluate_alerts(computed.ds, computed.cat, 2026)
    low = found[found['alert_key'] == 'low_participation']
    assert '1' not in set(low['personid']), 'sus minutos no se conocen: no se evalúa'
    assert '4' in set(low['personid']), 'quien tiene todos sus minutos conocidos sigue evaluándose (0 de 240)'
    assert set(computed.ds.minutes_gap_players(2026)['personid']) == {'1'}


def test_a_player_with_unknown_minutes_in_one_category_is_not_evaluated_in_another():
    """La categoría principal se elige por minutos: con minutos desconocidos no se puede decir cuál es."""
    changes = {(4, 2): {'minutesplayed': np.nan}}                     # P2 juega en U-14 (comp. 200) y en U-15
    computed = compute_all(raw_with(changes))
    low = alerts.evaluate_alerts(computed.ds, computed.cat, 2026)
    assert '2' not in set(low.loc[low['alert_key'] == 'low_participation', 'personid'])


# --- Quién juega: dato desconocido no es 0 -------------------------------------------------------------------------------------

def test_unknown_participation_is_not_turned_into_zero_minutes():
    """P1 titular del partido 2 sin la marca de jugó ni minutos: antes figuraba con 0 minutos."""
    ds = compute_all(raw_with({(2, 1): {'played': None, 'minutesplayed': np.nan}})).ds
    fact = ds.facts[(ds.facts['personid'] == '1') & (ds.facts['matchid'] == '2')].iloc[0]
    assert fact['role'] == 'Titular' and not fact['participated']
    assert pd.isna(fact['minutes']) and fact['minutes_unknown'], 'ni juega ni deja de jugar: sin dato'


def test_played_flag_contradicting_the_minutes_is_unknown_not_ignored():
    """P4 figura como que no jugó pero con 25 minutos: antes esos minutos se ignoraban en silencio (0)."""
    computed = compute_all(raw_with({(1, 4): {'minutesplayed': 25.0}}))
    fact = computed.ds.facts[(computed.ds.facts['personid'] == '4') & (computed.ds.facts['matchid'] == '1')].iloc[0]
    assert not fact['participated'] and pd.isna(fact['minutes']) and fact['minutes_unknown']
    p4 = cat_row(computed, 4)
    assert pd.isna(p4.minutes) and pd.isna(p4.participation_pct) and p4.minutes_missing == 1
    assert '4' not in set(alerts.evaluate_alerts(computed.ds, computed.cat, 2026)
                          .query("alert_key == 'low_participation'")['personid'])


def test_conflicting_rows_are_still_handled_only_by_the_conflict_policy():
    clash = comet_tiny.sheet_row(1, 1, True, True, 90, goals=2)       # copia de P1 con otros valores
    raw = comet_tiny.build(extra_sheet=[clash])
    computed = compute_all(raw)
    assert computed.ds.minutes_gap_players().empty, 'una fila contradictoria no es además «minutos desconocidos»'
    assert set(computed.ds.blocked_players()['personid']) == {'1'}


# --- Rankings: el de minutos no lista a quien no tiene minutos conocidos; goles y tarjetas sí ---------------------------------

def test_minutes_ranking_leaves_out_unknown_minutes_but_goals_and_cards_still_count():
    computed = compute_all(raw_with(P1_WITHOUT_MINUTES_IN_MATCH_2))
    cat = computed.cat
    minutes = metrics.ranking(cat, 'Minutos jugados', category='U-15', season_year=2026)
    assert '1' not in set(minutes['personid']), 'no se ordena por una suma parcial'
    goals = metrics.ranking(cat, 'Goles', category='U-15', season_year=2026)
    assert '1' in set(goals['personid']), 'su gol del partido 1 se conoce'
    yellow = metrics.ranking(cat, 'Tarjetas amarillas', category='U-15', season_year=2026)
    assert yellow.set_index('personid').loc['1', 'yellow_cards'] == 2
    listed = metrics.minutes_gap_players(cat, category='U-15', season_year=2026)
    assert listed['personid'].tolist() == ['1'] and listed['minutes_missing'].tolist() == [1]


# --- Indicadores de la serie ----------------------------------------------------------------------------------------------------

def test_series_participation_leaves_out_players_with_unknown_minutes_from_both_sides():
    """Numerador y denominador salen de los mismos jugadores: (190 + 160 + 0) / (3 × 240) = 48,6 %."""
    computed = compute_all(raw_with(P1_WITHOUT_MINUTES_IN_MATCH_2))
    ind = indicators.category_indicators(computed.ds, computed.cat, 2026, comet_tiny.TODAY)
    u15 = ind[ind['category'] == 'U-15'].iloc[0]
    assert u15.participacion_pct == pytest.approx(350 / 720 * 100)
    assert u15.jugadores_minutos_incompletos == 1 and u15.actuaciones_sin_minutos == 1
    clean = indicators.category_indicators(*(lambda c: (c.ds, c.cat))(compute_all(comet_tiny.build())), 2026, comet_tiny.TODAY)
    assert clean[clean['category'] == 'U-15'].iloc[0].jugadores_minutos_incompletos == 0
    assert clean[clean['category'] == 'U-15'].iloc[0].participacion_pct == pytest.approx(490 / 960 * 100)


# --- Adelantados -----------------------------------------------------------------------------------------------------------------

def test_advanced_players_indicators_leave_out_unknown_minutes():
    """P2 (14 años) juega en U-15 y es adelantado; con minutos desconocidos no se afirman cifras de minutos."""
    computed = compute_all(raw_with({(1, 2): {'minutesplayed': np.nan}}))
    ds = computed.ds
    assert '2' not in set(adelantados.ahead_players(ds, 2026)['personid'])
    assert '2' not in set(adelantados.ahead_permanence(ds, 2026)['personid'])
    assert 'Adelantados' not in set(adelantados.ahead_vs_peers(ds, computed.cat, 2026)['group'])
    reference = compute_all(comet_tiny.build())
    assert '2' in set(adelantados.ahead_players(reference.ds, 2026)['personid']), 'sin el hueco sí figura'


def test_playing_up_alert_does_not_quote_partial_minutes():
    computed = compute_all(raw_with({(1, 2): {'minutesplayed': np.nan}}))
    up = alerts.evaluate_alerts(computed.ds, computed.cat, 2026).query("alert_key == 'playing_up'")
    p2 = up[up['personid'] == '2'].iloc[0]
    assert pd.isna(p2['value']) and 'minutos incompletos' in p2['detail'] and ' 0 min' not in p2['detail']
    reference = alerts.evaluate_alerts(*(lambda c: (c.ds, c.cat))(compute_all(comet_tiny.build())), 2026)
    assert reference.query("alert_key == 'playing_up'").iloc[0]['detail'].endswith('190 min'), 'sin hueco, igual que antes'


# --- Evolución de minutos: un mes con minutos desconocidos no se dibuja como una suma parcial ---------------------------------

def test_minutes_timeline_does_not_draw_a_partial_month():
    computed = compute_all(raw_with(P1_WITHOUT_MINUTES_IN_MATCH_2))
    timeline = metrics.minutes_timeline(computed.ds, '1')
    assert timeline['periodo'].tolist() == ['2026-03'] and pd.isna(timeline['minutes'].iloc[0])
    reference = metrics.minutes_timeline(compute_all(comet_tiny.build()).ds, '1')
    assert reference['minutes'].tolist() == [140]


# --- Control de calidad -------------------------------------------------------------------------------------------------------------

def test_quality_report_counts_players_and_rows_with_unknown_minutes():
    raw = raw_with({**P1_WITHOUT_MINUTES_IN_MATCH_2, (1, 4): {'minutesplayed': 25.0}})
    computed = compute_all(raw)
    report = computed.quality.set_index('control')
    control = report.loc['Jugadores con minutos desconocidos']
    assert control['nivel'] == 'Error' and control['cantidad'] == 2
    assert '«—»' in control['efecto']
    clean = compute_all(comet_tiny.build()).quality.set_index('control')
    assert clean.loc['Jugadores con minutos desconocidos', 'nivel'] == 'Correcto'


def test_weekly_digest_notes_players_not_evaluated_for_participation():
    from datetime import date
    from scouting.comet.digest import build_weekly_digest
    computed = compute_all(raw_with(P1_WITHOUT_MINUTES_IN_MATCH_2))
    found = alerts.evaluate_alerts(computed.ds, computed.cat, 2026)
    digest = build_weekly_digest(computed.ds, found, date(2026, 3, 16), generated_on=date(2026, 3, 30),
                                 no_minutes=len(computed.ds.minutes_gap_players(2026)))
    assert '1 jugador(es) no se evalúan en la alerta de participación' in digest.text
    quiet = build_weekly_digest(computed.ds, found, date(2026, 3, 16), generated_on=date(2026, 3, 30))
    assert 'alerta de participación' not in quiet.text


# --- Pantallas -----------------------------------------------------------------------------------------------------------------------

def page_text(app):
    return ' '.join(m.value for m in app.markdown) + ' ' + ' '.join(c.value for c in app.caption) + ' ' + \
        ' '.join(w.value for w in app.warning)


def test_screens_explain_unknown_minutes_without_partial_figures(screen_env):  # noqa: F811
    screen_env(raw_with(P1_WITHOUT_MINUTES_IN_MATCH_2))
    ranking = render('comet_followup', 'page_rankings')
    assert not ranking.exception, [e.value for e in ranking.exception]
    assert any('ranking de minutos' in w.value and 'Jugador Uno' in w.value for w in ranking.warning)
    player = render('comet_followup', 'page_player')
    assert not player.exception, [e.value for e in player.exception]
    player.selectbox(key='cp_player').set_value('1').run()
    assert not player.exception, [e.value for e in player.exception]
    assert any('sin los minutos' in w.value or 'no trae los minutos' in w.value for w in player.warning)
    metrics_by_label = {m.label: m.value for m in player.metric}
    assert metrics_by_label['Minutos'] == '—', 'no se muestra el 80 parcial'
    assert metrics_by_label['Partidos jugados'] == '2'
    alerts_page = render('comet_insights', 'page_alerts')
    assert not alerts_page.exception, [e.value for e in alerts_page.exception]
    assert any('sin minutos completos' in e.label for e in alerts_page.expander)
    indicators_page = render('comet_insights', 'page_indicators')
    assert not indicators_page.exception, [e.value for e in indicators_page.exception]
    assert 'sin minutos' in page_text(indicators_page)
    advanced = render('comet_insights', 'page_adelantados')
    assert not advanced.exception, [e.value for e in advanced.exception]


def test_screens_without_unknown_minutes_show_no_new_warning(screen_env):  # noqa: F811
    screen_env(comet_tiny.build())
    ranking = render('comet_followup', 'page_rankings')
    assert not ranking.exception and not any('ranking de minutos' in w.value for w in ranking.warning)
    alerts_page = render('comet_insights', 'page_alerts')
    assert not alerts_page.exception and not any('sin minutos completos' in e.label for e in alerts_page.expander)
