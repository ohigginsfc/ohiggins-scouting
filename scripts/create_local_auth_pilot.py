"""Create a synthetic portal in an EMPTY loopback database named portal_pilot.

Development tool only. It never reads production .env files and cannot target
Supabase. Keep its generated credentials in .local_checks, outside version control.
"""
import argparse
from datetime import date
import json
import os
from pathlib import Path
import re
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT))
os.environ['SCOUTING_TEST_MODE'] = '1'  # No automatic application .env loading.

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.types.json import Jsonb
from scouting.portal.local_pilot import write_credentials


def validate_setup_dsn(dsn):
    try:
        params = conninfo_to_dict(dsn)
        safe = (params.get('host') in {'localhost', '127.0.0.1', '::1'}
                and params.get('dbname') == 'portal_pilot'
                and params.get('hostaddr', '127.0.0.1') in {'127.0.0.1', '::1'}
                and not params.get('service')
                and not any(os.environ.get(k) for k in ('PGHOSTADDR', 'PGSERVICE', 'PGSERVICEFILE')))
    except Exception:
        safe = False
    if not safe:
        raise ValueError('Setup solo admite la BD local portal_pilot.')
    return params


def _migration(conn, path):
    source = path.read_text(encoding='utf-8')
    conn.execute(re.sub(r'(?m)^(?:BEGIN|COMMIT);[ \t]*$', '', source))


