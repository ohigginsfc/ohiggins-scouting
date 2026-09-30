"""Cálculos COMET verificados a mano sobre un mini-torneo ficticio (ver tests/comet_tiny.py)."""
from datetime import date

import numpy as np
import pandas as pd
import pytest

from scouting.comet import adelantados, alerts, categories, digest, indicators, metrics, quality
from scouting.comet.facts import (ROLE_STARTER, ROLE_SUB_IN, ROLE_SUB_OUT, ROLE_UNKNOWN, build_dataset, norm_id,
                                  season_year_of, to_bool)
from scouting.comet.rules import RULE_DEFS, STATUS_CONFIRMED, STATUS_PENDING, STATUS_REQUESTED, Rules, parse
from tests import comet_tiny
from tests.comet_tiny import sheet_row

AVAILABLE = ['U-12', 'U-14', 'U-15', 'U-16', 'U-19', 'Primer Equipo']


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
    assert len(picked) == 1, f'se esperaba una fila para {personid} {where}'
    return picked.iloc[0]


# --- categorías ---------------------------------------------------------------------------------------

def test_parse_category_variants():
    assert categories.parse_category('U-15').cap == 15
    assert categories.parse_category('Sub 15').label == 'U-15'
    assert categories.parse_category(' u_16 ').cap == 16
    senior = categories.parse_category('Primer Equipo')
    assert (senior.label, senior.rank, senior.cap) == ('Primer Equipo', 1000, None)
    assert categories.parse_category('Reserva').rank is None
    assert categories.parse_category(None).rank is None
    assert categories.order_categories(['U-14', 'Primer Equipo', 'U-19', 'Reserva', 'U-14']) == ['Primer Equipo', 'U-19', 'U-14']


@pytest.mark.parametrize('age, expected', [(11, 'U-12'), (12, 'U-12'), (13, 'U-14'), (15, 'U-15'), (16, 'U-16'),
                                           (17, 'U-19'), (19, 'U-19'), (20, 'Primer Equipo'), (None, None)])
def test_age_category_is_smallest_category_that_fits(age, expected):
    assert categories.category_for_age(age, AVAILABLE) == expected


def test_steps_count_categories_not_years():
    assert categories.steps_ahead('U-19', 'U-16', AVAILABLE) == 1      # no existen U-17 ni U-18
    assert categories.steps_ahead('U-16', 'U-14', AVAILABLE) == 2
    assert categories.steps_ahead('U-15', 'U-15', AVAILABLE) == 0
    assert categories.steps_ahead('Primer Equipo', 'U-19', AVAILABLE) == 1
    assert categories.steps_ahead('U-14', 'U-15', AVAILABLE) == -1
    assert categories.steps_ahead('Reserva', 'U-15', AVAILABLE) is None


def test_age_on_respects_birthday_and_cutoff():
    birth = pd.Timestamp('2011-06-10')
    assert categories.age_on(birth, date(2026, 6, 9)) == 14
    assert categories.age_on(birth, date(2026, 6, 10)) == 15
    assert categories.age_on(pd.NaT, date(2026, 6, 10)) is None
    assert categories.years_younger(13, 'U-15') == 2
    assert categories.years_younger(13, 'Primer Equipo') is None


# --- reglas ---------------------------------------------------------------------------------------------

def test_rule_status_never_presents_an_assumption_as_approved():
    rules = Rules()
    assert rules.status('yellow_threshold') == STATUS_REQUESTED
    assert rules.status('card_cycle') == STATUS_PENDING
    assert {r.key for r in rules.pending()} == {r.key for r in RULE_DEFS if r.origin == 'supuesto'}
    approved = Rules({'card_cycle': {'value': 'temporada', 'confirmed': True}})
    assert approved.status('card_cycle') == STATUS_CONFIRMED and approved.value('card_cycle') == 'temporada'
    assert approved.status('possible_from_first_call') == STATUS_PENDING
    assert all(r.question for r in rules.pending() if r.key != 'digest_weekday')


def test_invalid_stored_values_fall_back_and_strict_parse_rejects_them():
    rules = Rules({'yellow_threshold': {'value': 'muchas'}, 'card_cycle': {'value': 'otro'},
                   'age_cutoff': {'value': '02-30'}})
    assert (rules.value('yellow_threshold'), rules.value('card_cycle'), rules.value('age_cutoff')) == (4, 'competicion', '12-31')
    from scouting.comet.rules import RULES_BY_KEY
    for key, bad in [('yellow_threshold', 0), ('yellow_threshold', True), ('participation_threshold', 101),
                     ('age_cutoff', '13-01'), ('digest_recipients', ['sin-arroba']), ('possible_from_first_call', 'si')]:
        with pytest.raises(ValueError):
            parse(RULES_BY_KEY[key], bad)
    assert parse(RULES_BY_KEY['age_cutoff'], '6-30') == '06-30'


