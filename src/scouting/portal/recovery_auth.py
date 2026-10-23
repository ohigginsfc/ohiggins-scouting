"""Persistent attempt limiter for explicit, read-only server recovery.

SQLite holds counters, not passwords, tokens, emails or sporting records.
"""
import hashlib
import hmac
import os
from pathlib import Path
import sqlite3
import time

WINDOW = 900
PER_USER = 5
GLOBAL = 60
_clock = time.time


def validate_environment():
    from .readonly_pilot import validate_environment as validate_connections
    if os.environ.get('PORTAL_RECOVERY_ENABLED') != '1':
        raise RuntimeError('Activa la recuperación explícitamente; COMET y cuentas conservan solo lectura.')
    if os.environ.get('PORTAL_RECOVERY_SCOUTING_WRITES', '0') not in {'0', '1'}:
        raise RuntimeError('Configura las escrituras de scouting como 0 o 1.')
    if not Path(os.environ.get('PORTAL_RECOVERY_STATE_DIR', '')).is_absolute():
        raise RuntimeError('Configura el directorio privado de estado de acceso.')
    validate_connections()


def _connect():
    directory = Path(os.environ.get('PORTAL_RECOVERY_STATE_DIR', ''))
    if not directory.is_absolute():
        raise RuntimeError('Configura el directorio privado de estado de acceso.')
    db = None
    try:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = directory / 'attempts.sqlite3'
        db = sqlite3.connect(path, timeout=5, isolation_level=None)
        os.chmod(path, 0o600)
        db.execute('CREATE TABLE IF NOT EXISTS attempts (key TEXT PRIMARY KEY, count INTEGER NOT NULL, started REAL NOT NULL)')
        return db
    except (OSError, sqlite3.Error):
        if db is not None:
            db.close()
        raise RuntimeError('No se pudo abrir el control privado de intentos.') from None


def _key(username, secret):
    return hmac.new(secret.encode(), username.encode(), hashlib.sha256).hexdigest()


def reserve_attempt(username, secret):
    key, now = _key(username, secret), _clock()
    db = _connect()
    try:
        db.execute('BEGIN IMMEDIATE')
        db.execute('DELETE FROM attempts WHERE started <= ?', (now - WINDOW,))
        for candidate, limit in ((key, PER_USER), ('global', GLOBAL)):
            row = db.execute('SELECT count FROM attempts WHERE key=?', (candidate,)).fetchone()
            if row and row[0] >= limit:
                db.rollback()
                return None
        for candidate in (key, 'global'):
            db.execute('INSERT INTO attempts VALUES(?,1,?) ON CONFLICT(key) DO UPDATE SET count=count+1',
                       (candidate, now))
        db.commit()
        return key
    except sqlite3.Error:
        db.rollback()
        raise RuntimeError('No se pudo verificar el límite de intentos.') from None
    finally:
        db.close()


def clear_user_attempts(username, secret):
    db = _connect()
    try:
        db.execute('DELETE FROM attempts WHERE key=?', (_key(username, secret),))
    except sqlite3.Error:
        raise RuntimeError('No se pudo actualizar el límite de intentos.') from None
    finally:
        db.close()
