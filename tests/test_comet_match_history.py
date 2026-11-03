"""Historial completo de quien sube de categoría: subidas marcadas, filtros y orden (petición del 30-10-2026).

Datos ficticios. «Jugador Seis» nació el 2012-02-02 (14 años en 2026): le corresponde U-14.

    M10 01-02 U-14  jugó 70'          primer partido jugado: no hay de dónde subir
    M11 15-02 U-14  solo citado
    M12 22-02 U-16  solo citado       citarlo en una categoría alta no es haber jugado en ella
    M13 01-03 U-15  jugó 45'          SUBE de U-14 a U-15
    M14 05-04 U-15  jugó 80'
    M15 03-05 U-16  jugó 30'          SUBE de U-15 a U-16
    M16 10-05 U-16  solo citado
    M17 17-05 U-15  jugó 60'          baja un escalón: no es una subida
    M18 07-06 U-16  jugó 90'          vuelve a U-16, donde ya había jugado: no es una subida
    M19 14-06 Amistoso (categoría que no está en la escalera) jugó 20'

«Jugador Siete» (2011-01-01, 15 años: U-15) solo jugó el M15 en U-16: sin historial anterior no se afirma una subida.
"""
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from scouting.comet import adelantados
from scouting.comet.facts import build_dataset
from tests import comet_tiny
from tests.comet_tiny import sheet_row
from tests.test_comet_pages import ADMIN, PAGES, SCRIPT


def match(matchid, day, category, comp, goals_for, goals_against, result):
    return dict(matchid=matchid, competition_id=comp, matchdate=pd.Timestamp(f'2026-{day} 15:00'), category=category,
                competition=f'Campeonato {category} 2026', season='2026', venue='Local', home_team="O'Higgins",
                away_team=f'Rival {matchid}', goals_for=goals_for, goals_against=goals_against, result=result)


def player(personid, name, born):
    return dict(personid=personid, displayname=name, dateofbirth=born, nationality='Chile', level='Formativo',
                status='ACTIVO', orgname="O'Higgins")


def raw_data():
    return comet_tiny.build(
        extra_matches=[
            match(10, '02-01', 'U-14', 200, 1, 0, 'Victoria'), match(11, '02-15', 'U-14', 200, 0, 0, 'Empate'),
            match(12, '02-22', 'U-16', 300, 1, 1, 'Empate'), match(13, '03-01', 'U-15', 100, 2, 1, 'Victoria'),
            match(14, '04-05', 'U-15', 100, 1, 1, 'Empate'), match(15, '05-03', 'U-16', 300, 0, 2, 'Derrota'),
            match(16, '05-10', 'U-16', 300, 3, 0, 'Victoria'), match(17, '05-17', 'U-15', 100, 1, 0, 'Victoria'),
            match(18, '06-07', 'U-16', 300, 2, 2, 'Empate'), match(19, '06-14', 'Amistoso', 400, 4, 0, 'Victoria')],
        extra_players=[player(6, 'Jugador Seis', '2012-02-02'), player(7, 'Jugador Siete', '2011-01-01')],
        extra_sheet=[
            sheet_row(10, 6, True, True, 70, goals=1, comp=200), sheet_row(11, 6, False, False, 0, comp=200),
            sheet_row(12, 6, False, False, 0, comp=300), sheet_row(13, 6, True, False, 45, comp=100),
            sheet_row(14, 6, True, True, 80, yellow=1, comp=100), sheet_row(15, 6, True, False, 30, comp=300),
            sheet_row(16, 6, False, False, 0, comp=300), sheet_row(17, 6, True, True, 60, comp=100),
            sheet_row(18, 6, True, True, 90, goals=2, comp=300), sheet_row(19, 6, True, False, 20, comp=400),
            sheet_row(15, 7, True, False, 20, comp=300)])


@pytest.fixture(scope='module')
def dataset():
    raw = raw_data()
    return build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers'])


# --- Cálculo ----------------------------------------------------------------------------------------------------------------

def test_every_match_is_kept_in_order_and_each_climb_is_marked_where_it_happened(dataset):
    log = adelantados.player_timeline(dataset, '6')
    assert log['matchid'].tolist() == [str(n) for n in range(10, 20)], 'también las citaciones sin jugar'
    assert log['matchdate'].is_monotonic_increasing
    assert log['participated'].tolist() == [True, False, False, True, True, True, False, True, True, True]
    assert log['ascended'].tolist() == [False, False, False, True, False, True, False, False, False, False]
    assert log['ascents'].tolist() == [0, 0, 0, 1, 1, 2, 2, 2, 2, 2]
    assert log.loc[log['ascended'], ['highest_before', 'category']].values.tolist() == [['U-14', 'U-15'], ['U-15', 'U-16']]


