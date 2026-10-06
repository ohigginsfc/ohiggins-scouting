"""Both roles manage hidden reports; visible ownership and COMET stay protected."""
from contextlib import contextmanager
from datetime import datetime, date
from pathlib import Path
from unittest.mock import Mock, MagicMock
import os

import psycopg
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
@pytest.mark.parametrize('hidden', [True, False])
def test_hidden_management_does_not_grant_access_to_another_visible_report(monkeypatch, operation, hidden):
    report = {**REPORT, 'is_hidden': hidden, 'raw_payload': {'portal_owner_id': ADMIN['id']}}
    monkeypatch.setattr(reports_repository, 'get_report_by_id', lambda *args: report)
    writes = []
    for repository, names in [
        (reports_repository, ['update_report_fields', 'update_report_recommendation', 'hide_report', 'restore_report', 'delete_report_permanently']),
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
        'attributes': lambda: attribute_ratings_service.save_attribute_ratings_for_report(conn, 7, [dict(attribute_group='Técnica', attribute_name='Pase', rating=3)]),
        'replace_attributes': lambda: attribute_ratings_service.replace_attribute_ratings_for_report(conn, 7, [dict(attribute_group='Técnica', attribute_name='Pase', rating=3)]),
    }
    with security.session_scope({}, verified_user=SCOUT):
        if hidden:
            actions[operation]()
            assert any(write.called for write in writes)
        else:
            with pytest.raises(PermissionError):
                actions[operation]()
            for write in writes:
                write.assert_not_called()


@pytest.mark.parametrize('action', ['hide_report', 'restore_report', 'delete_report_permanently'])
def test_scout_cannot_manage_visible_report_even_when_owned(monkeypatch, action):
    monkeypatch.setattr(reports_repository, 'get_report_by_id', lambda *args: {**REPORT, 'is_hidden': False})
    write = Mock()
    monkeypatch.setattr(reports_repository, action, write)
    with security.session_scope({}, verified_user=SCOUT), pytest.raises(PermissionError):
        getattr(reports_service, action)(object(), 7)
    write.assert_not_called()


@pytest.mark.parametrize('user', [None, {**SCOUT, 'active': False}])
@pytest.mark.parametrize('action', ['hide_report', 'restore_report', 'delete_report_permanently'])
def test_invalid_session_cannot_manage_hidden_reports(monkeypatch, user, action):
    monkeypatch.setattr(accounts, 'resolve_session', lambda token: user)
    monkeypatch.setattr(reports_repository, 'get_report_by_id', Mock(return_value=REPORT))
    write = Mock()
    monkeypatch.setattr(reports_repository, action, write)
    with security.session_scope({}, verified_user=user), pytest.raises(PermissionError):
        getattr(reports_service, action)(object(), 7)
    write.assert_not_called()


def test_edit_updates_only_supplied_fields_without_erasing_ownership():
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    reports_repository.update_report_fields(conn, 7, summary='Changed', recommendation='Prioritario')
    statement, values = cursor.execute.call_args.args
    assert statement.as_string() == 'UPDATE scouting_reports SET "summary" = %s, "recommendation" = %s WHERE id = %s'
    assert values == ('Changed', 'Prioritario', 7)
    conn.commit.assert_called_once()


def test_partial_edit_preserves_unedited_columns_in_postgres():
    dsn = os.environ.get('SCOUTING_TEST_DATABASE_URL')
    if not dsn:
        pytest.skip('Disposable PostgreSQL not configured')
    params = psycopg.conninfo.conninfo_to_dict(dsn)
    if params.get('host') not in ('127.0.0.1', 'localhost') or params.get('dbname') != 'scouting_test':
        pytest.fail('This test requires loopback database scouting_test')
    with psycopg.connect(dsn) as conn:
        conn.execute('CREATE TEMP TABLE scouting_reports (id int PRIMARY KEY, source_type text NOT NULL, summary text, scout_name text, raw_payload jsonb, rating numeric, is_hidden boolean)')
        conn.execute("INSERT INTO scouting_reports VALUES (7, 'manual', 'Original', 'Autor original', '{\"portal_owner_id\":\"original\"}', 3.5, true)")
        reports_repository.update_report_fields(conn, 7, summary='Editado')
        row = conn.execute('SELECT summary, source_type, scout_name, raw_payload, rating, is_hidden FROM scouting_reports WHERE id=7').fetchone()
        assert row[0:4] == ('Editado', 'manual', 'Autor original', {'portal_owner_id': 'original'})
        assert float(row[4]) == 3.5 and row[5] is True


