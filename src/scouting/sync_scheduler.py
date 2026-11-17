"""Persistent Tuesday 06:15 UTC schedule for the isolated Docker worker."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from scouting.manual_sync import read, save
from scouting.sofascore_leagues import DEFAULT_LEAGUE

ROOT = Path(__file__).resolve().parents[2]
SHARED_LOCK = ROOT / DEFAULT_LEAGUE.folder / 'weekly.lock'


def next_run(now, *, league=DEFAULT_LEAGUE):
    now = now.astimezone(timezone.utc)
    slot = now.replace(hour=league.schedule_hour, minute=15, second=0, microsecond=0)
    slot += timedelta(days=(1 - now.weekday()) % 7)
    return slot if slot > now else slot + timedelta(days=7)


def worker_command(folder, *, league=DEFAULT_LEAGUE):
    return ['flock', '-n', '-E', '75', str(SHARED_LOCK), sys.executable,
            str(ROOT / 'scripts/manual_scouting_sync.py'), '--folder', str(folder),
            '--league', league.key,
            'weekly', '--apply', '--max-requests', '240', '--seconds', '1800']


def _validate_scope(state, league):
    if state.get('version') != 1 or state.get('league_key', DEFAULT_LEAGUE.key) != league.key:
        raise ValueError('Wrong scheduler scope/version')


def tick(folder, now, execute, *, league=DEFAULT_LEAGUE):
    path = Path(folder) / 'scheduler-state.json'
    if not path.exists():
        state = dict(version=1, league_key=league.key, status='waiting', next_run_at=next_run(now, league=league).isoformat())
        save(path, state)
        return state
    state = read(path)
    _validate_scope(state, league)
    if datetime.fromisoformat(state['next_run_at']) > now:
        return state
    # Persist the next slot BEFORE starting: restarting a blocked worker must not hammer the provider.
    state.pop('error_type', None)
    state.update(status='running', last_started_at=now.isoformat(), next_run_at=next_run(now, league=league).isoformat())
    save(path, state)
    try:
        code = execute()
    except Exception as exc:
        code = 1
        state['error_type'] = type(exc).__name__
    state.update(last_exit_code=code, last_finished_at=datetime.now(timezone.utc).isoformat(),
                 status={0: 'success', 2: 'blocked', 75: 'busy', 124: 'timeout', 130: 'interrupted'}.get(code, 'failed'))
    save(path, state)
    return state


def recover_interrupted(folder, *, league=DEFAULT_LEAGUE):
    path = Path(folder) / 'scheduler-state.json'
    if path.exists():
        state = read(path)
        _validate_scope(state, league)
        if state.get('status') == 'running':
            state.update(status='interrupted', last_exit_code=130,
                         last_finished_at=datetime.now(timezone.utc).isoformat())
            save(path, state)


def execute_worker(folder, stop, *, league=DEFAULT_LEAGUE):
    # A separate process group lets SIGTERM or the one-hour watchdog stop the complete worker tree.
    SHARED_LOCK.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(worker_command(folder, league=league), start_new_session=True)
    deadline = time.monotonic() + 3600
    while not stop.is_set() and time.monotonic() < deadline:
        try:
            return process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass
    result = 130 if stop.is_set() else 124
    try:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    except ProcessLookupError:
        process.wait()
    return result


def serve(folder, stop, *, league=DEFAULT_LEAGUE):
    recover_interrupted(folder, league=league)
    previous = None
    while not stop.is_set():
        state = tick(folder, datetime.now(timezone.utc), lambda: execute_worker(folder, stop, league=league), league=league)
        if state != previous:
            print(json.dumps(dict(event='scouting_scheduler', **state)), flush=True)
            previous = state.copy()
        stop.wait(30)