# --- preparación de datos --------------------------------------------------------------------------------

def test_ids_and_booleans_are_normalised_and_missing_stays_missing():
    assert norm_id(12) == '12' and norm_id(12.0) == '12' and norm_id(' 7 ') == '7' and norm_id(None) is None
    assert norm_id(np.nan) is None
    values = to_bool(pd.Series([True, 'f', 't', 0, None, np.nan, 'quizás']))
    assert values.tolist()[:4] == [True, False, True, False]
    assert values.isna().tolist()[4:] == [True, True, True]
    assert season_year_of('2025/2026') == 2025 and season_year_of(None, 2024) == 2024


def test_roles_and_missing_minutes_are_not_turned_into_zero():
    extra = [sheet_row(1, 6, True, True, None), sheet_row(1, 7, None, None, 20), sheet_row(2, 8, True, False, 10)]
    players = [dict(personid=p, displayname=f'X{p}', dateofbirth='2011-01-01', nationality='Chile', level='F',
                    status='ACTIVO', orgname='O') for p in (6, 7, 8)]
    ds, _ = dataset(extra_sheet=extra, extra_players=players)
    f = ds.facts.set_index('personid')
    roles = {p: f.loc[p]['role'] if isinstance(f.loc[p], pd.Series) else f.loc[p]['role'].iloc[0] for p in ('6', '7', '8')}
    assert roles == {'6': ROLE_STARTER, '7': ROLE_UNKNOWN, '8': ROLE_SUB_IN}
    assert pd.isna(f.loc['6']['minutes']), 'jugó sin minutos: dato ausente, no 0'
    assert f.loc['7']['minutes'] == 20 and bool(f.loc['7']['participated']), 'sin marca de jugó pero con minutos'
    comp, _ = summaries(ds)
    assert pd.isna(row(comp, 6)['minutes']), 'todos sus minutos faltan: se muestra "—"'
    assert row(comp, 1)['minutes'] == 140


def test_utc_match_dates_are_converted_to_santiago_time():
    raw = comet_tiny.build()
    raw['matches']['matchdate'] = pd.to_datetime(['2026-03-08 02:00', '2026-03-14 18:00', '2026-03-21 18:00',
                                                  '2026-03-08 14:00'], utc=True)
    ds = build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers'])
    first = ds.matches.set_index('matchid').loc['1']
    assert first['matchdate'] == pd.Timestamp('2026-03-07 23:00'), 'Chile está en UTC-3 en marzo'
    assert first['week_start'] == pd.Timestamp('2026-03-02')
    assert ds.current_season(pd.Timestamp('2026-09-30')) == 2026


def test_age_and_adelantado_fields():
    ds, _ = dataset()
    f = ds.facts
    p2_u15 = f[(f['personid'] == '2') & (f['category'] == 'U-15')].iloc[0]
    assert (p2_u15['age'], p2_u15['age_category'], p2_u15['steps_ahead'], p2_u15['years_younger']) == (14, 'U-14', 1, 1)
    p1 = f[f['personid'] == '1'].iloc[0]
    assert (p1['age'], p1['age_category'], p1['steps_ahead']) == (15, 'U-15', 0)
    assert ds.categories == ('U-15', 'U-14')
    late = Rules({'age_cutoff': {'value': '03-01'}})
    ds_late, _ = dataset(late)
    assert ds_late.facts[ds_late.facts['personid'] == '1']['age'].iloc[0] == 14, \
        'nació el 10 de junio: al 1 de marzo de 2026 aún tiene 14 años'


# --- métricas por jugador ----------------------------------------------------------------------------------

def test_player_summary_matches_hand_calculation():
    ds, _ = dataset()
    comp, _ = summaries(ds)
    p1 = row(comp, 1, competition_id='100')
    assert (p1.cited, p1.started, p1.sub_in, p1.only_called, p1.played) == (3, 2, 0, 1, 2)
    assert (p1.minutes, p1.goals, p1.yellow_cards, p1.red_cards) == (140, 1, 2, 0)
    assert p1.possible_minutes == 240 and p1.participation_pct == pytest.approx(140 / 240 * 100)
    assert (p1.wins_with, p1.draws_with, p1.losses_with, p1.results_with, p1.win_pct_with) == (1, 1, 0, 2, 50.0)

    p2 = row(comp, 2, competition_id='100')
    assert (p2.cited, p2.started, p2.sub_in, p2.only_called, p2.played) == (3, 2, 1, 0, 3)
    assert (p2.minutes, p2.goals, p2.yellow_cards) == (190, 1, 1)
    assert p2.participation_pct == pytest.approx(190 / 240 * 100) and p2.win_pct_with == pytest.approx(100 / 3)

    p3 = row(comp, 3, competition_id='100')
    assert (p3.minutes, p3.only_called, p3.wins_with, p3.results_with) == (160, 1, 1, 2)

    p4 = row(comp, 4, competition_id='100')
    assert (p4.minutes, p4.played, p4.only_called, p4.participation_pct) == (0, 0, 3, 0.0)
    assert pd.isna(p4.win_pct_with), 'sin partidos jugados no hay % de victorias (no es 0 %)'


