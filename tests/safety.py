"""Fail closed before test collection: no production secrets, SQL or HTTP."""
from functools import wraps
import inspect
import os
import socket

import psycopg
from psycopg.conninfo import conninfo_to_dict

LOOPBACK = {'localhost', '127.0.0.1', '::1'}


def validate_test_database(conninfo='', **kwargs):
    try:
        params = conninfo_to_dict(conninfo, **kwargs)
    except psycopg.Error:
        raise RuntimeError('Invalid test DSN; use an explicit loopback database named scouting_test.') from None
    if (params.get('host') not in LOOPBACK or params.get('dbname') != 'scouting_test'
            or params.get('hostaddr', '127.0.0.1') not in LOOPBACK
            or params.get('service') or params.get('servicefile')):
        raise RuntimeError('Tests only allow an explicit loopback database named scouting_test.')
    return params


def isolate_environment(patch):
    dsn = os.environ.get('SCOUTING_TEST_DATABASE_URL', '')
    if dsn:
        validate_test_database(dsn)
    prefixes = ('DB_', 'PG', 'PORTAL_', 'COMET_', 'SUPABASE_', 'SMTP_', 'GOOGLE_')
    names = {'SCOUTING_DATABASE_URL', 'DATABASE_URL', 'SESSION_URL',
             'SCOUTING_PASSWORD_HASH', 'SCOUTING_PASSWORD', 'SCOUTING_USERNAME',
             'SOFASCORE_ARTIFACT_KEY'}
    for name in list(os.environ):
        if name.startswith(prefixes) or name in names:
            patch.delenv(name, raising=False)
    patch.setenv('PYTHON_DOTENV_DISABLED', '1')
    patch.setenv('SCOUTING_TEST_MODE', '1')
    patch.setenv('DISABLE_SOFASCORE_UPDATE', '1')
    # Synthetic defaults also prevent native subprocesses from inheriting DB secrets.
    for name, value in dict(DB_HOST='127.0.0.1', DB_PORT='5432', DB_NAME='scouting_test',
                            DB_USER='scouting_test', DB_PASSWORD='synthetic-test-password').items():
        patch.setenv(name, value)


def install_guards(patch):
    # The pinned python-dotenv 1.0.1 does not implement PYTHON_DOTENV_DISABLED.
    # Patch both public entrypoints before application imports, not just the env flag.
    import dotenv
    import dotenv.main
    for module in (dotenv, dotenv.main):
        patch.setattr(module, 'load_dotenv', lambda *a, **kw: False)
        patch.setattr(module, 'dotenv_values', lambda *a, **kw: {})
    original = psycopg.connect
    signature = inspect.signature(original)

    @wraps(original)
    def connect(*args, **kwargs):
        bound = signature.bind(*args, **kwargs)
        validate_test_database(bound.arguments.get('conninfo', ''), **bound.arguments.get('kwargs', {}))
        return original(*args, **kwargs)

    patch.setattr(psycopg, 'connect', connect)
    # psycopg.connect is an alias; also cover callers using Connection.connect.
    patch.setattr(psycopg.Connection, 'connect', staticmethod(connect))

    def no_http(*args, **kwargs):
        raise RuntimeError('HTTP is disabled in tests; mock the provider response.')

    import requests
    patch.setattr(requests.sessions.Session, 'request', no_http)
    try:
        from curl_cffi import requests as curl_requests
    except ImportError:
        pass
    else:
        patch.setattr(curl_requests.Session, 'request', no_http)
        patch.setattr(curl_requests.AsyncSession, 'request', no_http)

    original_connect, original_connect_ex = socket.socket.connect, socket.socket.connect_ex

    def network_guard(original):
        @wraps(original)
        def guarded(sock, address):
            # Keep local socketpairs/event loops working. libpq is native and is
            # independently guarded above by database name AND destination.
            if sock.family in (socket.AF_INET, socket.AF_INET6) and address[0] not in LOOPBACK:
                raise RuntimeError('External network is disabled in tests.')
            return original(sock, address)
        return guarded

    patch.setattr(socket.socket, 'connect', network_guard(original_connect))
    patch.setattr(socket.socket, 'connect_ex', network_guard(original_connect_ex))
