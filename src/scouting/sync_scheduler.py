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

ROOT = Path(__file__).resolve().parents[2]


def next_run(now):
    now = now.astimezone(timezone.utc)
    slot = now.replace(hour=6, minute=15, second=0, microsecond=0)
    slot += timedelta(days=(1 - now.weekday()) % 7)
    return slot if slot > now else slot + timedelta(days=7)


def worker_command(folder):
    return ['flock', '-n', '-E', '75', str(Path(folder) / 'weekly.lock'), sys.executable,
            str(ROOT / 'scripts/manual_scouting_sync.py'), '--folder', str(folder),
            'weekly', '--apply', '--max-requests', '240', '--seconds', '1800']


def tick(folder, now, execute):
    path = Path(folder) / 'scheduler-state.json'
    if not path.exists():
        state = dict(version=1, status='waiting', next_run_at=next_run(now).isoformat())
        save(path, state)
        return state
    state = read(path)
    if state.get('version') != 1:
        raise ValueError('Unsupported scheduler state')
    if datetime.fromisoformat(state['next_run_at']) > now:
        return state
    # Persist the next slot BEFORE starting: restarting a blocked worker must not hammer the provider.
    state.pop('error_type', None)
    state.update(status='running', last_started_at=now.isoformat(), next_run_at=next_run(now).isoformat())
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


def recover_interrupted(folder):
    path = Path(folder) / 'scheduler-state.json'
    if path.exists():
        state = read(path)
        if state.get('version') == 1 and state.get('status') == 'running':
            state.update(status='interrupted', last_exit_code=130,
                         last_finished_at=datetime.now(timezone.utc).isoformat())
            save(path, state)


def execute_worker(folder, stop):
    # A separate process group lets SIGTERM or the one-hour watchdog stop the complete worker tree.
    process = subprocess.Popen(worker_command(folder), start_new_session=True)
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


def serve(folder, stop):
    recover_interrupted(folder)
    previous = None
    while not stop.is_set():
        state = tick(folder, datetime.now(timezone.utc), lambda: execute_worker(folder, stop))
        if state != previous:
            print(json.dumps(dict(event='scouting_scheduler', **state)), flush=True)
            previous = state.copy()
        stop.wait(30)
