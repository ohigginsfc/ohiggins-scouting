"""Hidden reports are readable by scouts, while mutations remain restricted."""
from contextlib import contextmanager
from datetime import datetime, date
from pathlib import Path
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from scouting.portal import accounts, security
from scouting.repositories import reports_repository, attribute_ratings_repository
from scouting.services import reports_service, attribute_ratings_service


ADMIN = dict(id='synthetic-admin', display_name='Admin', role='admin', active=True)
SCOUT = dict(id='synthetic-scout', display_name='Scout', role='scout', active=True)
REPORT = dict(
    id=7, player_full_name='Jugador de prueba', player_position='Delantero',
    scout_name='Scout', report_date=date(2026, 10, 1), is_hidden=True,
    hidden_at=datetime(2026, 10, 2), hidden_by='Admin', rating=7,
    recommendation='Interesante', summary='Resumen de prueba',
    strengths='Fortaleza de prueba', weaknesses='Aspecto de prueba',
    match_observed='Partido de prueba', minutes_observed=60,
    raw_payload={'portal_owner_id': SCOUT['id']},
)


@pytest.fixture(autouse=True)
def portal_mode(monkeypatch):
    monkeypatch.setenv('PORTAL_MODE', '1')


@pytest.mark.parametrize('user', [SCOUT, ADMIN])
def test_authenticated_roles_can_count_and_read_hidden_reports(monkeypatch, user):
    count = Mock(return_value=49)
    read = Mock(return_value=[REPORT])
    monkeypatch.setattr(reports_repository, 'count_hidden_reports', count)
    monkeypatch.setattr(reports_repository, 'get_hidden_reports', read)
    conn = object()
    with security.session_scope({}, verified_user=user):
        assert reports_service.count_hidden_reports(conn) == 49
        assert reports_service.fetch_hidden_reports(conn, limit=200) == [REPORT]
    count.assert_called_once_with(conn)
    read.assert_called_once_with(conn, limit=200)


@pytest.mark.parametrize('user', [None, {**SCOUT, 'active': False}])
def test_invalid_sessions_cannot_read_hidden_reports(monkeypatch, user):
    monkeypatch.setattr(accounts, 'resolve_session', lambda token: user)
    count, read = Mock(), Mock()
    monkeypatch.setattr(reports_repository, 'count_hidden_reports', count)
    monkeypatch.setattr(reports_repository, 'get_hidden_reports', read)
    with security.session_scope({}, verified_user=user):
        for action in [reports_service.count_hidden_reports, reports_service.fetch_hidden_reports]:
            with pytest.raises(PermissionError):
                action(object())
    count.assert_not_called()
    read.assert_not_called()


@pytest.mark.parametrize('operation', ['edit', 'recommendation', 'hide', 'restore', 'delete', 'attributes', 'replace_attributes'])
def test_scout_cannot_mutate_even_own_hidden_report(monkeypatch, operation):
    monkeypatch.setattr(reports_repository, 'get_report_by_id', lambda *args: REPORT)
    writes = []
    for repository, names in [
        (reports_repository, ['update_report', 'update_report_recommendation', 'hide_report', 'restore_report', 'delete_report_permanently']),
        (attribute_ratings_repository, ['create_attribute_rating', 'delete_attribute_ratings_by_report']),
    ]:
        for name in names:
            write = Mock()
            monkeypatch.setattr(repository, name, write)
            writes.append(write)
    conn = object()
    actions = {
        'edit': lambda: reports_service.update_report(conn, 7, summary='Changed'),
        'recommendation': lambda: reports_service.update_report_recommendation(conn, 7, 'Prioritario'),
        'hide': lambda: reports_service.hide_report(conn, 7),
        'restore': lambda: reports_service.restore_report(conn, 7),
        'delete': lambda: reports_service.delete_report_permanently(conn, 7),
        'attributes': lambda: attribute_ratings_service.save_attribute_ratings_for_report(conn, 7, []),
        'replace_attributes': lambda: attribute_ratings_service.replace_attribute_ratings_for_report(conn, 7, []),
    }
    with security.session_scope({}, verified_user=SCOUT), pytest.raises(PermissionError):
        actions[operation]()
    for write in writes:
        write.assert_not_called()


@pytest.mark.parametrize('user', [SCOUT, ADMIN])
def test_real_portal_renders_hidden_details_with_role_specific_actions(monkeypatch, user):
    monkeypatch.syspath_prepend(str(Path('app').resolve()))
    monkeypatch.setenv('DB_SCHEMA', 'scouting')
    monkeypatch.setenv('DISABLE_SOFASCORE_UPDATE', '1')
    import portal
    import streamlit_app

    @contextmanager
    def connection():
        yield object()

    monkeypatch.setattr(portal.accounts, 'resolve_session', lambda token: user)
    monkeypatch.setattr(streamlit_app, 'get_connection', connection)
    read = Mock(return_value=[REPORT])
    ratings = Mock(return_value=[dict(attribute_group='Técnica', attribute_name='Pase', rating=7, max_rating=10, notes='Nota de prueba')])
    monkeypatch.setattr(reports_repository, 'get_hidden_reports', read)
    monkeypatch.setattr(attribute_ratings_repository, 'get_attribute_ratings_by_report', ratings)
    app = AppTest.from_string('import portal\nportal.main()', default_timeout=20)
    app.session_state['portal_session'] = {'synthetic': True}
    app.session_state['portal_module'] = 'Scouting'
    app.session_state['_portal_previous_module'] = 'Scouting'
    app.session_state['page'] = 'Informes ocultos'
    app.run()

    assert not app.exception and not app.error
    assert app.button(key='nav_informes_ocultos')
    assert 'Jugador de prueba' in app.selectbox(key='hidden_selected_report_label').value
    text = '\n'.join(element.value for element in app.markdown)
    assert 'Resumen de prueba' in text and 'Fortaleza de prueba' in text and 'Aspecto de prueba' in text
    assert app.dataframe[-1].value.iloc[0]['attribute_name'] == 'Pase'
    keys = {button.key for button in app.button}
    if user['role'] == 'scout':
        assert 'hidden_restore_report' not in keys
        assert 'hidden_delete_permanent_7' not in keys
        assert not app.checkbox
        assert app.radio(key='portal_module').options == ['Scouting']
    else:
        assert 'hidden_restore_report' in keys
        assert 'hidden_delete_permanent_7' in keys
        assert app.button(key='hidden_delete_permanent_7').disabled
        assert app.checkbox(key='hidden_confirm_delete_7')
    read.assert_called_once()
    ratings.assert_called_once()
