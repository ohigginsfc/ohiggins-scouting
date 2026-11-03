"""Goles por año de temporada: filtro de año y tabla «goles por año» en las pantallas SQL de COMET (petición del 30-10-2026)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scouting.comet import config_store, roster, yearly
from tests.test_comet_plantel_bajas import OVERVIEW, SQUAD, TODAY, metric, render, text


# --- Cálculo ----------------------------------------------------------------------------------------------------------------

def stat(personid, name, year, **values):
    base = dict(personid=personid, displayname=name, age=15, nationality='Chile', level='Formativo', category='U-15',
                season_year=year, matches=10, minutes=800, starts=9, goals=3, yellow_cards=1, red_cards=0)
    return {**base, **values}


UNIT = pd.DataFrame([
    stat(1, 'Ana', 2024, goals=3),
    stat(1, 'Ana', 2025, matches=20, minutes=1500, starts=18, goals=7, yellow_cards=2, red_cards=1),
    stat(2, 'Beto', 2025, matches=5, minutes=300, starts=2, goals=0),
    stat(3, 'Caro', 2025, matches=2, minutes=0, starts=0, goals=np.nan),   # 0 minutos: no entra
    stat(4, 'Dani', 2025, goals=np.nan),                                  # jugó, pero se desconocen sus goles
])


def test_season_year_comes_from_the_season_name_or_else_from_the_match_year():
    frame = pd.DataFrame({'season': ['2026', '2025/2026', 'Copa de invierno', None, 'Apertura'],
                          'match_year': [2026.0, 2025.0, 2024.0, np.nan, np.nan]})
    years = yearly.with_season_year(frame)['season_year']
    assert years.iloc[:3].tolist() == [2026, 2025, 2024], '«2025/2026» es la temporada 2025; sin año en el nombre vale el del partido'
    assert years.iloc[3:].isna().all(), 'sin ninguno de los dos no se inventa un año'
    empty = yearly.with_season_year(pd.DataFrame(columns=['season', 'match_year']))
    assert empty.empty and 'season_year' in empty and yearly.years_available(empty) == []
    assert yearly.years_available(pd.DataFrame()) == []


def test_years_are_listed_newest_first_and_labelled():
    assert yearly.years_available(UNIT) == [2025, 2024]
    assert yearly.label(None) == 'Todos los años' and yearly.label(2025) == '2025'
    assert len(yearly.in_year(UNIT, None)) == 5 and yearly.in_year(UNIT, 2024)['personid'].tolist() == [1]


def test_stats_add_up_all_years_or_pick_one_and_keep_unknown_goals_unknown():
    everything = yearly.stats_for_year(UNIT).set_index('personid')
    assert everything.index.tolist() == [1, 4, 2], 'por minutos; Caro (0 minutos) no entra'
    ana = everything.loc[1]
    assert (ana.matches, ana.minutes, ana.starts, ana.goals, ana.yellow_cards, ana.red_cards) == (30, 2300, 27, 10, 3, 1)
    assert ana.avg_minutes == 77 and ana.goals_per90 == pytest.approx(0.39)
    assert pd.isna(everything.loc[4, 'goals']) and pd.isna(everything.loc[4, 'goals_per90']), 'goles desconocidos: no es un 0'
    assert everything.loc[2, 'goals'] == 0 and everything.loc[2, 'goals_per90'] == 0, 'un 0 real sí es 0'
    only_2024 = yearly.stats_for_year(UNIT, 2024)
    assert only_2024['personid'].tolist() == [1] and only_2024['goals'].tolist() == [3] and only_2024['matches'].tolist() == [10]
    nothing = yearly.stats_for_year(UNIT, 2023)
    assert nothing.empty and list(nothing.columns) == yearly.STATS_COLUMNS
    assert yearly.stats_for_year(pd.DataFrame()).empty


def test_players_in_two_categories_stay_separate_rows():
    frame = pd.concat([UNIT, pd.DataFrame([stat(1, 'Ana', 2025, category='U-16', matches=3, minutes=200, goals=1)])], ignore_index=True)
    ana = yearly.stats_for_year(frame)
    assert sorted(ana[ana['personid'] == 1]['category']) == ['U-15', 'U-16']
    table = yearly.goals_by_year(frame, ana[ana['personid'] == 1]).set_index('category')
    assert table.loc['U-15', 'Total'] == 10 and table.loc['U-16', 'Total'] == 1


def test_goals_by_year_has_a_column_per_year_the_total_and_blanks_for_years_without_matches():
    stats = yearly.stats_for_year(UNIT)
    table = yearly.goals_by_year(UNIT, stats)
    assert table['displayname'].tolist() == ['Ana', 'Dani', 'Beto'], 'en el mismo orden que la tabla principal'
    assert yearly.year_columns(table) == ['2024', '2025'] and 'Total' in table
    by_name = table.set_index('displayname')
    assert by_name.loc['Ana', ['2024', '2025', 'Total']].tolist() == [3, 7, 10]
    assert pd.isna(by_name.loc['Beto', '2024']) and by_name.loc['Beto', '2025'] == 0 and by_name.loc['Beto', 'Total'] == 0, \
        'sin partidos en 2024: sin dato; en 2025 jugó y no marcó: 0'
    assert by_name.loc['Dani', ['2024', '2025', 'Total']].isna().all(), 'goles desconocidos tampoco son 0'
    assert yearly.goals_by_year(UNIT, stats.iloc[0:0]).empty
    assert list(yearly.goals_by_year(UNIT.iloc[0:0], stats).columns) == ['personid', 'displayname', 'category', 'Total']


@pytest.mark.parametrize('years, goals, expected_years, expected_total', [
    ([2026, None], [2, 3], ['2026'], 5),
    ([None], [3], [], 3),
])
def test_goals_total_keeps_matches_without_a_known_season_year(years, goals, expected_years, expected_total):
    frame = pd.DataFrame([stat(1, 'Ana', year, goals=scored) for year, scored in zip(years, goals)])
    frame['season_year'] = pd.array(frame['season_year'], dtype='Int64')
    players = yearly.stats_for_year(frame)

    table = yearly.goals_by_year(frame, players)

    assert table.loc[0, 'Total'] == players.loc[0, 'goals'] == expected_total
    assert yearly.year_columns(table) == expected_years, 'sin fecha no se asigna un año ficticio'
    assert list(table.columns) == ['personid', 'displayname', 'category', *expected_years, 'Total']
    if expected_years:
        assert table.loc[0, '2026'] == 2, 'solo los goles fechados se atribuyen a 2026'


def test_keeper_stats_use_the_same_year_filter():
    keepers = pd.DataFrame([
        dict(personid=9, displayname='Portero', age=17, category='U-16', season_year=2025, matches=10, minutes=900,
             goals_conceded=12, clean_sheets=3),
        dict(personid=9, displayname='Portero', age=17, category='U-16', season_year=2026, matches=20, minutes=1800,
             goals_conceded=14, clean_sheets=9),
        dict(personid=8, displayname='Sin minutos', age=17, category='U-16', season_year=2026, matches=1, minutes=0,
             goals_conceded=0, clean_sheets=1)])
    total = yearly.keeper_stats_for_year(keepers).iloc[0]
    assert (total.matches, total.minutes, total.goals_conceded, total.clean_sheets) == (30, 2700, 26, 12)
    assert total.gc_per90 == 0.87 and total.clean_sheet_pct == 40.0
    last = yearly.keeper_stats_for_year(keepers, 2026).iloc[0]
    assert last.gc_per90 == 0.7 and last.clean_sheet_pct == 45.0
    assert len(yearly.keeper_stats_for_year(keepers)) == 1, 'quien suma 0 minutos no entra'
    assert yearly.keeper_stats_for_year(keepers, 2020).empty


# --- Pantallas --------------------------------------------------------------------------------------------------------------

def by_year_row(personid, name, year, matches, minutes, goals, age=14):
    return stat(personid, name, year, age=age, matches=matches, minutes=minutes, starts=matches, goals=goals,
                yellow_cards=0, red_cards=0)


BY_YEAR = pd.DataFrame([
    by_year_row(201, 'Sub Quince Uno', 2025, 8, 600, 2),
    by_year_row(201, 'Sub Quince Uno', 2026, 9, 700, 5),
    by_year_row(202, 'Sub Quince Dos', 2026, 7, 450, 1),
    by_year_row(203, 'Sub Quince Ido', 2024, 10, 800, 4, age=15),     # ya no está en el plantel (última planilla en 2025)
    by_year_row(203, 'Sub Quince Ido', 2025, 20, 1500, 12, age=15)])
KEEPERS = pd.DataFrame([
    dict(personid=102, displayname='Portero Actual', age=29, category='Primer Equipo', season_year=2025, matches=10,
         minutes=900, goals_conceded=12, clean_sheets=3),
    dict(personid=102, displayname='Portero Actual', age=29, category='Primer Equipo', season_year=2026, matches=20,
         minutes=1800, goals_conceded=14, clean_sheets=9)])
STANDINGS = pd.DataFrame([
    dict(category='U-15', competition_name='Campeonato U-15 2025', season='2025', position=2, matches=20, wins=12, draws=4,
         losses=4, points=40, goalsfor=40, goalsagainst=20, goaldifference=20, efectividad=66.7, pts_per_match=2.0),
    dict(category='U-15', competition_name='Campeonato U-15 2026', season='2026', position=1, matches=10, wins=8, draws=1,
         losses=1, points=25, goalsfor=25, goalsagainst=8, goaldifference=17, efectividad=83.3, pts_per_match=2.5)])
MATCHES = pd.DataFrame([
    dict(matchid=1, matchdate=pd.Timestamp('2025-05-03 15:00'), category='U-15', competition='Campeonato U-15 2025',
         season='2025', result='Victoria', goals_for=2, goals_against=0, venue='Local'),
    dict(matchid=2, matchdate=pd.Timestamp('2026-04-04 15:00'), category='U-15', competition='Campeonato U-15 2026',
         season='2026', result='Derrota', goals_for=0, goals_against=1, venue='Visita'),
    dict(matchid=3, matchdate=pd.Timestamp('2026-04-11 15:00'), category='U-15', competition='Campeonato U-15 2026',
         season='2026', result='Empate', goals_for=1, goals_against=1, venue='Local')])


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
    monkeypatch.setattr(comet_dashboard, 'get_player_stats_by_year', lambda category=None: BY_YEAR.copy())
    monkeypatch.setattr(comet_dashboard, 'get_goalkeeper_stats_by_year', lambda category=None: KEEPERS.copy())
    monkeypatch.setattr(comet_dashboard, 'get_standings_by_category', lambda category=None: STANDINGS.copy())
    monkeypatch.setattr(comet_dashboard, 'get_match_results_by_category', lambda category=None: MATCHES.copy())
    monkeypatch.setattr(config_store, 'load_roster_config', lambda: ({}, roster.EMPTY_BAJAS, None))


def shown(row, columns):
    '''Celdas como se ven: una columna con datos ausentes se muestra como texto («—»); si no, como número.'''
    return [v if isinstance(v, str) else str(int(v)) for v in row[columns]]


def youth(app):
    app.selectbox(key='youth_cat').select('U-15').run()
    assert not app.exception, [e.value for e in app.exception]
    return app


def test_youth_development_offers_every_year_and_starts_on_all_of_them(screen):
    app = youth(render('page_youth_development'))
    year = app.selectbox(key='youth_year_U-15')
    assert year.options == ['Todos los años', '2026', '2025', '2024'], 'también los años del histórico'
    assert year.value is None
    scorers = app.dataframe[0].value
    assert dict(zip(scorers['Jugador'], scorers['Goles'])) == {'Sub Quince Uno': 7, 'Sub Quince Dos': 1}, '2 + 5 y 1; sin el ex jugador'
    assert 'Mejores Jugadores - U-15 · Todos los años' in ' '.join(s.value for s in app.subheader)


def test_youth_development_filters_goals_by_the_chosen_year_and_still_shows_every_year(screen):
    app = youth(render('page_youth_development'))
    app.selectbox(key='youth_year_U-15').select(2026).run()
    scorers = app.dataframe[0].value
    assert dict(zip(scorers['Jugador'], scorers['Goles'])) == {'Sub Quince Uno': 5, 'Sub Quince Dos': 1}
    assert 'Mejores Jugadores - U-15 · 2026' in ' '.join(s.value for s in app.subheader)
    by_year = app.dataframe[1].value.set_index('Jugador')
    assert list(by_year.columns) == ['2025', '2026', 'Total']
    assert shown(by_year.loc['Sub Quince Uno'], ['2025', '2026', 'Total']) == ['2', '5', '7'], 'separa los goles de cada año'
    assert shown(by_year.loc['Sub Quince Dos'], ['2025', '2026', 'Total']) == ['—', '1', '1'], 'sin partidos en 2025: «—»'
    app.selectbox(key='youth_year_U-15').select(2025).run()
    assert dict(zip(app.dataframe[0].value['Jugador'], app.dataframe[0].value['Goles'])) == {'Sub Quince Uno': 2}


def test_a_year_with_only_former_players_says_so_until_the_history_is_included(screen):
    app = youth(render('page_youth_development'))
    app.selectbox(key='youth_year_U-15').select(2024).run()
    assert any('No hay estadísticas disponibles para U-15 (2024)' in i.value for i in app.info)
    assert not app.dataframe
    app.checkbox(key='youth_include_former').check().run()
    assert not app.exception, [e.value for e in app.exception]
    assert dict(zip(app.dataframe[0].value['Jugador'], app.dataframe[0].value['Goles'])) == {'Sub Quince Ido': 4}


def test_the_year_filter_does_not_carry_over_to_another_category(screen):
    app = youth(render('page_youth_development'))
    app.selectbox(key='youth_year_U-15').select(2026).run()
    app.selectbox(key='youth_cat').select('U-20').run()
    assert not app.exception, [e.value for e in app.exception]
    assert app.selectbox(key='youth_year_U-20').value is None, 'cada categoría arranca en «Todos los años»'


def test_player_analysis_splits_goals_by_year(screen):
    app = render('page_player_analysis')
    assert not app.exception, [e.value for e in app.exception]
    assert app.selectbox(key='analysis_year_Todas').options == ['Todos los años', '2026', '2025', '2024']
    table = app.dataframe[0].value.set_index('Jugador')
    assert table.loc['Sub Quince Uno', 'Goles'] == 7 and table.loc['Sub Quince Uno', 'Partidos jugados'] == 17
    assert table.loc['Sub Quince Uno', 'Goles/90'] == pytest.approx(0.48)
    assert set(table.index) == {'Sub Quince Uno', 'Sub Quince Dos'}
    app.selectbox(key='analysis_year_Todas').select(2026).run()
    assert not app.exception, [e.value for e in app.exception]
    table = app.dataframe[0].value.set_index('Jugador')
    assert table.loc['Sub Quince Uno', 'Goles'] == 5 and table.loc['Sub Quince Uno', 'Partidos jugados'] == 9
    assert table.loc['Sub Quince Uno', 'Goles/90'] == pytest.approx(0.64)
    assert 'Jugadores de Campo (2 jugadores · 2026)' in ' '.join(s.value for s in app.subheader)
    per_year = app.dataframe[1].value.set_index('Jugador')
    assert shown(per_year.loc['Sub Quince Uno'], ['2025', '2026', 'Total']) == ['2', '5', '7']


def test_player_analysis_filters_goalkeepers_by_year_too(screen):
    app = render('page_player_analysis')
    app.selectbox(key='pos_type').select('Arqueros').run()
    assert not app.exception, [e.value for e in app.exception]
    assert app.selectbox(key='analysis_year_gk_Todas').options == ['Todos los años', '2026', '2025']
    keeper = app.dataframe[0].value.iloc[0]
    assert (keeper['Goles recibidos'], keeper['Vallas invictas'], keeper['% vallas invictas']) == (26, 12, 40.0)
    app.selectbox(key='analysis_year_gk_Todas').select(2026).run()
    keeper = app.dataframe[0].value.iloc[0]
    assert (keeper['Goles recibidos'], keeper['Goles recibidos/90'], keeper['% vallas invictas']) == (14, 0.7, 45.0)
    assert 'Arqueros (1 arqueros · 2026)' in ' '.join(s.value for s in app.subheader)


def test_category_performance_splits_team_goals_by_year(screen):
    app = render('page_competition_performance')
    app.selectbox(key='comp_cat').select('U-15').run()
    assert not app.exception, [e.value for e in app.exception]
    assert app.selectbox(key='comp_year_U-15').options == ['Todos los años', '2026', '2025']
    assert metric(app, 'Goles a favor (Todos los años)') == '65'
    assert len(app.dataframe[0].value) == 2
    app.selectbox(key='comp_year_U-15').select(2026).run()
    assert not app.exception, [e.value for e in app.exception]
    assert metric(app, 'Goles a favor (2026)') == '25' and metric(app, 'Diferencia de gol (2026)') == '+17'
    assert app.dataframe[0].value['Competición'].tolist() == ['Campeonato U-15 2026']
    summary = text(app)
    assert '1 Victoria' not in summary and 'Derrota' in summary and 'Empate' in summary, 'los partidos también son solo los de 2026'


def test_category_performance_says_when_a_year_has_no_standings(screen, monkeypatch):
    import comet_dashboard
    monkeypatch.setattr(comet_dashboard, 'get_standings_by_category', lambda category=None: STANDINGS[STANDINGS['season'] == '2025'].copy())
    app = render('page_competition_performance')
    app.selectbox(key='comp_cat').select('U-15').run()
    app.selectbox(key='comp_year_U-15').select(2026).run()      # 2026 solo existe en los partidos
    assert not app.exception, [e.value for e in app.exception]
    assert any('No hay posiciones registradas para U-15 (2026)' in i.value for i in app.info)