def test_hidden_edit_cannot_change_owner_or_hidden_state(monkeypatch):
    monkeypatch.setattr(reports_repository, 'get_report_by_id', lambda *args: REPORT)
    conn = Mock()
    with security.session_scope({}, verified_user=SCOUT):
        with pytest.raises(ValueError):
            reports_service.update_report(conn, 7, raw_payload={'portal_owner_id': ADMIN['id']})
        with pytest.raises(ValueError):
            reports_service.update_report(conn, 7, is_hidden=False)
    conn.cursor.assert_not_called()


@pytest.mark.parametrize('user', [SCOUT, ADMIN])
@pytest.mark.parametrize('action', ['view', 'edit', 'restore', 'delete'])
def test_real_portal_allows_hidden_management_for_both_roles(monkeypatch, user, action):
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
    report = {**REPORT, 'raw_payload': None}
    read = Mock(return_value=[report])
    ratings = Mock(return_value=[dict(attribute_group='Técnica', attribute_name='Pase', rating=7, max_rating=10, notes='Nota de prueba')])
    monkeypatch.setattr(reports_repository, 'get_hidden_reports', read)
    monkeypatch.setattr(reports_repository, 'get_report_by_id', lambda *args: report)
    monkeypatch.setattr(attribute_ratings_repository, 'get_attribute_ratings_by_report', ratings)
    edit = Mock()
    monkeypatch.setattr(reports_repository, 'update_report_fields', edit)
    def restored(*args):
        report['is_hidden'] = False
        read.return_value = []
    restore = Mock(side_effect=restored)
    monkeypatch.setattr(reports_repository, 'restore_report', restore)
    def deleted(*args):
        read.return_value = []
        return True
    delete = Mock(side_effect=deleted)
    monkeypatch.setattr(reports_repository, 'delete_report_permanently', delete)
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
    assert 'hidden_restore_report' in keys
    assert 'hidden_delete_permanent_7' in keys
    assert any(button.label == 'Guardar cambios' for button in app.button)
    assert app.button(key='hidden_delete_permanent_7').disabled
    assert app.checkbox(key='hidden_confirm_delete_7')
    if user['role'] == 'scout':
        assert app.radio(key='portal_module').options == ['Scouting']
    read.assert_called_once()
    ratings.assert_called_once()
    edit.assert_not_called()
    restore.assert_not_called()
    delete.assert_not_called()
    if action == 'edit':
        app.text_area(key='hidden_edit_7_summary').set_value('Resumen editado')
        next(button for button in app.button if button.label == 'Guardar cambios').click().run()
        assert edit.call_args.args[1] == 7
        assert edit.call_args.kwargs == dict(summary='Resumen editado', strengths=REPORT['strengths'],
                                            weaknesses=REPORT['weaknesses'], recommendation='Interesante')
    elif action == 'restore':
        app.button(key='hidden_restore_report').click().run()
        restore.assert_called_once()
        if user['role'] == 'scout':
            with security.session_scope({}, verified_user=user):
                assert not security.can_edit(report), 'restored migrated report becomes admin-only again'
    elif action == 'delete':
        app.checkbox(key='hidden_confirm_delete_7').check().run()
        assert not app.button(key='hidden_delete_permanent_7').disabled
        app.button(key='hidden_delete_permanent_7').click().run()
        delete.assert_called_once()
    assert not app.exception and not app.error