def test_result_with_player_uses_minimum_minutes_rule():
    ds, _ = dataset(Rules({'min_minutes_on_pitch': {'value': 45}}))
    comp, _ = summaries(ds)
    p2 = row(comp, 2, competition_id='100')
    assert p2.results_with == 2, 'ya no cuenta el partido en que jugó 30 minutos'
    assert p2.wins_with == 0


def test_possible_minutes_rules_from_first_call_and_selection_periods():
    earlier = dict(matchid=9, competition_id=100, matchdate=pd.Timestamp('2026-02-28 15:00'), category='U-15',
                   competition='Campeonato U-15 2026', season='2026', venue='Local', home_team='O', away_team='R',
                   goals_for=1, goals_against=0, result='Victoria')
    sheet = [sheet_row(9, 2, True, True, 80), sheet_row(9, 3, True, True, 80)]
    ds, _ = dataset(extra_sheet=sheet, extra_matches=[earlier])
    comp, _ = summaries(ds)
    assert row(comp, 1, competition_id='100').possible_minutes == 320, 'cuenta también el partido anterior a su llegada'
    ds_first, _ = dataset(Rules({'possible_from_first_call': {'value': True}}), extra_sheet=sheet, extra_matches=[earlier])
    comp_first, _ = summaries(ds_first)
    assert row(comp_first, 1, competition_id='100').possible_minutes == 240
    assert row(comp_first, 2, competition_id='100').possible_minutes == 320, 'P2 sí fue citado en el partido 9'

    # P1 no jugó el partido 3 (21-03): dentro de un período de selección se descuenta de sus minutos posibles.
    periods = pd.DataFrame([dict(personid='1', start=pd.Timestamp('2026-03-21'), end=pd.Timestamp('2026-03-22'),
                                 kind='microciclo', active=True)])
    comp_off, _ = summaries(ds, periods)
    assert row(comp_off, 1, competition_id='100').possible_minutes == 320, 'con la regla apagada solo se muestran'
    ds_on, _ = dataset(Rules({'exclude_selection_periods': {'value': True}}), extra_sheet=sheet, extra_matches=[earlier])
    comp_on, _ = summaries(ds_on, periods)
    p1 = row(comp_on, 1, competition_id='100')
    assert p1.possible_minutes == 240 and p1.participation_pct == pytest.approx(140 / 240 * 100)
    assert row(comp_on, 2, competition_id='100').possible_minutes == 320, 'otros jugadores no se ven afectados'
    retired = periods.assign(active=False)
    assert row(summaries(ds_on, retired)[0], 1, competition_id='100').possible_minutes == 320


def test_selection_periods_never_push_participation_above_100_percent():
    """Hallazgo de la revisión: 140 min jugados sobre 80 posibles daba 175 %. Numerador y denominador usan
    el mismo conjunto de partidos y un partido jugado nunca se descuenta."""
    periods = pd.DataFrame([dict(personid='1', start=pd.Timestamp('2026-03-14'), end=pd.Timestamp('2026-03-22'),
                                 kind='microciclo', active=True)])   # cubre el partido 2 (jugó 60') y el 3 (no jugó)
    ds, raw = dataset(Rules({'exclude_selection_periods': {'value': True}}))
    comp, cat = summaries(ds, periods)
    p1 = row(comp, 1, competition_id='100')
    assert p1.possible_minutes == 160, 'el partido 3 (no jugado) se descuenta; el 2 (jugado) cuenta'
    assert p1.counted_minutes == 140 and p1.participation_pct == pytest.approx(87.5)
    assert (comp['participation_pct'].dropna() <= 100).all()
    report = quality.data_quality(ds, raw['sheet'], raw['matches'], periods, comp).set_index('control')
    assert report.loc['Partidos jugados dentro de un período de selección', 'cantidad'] == 1, 'la contradicción se avisa'
    assert report.loc['Participación superior al 100 %', 'nivel'] == 'Correcto'


