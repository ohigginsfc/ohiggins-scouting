"""Explicit opt-in for a loopback-only preview of existing Supabase records.

No provisioning, migrations, Auth requests or background workers belong here.
The normal Supabase provider and the disposable local pilot remain unchanged.
"""
import os
import re
from functools import wraps

from psycopg.conninfo import conninfo_to_dict


def enabled():
    return (os.environ.get('PORTAL_AUTH_PROVIDER', '').strip() == 'local_pilot'
            and os.environ.get('PORTAL_PILOT_DATA_MODE') == 'supabase_readonly')


def validate_environment():
    project = os.environ.get('PORTAL_PILOT_SUPABASE_PROJECT', '')
    if not re.fullmatch(r'[a-z]{20}', project):
        raise RuntimeError('Configura el proyecto del piloto de solo lectura.')
    roles = {'PORTAL_AUTH_DATABASE_URL': 'portal_runtime',
             'SCOUTING_DATABASE_URL': 'scouting_runtime',
             'COMET_DATABASE_URL': 'comet_reader'}
    for key, role in roles.items():
        try:
            params = conninfo_to_dict(os.environ.get(key, ''))
            safe = (params.get('user') == f'{role}.{project}'
                    and params.get('dbname') == 'postgres'
                    and params.get('sslmode') in {'require', 'verify-ca', 'verify-full'}
                    and params.get('port', '5432') == '5432'
                    and re.fullmatch(r'aws-\d+-[a-z0-9-]+\.pooler\.supabase\.com', params.get('host', ''))
                    and not params.get('hostaddr') and not params.get('service'))
        except Exception:
            safe = False
        if not safe:
            raise RuntimeError('El piloto requiere tres roles aislados, session pooler y SSL.')


def connection_options(schema, timeout=15000):
    # Replace DSN options, rather than allow an inherited setting to undo this.
    if schema not in {'portal', 'scouting', 'public'}:
        raise ValueError('Esquema no permitido.')
    return (f'-c search_path={schema} -c default_transaction_read_only=on '
            f'-c statement_timeout={timeout} -c idle_in_transaction_session_timeout=15000 '
            '-c application_name=ohiggins_readonly_pilot')


def require_writable():
    if enabled():
        raise PermissionError('Este piloto solo permite consultar datos.')


def writable_only(fn):
    @wraps(fn)
    def guarded(*args, **kwargs):
        require_writable()
        return fn(*args, **kwargs)
    return guarded
