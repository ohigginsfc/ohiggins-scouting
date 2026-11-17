"""The background scheduler is tested with a clock and worker that do no I/O."""
from datetime import datetime, timezone
from threading import Event
from unittest.mock import MagicMock
import signal

import pytest

from scouting import sync_scheduler as scheduler


def utc(value):
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


@pytest.mark.parametrize('now, expected', [
    ('2026-11-16T10:00:00', '2026-11-17T06:15:00'),
    ('2026-11-17T06:14:59', '2026-11-17T06:15:00'),
    ('2026-11-17T06:15:00', '2026-11-24T06:15:00'),
    ('2026-11-18T10:00:00', '2026-11-24T06:15:00'),
])
def test_next_execution_is_tuesday_0615_utc(now, expected):
    assert scheduler.next_run(utc(now)) == utc(expected)


def test_initial_start_only_schedules_and_never_downloads(tmp_path):
    result = scheduler.tick(tmp_path, utc('2026-11-16T10:00:00'),
                            lambda: pytest.fail('download on startup'))
    assert result['next_run_at'] == utc('2026-11-17T06:15:00').isoformat()
    assert result['status'] == 'waiting'


def test_restart_keeps_the_existing_schedule(tmp_path):
    scheduler.tick(tmp_path, utc('2026-11-16T10:00:00'), lambda: None)
    result = scheduler.tick(tmp_path, utc('2026-11-17T06:14:00'),
                            lambda: pytest.fail('early download'))
    assert result['next_run_at'] == utc('2026-11-17T06:15:00').isoformat()


@pytest.mark.parametrize('exit_code,status', [(0, 'success'), (2, 'blocked'), (75, 'busy'), (1, 'failed'), (124, 'timeout')])
def test_due_job_runs_once_and_records_failure_without_immediate_retry(tmp_path, exit_code, status):
    scheduler.tick(tmp_path, utc('2026-11-16T10:00:00'), lambda: None)
    calls = []

    def execute():
        calls.append(True)
        # Advance the schedule before launching: a crash/restart must not start a retry loop.
        state = scheduler.read(tmp_path / 'scheduler-state.json')
        assert state['status'] == 'running'
        assert state['next_run_at'] == utc('2026-11-24T06:15:00').isoformat()
        return exit_code

    result = scheduler.tick(tmp_path, utc('2026-11-17T06:16:00'), execute)
    assert calls == [True] and result['status'] == status and result['last_exit_code'] == exit_code
    scheduler.tick(tmp_path, utc('2026-11-17T06:17:00'), lambda: pytest.fail('immediate retry'))


def test_missed_weeks_produce_only_one_catchup_run(tmp_path):
    scheduler.tick(tmp_path, utc('2026-10-01T00:00:00'), lambda: None)
    calls = []
    result = scheduler.tick(tmp_path, utc('2026-11-17T06:16:00'), lambda: calls.append(True) or 0)
    assert calls == [True]
    assert result['next_run_at'] == utc('2026-11-24T06:15:00').isoformat()


def test_worker_command_uses_the_shared_lock_and_bounded_weekly_publisher(tmp_path):
    command = scheduler.worker_command(tmp_path)
    assert command[:4] == ['flock', '-n', '-E', '75']
    assert command[4] == str(tmp_path / 'weekly.lock')
    assert command[-6:] == ['weekly', '--apply', '--max-requests', '240', '--seconds', '1800']


def test_crashed_worker_start_does_not_create_an_immediate_retry(tmp_path):
    scheduler.tick(tmp_path, utc('2026-11-16T10:00:00'), lambda: None)

    def fail():
        raise OSError('synthetic process failure')

    result = scheduler.tick(tmp_path, utc('2026-11-17T06:16:00'), fail)
    assert result['status'] == 'failed' and result['last_exit_code'] == 1
    scheduler.tick(tmp_path, utc('2026-11-17T06:17:00'), lambda: pytest.fail('restart storm'))


def test_restart_marks_the_interrupted_attempt_without_repeating_it(tmp_path):
    scheduler.save(tmp_path / 'scheduler-state.json', dict(version=1, status='running',
                   next_run_at=utc('2026-11-24T06:15:00').isoformat()))
    scheduler.recover_interrupted(tmp_path)
    result = scheduler.tick(tmp_path, utc('2026-11-17T07:00:00'), lambda: pytest.fail('crash retry'))
    assert result['status'] == 'interrupted' and result['last_exit_code'] == 130


def test_success_clears_the_previous_error_type(tmp_path):
    scheduler.save(tmp_path / 'scheduler-state.json', dict(version=1, status='failed', error_type='OSError',
                   next_run_at=utc('2026-11-17T06:15:00').isoformat()))
    result = scheduler.tick(tmp_path, utc('2026-11-17T07:00:00'), lambda: 0)
    assert result['status'] == 'success' and 'error_type' not in result


def test_worker_completion_returns_its_exit_code(monkeypatch, tmp_path):
    process = MagicMock()
    process.wait.return_value = 2
    popen = MagicMock(return_value=process)
    monkeypatch.setattr(scheduler.subprocess, 'Popen', popen)
    assert scheduler.execute_worker(tmp_path, Event()) == 2
    assert popen.call_args.kwargs['start_new_session'] is True


@pytest.mark.parametrize('stopping,exit_code', [(True, 130), (False, 124)])
def test_stop_and_watchdog_terminate_the_whole_worker_group(monkeypatch, tmp_path, stopping, exit_code):
    process = MagicMock(pid=12345)
    monkeypatch.setattr(scheduler.subprocess, 'Popen', lambda *a, **k: process)
    clock = iter([0, 3601])
    monkeypatch.setattr(scheduler.time, 'monotonic', lambda: next(clock))
    killed = []
    monkeypatch.setattr(scheduler.os, 'killpg', lambda pid, sig: killed.append((pid, sig)), raising=False)
    stop = Event()
    if stopping:
        stop.set()
    assert scheduler.execute_worker(tmp_path, stop) == exit_code
    assert killed == [(12345, signal.SIGTERM)]
