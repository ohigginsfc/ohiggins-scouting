"""Rankings por categoría: el control «Mostrar» va de 0 hasta todos los jugadores (petición del 30-10-2026)."""
import pytest

from scouting.comet import metrics
from scouting.comet.facts import build_dataset
from tests import comet_tiny
from tests.comet_tiny import sheet_row
from tests.test_comet_review_fixes import render, screen_env, summaries  # noqa: F401  (fixture de pantallas)

SLIDER = 'cr_top_2026_U-15'


def minute_table(app):
    """Tabla del ranking de minutos (la primera pestaña es la primera tabla de la pantalla)."""
    return app.dataframe[0].value


def test_top_zero_is_nobody_and_none_is_everybody():
    raw = comet_tiny.build()
    _, cat = summaries(build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers']))
    scope = dict(category='U-15', season_year=2026)
    assert len(metrics.ranking(cat, 'Minutos jugados', **scope)) == 3
    assert len(metrics.ranking(cat, 'Minutos jugados', top=None, **scope)) == 3
    assert metrics.ranking(cat, 'Minutos jugados', top=0, **scope).empty, '0 es ningún jugador, no todos'
    assert metrics.ranking(cat, 'Minutos jugados', top=-3, **scope).empty
    assert metrics.ranking(cat, 'Minutos jugados', top=2, **scope)['personid'].tolist() == ['2', '3']
    assert len(metrics.ranking(cat, 'Minutos jugados', top=99, **scope)) == 3, 'pedir más de los que hay devuelve todos'


def test_the_slider_goes_from_zero_to_all_and_starts_on_all_when_there_are_few_players(screen_env):  # noqa: F811
    screen_env(comet_tiny.build())
    app = render('comet_followup', 'page_rankings')
    assert not app.exception, [e.value for e in app.exception]
    slider = app.select_slider(key=SLIDER)
    assert slider.options == ['0', '1', '2', '3', 'Todos'], 'U-15 2026 tiene 4 jugadores: de 0 a todos'
    assert slider.value == 4, 'con pocos jugadores arranca en «Todos» (la última posición)'
    assert minute_table(app)['Jugador'].tolist() == ['Jugador Dos', 'Arquero Tres', 'Jugador Uno'], \
        'por defecto muestra a todos los que tienen minutos'


@pytest.mark.parametrize('shown, expected', [(2, ['Jugador Dos', 'Arquero Tres']), (1, ['Jugador Dos'])])
def test_choosing_a_number_limits_every_ranking(screen_env, shown, expected):  # noqa: F811
    screen_env(comet_tiny.build())
    app = render('comet_followup', 'page_rankings')
    app.select_slider(key=SLIDER).set_value(shown).run()
    assert not app.exception, [e.value for e in app.exception]
    assert minute_table(app)['Jugador'].tolist() == expected
    assert all(len(table.value) <= shown for table in app.dataframe), 'todas las pestañas respetan el tope'


def test_zero_shows_no_player_and_says_so_instead_of_claiming_there_is_no_data(screen_env):  # noqa: F811
    screen_env(comet_tiny.build())
    app = render('comet_followup', 'page_rankings')
    app.select_slider(key=SLIDER).set_value(0).run()
    assert not app.exception, [e.value for e in app.exception]
    assert len(app.dataframe) == 0
    notes = [i.value for i in app.info]
    assert any('Mostrando 0 jugadores' in n for n in notes)
    assert not any('Nadie tiene datos' in n for n in notes), '0 jugadores no es «sin datos»'


def test_players_left_out_for_contradictory_rows_do_not_count_in_the_total(screen_env):  # noqa: F811
    screen_env(comet_tiny.build(extra_sheet=[sheet_row(3, 2, True, True, 70)]))   # P2 con dos renglones distintos
    app = render('comet_followup', 'page_rankings')
    assert not app.exception, [e.value for e in app.exception]
    assert app.select_slider(key=SLIDER).options == ['0', '1', '2', 'Todos'], 'P2 no entra en los rankings'
    assert any('no entran en los rankings' in w.value for w in app.warning)


def test_the_slider_starts_on_twenty_when_there_are_more_players(screen_env):  # noqa: F811
    players = [dict(personid=p, displayname=f'Extra {p}', dateofbirth='2011-02-02', nationality='Chile', level='F',
                    status='ACTIVO', orgname='O') for p in range(10, 40)]
    sheet = [sheet_row(1, p, True, False, 10 + p) for p in range(10, 40)]
    screen_env(comet_tiny.build(extra_players=players, extra_sheet=sheet))        # 34 jugadores en U-15
    app = render('comet_followup', 'page_rankings')
    assert not app.exception, [e.value for e in app.exception]
    slider = app.select_slider(key=SLIDER)
    assert slider.options[0] == '0' and slider.options[-1] == 'Todos' and len(slider.options) == 35
    assert len(minute_table(app)) == 20, 'con muchos jugadores arranca en 20, no en todos'
    slider.set_value(34).run()
    assert len(minute_table(app)) == 33, 'todos los que tienen minutos (4 sin ellos: P4 no jugó)'
