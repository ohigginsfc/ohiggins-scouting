"""Worker aislado: publicación, permisos por ámbito, fallos y modo de validación."""
import base64
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest
import requests

from scouting.comet_ingest import publisher, sync
from scouting.comet_ingest.api import CometAPI, Endpoint
from scouting.comet_ingest.db_pipeline.specs import SPECS
from scripts import sync_comet


def source_api():
    data = {}
    for table, name in sync.REPORTS.items():
        row = {column: 1 for column in SPECS[table].required}
        data.setdefault(name, {}).update(row)
    data['equipos_en_competencia']['club'] = 'Club ficticio'
    api = CometAPI(verbose=False)
    api.endpoints = [Endpoint(name, 'synthetic') for name in data]
    api.load_configured_endpoints = lambda: api.endpoints
    api.fetch_all = lambda: None
    api.datasets = {name: pd.DataFrame([row]) for name, row in data.items()}
    return api


def response(status=201, **headers):
    return Mock(status_code=status, headers=headers)


def test_dry_run_never_constructs_writer_or_sends_anything():
    factory = Mock(side_effect=AssertionError('writer instantiated'))
    summary = sync.run_sync(api=source_api(), publisher_factory=factory, out=lambda _: None)
    assert summary['mode'] == 'dry-run' and summary['rows_prepared'] == 12 and summary['rows_published'] == 0
    assert summary['complete'] and set(summary['tables']) == set(publisher.TABLES)
    factory.assert_not_called()


def test_complete_source_is_cleaned_before_first_write_and_parent_order_is_preserved():
    api = source_api()
    writer = Mock()
    writer.upsert.side_effect = lambda table, frame: len(frame)
    summary = sync.run_sync(dry_run=False, api=api, publisher_factory=lambda: writer, out=lambda _: None)
    assert [call.args[0] for call in writer.upsert.call_args_list] == list(publisher.TABLES)
    assert summary['complete'] and summary['rows_prepared'] == summary['rows_published'] == 12
    assert summary['tables']['competiciones']['cleaning']['source_rows'] == 1


@pytest.mark.parametrize('failure', ['download', 'contract', 'empty_catalog'])
def test_source_failure_or_empty_catalog_causes_zero_publication(failure):
    api = source_api()
    if failure == 'download':
        api.fetch_all = Mock(side_effect=RuntimeError('partial download'))
    elif failure == 'contract':
        api.datasets['eventos_de_partido'] = pd.DataFrame([{'unexpected': 1}])
    else:
        api.datasets['registro_de_personas'] = pd.DataFrame()
    factory = Mock()
    with pytest.raises((RuntimeError, ValueError)):
        sync.run_sync(dry_run=False, api=api, publisher_factory=factory)
    factory.assert_not_called()


def test_valid_empty_child_report_publishes_no_rows_in_that_table():
    api = source_api()
    api.datasets['eventos_de_partido'] = pd.DataFrame()
    summary = sync.run_sync(api=api, out=lambda _: None)
    assert summary['tables']['eventos_partido']['prepared'] == 0


def test_publication_error_stops_children_and_never_returns_success():
    writer = Mock()
    writer.upsert.side_effect = [1, RuntimeError('HTTP 403')]
    with pytest.raises(RuntimeError):
        sync.run_sync(dry_run=False, api=source_api(), publisher_factory=lambda: writer)
    assert writer.upsert.call_count == 2


def test_publisher_preserves_natural_key_text_nulls_dates_and_public_schema(monkeypatch):
    post = Mock(return_value=response())
    monkeypatch.setattr(publisher.requests, 'post', post)
    frame = pd.DataFrame([{'id': 1.0, 'clubId': 2.0, 'uid': 3.0, 'season': '005.0',
                           'lastupdateddatetime': pd.Timestamp('2026-01-01T00:00:00Z'), 'status': pd.NA}])
    writer = publisher.Publisher('https://example.invalid', 'private-token')
    assert 'private-token' not in repr(writer)
    assert writer.upsert('competidores', frame) == 1
    args, kwargs = post.call_args
    assert args == ('https://example.invalid/rest/v1/competidores',)
    assert kwargs['params'] == {'on_conflict': 'id,clubid'}
    assert kwargs['headers']['Content-Profile'] == 'public'
    assert kwargs['headers']['Prefer'] == 'resolution=merge-duplicates,return=minimal'
    assert kwargs['json'] == [{'id': 1, 'clubid': 2, 'uid': 3, 'season': '005.0',
                              'lastupdateddatetime': '2026-01-01T00:00:00+00:00', 'status': None}]


@pytest.mark.parametrize('status', [401, 403, 409, 400])
def test_auth_or_contract_error_is_not_retried_or_logged_with_body(monkeypatch, status):
    result = response(status)
    result.text = 'private-person private-token'
    post = Mock(return_value=result)
    monkeypatch.setattr(publisher.requests, 'post', post)
    with pytest.raises(RuntimeError) as failure:
        publisher.Publisher('https://example.invalid', 'private-token').upsert('competiciones', pd.DataFrame([{'id': 1}]))
    assert str(status) in str(failure.value) and 'private' not in str(failure.value)
    assert post.call_count == 1


def test_transient_retry_keeps_exact_idempotent_batch_and_respects_retry_after(monkeypatch):
    post = Mock(side_effect=[response(429, **{'Retry-After': '9'}), requests.Timeout('private-token'), response()])
    sleep = Mock()
    monkeypatch.setattr(publisher.requests, 'post', post)
    monkeypatch.setattr(publisher.time, 'sleep', sleep)
    written = publisher.Publisher('https://example.invalid', 'private-token').upsert('competiciones', pd.DataFrame([{'id': 1}]))
    assert written == 1 and post.call_count == 3
    assert [call.args[0] for call in sleep.call_args_list] == [9, 2]
    assert all(call.kwargs['json'] == [{'id': 1}] for call in post.call_args_list)


