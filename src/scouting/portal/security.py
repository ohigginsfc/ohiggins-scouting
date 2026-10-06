"""Request-scoped authorization; never infer roles from a menu or query parameter."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

_session = ContextVar('portal_session', default=None)
_principal = ContextVar('portal_principal', default=None)


@contextmanager
def session_scope(session, verified_user=None):
    token = _session.set(session)
    principal_token = _principal.set(verified_user)
    try:
        yield
    finally:
        _session.reset(token)
        _principal.reset(principal_token)


def require_user():
    from .accounts import resolve_session
    user = _principal.get() or resolve_session(_session.get())
    if not user or not user.get('active'):
        raise PermissionError('La sesión no está vigente. Inicia sesión de nuevo.')
    return user


def require_admin():
    user = require_user()
    if user['role'] != 'admin':
        raise PermissionError('Acceso reservado al administrador.')
    return user


def admin_only(fn):
    @wraps(fn)
    def guarded(*args, **kwargs):
        require_admin()  # Outside cached functions: also checked on cache hits.
        return fn(*args, **kwargs)
    return guarded


def can_edit(report):
    user = require_user()
    return user['role'] == 'admin' or (user['role'] == 'scout' and (
        report.get('is_hidden') or
        (report.get('raw_payload') or {}).get('portal_owner_id') == user['id']))


def require_report_management(conn, report_id):
    """Admin manages all reports; scout may manage any currently hidden report."""
    user = require_user()
    if user['role'] == 'admin':
        return
    from scouting.repositories.reports_repository import get_report_by_id
    report = get_report_by_id(conn, report_id)
    if user['role'] != 'scout' or not report or not report.get('is_hidden'):
        raise PermissionError('Scout solo puede restaurar o eliminar informes ocultos.')


def require_report_owner(conn, report_id):
    from scouting.repositories.reports_repository import get_report_by_id
    report = get_report_by_id(conn, report_id)
    if not report or not can_edit(report):
        raise PermissionError('Solo puedes modificar tus informes visibles o los informes ocultos.')
    return report