def test_overlapping_periods_and_minutes_outside_the_possible_set_are_reported():
    periods = pd.DataFrame([
        dict(personid='1', start=pd.Timestamp('2026-03-10'), end=pd.Timestamp('2026-03-20'), kind='microciclo', active=True),
        dict(personid='1', start=pd.Timestamp('2026-03-15'), end=pd.Timestamp('2026-03-25'), kind='mundial', active=True),
        dict(personid='2', start=pd.Timestamp('2026-01-01'), end=pd.Timestamp('2026-01-05'), kind='mundial', active=False)])
    ds, raw = dataset()
    report = quality.data_quality(ds, raw['sheet'], raw['matches'], periods).set_index('control')
    assert report.loc['Períodos de selección solapados', 'cantidad'] == 1
    # Con la duración nominal elegida y sin duración nominal, los minutos jugados quedan fuera del conjunto de posibles.
    nominal, raw_n = dataset(Rules({'duration_source': {'value': 'nominal'}}))
    comp, _ = summaries(nominal)
    assert pd.isna(row(comp, 1, competition_id='100').possible_minutes), 'sin duración nominal no se cambia de fuente a escondidas'
    assert pd.isna(row(comp, 1, competition_id='100').participation_pct)
    report_n = quality.data_quality(nominal, raw_n['sheet'], raw_n['matches'], periods, comp).set_index('control')
    assert report_n.loc['Minutos jugados fuera de los partidos que cuentan como posibles', 'cantidad'] > 0


def test_matches_without_recorded_minutes_are_not_assumed_to_last_90():
    unknown = dict(matchid=11, competition_id=100, matchdate=pd.Timestamp('2026-04-04 15:00'), category='U-15',
                   competition='Campeonato U-15 2026', season='2026', venue='Local', home_team='O', away_team='R',
                   goals_for=None, goals_against=None, result=None)
    ds, _ = dataset(extra_matches=[unknown])
    assert pd.isna(ds.matches.set_index('matchid').loc['11', 'duration'])
    comp, _ = summaries(ds)
    assert row(comp, 1, competition_id='100').possible_minutes == 240


def test_ranking_ties_share_position_and_zero_or_missing_do_not_enter():
    ds, _ = dataset()
    _, cat = summaries(ds)
    goals = metrics.ranking(cat, 'Goles', category='U-15', season_year=2026)
    assert goals['position'].tolist() == [1, 1] and goals['personid'].tolist() == ['2', '1'], 'desempata por minutos'
    minutes = metrics.ranking(cat, 'Minutos jugados', category='U-15', season_year=2026)
    assert minutes['personid'].tolist() == ['2', '3', '1'] and minutes['position'].tolist() == [1, 2, 3]
    assert '4' not in minutes['personid'].tolist(), 'quien no jugó no aparece en el ranking de minutos'
    wins = metrics.ranking(cat, 'Partidos ganados con el jugador en cancha', category='U-15', season_year=2026)
    assert set(wins['personid']) == {'1', '2', '3'} and set(wins['position']) == {1}
    yellows = metrics.ranking(cat, 'Tarjetas amarillas', category='U-15', season_year=2026, top=1)
    assert yellows['personid'].tolist() == ['1'] and yellows['yellow_cards'].iloc[0] == 2
    assert metrics.ranking(cat, 'Tarjetas rojas', category='U-15', season_year=2026).empty
    assert metrics.ranking(cat, 'Goles', category='U-14', season_year=2026).empty


def test_timeline_shows_real_zeros_but_not_months_without_matches():
    april = dict(matchid=12, competition_id=100, matchdate=pd.Timestamp('2026-04-04 15:00'), category='U-15',
                 competition='Campeonato U-15 2026', season='2026', venue='Local', home_team='O', away_team='R',
                 goals_for=1, goals_against=1, result='Empate')
    ds, _ = dataset(extra_sheet=[sheet_row(12, 2, True, True, 80)], extra_matches=[april])
    months = metrics.minutes_timeline(ds, '1', 'Mes').set_index('periodo')['minutes']
    assert months.to_dict() == {'2026-03': 140, '2026-04': 0}, 'abril: hubo partido y no jugó (0 real); mayo no existe'
    semester = metrics.minutes_timeline(ds, '1', 'Semestre')
    assert semester['periodo'].tolist() == ['2026 · S1'] and semester['minutes'].iloc[0] == 140
    assert metrics.minutes_timeline(ds, '999').empty


