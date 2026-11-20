"""Exercise the real Streamlit selector with synthetic data and no database access."""
from contextlib import contextmanager
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from scouting.sofascore_leagues import LEAGUES


@pytest.fixture
def explorer(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / 'app'))
    monkeypatch.setenv('SOFASCORE_ACTIVE_SEASON','2026')
    import streamlit_app as ui
    @contextmanager
    def connection():
        yield object()
    monkeypatch.setattr(ui,'get_connection',connection)
    published = ['Primera División Chile','Primera B Chile']
    monkeypatch.setattr(ui.metrics_service,'get_objective_data_filter_options',lambda conn: dict(
        seasons=['2026'] if published else [],competitions=published,positions=[],teams=[]))
    queries=[]
    monkeypatch.setattr(ui.metrics_service,'get_objective_players_summary',
                        lambda conn,**kw: queries.append(kw) or [])
    app=AppTest.from_string('import streamlit_app\nstreamlit_app._render_objective_explorer()',default_timeout=30)
    return app,published,queries


def test_selector_exposes_all_regional_leagues_and_marks_unpublished_ones(explorer):
    app,published,_=explorer
    app.run()
    assert not app.exception
    choices=app.selectbox(key='obj_simple_competition').options
    assert 'Primera B Chile' in choices
    for key in ('ar_primera','ar_primera_nacional','uy_primera'):
        assert LEAGUES[key].competition + ' · pendiente' in choices
    app.selectbox(key='obj_simple_competition').set_value(LEAGUES['ar_primera'].competition).run()
    assert not app.exception
    assert any('pendientes de publicación' in x.value for x in app.info)


def test_published_league_selection_filters_query_by_exact_database_name(explorer):
    app,published,queries=explorer
    published.append(LEAGUES['ar_primera'].competition)
    app.run()
    assert LEAGUES['ar_primera'].competition in app.selectbox(key='obj_simple_competition').options
    app.selectbox(key='obj_simple_competition').set_value(LEAGUES['ar_primera'].competition).run()
    assert not app.exception
    assert queries[-1]['competition'] == LEAGUES['ar_primera'].competition
    assert queries[-1]['season'] == '2026'


def test_league_selector_is_available_before_the_first_publication(explorer):
    app,published,queries=explorer
    published.clear()
    app.run()
    assert not app.exception
    assert LEAGUES['uy_primera'].competition + ' · pendiente' in app.selectbox(key='obj_simple_competition').options
    queries.clear()
    app.selectbox(key='obj_simple_competition').set_value(LEAGUES['uy_primera'].competition).run()
    assert not queries  # never substitute another league's data for a pending league
