import importlib
import sys
import time
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

from scouting.portal import accounts, security
from scouting.services import reports_service, attribute_ratings_service

ADMIN = dict(id='00000000-0000-0000-0000-000000000001', role='admin', active=True, revision=1, display_name='Admin')
SCOUT = dict(id='00000000-0000-0000-0000-000000000002', role='scout', active=True, revision=1, display_name='Scout')


@pytest.fixture
def portal(monkeypatch):
    monkeypatch.setenv('PORTAL_MODE', '1')


def test_context_never_leaks_between_sessions():
    with security.session_scope({}, verified_user=ADMIN):
        assert security.require_admin() == ADMIN
    with pytest.raises(PermissionError):
        security.require_admin()
    with security.session_scope({}, verified_user=SCOUT), pytest.raises(PermissionError):
        security.require_admin()


def test_tokens_checked_remotely_and_role_comes_from_database(monkeypatch):
    monkeypatch.setattr(accounts, '_auth', lambda *a, **kw: {'id': SCOUT['id'], 'user_metadata': {'role': 'admin'}})
    monkeypatch.setattr(accounts, 'get_user', lambda uid: SCOUT)
    token = dict(id=SCOUT['id'], revision=1, expires=time.time()+60, access_token='synthetic')
    assert accounts.resolve_session(token)['role'] == 'scout'
    assert accounts.resolve_session({**token, 'revision': 0}) is None
    assert accounts.resolve_session({**token, 'expires': 0}) is None
    assert accounts.resolve_session({**token, 'id': ADMIN['id']}) is None
    monkeypatch.setattr(accounts, 'get_user', lambda uid: {**SCOUT, 'active': False})
    assert accounts.resolve_session(token) is None


def test_owner_is_not_a_name_and_legacy_is_admin_only():
    with security.session_scope({}, verified_user=SCOUT):
        assert security.can_edit({'raw_payload': {'portal_owner_id': SCOUT['id']}})
        assert not security.can_edit({'scout_name': 'Scout', 'raw_payload': None})
        assert not security.can_edit({'raw_payload': {'portal_owner_id': ADMIN['id']}})
        assert security.can_edit({'raw_payload': {'portal_owner_id': SCOUT['id']}, 'is_hidden': True})
        assert security.can_edit({'raw_payload': None, 'is_hidden': True})
    with security.session_scope({}, verified_user=ADMIN):
        assert security.can_edit({'raw_payload': None})


def test_scout_cannot_mutate_another_report_or_delete_own(portal, monkeypatch):
    from scouting.repositories import reports_repository
    monkeypatch.setattr(reports_repository, 'get_report_by_id', lambda *a: {'raw_payload': {'portal_owner_id': ADMIN['id']}})
    write = Mock()
    monkeypatch.setattr(reports_repository, 'update_report_recommendation', write)
    with security.session_scope({}, verified_user=SCOUT):
        with pytest.raises(PermissionError):
            reports_service.update_report_recommendation(Mock(), 1, 'Interesante')
        for action in [reports_service.delete_report_permanently, reports_service.hide_report, reports_service.restore_report]:
            with pytest.raises(PermissionError):
                action(Mock(), 1)
        with pytest.raises(PermissionError):
            attribute_ratings_service.replace_attribute_ratings_for_report(Mock(), 1, [])
    write.assert_not_called()


def test_create_forces_authenticated_owner(portal, monkeypatch):
    from scouting.repositories import players_repository, reports_repository
    monkeypatch.setattr(players_repository, 'get_or_create_player', lambda *a, **kw: (7, True))
    create = Mock(return_value=12)
    monkeypatch.setattr(reports_repository, 'create_report', create)
    with security.session_scope({}, verified_user=SCOUT):
        reports_service.create_scouting_report_from_dict(Mock(), {'player_name':'Synthetic', 'scout_name':'Impostor', 'raw_payload':{'portal_owner_id':ADMIN['id']}})
    assert create.call_args.kwargs['scout_name'] == 'Scout'
    assert create.call_args.kwargs['raw_payload']['portal_owner_id'] == SCOUT['id']


def test_comet_guard_runs_before_cached_result_and_connection(monkeypatch):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
    comet = importlib.import_module('comet_dashboard')
    query = Mock(return_value=pd.DataFrame())
    monkeypatch.setattr(comet, 'load_data', query)
    with security.session_scope({}, verified_user=ADMIN):
        comet.get_categories_overview()
    before = query.call_count
    with security.session_scope({}, verified_user=SCOUT):
        for call in [comet.get_categories_overview, comet.get_db_connection, comet.page_executive_summary]:
            with pytest.raises(PermissionError):
                call()
    assert query.call_count == before


def test_auth_only_identity_is_denied(monkeypatch):
    monkeypatch.setattr(accounts, '_auth', lambda *a, **kw: {'user': {'id':SCOUT['id']}, 'access_token':'synthetic'})
    monkeypatch.setattr(accounts, 'get_user', lambda uid: None)
    assert accounts.authenticate('scout@example.test', 'synthetic') is None