def test_the_first_played_match_and_a_player_without_history_are_not_climbs(dataset):
    first = adelantados.player_timeline(dataset, '6').iloc[0]
    assert first['participated'] and not first['ascended'] and pd.isna(first['highest_before'])
    lonely = adelantados.player_timeline(dataset, '7')
    assert len(lonely) == 1 and not lonely['ascended'].any(), 'sin partidos anteriores no se afirma ninguna subida'
    assert lonely['ahead'].tolist() == [True], 'aunque sí juega por encima de su edad'


def test_a_call_without_playing_neither_climbs_nor_erases_what_was_played_before(dataset):
    log = adelantados.player_timeline(dataset, '6').set_index('matchid')
    assert not log.loc['12', 'participated'] and not log.loc['12', 'ascended'], 'citado en U-16 sin jugar: no sube'
    assert log.loc['13', 'highest_before'] == 'U-14', 'esa citación no cuenta como haber jugado en U-16'
    assert log.loc['15', 'ascended'] and log.loc['15', 'highest_before'] == 'U-15'
    assert not log.loc['16', 'participated'] and not log.loc['16', 'ascended']
    assert log.loc['17', 'category'] == 'U-15' and not log.loc['17', 'ascended'] and log.loc['17', 'highest_before'] == 'U-16'
    assert not log.loc['18', 'ascended'], 'volver a U-16 tras citarse y bajar a U-15 no es subir otra vez'


def test_a_category_outside_the_ladder_is_shown_but_never_counted_as_a_climb(dataset):
    last = adelantados.player_timeline(dataset, '6').set_index('matchid').loc['19']
    assert last['category'] == 'Amistoso' and last['participated']
    assert not last['ascended'] and last['highest_before'] == 'U-16'
    assert not last['ahead'], 'sin categoría reconocida no se sabe cuántos escalones sube'


def test_ahead_marks_every_match_in_a_category_above_the_age_category(dataset):
    log = adelantados.player_timeline(dataset, '6')
    assert log['steps_ahead'].iloc[:9].tolist() == [0, 0, 2, 1, 1, 2, 2, 1, 2]
    assert log['ahead'].tolist() == [False, False, True, True, True, True, True, True, True, False]


def test_unknown_player_gives_an_empty_timeline_with_the_same_columns(dataset):
    empty = adelantados.player_timeline(dataset, 'nadie')
    assert empty.empty
    assert {'ascended', 'highest_before', 'ascents', 'ahead'} <= set(empty.columns)


# --- Pantallas --------------------------------------------------------------------------------------------------------------

@pytest.fixture
def portal_data(monkeypatch):
    monkeypatch.syspath_prepend(str(Path('app').resolve()))
    for key, value in [('PORTAL_MODE', '1'), ('DB_SCHEMA', 'scouting'), ('DISABLE_SOFASCORE_UPDATE', '1')]:
        monkeypatch.setenv(key, value)
    import comet_context
    raw = raw_data()
    monkeypatch.setattr(comet_context, 'load_raw', lambda: raw)
    monkeypatch.setattr(comet_context, 'load_config', lambda: ({}, comet_context.EMPTY_MARKS, comet_context.EMPTY_PERIODS, None))
    monkeypatch.setattr(comet_context, 'now', lambda: comet_tiny.TODAY)
    import comet_matchlog
    return comet_matchlog


def run(page, **state):
    module, function = PAGES[page]
    app = AppTest.from_string(SCRIPT.format(module=module, function=function, admin=ADMIN), default_timeout=90)
    for key, value in state.items():
        app.session_state[key] = value
    app.run()
    assert not app.exception, [e.value for e in app.exception]
    return app


def log_table(app):
    tables = [df.value for df in app.dataframe if 'Subida de categoría' in df.value.columns]
    assert len(tables) == 1, 'una sola tabla de historial por pantalla'
    return tables[0]


def metrics(app):
    return {m.label: m.value for m in app.metric}


def captions(app):
    return [c.value for c in app.caption]


CLIMBS = ['Subió de U-14 a U-15 en su partido del 01-03-2026, temporada 2026.',
          'Subió de U-15 a U-16 en su partido del 03-05-2026, temporada 2026.']
ABOVE_AGE_NEWEST_FIRST = ['07-06-2026', '17-05-2026', '03-05-2026', '05-04-2026', '01-03-2026']


def test_player_sheet_lists_every_match_newest_first_with_the_climbs_marked(portal_data):
    app = run('Ficha del jugador', cp_player='6')
    table = log_table(app)
    assert len(table) == 10
    assert table['Fecha'].tolist()[0] == '14-06-2026' and table['Fecha'].tolist()[-1] == '01-02-2026'
    climbs = [mark for mark in table['Subida de categoría'] if mark.startswith('Subió')]
    assert climbs == ['Subió de U-15 a U-16', 'Subió de U-14 a U-15'], 'la más reciente primero'
    marks = dict(zip(table['Fecha'], table['Subida de categoría']))
    assert marks['01-03-2026'] == 'Subió de U-14 a U-15' and marks['03-05-2026'] == 'Subió de U-15 a U-16'
    roles = dict(zip(table['Fecha'], table['Rol']))
    assert (roles['01-02-2026'], roles['10-05-2026'], roles['03-05-2026']) == (
        'Titular', 'Suplente que no ingresó', 'Suplente que ingresó')
    shown = metrics(app)
    assert shown['Partidos en su historial'] == '10' and shown['Subidas de categoría'] == '2'
    assert shown['Partidos jugados'] == '7' and shown['Jugados por encima de su edad'] == '5'
    assert all(climb in captions(app) for climb in CLIMBS)
    assert any('Minutos jugados por encima de su edad: 305' in c for c in captions(app))


