"""Prepare/run an explicit read-only Supabase preview on 127.0.0.1:18504.

Pass a private .env.portal with --env-file once. Only three PostgreSQL connections
are imported. This script never uses Supabase Auth or provisions database records.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
CONNECTIONS = ('PORTAL_AUTH_DATABASE_URL', 'SCOUTING_DATABASE_URL', 'COMET_DATABASE_URL')
SEASONS = ('SOFASCORE_ACTIVE_SEASON', 'SOFASCORE_HISTORICAL_SEASON')
PRIVATE = ROOT / '.local_checks/supabase-readonly-pilot'


def clean_environment():
    return clean_from(os.environ)


def prepare(env_file, destination, project):
    from dotenv import dotenv_values
    from scouting.portal import accounts, local_pilot, readonly_pilot, security
    from scouting.db import get_connection
    from psycopg.conninfo import conninfo_to_dict

    destination = destination.resolve()
    if destination.exists() or ROOT / '.local_checks' not in destination.parents:
        raise ValueError('Usa un directorio nuevo dentro de .local_checks.')
    supplied = dotenv_values(env_file, interpolate=False)
    values = {k: supplied.get(k, '') for k in CONNECTIONS}
    values.update({SEASONS[0]: supplied.get(SEASONS[0]) or str(date.today().year),
                   SEASONS[1]: supplied.get(SEASONS[1]) or str(date.today().year - 1)})
    values.update(PORTAL_AUTH_PROVIDER='local_pilot', PORTAL_PILOT_DATA_MODE='supabase_readonly',
                  PORTAL_PILOT_SUPABASE_PROJECT=project, SCOUTING_TEST_MODE='1',
                  DB_SCHEMA='scouting', PORTAL_MODE='1', DISABLE_SOFASCORE_UPDATE='1')
    saved = dict(os.environ)
    try:
        os.environ.clear()
        os.environ.update(clean_from(saved))
        os.environ.update(values)
        local_pilot.validate_environment()
        checks = {}
        with accounts.connect() as db:
            if db.execute('SHOW transaction_read_only').fetchone()['transaction_read_only'] != 'on':
                raise RuntimeError('La conexión de perfiles no está en solo lectura.')
            profiles = db.execute(
                'SELECT id::text, email AS username, display_name, role, active, revision '
                'FROM portal.accounts WHERE email IN (%s,%s)',
                ('pcalandria@ohigginsfc.cl', 'scouting@ohigginsfc.cl')).fetchall()
        by_role = {p['role']: p for p in profiles if p['active']}
        if (len(profiles) != 2 or set(by_role) != {'admin', 'scout'}
                or by_role['admin']['username'] != 'pcalandria@ohigginsfc.cl'
                or by_role['scout']['username'] != 'scouting@ohigginsfc.cl'):
            raise RuntimeError('No se encontraron los dos perfiles activos esperados.')
        checks['portal_read_only'] = True
        with security.session_scope({}, verified_user=by_role['scout']):
            with get_connection() as db:
                if db.execute('SHOW transaction_read_only').fetchone()[0] != 'on':
                    raise RuntimeError('La conexión de scouting no está en solo lectura.')
                checks['scouting_read_only'] = True
                checks['reports'] = db.execute(
                    'SELECT count(*) FILTER (WHERE NOT is_hidden), count(*) FILTER (WHERE is_hidden) '
                    'FROM scouting.scouting_reports').fetchone()
                checks['objective_records'], checks['sofascore_records'] = db.execute(
                    "SELECT count(*), count(*) FILTER (WHERE source_type='sofascore') "
                    'FROM scouting.objective_metrics').fetchone()
        # COMET uses its independent existing reader role, without loading all data.
        import psycopg
        params = conninfo_to_dict(values['COMET_DATABASE_URL'])
        params['options'] = readonly_pilot.connection_options('public')
        with psycopg.connect(**params, connect_timeout=10) as db:
            db.read_only = True
            if db.execute('SHOW transaction_read_only').fetchone()[0] != 'on':
                raise RuntimeError('La conexión de COMET no está en solo lectura.')
            checks['comet_read_only'] = True
            checks['comet_matches'] = db.execute('SELECT count(*) FROM public.partidos').fetchone()[0]
        destination.mkdir(parents=True)
        credentials = destination / 'credentials.private.json'
        passwords = [(p, secrets.token_urlsafe(18)) for p in profiles]
        local_pilot.write_credentials(credentials, passwords)
        values['PORTAL_PILOT_CREDENTIALS'] = str(credentials)
        files = {
            'environment.private.json': json.dumps(values),
            'validation.private.json': json.dumps(checks, indent=2),
            'access.private.txt': 'SOLO PILOTO LOCAL - http://127.0.0.1:18504/\n'
                'Contraseñas temporales locales; no cambian las de Supabase Auth.\n\n'
                + '\n\n'.join(f"{p['role']}\n{p['username']}\n{password}" for p, password in passwords),
        }
        for name, content in files.items():
            path = destination / name
            with path.open('x', encoding='utf-8') as file:
                os.chmod(path, 0o600)
                file.write(content)
        return checks
    finally:
        os.environ.clear()
        os.environ.update(saved)


def clean_from(source):
    return {k: v for k, v in source.items() if not k.startswith(
        ('PORTAL_', 'COMET_', 'SCOUTING_', 'SUPABASE_', 'DB_', 'PG', 'SMTP_', 'GOOGLE_'))
        and k not in {'DATABASE_URL', 'SESSION_URL'}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--project', default='smjicdkycruyholhlbfd')
    parser.add_argument('--directory', type=Path, default=PRIVATE)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if args.check_only and not args.env_file:
        parser.error('--check-only requiere --env-file; no se ha consultado ninguna BD.')
    try:
        if args.env_file:
            checks = prepare(args.env_file, args.directory, args.project)
            print(json.dumps(checks))  # Aggregate counts and booleans only, never DSNs.
        if args.check_only:
            return 0
        values = json.loads((args.directory / 'environment.private.json').read_text(encoding='utf-8'))
        # Allowlist; never import arbitrary settings or SMTP/Auth keys from a file.
        env = clean_environment()
        env.update({k: values[k] for k in CONNECTIONS + SEASONS
                    + ('PORTAL_PILOT_CREDENTIALS', 'PORTAL_PILOT_SUPABASE_PROJECT')})
        env.update(PORTAL_AUTH_PROVIDER='local_pilot', PORTAL_PILOT_DATA_MODE='supabase_readonly',
                   SCOUTING_TEST_MODE='1', PORTAL_MODE='1', DB_SCHEMA='scouting', DISABLE_SOFASCORE_UPDATE='1')
        return subprocess.call([sys.executable, '-m', 'streamlit', 'run', str(ROOT / 'app/portal.py'),
                                '--server.address=127.0.0.1', '--server.port=18504',
                                '--server.headless=true', '--browser.gatherUsageStats=false'], cwd=ROOT, env=env)
    except Exception as exc:
        print(f'FAIL {type(exc).__name__}: piloto no iniciado; revisar configuración privada.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