def test_match_sheet_order_not_called_reference_and_goalkeeper_conceded():
    other = dict(matchid=13, competition_id=100, matchdate=pd.Timestamp('2026-04-11 15:00'), category='U-15',
                 competition='Campeonato U-15 2026', season='2026', venue='Local', home_team='O', away_team='R',
                 goals_for=0, goals_against=0, result='Empate')
    ds, _ = dataset(extra_sheet=[sheet_row(13, 1, True, True, 80), sheet_row(13, 2, True, True, 80)], extra_matches=[other])
    sheet = metrics.match_sheet(ds, '1')
    assert sheet['role'].tolist() == [ROLE_STARTER, ROLE_STARTER, ROLE_SUB_IN, ROLE_SUB_OUT]
    absent = metrics.not_called_reference(ds, '13')
    assert absent['displayname'].tolist() == ['Arquero Tres', 'Jugador Cuatro']
    assert metrics.not_called_reference(ds, '1').empty, 'todos los de la competición estaban en la planilla del partido 1'
    conceded = metrics.goalkeeper_conceded(ds, '3')
    assert conceded['goalsconceded'].tolist() == [3] and conceded['displayname'].tolist() == ['Arquero Tres']
    assert metrics.goalkeeper_conceded(ds)['goalsconceded'].sum() == 4


# --- temporadas sin promoción ---------------------------------------------------------------------------------

def seasons_dataset(spec, rules=None):
    """spec: {personid: {año: categoría}}; cada (año, categoría) es una competición con 2 partidos de 80 min."""
    matches, sheet, players, comps = [], [], [], {}
    for pid, by_year in spec.items():
        players.append(dict(personid=pid, displayname=f'Jugador {pid}', dateofbirth='2011-06-10', nationality='Chile',
                            level='F', status='ACTIVO', orgname='O'))
        for year, cat in by_year.items():
            comp = comps.setdefault((year, cat), 1000 + len(comps))
            for k in (1, 2):
                mid = comp * 10 + k
                if not any(m['matchid'] == mid for m in matches):
                    matches.append(dict(matchid=mid, competition_id=comp, matchdate=pd.Timestamp(f'{year}-05-0{k} 15:00'),
                                        category=cat, competition=f'{cat} {year}', season=str(year), venue='Local',
                                        home_team='O', away_team='R', goals_for=1, goals_against=0, result='Victoria'))
                sheet.append(sheet_row(mid, pid, True, True, 80, comp=comp))
    keepers = pd.DataFrame(columns=['matchid', 'competition_id', 'personid', 'played', 'minutesplayed', 'goalsconceded'])
    return build_dataset(pd.DataFrame(sheet), pd.DataFrame(matches), pd.DataFrame(players), keepers, rules)


HISTORY = {
    1: {2024: 'U-15', 2025: 'U-15', 2026: 'U-15'},   # 3 seguidas -> alerta
    2: {2025: 'U-15', 2026: 'U-15'},                  # 2 -> no
    3: {2024: 'U-14', 2025: 'U-15', 2026: 'U-15'},   # promovido en 2025 -> 2
    4: {2024: 'U-15', 2026: 'U-15'},                  # hueco en 2025 -> 1
    5: {2024: 'U-15', 2025: 'U-14', 2026: 'U-14'},   # bajó de categoría: sin promoción desde 2024 -> 3
    6: {2024: 'U-15', 2025: 'U-15', 2026: 'Primer Equipo'},
}


def test_seasons_without_promotion_counts_streak_and_stops_at_promotion_or_gap():
    ds = seasons_dataset(HISTORY)
    _, cat = summaries(ds)
    principal = metrics.principal_categories(cat)
    streak = metrics.seasons_without_promotion(principal, 2026).set_index('personid')['seasons_in_category'].to_dict()
    assert streak == {'1': 3, '2': 2, '3': 2, '4': 1, '5': 3, '6': 1}
    found = alerts.evaluate_alerts(ds, cat, 2026)
    flagged = found[found['alert_key'] == 'no_promotion']
    assert set(flagged['personid']) == {'1', '5'}, 'más de 2 temporadas: 3 o más'
    assert 'historial disponible desde 2024' in flagged['detail'].iloc[0]
    strict = seasons_dataset(HISTORY, Rules({'seasons_without_promotion': {'value': 1}}))
    found_strict = alerts.evaluate_alerts(strict, summaries(strict)[1], 2026)
    assert set(found_strict.loc[found_strict['alert_key'] == 'no_promotion', 'personid']) == {'1', '2', '3', '5'}


# --- alertas ------------------------------------------------------------------------------------------------