def test_player_sheet_shows_what_the_player_did_in_each_match(portal_data):
    table = log_table(run('Ficha del jugador', cp_player='6')).set_index('Fecha')
    assert table.loc['01-02-2026', 'Marcador final'] == '1-0' and table.loc['01-02-2026', 'Resultado final'] == 'Victoria'
    assert table.loc['01-02-2026', 'Minutos'] == 70 and table.loc['01-02-2026', 'Goles'] == 1
    assert table.loc['07-06-2026', 'Minutos'] == 90 and table.loc['07-06-2026', 'Goles'] == 2
    assert table.loc['05-04-2026', 'Amarillas'] == 1
    assert table.loc['03-05-2026', 'Categoría'] == 'U-16' and table.loc['03-05-2026', 'Le corresponde por edad'] == 'U-14'
    assert table.loc['03-05-2026', 'Por encima de su edad'] == 'Sí, +2'
    assert table.loc['01-02-2026', 'Por encima de su edad'] == 'No'
    assert table.loc['22-02-2026', 'Por encima de su edad'] == '—', 'citado en U-16 sin jugar: no jugó por encima de su edad'
    assert table.loc['14-06-2026', 'Por encima de su edad'] == '—', 'categoría fuera de la escalera: se desconoce'


def test_player_sheet_can_show_only_the_climbs_or_only_what_was_played_above_the_age(portal_data):
    app = run('Ficha del jugador', cp_player='6')
    app.radio(key='cp_log_filter').set_value(portal_data.ONLY_ASCENTS).run()
    assert not app.exception
    only_climbs = log_table(app)
    assert only_climbs['Fecha'].tolist() == ['03-05-2026', '01-03-2026']
    assert only_climbs['Subida de categoría'].tolist() == ['Subió de U-15 a U-16', 'Subió de U-14 a U-15']
    assert metrics(app)['Partidos en su historial'] == '10', 'el resumen sigue contando todo el historial'

    app.radio(key='cp_log_filter').set_value(portal_data.ONLY_ABOVE_AGE).run()
    assert log_table(app)['Fecha'].tolist() == ABOVE_AGE_NEWEST_FIRST, 'sin las citaciones ni el amistoso'

    app.radio(key='cp_log_filter').set_value(portal_data.ALL_MATCHES).run()
    assert len(log_table(app)) == 10, 'volver a «todos» devuelve cada partido'


def test_player_sheet_can_be_read_from_the_first_match_to_the_last(portal_data):
    app = run('Ficha del jugador', cp_player='6')
    app.radio(key='cp_log_order').set_value(portal_data.CHRONOLOGICAL).run()
    dates = log_table(app)['Fecha'].tolist()
    assert dates[0] == '01-02-2026' and dates[-1] == '14-06-2026'


def test_player_who_never_climbed_has_no_climb_marks(portal_data):
    app = run('Ficha del jugador', cp_player='7')
    assert metrics(app)['Subidas de categoría'] == '0' and metrics(app)['Partidos en su historial'] == '1'
    assert not any(c.startswith('Subió de') for c in captions(app))
    assert set(log_table(app)['Subida de categoría']) == {'—'}


def test_players_who_play_above_their_age_have_a_full_history_tab(portal_data):
    app = run('Jugadores adelantados')
    picker = app.selectbox(key='cd_log_player')
    assert picker.options[0].startswith('Jugador Seis · juega en U-15, U-16 (le corresponde U-14)'), picker.options
    assert len(picker.options) == 3, 'Jugador Seis, Jugador Dos (U-15) y Jugador Siete (U-16)'
    table = log_table(app)
    assert table['Fecha'].tolist()[0] == '01-02-2026', 'aquí se lee del primer partido al último'
    assert len(table) == 10 and all(climb in captions(app) for climb in CLIMBS)

    picker.select('7').run()
    assert not app.exception
    assert len(log_table(app)) == 1 and metrics(app)['Subidas de categoría'] == '0'


def test_the_history_tab_keeps_the_other_tabs_and_their_figures(portal_data):
    app = run('Jugadores adelantados')
    assert metrics(app)['Jugadores adelantados'] == '3'
    assert [t.label for t in app.tabs][-1] == 'Historial completo'
