"""Exercise the real router against forged module state without cloud credentials."""
from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_scout_cannot_route_to_comet_or_administration(monkeypatch):
    monkeypatch.syspath_prepend(str(Path('app').resolve()))
    for key, value in [('PORTAL_MODE', '1'), ('DB_SCHEMA', 'scouting'), ('DISABLE_SOFASCORE_UPDATE', '1')]:
        monkeypatch.setenv(key, value)
    import portal
    user = dict(id='synthetic-scout', display_name='Scout', role='scout', active=True)
    monkeypatch.setattr(portal.accounts, 'resolve_session', lambda token: user)
    monkeypatch.setattr(portal, 'render_scouting', lambda user: portal.st.write('Scouting autorizado'))
    def forbidden():
        raise AssertionError('Restricted renderer invoked for scout')
    monkeypatch.setattr(portal, 'render_comet', forbidden)
    monkeypatch.setattr(portal, 'manage_accounts', forbidden)
    for module in ['COMET', 'Administración']:
        app = AppTest.from_string('import portal\nportal.main()')
        app.session_state['portal_session'] = {'synthetic': True}
        app.session_state['portal_module'] = module
        app.session_state['_portal_previous_module'] = module
        app.session_state['comet_cached_selection'] = 'sensitive-state'
        app.query_params['module'] = module
        app.run()
        assert not app.exception and not app.error
        assert app.radio(key='portal_module').options == ['Scouting']
        assert app.radio(key='portal_module').value == 'Scouting'
        assert 'comet_cached_selection' not in app.session_state
        assert not app.query_params
