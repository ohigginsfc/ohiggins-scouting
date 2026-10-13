"""Lo decidido con Pablo el 13-10-2026: secciones del club, amarillas por temporada en las inferiores y por competición
en el Primer Equipo, y el listado del plantel que se mantiene como está. Datos ficticios con cifras hechas a mano."""
import pandas as pd
import pytest

from scouting.comet import adelantados, alerts, categories
from scouting.comet.pipeline import compute_all
from scouting.comet.rules import RULES_BY_KEY, STATUS_CONFIRMED, STATUS_PENDING, STATUS_REQUESTED, Rules, parse
from tests import comet_tiny
from tests.comet_tiny import sheet_row
from tests.test_comet_review_fixes import render, screen_env  # noqa: F401  (fixture de pantallas)

LADDER = categories.build_ladder(categories.DEFAULT_LADDER_CAPS)


# --- Secciones: sub-20, sub-18, sub-16, sub-15, sub-14, sub-13, sub-12 «y así» --------------------------------------------------

@pytest.mark.parametrize('age, expected', [(None, None), (9, 'U-11'), (11, 'U-11'), (12, 'U-12'), (13, 'U-13'), (14, 'U-14'),
                                           (15, 'U-15'), (16, 'U-16'), (17, 'U-18'), (18, 'U-18'), (19, 'U-20'),
                                           (20, 'U-20'), (21, 'Primer Equipo'), (30, 'Primer Equipo')])
def test_age_goes_to_the_smallest_section_that_fits(age, expected):
    assert categories.category_for_age(age, LADDER) == expected


def test_official_ladder_is_listed_from_senior_down_and_keeps_extra_categories_from_the_data():
    assert LADDER == ['Primer Equipo', 'U-20', 'U-18', 'U-16', 'U-15', 'U-14', 'U-13', 'U-12', 'U-11']
    with_extra = categories.build_ladder(categories.DEFAULT_LADDER_CAPS, ['U-19', 'Sub 10', 'Reserva', None])
    assert with_extra[:3] == ['Primer Equipo', 'U-20', 'U-19'] and with_extra[-1] == 'U-10'
    assert 'Reserva' not in with_extra, 'una categoría que no se reconoce no entra en la escalera'
    assert categories.steps_ahead('U-20', 'U-18', LADDER) == 1 and categories.steps_ahead('U-16', 'U-14', LADDER) == 2


def test_ladder_rule_is_editable_validated_and_falls_back_to_the_official_one():
    rule = RULES_BY_KEY['category_ladder']
    assert Rules().status('category_ladder') == STATUS_REQUESTED and Rules().ladder_caps() == (20, 18, 16, 15, 14, 13, 12, 11)
    assert parse(rule, '12, 20;16,18') == '20,18,16,12'
    assert Rules({'category_ladder': {'value': '20,18,16,15,14,13,12,11,10'}}).ladder_caps()[-1] == 10
    for bad in ('', 'veinte', '20,20', '3,20', '20,40'):
        with pytest.raises(ValueError):
            parse(rule, bad)
    assert Rules({'category_ladder': {'value': 'basura'}}).ladder_caps() == categories.DEFAULT_LADDER_CAPS


def test_sql_case_has_the_same_rule_as_the_calculation():
    sql = categories.age_category_case_sql('x')
    assert sql.startswith("CASE WHEN x IS NULL THEN NULL WHEN x > 20 THEN 'Primer Equipo' WHEN x > 18 THEN 'U-20'")
    assert sql.endswith("WHEN x > 11 THEN 'U-12' ELSE 'U-11' END")
    assert 'U-19' not in sql and 'U-17' not in sql, 'no existen esas secciones'


def test_a_seventeen_year_old_in_the_sub_20_is_ahead_even_without_sub_18_matches():
    """Sin U-18 en los datos, antes se le asignaba la sub-20 (la siguiente que existía) y no figuraba como adelantado."""
    matches = [dict(matchid=30, competition_id=400, matchdate=pd.Timestamp('2026-04-04 15:00'), category='U-20',
                    competition='Campeonato U-20 2026', season='2026', venue='Local', home_team="O'Higgins",
                    away_team='Rival E', goals_for=1, goals_against=1, result='Empate')]
    players = [dict(personid=p, displayname=f'Jugador {p}', dateofbirth=born, nationality='Chile', level='Formativo',
                    status='ACTIVO', orgname="O'Higgins")
               for p, born in ((20, '2009-05-05'), (21, '2007-02-02'), (22, '2005-03-03'))]
    sheet = [sheet_row(30, p, True, True, 90, comp=400) for p in (20, 21, 22)]
    computed = compute_all(comet_tiny.build(extra_matches=matches, extra_players=players, extra_sheet=sheet))
    facts = computed.ds.facts.set_index('personid')
    assert facts.loc['20', 'age'] == 17 and facts.loc['20', 'age_category'] == 'U-18' and facts.loc['20', 'steps_ahead'] == 1
    assert facts.loc['21', 'age_category'] == 'U-20' and facts.loc['21', 'steps_ahead'] == 0
    assert facts.loc['22', 'age_category'] == 'Primer Equipo' and facts.loc['22', 'steps_ahead'] == -1
    assert 'U-18' in computed.ds.ladder and 'U-18' not in computed.ds.categories
    assert '20' in set(adelantados.ahead_players(computed.ds, 2026)['personid'])
    up = alerts.evaluate_alerts(computed.ds, computed.cat, 2026).query("alert_key == 'playing_up'")
    assert '20' in set(up['personid']) and '21' not in set(up['personid'])


