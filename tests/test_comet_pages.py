"""Renderiza cada pantalla COMET nueva con datos ficticios y sin credenciales de la nube."""
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from scripts import comet_demo_data

ADMIN = dict(id='00000000-0000-0000-0000-000000000001', role='admin', active=True, revision=1,
             display_name='Admin', username='admin@example.test')

PAGES = {
    'Partido semanal': ('comet_followup', 'page_weekly_match'),
    'Rankings por categoría': ('comet_followup', 'page_rankings'),
    'Ficha del jugador': ('comet_followup', 'page_player'),
    'Indicadores': ('comet_insights', 'page_indicators'),
    'Alertas': ('comet_insights', 'page_alerts'),
    'Jugadores adelantados': ('comet_insights', 'page_adelantados'),
    'Seguimiento y configuración': ('comet_insights', 'page_tracking'),
}

SCRIPT = '''
import {module}
from scouting.portal import security
ADMIN = {admin!r}
with security.session_scope({{}}, verified_user=ADMIN):
    {module}.{function}()
'''


@pytest.fixture(scope='module')
def raw():
    return comet_demo_data.build_raw()


@pytest.fixture
def comet_env(monkeypatch, raw):
    monkeypatch.syspath_prepend(str(Path('app').resolve()))
    for key, value in [('PORTAL_MODE', '1'), ('DB_SCHEMA', 'scouting'), ('DISABLE_SOFASCORE_UPDATE', '1')]:
        monkeypatch.setenv(key, value)
    import comet_context
    monkeypatch.setattr(comet_context, 'load_raw', lambda: raw)
    monkeypatch.setattr(comet_context, 'load_config', lambda: (
        {}, comet_context.EMPTY_MARKS, comet_context.EMPTY_PERIODS, 'Falta aplicar db/portal/003_comet_followup.sql en Supabase.'))
    monkeypatch.setattr(comet_context, 'now', lambda: comet_demo_data.TODAY)
    return comet_context


def render(page: str) -> AppTest:
    module, function = PAGES[page]
    app = AppTest.from_string(SCRIPT.format(module=module, function=function, admin=ADMIN), default_timeout=90)
    return app.run()


@pytest.mark.parametrize('page', list(PAGES))
def test_page_renders_for_admin_without_exceptions(comet_env, page):
    app = render(page)
    assert not app.exception, [e.value for e in app.exception]
    assert not app.error, [e.value for e in app.error]


def test_weekly_match_shows_every_sheet_block(comet_env):
    app = render('Partido semanal')
    text = ' '.join(m.value for m in app.markdown)
    for block in ['Titulares', 'Suplentes que ingresaron', 'Suplentes que no ingresaron',
                  'No citados que no participaron', 'Goles recibidos por arquero']:
        assert block in text
    assert app.selectbox(key='cw_match').options, 'debe ofrecer los partidos de la semana'


def test_pending_rules_are_labelled_as_assumptions_not_approved(comet_env):
    app = render('Rankings por categoría')
    notes = ' '.join(m.value for m in app.markdown if 'cm-note' in m.value)
    assert 'pendiente de confirmar' in notes
    assert 'aprobada' not in notes.lower()


def test_tracking_screen_degrades_without_store(comet_env):
    app = render('Seguimiento y configuración')
    assert any('003_comet_followup.sql' in w.value for w in app.warning)
    assert all(b.disabled for b in app.button if b.label.startswith('Guardar'))