def provision(dsn, output):
    params = validate_setup_dsn(dsn)
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT / '.local_checks') or output.exists():
        raise ValueError('Elige una carpeta NUEVA dentro de .local_checks.')
    # The same tiny synthetic competition used in PostgreSQL regression tests.
    # This is deliberately a dev tool, not part of the production image.
    from tests.test_comet_postgres import _create_comet_tables, _fill_comet_tables
    from scouting.comet_ingest.db_pipeline.specs import SPECS
    profiles = [dict(id='00000000-0000-0000-0000-000000000001', username='admin@pilot.test',
                     display_name='Admin piloto', role='admin'),
                dict(id='00000000-0000-0000-0000-000000000002', username='scout@pilot.test',
                     display_name='Scout piloto', role='scout')]
    role_passwords = {role: secrets.token_urlsafe(32) for role in
                      ('portal_runtime', 'pilot_scouting', 'comet_reader')}
    with psycopg.connect(dsn, connect_timeout=5) as conn:
        conn.execute("SET LOCAL statement_timeout='30000'")
        if conn.execute("SELECT EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                        "WHERE n.nspname IN ('public','portal','scouting') AND c.relkind IN ('r','p'))").fetchone()[0]:
            raise ValueError('La BD del piloto debe estar vacía; no se borran tablas existentes.')
        for role in ('anon', 'authenticated'):
            if not conn.execute('SELECT 1 FROM pg_roles WHERE rolname=%s', (role,)).fetchone():
                conn.execute(sql.SQL('CREATE ROLE {} NOLOGIN').format(sql.Identifier(role)))
        conn.execute('CREATE SCHEMA auth; CREATE TABLE auth.users(id uuid PRIMARY KEY)')
        _create_comet_tables(conn)
        _fill_comet_tables(conn)
        # Supply optional legacy-dashboard columns too; all values remain synthetic.
        for name, spec in SPECS.items():
            conn.execute(sql.SQL('CREATE TABLE IF NOT EXISTS public.{} (__pilot_empty boolean)').format(sql.Identifier(name)))
            integer, numeric, boolean, timestamp = [set(c.lower() for c in group) for group in
                (spec.int_cols, spec.float_cols, spec.bool_cols, spec.tz_cols)]
            for column in spec.cols:
                column = column.lower()
                kind = ('bigint' if column in integer else 'numeric' if column in numeric
                        else 'boolean' if column in boolean else 'timestamptz' if column in timestamp else 'text')
                conn.execute(sql.SQL('ALTER TABLE public.{} ADD COLUMN IF NOT EXISTS {} {}').format(
                    sql.Identifier(name), sql.Identifier(column), sql.SQL(kind)))
            conn.execute(sql.SQL('ALTER TABLE public.{} ENABLE ROW LEVEL SECURITY').format(sql.Identifier(name)))
        conn.execute('CREATE SCHEMA scouting; SET LOCAL search_path=scouting')
        _migration(conn, ROOT / 'db/init.sql')
        for path in sorted((ROOT / 'db/migrations').glob('*.sql')):
            _migration(conn, path)
        conn.execute('SET LOCAL search_path=public')
        for path in sorted((ROOT / 'db/portal').glob('*.sql')):
            _migration(conn, path)
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname='pilot_scouting'").fetchone():
            conn.execute('CREATE ROLE pilot_scouting LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE')
        conn.execute('GRANT USAGE ON SCHEMA scouting TO pilot_scouting; '
                     'GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA scouting TO pilot_scouting; '
                     'GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA scouting TO pilot_scouting')
        for role, password in role_passwords.items():
            conn.execute(sql.SQL('ALTER ROLE {} PASSWORD {}').format(sql.Identifier(role), sql.Literal(password)))
        for profile in profiles:
            conn.execute('INSERT INTO auth.users(id) VALUES(%s)', (profile['id'],))
            conn.execute('INSERT INTO portal.accounts(id,email,display_name,role) VALUES(%s,%s,%s,%s)',
                         (profile['id'], profile['username'], profile['display_name'], profile['role']))
        for index, hidden in enumerate((False, True), start=1):
            player_id = conn.execute('INSERT INTO scouting.players(full_name,normalized_name,position,current_team) '
                'VALUES(%s,%s,%s,%s) RETURNING id',
                (f'Jugador sintético {index}', f'jugador-sintetico-{index}', 'Mediocentro', "O'Higgins")).fetchone()[0]
            conn.execute('INSERT INTO scouting.scouting_reports(player_id,source_type,scout_name,report_date,'
                         'competition,position_observed,summary,recommendation,rating,is_hidden,raw_payload) '
                         'VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                         (player_id, 'manual', 'Scout piloto', date.today(), 'Liga sintética', 'Mediocentro',
                          'Informe ficticio para comprobar permisos.', 'Interesante', 3.5, hidden,
                          Jsonb({'portal_owner_id': profiles[1]['id']})))
    output.mkdir(parents=True)
    credential_path = output / 'credentials.private.json'
    passwords = [(profile, secrets.token_urlsafe(18)) for profile in profiles]
    write_credentials(credential_path, passwords)
    environment = dict(PORTAL_AUTH_PROVIDER='local_pilot', PORTAL_PILOT_CREDENTIALS=str(credential_path),
                       PORTAL_BIND_ADDRESS='127.0.0.1', PORTAL_PORT='18503',
                       DB_SCHEMA='scouting', DISABLE_SOFASCORE_UPDATE='1', SCOUTING_TEST_MODE='1')
    for key, role in [('PORTAL_AUTH_DATABASE_URL', 'portal_runtime'),
                      ('SCOUTING_DATABASE_URL', 'pilot_scouting'), ('COMET_DATABASE_URL', 'comet_reader')]:
        environment[key] = make_conninfo(**(params | dict(user=role, password=role_passwords[role])))
    (output / 'environment.private.json').write_text(json.dumps(environment, indent=2), encoding='utf-8')
    access = '\n'.join(f"{profile['display_name']}: {profile['username']}\nContraseña: {password}\n" for profile, password in passwords)
    (output / 'access.private.txt').write_text('PILOTO LOCAL, DATOS SINTÉTICOS\nhttp://127.0.0.1:18503/\n\n' + access, encoding='utf-8')
    for path in output.iterdir():
        os.chmod(path, 0o600)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.local_checks/local-auth-pilot')
    args = parser.parse_args()
    try:
        output = provision(os.environ.get('PORTAL_PILOT_SETUP_DSN', ''), args.output)
    except Exception as error:
        print('No se pudo preparar el piloto: ' + type(error).__name__ + '. Comprueba destino local vacío y dependencias.', file=sys.stderr)
        return 1
    print('Piloto sintético preparado. Archivos privados: ' + str(output))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