# --- Amarillas: temporada completa en inferiores, por competición en el Primer Equipo ----------------------------------------

def match(matchid, competition_id, category, name, day):
    return dict(matchid=matchid, competition_id=competition_id, matchdate=pd.Timestamp(f'2026-05-{day:02d} 15:00'),
                category=category, competition=name, season='2026', venue='Local', home_team="O'Higgins", away_team='Rival',
                goals_for=1, goals_against=0, result='Victoria')


def cards_dataset():
    matches = [match(40, 501, 'Primer Equipo', 'Campeonato Primer Equipo 2026', 2),
               match(41, 502, 'Primer Equipo', 'Copa Primer Equipo 2026', 9),
               match(42, 700, 'U-15', 'Campeonato U-15 B 2026', 16),
               match(43, 300, 'U-15', 'Copa U-15 2026', 23),
               match(44, 600, 'Reserva', 'Torneo de reserva 2026', 30)]
    players = [dict(personid=p, displayname=f'Jugador {p}', dateofbirth=born, nationality='Chile', level='F', status='ACTIVO',
                    orgname="O'Higgins") for p, born in ((50, '2000-01-01'), (51, '2011-01-01'), (52, '2000-02-02'))]
    sheet = [sheet_row(40, 50, True, True, 90, yellow=2, comp=501), sheet_row(41, 50, True, True, 90, yellow=2, comp=502),   # 2 + 2 en dos competiciones
             sheet_row(42, 51, True, True, 80, yellow=2, comp=700), sheet_row(43, 51, True, True, 80, yellow=2, comp=300),    # 2 + 2 en dos competiciones
             sheet_row(40, 52, True, True, 90, yellow=4, comp=501),                                                          # 4 en una sola
             sheet_row(44, 52, True, True, 90, yellow=1, comp=600)]                                                          # y 1 en la reserva
    return comet_tiny.build(extra_matches=matches, extra_players=players, extra_sheet=sheet)


def yellow_alerts(raw, **rules):
    computed = compute_all(raw, {'yellow_threshold': {'value': 4}, **rules})
    found = alerts.evaluate_alerts(computed.ds, computed.cat, 2026).query("alert_key == 'yellow_cards'")
    return found.set_index('personid')


def test_default_cycle_is_season_for_youth_and_competition_for_the_first_team():
    found = yellow_alerts(cards_dataset())
    assert set(found.index) == {'51', '52'}, 'P51 (inferiores) suma 2+2 en la temporada; P50 (Primer Equipo) solo 2+2 en competiciones distintas'
    assert found.loc['51', 'value'] == 4 and found.loc['51', 'detail'] == '4 amarillas en la temporada 2026'
    assert found.loc['51', 'category'] == 'U-15'
    assert found.loc['52', 'detail'] == '4 amarillas en Campeonato Primer Equipo 2026', 'el Primer Equipo se cuenta por competición'


def test_the_other_cycle_options_still_apply_one_rule_to_everyone():
    by_season = yellow_alerts(cards_dataset(), card_cycle={'value': 'temporada'})
    assert set(by_season.index) == {'50', '51', '52'} and by_season.loc['52', 'value'] == 5, '4 + 1 de la reserva, en una temporada'
    by_competition = yellow_alerts(cards_dataset(), card_cycle={'value': 'competicion'})
    assert set(by_competition.index) == {'52'}


def test_unrecognised_category_is_counted_by_competition_and_never_added_to_a_youth_season():
    """«Reserva» no es una sección: se cuenta por competición (la regla más fina) y no entra en el total de temporada."""
    mixed = yellow_alerts(cards_dataset(), yellow_threshold={'value': 1})
    reserve = mixed[mixed['detail'].str.contains('Torneo de reserva 2026')]
    assert reserve['value'].tolist() == [1] and reserve.index.tolist() == ['52']


def test_cycle_and_roster_decisions_are_recorded_and_open_questions_stay_open():
    rules = Rules()
    assert rules.value('card_cycle') == 'mixto' and rules.status('card_cycle') == STATUS_CONFIRMED
    assert 'Reunión con Pablo, 13-10-2026' in RULES_BY_KEY['card_cycle'].decision
    assert rules.status('roster_rule') == STATUS_CONFIRMED and rules.value('roster_rule') == 'planillas'
    # Lo que Pablo no contestó sigue pendiente, con su pregunta.
    for key in ('second_yellow_rule', 'suspensions_rule', 'age_cutoff', 'possible_from_first_call', 'duration_source',
                'seniority_rule', 'promotion_rule', 'digest_recipients', 'min_minutes_on_pitch'):
        assert rules.status(key) == STATUS_PENDING and RULES_BY_KEY[key].question, key


# --- Pantallas -------------------------------------------------------------------------------------------------------------------

def test_rules_screen_shows_the_decided_rules_as_confirmed_and_the_ladder_as_requested(screen_env):  # noqa: F811
    screen_env(comet_tiny.build())
    app = render('comet_insights', 'page_tracking')
    assert not app.exception, [e.value for e in app.exception]
    text = ' '.join(m.value for m in app.markdown)
    assert 'Secciones del club' in text and 'Ciclo de tarjetas amarillas' in text
    assert text.count('Confirmada por el club') >= 2 and 'Solicitada por Pablo' in text
    ladder_input = [t for t in app.text_input if t.key == 'rule_category_ladder']
    assert ladder_input and ladder_input[0].value == '20,18,16,15,14,13,12,11'
    cycle = [s for s in app.selectbox if s.key == 'rule_card_cycle']
    assert cycle and cycle[0].value == 'mixto' and 'mixto' in cycle[0].options[0].lower()
