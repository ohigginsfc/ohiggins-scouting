"""Loopback-only authentication experiment; never a fallback after a cloud error.

Credentials live in a private local file. Roles/active/revision remain authoritative
in portal.accounts. The pilot cannot create or modify those profiles.
"""
from collections import OrderedDict
from functools import lru_cache
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import secrets
from threading import Lock
import time
import uuid

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from itsdangerous import BadData, URLSafeTimedSerializer
from psycopg.conninfo import conninfo_to_dict

LIFETIME = 3600
WINDOW = 900
MAX_ATTEMPTS = 5
_attempts = OrderedDict()
_lock = Lock()
_clock = time.monotonic
_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)


def validate_environment():
    """The experiment cannot point at Supabase or any non-local database."""
    if any(os.environ.get(key) for key in ('PGHOSTADDR', 'PGSERVICE', 'PGSERVICEFILE')):
        raise RuntimeError('Retira las variables de red libpq antes de ejecutar el piloto.')
    for key in ('PORTAL_AUTH_DATABASE_URL', 'SCOUTING_DATABASE_URL', 'COMET_DATABASE_URL'):
        try:
            params = conninfo_to_dict(os.environ.get(key, ''))
            safe = (params.get('host') in {'127.0.0.1', 'localhost', '::1'}
                    and params.get('dbname') in {'scouting_test', 'portal_pilot'}
                    and params.get('hostaddr', '127.0.0.1') in {'127.0.0.1', '::1'}
                    and not params.get('service'))
        except Exception:
            safe = False
        if not safe:
            raise RuntimeError('El piloto solo admite bases locales desechables.')


def settings():
    validate_environment()
    path = Path(os.environ.get('PORTAL_PILOT_CREDENTIALS', ''))
    try:
        if not path.is_absolute() or path.stat().st_size > 65536:
            raise ValueError()
        config = json.loads(path.read_text(encoding='utf-8'))
        if config.get('version') != 1 or not isinstance(config['secret'], str) or len(config['secret']) < 43:
            raise ValueError()
        entries = config['accounts']
        if not isinstance(entries, list) or not 1 <= len(entries) <= 64:
            raise ValueError()
        ids, emails = set(), set()
        for entry in entries:
            uid = str(uuid.UUID(entry['id']))
            email = entry['email']
            if (uid != entry['id'] or not isinstance(email, str) or '@' not in email
                    or email != email.strip().lower() or email in emails or uid in ids
                    or not entry['password_hash'].startswith('$argon2id$')
                    or 'role' in entry):
                raise ValueError()
            ids.add(uid)
            emails.add(email)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise RuntimeError('Configura el archivo privado de credenciales del piloto.') from None
    return config


def write_credentials(path, profiles):
    """Provision synthetic/local profiles; caller obtains passwords interactively."""
    path = Path(path)
    if not path.is_absolute() or path.exists():
        raise ValueError('Usa una ruta absoluta nueva para el archivo privado.')
    entries = []
    for profile, password in profiles:
        if not isinstance(password, str) or not 12 <= len(password) <= 128:
            raise ValueError('La contraseña del piloto debe tener entre 12 y 128 caracteres.')
        entries.append(dict(id=str(uuid.UUID(profile['id'])),
                            email=profile['username'].strip().lower(),
                            password_hash=_hasher.hash(password)))
    value = dict(version=1, secret=secrets.token_urlsafe(48), accounts=entries)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as file:
        os.chmod(path, 0o600)
        json.dump(value, file)


def _serializer(config):
    return URLSafeTimedSerializer(config['secret'], salt='ohiggins-local-pilot-v1',
                                  signer_kwargs={'digest_method': hashlib.sha256})


def _credential_digest(entry):
    return hashlib.sha256(entry['password_hash'].encode()).hexdigest()


@lru_cache(maxsize=1)
def _dummy_hash():
    return _hasher.hash(secrets.token_urlsafe(32))


def _reserve_attempt(username):
    # Per-process and bounded: sufficient for a loopback-only experiment, not a
    # distributed production rate limiter. Restarting the process resets it.
    key = hashlib.sha256(username.encode()).hexdigest()
    now = _clock()
    with _lock:
        count, started = _attempts.get(key, (0, now))
        if now - started >= WINDOW:
            count, started = 0, now
        if count >= MAX_ATTEMPTS:
            return None
        _attempts[key] = (count + 1, started)
        _attempts.move_to_end(key)
        while len(_attempts) > 256:
            _attempts.popitem(last=False)
    return key


def authenticate(username, password):
    from .accounts import get_user
    config = settings()
    if not isinstance(username, str) or not isinstance(password, str):
        return None
    username = username.strip().lower()
    if len(username) > 254 or not 1 <= len(password) <= 128:
        return None
    attempt = _reserve_attempt(username)
    if attempt is None:
        return None
    entry = next((e for e in config['accounts'] if e['email'] == username), None)
    try:
        _hasher.verify(entry['password_hash'] if entry else _dummy_hash(), password)
    except (VerificationError, InvalidHashError):
        return None
    if not entry:
        return None
    profile = get_user(entry['id'])
    if not profile or not profile['active'] or profile['username'] != entry['email']:
        return None
    with _lock:
        _attempts.pop(attempt, None)
    payload = dict(id=profile['id'], revision=profile['revision'],
                   credential=_credential_digest(entry), nonce=secrets.token_urlsafe(24))
    return dict(provider='local_pilot', id=profile['id'], revision=profile['revision'],
                local_token=_serializer(config).dumps(payload), expires=time.time() + LIFETIME)


def resolve_session(session):
    from .accounts import get_user
    if (not isinstance(session, dict) or session.get('provider') != 'local_pilot'
            or not isinstance(session.get('local_token'), str)
            or len(session['local_token']) > 4096
            or not isinstance(session.get('expires'), (int, float))
            or not math.isfinite(session['expires']) or session['expires'] <= time.time()):
        return None
    config = settings()
    try:
        payload = _serializer(config).loads(session['local_token'], max_age=LIFETIME)
        if not isinstance(payload, dict) or any(payload.get(k) != session.get(k) for k in ('id', 'revision')):
            return None
        entry = next((e for e in config['accounts'] if e['id'] == payload.get('id')), None)
        if not entry or not hmac.compare_digest(str(payload.get('credential', '')), _credential_digest(entry)):
            return None
    except (BadData, TypeError, ValueError):
        return None
    profile = get_user(payload['id'])
    if (not profile or not profile['active'] or profile['revision'] != payload['revision']
            or profile['username'] != entry['email']):
        return None
    return profile