def test_retry_exhaustion_and_oversized_wait_are_failures(monkeypatch):
    post = Mock(return_value=response(503))
    monkeypatch.setattr(publisher.requests, 'post', post)
    monkeypatch.setattr(publisher.time, 'sleep', Mock())
    with pytest.raises(RuntimeError, match='HTTP 503'):
        publisher.Publisher('https://example.invalid', 'key', max_retries=1).upsert('competiciones', pd.DataFrame([{'id': 1}]))
    assert post.call_count == 2
    post.return_value = response(429, **{'Retry-After': '999'})
    post.reset_mock()
    with pytest.raises(RuntimeError, match='espera'):
        publisher.Publisher('https://example.invalid', 'key').upsert('competiciones', pd.DataFrame([{'id': 1}]))
    assert post.call_count == 1


@pytest.mark.parametrize('table', ['scouting.players', 'portal.accounts', 'players', 'jugadores;DROP TABLE'])
def test_worker_cannot_publish_outside_comet_tables(monkeypatch, table):
    post = Mock()
    monkeypatch.setattr(publisher.requests, 'post', post)
    with pytest.raises(ValueError, match='ámbito'):
        publisher.Publisher('https://example.invalid', 'key').upsert(table, pd.DataFrame([{'id': 1}]))
    post.assert_not_called()


def test_worker_cannot_use_the_portal_or_scout_credentials(monkeypatch):
    monkeypatch.delenv('COMET_SUPABASE_URL', raising=False)
    monkeypatch.delenv('COMET_SUPABASE_SERVICE_ROLE_KEY', raising=False)
    monkeypatch.setenv('SUPABASE_URL', 'https://example.invalid')
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY', 'old-alias-is-not-used')
    with pytest.raises(ValueError, match='COMET_SUPABASE'):
        publisher.Publisher.from_env()


def test_chunking_preserves_all_rows_and_a_partial_receipt_is_not_success(monkeypatch):
    post = Mock(return_value=response())
    monkeypatch.setattr(publisher.requests, 'post', post)
    assert publisher.Publisher('https://example.invalid', 'key').upsert('competiciones', pd.DataFrame({'id': range(5)}), chunk_size=2) == 5
    assert [len(call.kwargs['json']) for call in post.call_args_list] == [2, 2, 1]
    writer = Mock()
    writer.upsert.return_value = 0
    with pytest.raises(RuntimeError, match='incompleta'):
        sync.run_sync(dry_run=False, api=source_api(), publisher_factory=lambda: writer)


@pytest.mark.parametrize('delay', ['0', '-1', 'inf', 'NaN', '61', 'oops'])
def test_operational_download_cannot_accidentally_disable_pacing(monkeypatch, delay):
    monkeypatch.setenv('COMET_REQUEST_DELAY', delay)
    with pytest.raises(ValueError, match='COMET_REQUEST_DELAY'):
        sync.configured_api()


def test_cli_defaults_to_dry_run_and_summary_contains_only_aggregates(monkeypatch, tmp_path):
    run = Mock(return_value={'complete': True, 'rows_prepared': 12, 'rows_published': 0})
    monkeypatch.setattr(sync_comet, 'run_sync', run)
    path = tmp_path/'summary.json'
    assert sync_comet.main(['--summary-json', str(path)]) == 0
    assert run.call_args.kwargs['dry_run'] is True
    assert json.loads(path.read_text())['complete']
    assert sync_comet.main(['--publish']) == 0
    assert run.call_args.kwargs['dry_run'] is False


def test_cli_masks_unexpected_errors_and_returns_failure(monkeypatch, capsys):
    monkeypatch.setattr(sync_comet, 'run_sync', Mock(side_effect=TypeError('private-data private-token')))
    assert sync_comet.main([]) == 1
    assert 'private' not in capsys.readouterr().err


def test_sheet_reader_has_only_read_scope_and_no_write_methods(monkeypatch):
    # Fake SDKs verify the credential scope without importing live credentials.
    import sys
    from types import ModuleType
    from scouting.comet_ingest.sheets import GoogleSheets
    gs = ModuleType('gspread')
    gs.authorize = Mock(return_value=Mock())
    account = ModuleType('google.oauth2.service_account')
    account.Credentials = Mock()
    monkeypatch.setitem(sys.modules, 'gspread', gs)
    monkeypatch.setitem(sys.modules, 'google.oauth2.service_account', account)
    monkeypatch.setenv('GOOGLE_SV_B64', base64.b64encode(b'{"type":"service_account"}').decode())
    reader = GoogleSheets()
    assert account.Credentials.from_service_account_info.call_args.kwargs['scopes'] == ['https://www.googleapis.com/auth/spreadsheets.readonly']
    assert not hasattr(reader, 'write_df') and not hasattr(reader, 'insert_row')


def test_workflow_is_manual_by_default_and_has_no_legacy_email_or_report_side_effects():
    source = Path('.github/workflows/comet-sync.yml').read_text(encoding='utf8')
    assert "vars.COMET_SCHEDULE_ENABLED == 'true'" in source and 'cancel-in-progress: false' in source
    assert 'default: true' in source and 'refs/heads/$DEFAULT_BRANCH' in source
    assert all(text not in source for text in ('GMAIL_', 'generate_report.py', 'check_alerts.py', 'PGPASSWORD', 'SCOUTING_DATABASE_URL'))
