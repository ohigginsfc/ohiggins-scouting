"""Una base COMET vacía o incompleta muestra avisos claros; no rompe ninguna pantalla."""
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from scouting.comet import alerts, metrics
from scouting.comet.facts import (GOALKEEPER_COLUMNS, MATCH_COLUMNS, PLAYER_COLUMNS, SHEET_COLUMNS, build_dataset)
from tests import comet_tiny
from tests.test_comet_pages import ADMIN, PAGES, SCRIPT


def empty(columns):
    return pd.DataFrame({c: pd.Series(dtype='object') for c in columns})


def raw_empty():
    return dict(sheet=empty(SHEET_COLUMNS), matches=empty(MATCH_COLUMNS), players=empty(PLAYER_COLUMNS),
                goalkeepers=empty(GOALKEEPER_COLUMNS))


def raw_matches_without_sheets():
    tiny = comet_tiny.build()
    return dict(sheet=empty(SHEET_COLUMNS), matches=tiny['matches'], players=empty(PLAYER_COLUMNS),
                goalkeepers=empty(GOALKEEPER_COLUMNS))


def raw_sheets_without_players_or_keepers():
    tiny = comet_tiny.build()
    return dict(sheet=tiny['sheet'], matches=tiny['matches'], players=empty(PLAYER_COLUMNS),
                goalkeepers=empty(GOALKEEPER_COLUMNS))


CASES = {'vacía': raw_empty, 'partidos sin planillas': raw_matches_without_sheets,
         'planillas sin fichas ni arqueros': raw_sheets_without_players_or_keepers}


@pytest.mark.parametrize('case', list(CASES))
def test_calculations_do_not_fail_with_missing_tables(case):
    raw = CASES[case]()
    ds = build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers'])
    comp = metrics.add_percentages(metrics.player_competition_summary(ds))
    cat = metrics.category_summary(comp)
    for season in ds.seasons or [2026]:
        alerts.evaluate_alerts(ds, cat, season)
    assert metrics.principal_categories(cat) is not None


@pytest.mark.parametrize('case', list(CASES))
@pytest.mark.parametrize('page', list(PAGES))
def test_screens_render_with_missing_tables(monkeypatch, case, page):
    monkeypatch.syspath_prepend(str(Path('app').resolve()))
    for key, value in [('PORTAL_MODE', '1'), ('DB_SCHEMA', 'scouting'), ('DISABLE_SOFASCORE_UPDATE', '1')]:
        monkeypatch.setenv(key, value)
    import comet_context
    raw = CASES[case]()
    monkeypatch.setattr(comet_context, 'load_raw', lambda: raw)
    monkeypatch.setattr(comet_context, 'load_config', lambda: (
        {}, comet_context.EMPTY_MARKS, comet_context.EMPTY_PERIODS, 'sin configuración'))
    monkeypatch.setattr(comet_context, 'now', lambda: comet_tiny.TODAY)
    module, function = PAGES[page]
    app = AppTest.from_string(SCRIPT.format(module=module, function=function, admin=ADMIN), default_timeout=90).run()
    assert not app.exception, [e.value for e in app.exception]
    assert not app.error, [e.value for e in app.error]