def test_alert_default_thresholds_on_tiny_tournament():
    ds, _ = dataset()
    _, cat = summaries(ds)
    found = alerts.evaluate_alerts(ds, cat, 2026)
    by_kind = {k: sorted(g['personid']) for k, g in found.groupby('alert_key')}
    assert by_kind == {'low_participation': ['4'], 'playing_up': ['2']}
    up = found[found['alert_key'] == 'playing_up'].iloc[0]
    assert up['value'] == 190, 'minutos en la categoría superior (los 70 de U-14 no cuentan)'
    assert 'Le corresponde U-14 por edad (14 años)' in up['detail'] and 'juega en U-15 (+1) · 190 min' in up['detail']
    assert found.set_index('alert_key').loc['low_participation', 'color'] == 'Rojo'


def test_yellow_card_alert_boundary_and_cycle():
    rules_2 = Rules({'yellow_threshold': {'value': 2}})
    ds, _ = dataset(rules_2)
    _, cat = summaries(ds)
    found = alerts.evaluate_alerts(ds, cat, 2026)
    yellow = found[found['alert_key'] == 'yellow_cards']
    assert yellow['personid'].tolist() == ['1'] and yellow['value'].iloc[0] == 2
    assert '2 amarillas en Campeonato U-15 2026' in yellow['detail'].iloc[0]
    ds3, _ = dataset(Rules({'yellow_threshold': {'value': 3}}))
    assert alerts.evaluate_alerts(ds3, summaries(ds3)[1], 2026).query("alert_key == 'yellow_cards'").empty

    # Ciclo por temporada: las amarillas de dos competiciones se suman; por competición no.
    extra_matches = [dict(matchid=20, competition_id=300, matchdate=pd.Timestamp('2026-05-02 15:00'), category='U-15',
                          competition='Copa U-15 2026', season='2026', venue='Local', home_team='O', away_team='R',
                          goals_for=1, goals_against=0, result='Victoria')]
    extra_sheet = [sheet_row(20, 2, True, True, 80, yellow=1, comp=300)]
    by_comp, _ = dataset(Rules({'yellow_threshold': {'value': 2}}), extra_sheet=extra_sheet, extra_matches=extra_matches)
    by_season, _ = dataset(Rules({'yellow_threshold': {'value': 2}, 'card_cycle': {'value': 'temporada'}}),
                           extra_sheet=extra_sheet, extra_matches=extra_matches)
    assert set(alerts.evaluate_alerts(by_comp, summaries(by_comp)[1], 2026).query("alert_key == 'yellow_cards'")['personid']) == {'1'}
    assert set(alerts.evaluate_alerts(by_season, summaries(by_season)[1], 2026).query("alert_key == 'yellow_cards'")['personid']) == {'1', '2'}


def test_participation_alert_is_strictly_below_threshold():
    for threshold, expected in [(58, set()), (59, {'1'})]:
        ds, _ = dataset(Rules({'participation_threshold': {'value': threshold}}))
        _, cat = summaries(ds)
        found = alerts.evaluate_alerts(ds, cat, 2026, {'playing_up': {'enabled': False, 'color': 'Azul'}})
        low = set(found.loc[found['alert_key'] == 'low_participation', 'personid'])
        assert low == expected | {'4'}, f'umbral {threshold}: 58,3 % no está por debajo de 58 pero sí de 59'


def test_alert_configuration_toggles_colors_and_ignores_garbage():
    ds, _ = dataset()
    _, cat = summaries(ds)
    config = {'playing_up': {'enabled': False, 'color': 'Azul'}, 'low_participation': {'enabled': True, 'color': 'Verde'},
              'yellow_cards': 'basura', 'inexistente': {'enabled': True, 'color': 'Rojo'}}
    resolved = alerts.resolve_config(config)
    assert resolved['yellow_cards'] == {'enabled': True, 'color': 'Naranja'} and 'inexistente' not in resolved
    found = alerts.evaluate_alerts(ds, cat, 2026, config)
    assert set(found['alert_key']) == {'low_participation'} and set(found['color']) == {'Verde'}
    assert alerts.resolve_config({'low_participation': {'enabled': True, 'color': 'Fucsia'}})['low_participation']['color'] == 'Rojo'
    everything_off = {k: {'enabled': False, 'color': 'Gris'} for k in alerts.ALERTS_BY_KEY}
    assert alerts.evaluate_alerts(ds, cat, 2026, everything_off).empty
    assert 'Menos del 20 %' in alerts.alert_label('low_participation', ds.rules)
    assert '4 o más' in alerts.alert_label('yellow_cards', ds.rules)


# --- indicadores ----------------------------------------------------------------------------------------------

