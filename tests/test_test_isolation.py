import os
import socket
import subprocess
import sys

import psycopg
import pytest
import requests
from tests.safety import isolate_environment, validate_test_database


@pytest.mark.parametrize('dsn', [
    'postgresql://synthetic@db.example.invalid/scouting_test',
    'postgresql://synthetic@localhost/postgres',
    'postgresql://synthetic@localhost/scouting_test?hostaddr=192.0.2.1',
    'postgresql:///scouting_test',
    'host=localhost dbname=scouting_test service=production',
])
def test_unsafe_database_is_rejected_before_libpq(dsn):
    for connect in (psycopg.connect, psycopg.Connection.connect):
        with pytest.raises(RuntimeError, match='scouting_test'):
            connect(dsn, connect_timeout=1)


def test_explicit_disposable_dsn_is_accepted_without_connecting():
    params = validate_test_database('postgresql://synthetic@127.0.0.1/scouting_test',
                                    options='-c search_path=synthetic')
    assert params['dbname'] == 'scouting_test'


def test_http_and_external_sockets_are_disabled():
    with pytest.raises(RuntimeError, match='HTTP is disabled'):
        requests.get('http://127.0.0.1:18502/')
    with socket.socket() as sock, pytest.raises(RuntimeError, match='External network'):
        sock.connect(('192.0.2.1', 443))


def test_native_curl_is_also_disabled_when_installed():
    curl_requests = pytest.importorskip('curl_cffi.requests')
    with pytest.raises(RuntimeError, match='HTTP is disabled'):
        curl_requests.get('http://127.0.0.1:18502/')


def test_private_dotenv_is_not_loaded(tmp_path):
    import dotenv
    import dotenv.main
    private = tmp_path / '.env.portal'
    private.write_text('TEST_PRIVATE_CANARY=do-not-load\n')
    assert dotenv.load_dotenv(private, override=True) is False
    assert dotenv.main.load_dotenv(private, override=True) is False
    assert dotenv.dotenv_values(private) == {}
    assert 'TEST_PRIVATE_CANARY' not in os.environ


def test_inherited_credentials_are_removed_before_imports(monkeypatch):
    monkeypatch.setenv('SCOUTING_DATABASE_URL', 'postgresql://synthetic@db.example.invalid/postgres')
    monkeypatch.setenv('PORTAL_SUPABASE_SECRET_KEY', 'synthetic-private')
    monkeypatch.setenv('COMET_DATABASE_URL', 'synthetic-private')
    monkeypatch.setenv('PGSERVICE', 'production')
    with pytest.MonkeyPatch.context() as patch:
        isolate_environment(patch)
        assert not any(key in os.environ for key in (
            'SCOUTING_DATABASE_URL', 'PORTAL_SUPABASE_SECRET_KEY', 'COMET_DATABASE_URL', 'PGSERVICE'))
        assert os.environ['DB_NAME'] == 'scouting_test'
        assert os.environ['SCOUTING_TEST_MODE'] == '1'


def test_remote_test_dsn_aborts_before_collection(tmp_path):
    env = os.environ.copy()
    env['SCOUTING_TEST_DATABASE_URL'] = 'postgresql://synthetic@db.example.invalid/postgres'
    result = subprocess.run([sys.executable, '-m', 'pytest', '--collect-only', '-q',
                             'tests/test_database_schema.py'], env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 4
    assert 'Tests only allow an explicit loopback database named scouting_test' in result.stderr
    assert 'synthetic@' not in result.stderr
