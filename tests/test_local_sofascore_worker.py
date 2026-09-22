"""Native worker contract exercised with a real child Python process, no network."""
import json
import sys
import pytest
from scouting.services import sofascore_incremental_runner as runner


@pytest.fixture
def local_worker(tmp_path, monkeypatch):
    monkeypatch.setenv('SOFASCORE_WORKER_MODE', 'local')
    monkeypatch.setattr(runner, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setattr(runner, 'LOG_DIR', tmp_path / 'logs')
    monkeypatch.setattr(runner, 'LOCK_PATH', tmp_path / 'sync.lock')
    monkeypatch.setattr(runner, 'UI_STATE_PATH', tmp_path / 'state.json')
    (tmp_path / 'scripts').mkdir()
    script = tmp_path / 'scripts/update_sofascore_incremental.py'
    return script


def test_local_worker_executes_direct_import_and_validates_summary(local_worker):
    payload = {'ok':True,'leagues':[{'slug':'synthetic','errors':0,'pending_total':0,'total_calendar':1}]}
    local_worker.write_text("import os,json\nassert os.environ['SOFASCORE_IMPORT_MODE']=='direct'\nprint('SOFASCORE_INCREMENTAL_JSON='+" + repr(json.dumps(payload)) + ")\n",encoding='utf-8')
    result = runner._execute_worker(['--json-summary'],log_suffix='test',timeout_sec=5)
    assert result.ok and result.json_payload == payload
    assert not runner.LOCK_PATH.exists()
    assert runner.check_worker_runtime().ok
    assert runner.build_worker_command([])[0] == sys.executable


@pytest.mark.parametrize('body', ["print('no summary')", "raise SystemExit(2)"])
def test_local_worker_failure_is_not_success(local_worker, body):
    local_worker.write_text(body,encoding='utf-8')
    result=runner._execute_worker(['--json-summary'],log_suffix='test',timeout_sec=5)
    assert not result.ok
    assert not runner.LOCK_PATH.exists()


def test_local_worker_timeout_clears_owned_lock(local_worker):
    local_worker.write_text('import time; time.sleep(5)',encoding='utf-8')
    result=runner._execute_worker(['--json-summary'],log_suffix='timeout',timeout_sec=0.1)
    assert not result.ok
    assert not runner.LOCK_PATH.exists()

@pytest.mark.parametrize('status', [403, 429])
def test_http_mode_reports_provider_error_without_browser_fallback(monkeypatch, status):
    import importlib.util
    from pathlib import Path
    from unittest.mock import Mock
    root=Path(__file__).resolve().parents[1]/'web_scraping_sofascore'
    monkeypatch.syspath_prepend(str(root))
    spec=importlib.util.spec_from_file_location('local_http_scraper',root/'sofascore_scraper.py')
    mod=importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules,spec.name,mod)
    spec.loader.exec_module(mod)
    monkeypatch.setenv('SOFASCORE_FETCH_MODE','http')
    get=Mock(return_value=Mock(status_code=status))
    monkeypatch.setattr(mod.std_requests,'get',get)
    with pytest.raises(RuntimeError,match=f'HTTP {status}'):
        mod.fetch_json('https://example.invalid/calendar',delay=0)
    get.assert_called_once()