def test_category_indicators_match_hand_calculation():
    ds, _ = dataset()
    _, cat = summaries(ds)
    ind = indicators.category_indicators(ds, cat, 2026, comet_tiny.TODAY).set_index('category')
    u15 = ind.loc['U-15']
    assert (u15['partidos'], u15['victorias'], u15['empates'], u15['derrotas']) == (3, 1, 1, 1)
    assert u15['pct_victorias'] == pytest.approx(33.3)
    assert (u15['jugadores_citados'], u15['jugadores_con_minutos']) == (4, 3)
    assert u15['edad_promedio'] == pytest.approx(14.75, abs=0.06)
    assert (u15['minutos_totales'], u15['goles'], u15['amarillas'], u15['rojas'], u15['goles_recibidos_arqueros']) == (490, 2, 3, 0, 4)
    assert (u15['min_tope_o_mayor'], u15['min_menor_1']) == (300, 190) and pd.isna(u15['min_menor_2'])
    assert u15['pct_menores'] == pytest.approx(38.8, abs=0.05)
    assert u15['participacion_pct'] == pytest.approx(490 / 960 * 100, abs=0.06)
    u14 = ind.loc['U-14']
    assert (u14['minutos_totales'], u14['min_tope_o_mayor'], u14['pct_menores']) == (140, 140, 0.0)


def test_minutes_by_younger_players_add_up_to_the_series_total():
    ds, _ = dataset()
    young = indicators.minutes_by_years_younger(ds, 2026).set_index('category')
    buckets = ['min_tope_o_mayor', 'min_menor_1', 'min_menor_2', 'min_menor_3', 'min_menor_4_o_mas', 'sin_dato']
    assert (young[buckets].sum(axis=1) == young['total_minutes']).all()


def test_seniority_is_measured_from_first_recorded_match_and_is_a_minimum():
    ds, _ = dataset()
    years = indicators.seniority_years(ds, comet_tiny.TODAY)
    today = pd.Timestamp('2026-09-30')
    assert years['1'] == pytest.approx((today - pd.Timestamp('2026-03-07 15:00')).days / 365.25, abs=0.01)
    assert years['5'] == pytest.approx((today - pd.Timestamp('2026-03-08 11:00')).days / 365.25, abs=0.01)
    assert years['1'] >= years['5'] > 0, 'nadie tiene antigüedad anterior a su primer partido registrado'


def test_age_category_matrix_has_ascending_axes():
    ds, _ = dataset()
    matrix = indicators.age_category_matrix(ds, 2026)
    assert list(matrix.index) == ['U-14', 'U-15'] and list(matrix.columns) == ['U-14', 'U-15']
    assert matrix.loc['U-14', 'U-15'] == 1, 'P2: le corresponde U-14 y juega en U-15'
    assert matrix.loc['U-15', 'U-15'] == 2 and matrix.loc['U-14', 'U-14'] == 2


# --- adelantados ---------------------------------------------------------------------------------------------------

def test_ahead_players_share_permanence_and_peer_comparison():
    ds, _ = dataset()
    _, cat = summaries(ds)
    players = adelantados.ahead_players(ds, 2026)
    assert players['personid'].tolist() == ['2']
    p2 = players.iloc[0]
    assert (p2['plays_in'], p2['ahead_minutes'], p2['total_minutes'], p2['steps']) == ('U-15', 190, 260, 1)
    assert p2['ahead_share_pct'] == pytest.approx(73.1)
    share = adelantados.ahead_share_by_category(ds, 2026).set_index('category')
    assert (share.loc['U-15', 'jugadores'], share.loc['U-15', 'adelantados']) == (3, 1)
    assert share.loc['U-15', 'pct_adelantados'] == pytest.approx(33.3) and share.loc['U-14', 'adelantados'] == 0
    monthly = adelantados.ahead_permanence(ds, 2026)
    assert monthly['mes'].tolist() == ['2026-03'] and monthly['minutes'].iloc[0] == 190
    summary = adelantados.ahead_permanence_summary(ds, 2026).iloc[0]
    assert (summary['matches_in_series'], summary['called'], summary['played'], summary['called_pct']) == (3, 3, 3, 100.0)
    peers = adelantados.ahead_vs_peers(ds, cat, 2026).set_index(['age_category', 'group'])
    ahead = peers.loc[('U-14', 'Adelantados')]
    assert (ahead['jugadores'], ahead['partidos_jugados'], ahead['minutos_por_partido']) == (1, 3, pytest.approx(63.3, abs=0.05))
    assert ahead['goles_por_90'] == pytest.approx(1 * 90 / 190, abs=0.01)
    assert peers.loc[('U-14', 'Grupo de edad'), 'jugadores'] == 2


