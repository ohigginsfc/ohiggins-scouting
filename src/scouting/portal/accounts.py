"""Personal identities in Supabase Auth; authorization in private portal.accounts."""
import os
import time
import uuid

import psycopg
from psycopg.rows import dict_row
import requests


def connect():
    dsn = os.environ.get('PORTAL_AUTH_DATABASE_URL', '').strip()
    if not dsn:
        raise RuntimeError('Falta configurar la conexión privada de cuentas.')
    return psycopg.connect(dsn, connect_timeout=10, row_factory=dict_row,
        options='-c search_path=portal -c statement_timeout=15000')


def _auth(method, path, *, payload=None, token=None, admin=False):
    url = os.environ.get('PORTAL_SUPABASE_URL', '').rstrip('/')
    key = os.environ.get('PORTAL_SUPABASE_SECRET_KEY' if admin else 'PORTAL_SUPABASE_PUBLISHABLE_KEY', '')
    if not url.startswith('https://') or not key:
        raise RuntimeError('Falta configurar Supabase Auth.')
    headers = {'apikey': key}
    if token or (admin and key.startswith('eyJ')):
        headers['Authorization'] = 'Bearer ' + (token or key)
    try:
        response = requests.request(method, url + '/auth/v1/' + path,
                                    headers=headers, json=payload, timeout=15)
        if not response.ok:
            if response.status_code in (400, 401, 403, 422, 429):
                raise ValueError('Supabase rechazó la operación. Revisa credenciales, usuario existente o límite de intentos.')
            raise RuntimeError('Supabase Auth no está disponible.')
        return response.json() if response.content else {}
    except requests.RequestException:
        raise RuntimeError('No se pudo contactar con Supabase Auth.') from None


def get_user(user_id):
    try:
        user_id = str(uuid.UUID(str(user_id)))
    except (TypeError, ValueError):
        return None
    with connect() as db:
        return db.execute('SELECT id::text, email AS username, display_name, role, active, revision FROM portal.accounts WHERE id=%s', (user_id,)).fetchone()


def _validate(name, role, password=''):
    if not name.strip() or role not in ('admin', 'scout'):
        raise ValueError('Nombre y rol válidos son obligatorios.')
    if password and not 12 <= len(password) <= 128:
        raise ValueError('La contraseña debe tener entre 12 y 128 caracteres.')


def _create(db, email, name, password, role, active=True):
    _validate(name, role, password)
    if not password or '@' not in email:
        raise ValueError('Correo personal y contraseña son obligatorios.')
    # Only admins create verified club identities; never send mail implicitly.
    user = _auth('POST', 'admin/users', payload={'email': email.strip().lower(),
                 'password': password, 'email_confirm': True}, admin=True)
    uid = user['id']
    # On DB failure, an Auth-only user is intentionally denied portal access.
    # Admin may attach that identity later; never delete it automatically.
    db.execute('INSERT INTO portal.accounts(id,email,display_name,role,active) VALUES(%s,%s,%s,%s,%s)',
               (uid, email.strip().lower(), name.strip(), role, active))
    return uid


def bootstrap_admin(username, name, password):
    with connect() as db:
        db.execute('SELECT pg_advisory_xact_lock(73219401)')
        if db.execute('SELECT count(*) AS n FROM portal.accounts').fetchone()['n']:
            raise ValueError('Ya existen cuentas. Utiliza Administración.')
        return _create(db, username, name, password, 'admin')


def list_users():
    from .security import require_admin
    require_admin()
    with connect() as db:
        return db.execute('SELECT id::text,email AS username,display_name,role,active,revision FROM portal.accounts ORDER BY email').fetchall()


def save_user(*, username='', name='', password='', role='scout', user_id=None, active=True):
    from .security import require_admin
    actor = require_admin()
    _validate(name, role, password)
    with connect() as db:
        db.execute('SELECT pg_advisory_xact_lock(73219401)')
        current = db.execute('SELECT * FROM portal.accounts WHERE id=%s FOR UPDATE', (actor['id'],)).fetchone()
        if not current or not current['active'] or current['role'] != 'admin' or current['revision'] != actor['revision']:
            raise PermissionError('Sesión no vigente.')
        if user_id:
            old = db.execute('SELECT * FROM portal.accounts WHERE id=%s FOR UPDATE', (user_id,)).fetchone()
            if not old:
                raise ValueError('Cuenta no encontrada.')
            if old['role'] == 'admin' and old['active'] and (role != 'admin' or not active):
                if db.execute("SELECT count(*) AS n FROM portal.accounts WHERE role='admin' AND active").fetchone()['n'] <= 1:
                    raise ValueError('No se puede desactivar al último administrador.')
            if password:
                _auth('PUT', 'admin/users/' + str(uuid.UUID(user_id)), payload={'password': password}, admin=True)
            db.execute('UPDATE portal.accounts SET display_name=%s,role=%s,active=%s,revision=revision+1 WHERE id=%s',
                       (name.strip(), role, active, user_id))
        else:
            user_id = _create(db, username, name, password, role, active)
        db.execute('INSERT INTO portal.account_audit(actor_id,action,target_id) VALUES(%s,%s,%s)',
                   (actor['id'], 'save_user', user_id))
        return user_id


def authenticate(username, password):
    try:
        result = _auth('POST', 'token?grant_type=password', payload={'email': username.strip().lower(), 'password': password})
    except ValueError:
        return None
    profile = get_user(result['user']['id'])
    if not profile or not profile['active']:
        return None
    return {'id': profile['id'], 'revision': profile['revision'],
            'access_token': result['access_token'], 'expires': time.time() + min(result.get('expires_in', 3600), 8 * 3600)}


def resolve_session(session):
    if not isinstance(session, dict) or session.get('expires', 0) <= time.time() or not session.get('access_token'):
        return None
    try:
        identity = _auth('GET', 'user', token=session['access_token'])
    except ValueError:
        return None
    if identity.get('id') != session.get('id'):
        return None
    user = get_user(identity['id'])
    return user if user and user['active'] and user['revision'] == session.get('revision') else None