# --- control de calidad --------------------------------------------------------------------------------------------------

def test_quality_report_flags_each_kind_of_data_problem():
    extra = [sheet_row(1, 2, True, False, 20),                           # jugador repetido en el partido 1
             sheet_row(2, 6, True, True, None),                          # jugó sin minutos
             sheet_row(2, 7, False, False, 15),                          # minutos sin marca de jugó
             sheet_row(3, 8, True, True, 200),                           # minutos fuera de rango
             sheet_row(99, 1, True, True, 80)]                           # partido que no existe
    ds, raw = dataset(extra_sheet=extra)
    report = quality.data_quality(ds, raw['sheet'], raw['matches']).set_index('control')
    for control in ['Filas repetidas contradictorias (jugador y partido)', 'Jugó y sin minutos', 'Minutos sin marca de jugó',
                    'Minutos fuera de rango', 'Filas de planilla sin partido', 'Jugadores sin ficha']:
        assert report.loc[control, 'cantidad'] >= 1 and report.loc[control, 'nivel'] in ('Aviso', 'Error'), control
    assert report.loc['Filas repetidas contradictorias (jugador y partido)', 'nivel'] == 'Error'
    clean_ds, clean_raw = dataset()
    clean = quality.data_quality(clean_ds, clean_raw['sheet'], clean_raw['matches']).set_index('control')
    assert 'Error' not in set(clean['nivel'])
    assert list(clean.index[clean['nivel'] == 'Aviso']) == ['Partidos sin arquero registrado']
    assert clean.loc['Partidos sin arquero registrado', 'cantidad'] == 2, 'los partidos 2 y 4 no traen arquero en el mini-torneo'
    assert clean.loc['Goles de jugadores distintos del marcador', 'nivel'] == 'Información'
    assert clean.loc['Filas repetidas contradictorias (jugador y partido)', 'nivel'] == 'Correcto'


def test_quality_detects_sheets_that_only_list_players_who_played():
    raw = comet_tiny.build()
    raw['sheet'] = raw['sheet'][raw['sheet']['played'] == True]  # noqa: E712
    ds = build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers'])
    report = quality.data_quality(ds, raw['sheet'], raw['matches']).set_index('control')
    assert report.loc['Planillas que solo traen a quienes jugaron', 'nivel'] == 'Error'


# --- resumen semanal -----------------------------------------------------------------------------------------------------

def test_previous_week_and_span():
    assert digest.previous_week('2026-09-30') == (date(2026, 9, 21), date(2026, 9, 27))
    assert digest.previous_week('2026-09-28') == (date(2026, 9, 21), date(2026, 9, 27))
    assert digest.previous_week('2026-09-27') == (date(2026, 9, 14), date(2026, 9, 20))
    assert digest.week_span(date(2026, 9, 21), date(2026, 9, 27)) == '21 al 27 de septiembre de 2026'
    assert digest.week_span(date(2026, 9, 28), date(2026, 10, 4)) == '28 de septiembre al 4 de octubre de 2026'
    assert digest.week_span(date(2026, 12, 28), date(2027, 1, 3)).startswith('28 de diciembre de 2026 al')


def test_weekly_digest_lists_matches_alerts_and_pending_rules_and_escapes_html():
    hostile = dict(personid=6, displayname='<script>alert(1)</script> & Cía', dateofbirth='2011-06-10',
                   nationality='Chile', level='F', status='ACTIVO', orgname='O')
    ds, _ = dataset(extra_sheet=[sheet_row(3, 6, True, False, 10, goals=1)], extra_players=[hostile])
    _, cat = summaries(ds)
    found = alerts.evaluate_alerts(ds, cat, 2026)
    result = digest.build_weekly_digest(ds, found, date(2026, 3, 16), generated_on=date(2026, 3, 30), pending_rules=9)
    assert result.matches == 1 and 'Campeonato U-15 2026' in result.text and '0-3 Derrota' in result.text
    assert 'Goles recibidos por arquero: Arquero Tres (3)' in result.text
    assert 'ALERTAS VIGENTES' in result.text and 'Le corresponde U-14 por edad' in result.text
    assert '9 reglas de cálculo son supuestos pendientes' in result.text and 'menores de edad' in result.text
    assert '<script>' not in result.html and '&lt;script&gt;' in result.html
    empty = digest.build_weekly_digest(ds, found.iloc[0:0], date(2026, 1, 5), generated_on=date(2026, 1, 12))
    assert 'No hay partidos registrados en esta semana.' in empty.text and 'No hay alertas vigentes.' in empty.text
    assert 'supuestos pendientes' not in empty.text
