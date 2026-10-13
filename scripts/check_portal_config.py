"""Diagnóstico de despliegue: Auth y tres conexiones, sin credenciales ni datos personales."""
import argparse
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit
import psycopg
import requests

REQUIRED = ('PORTAL_SUPABASE_URL', 'PORTAL_SUPABASE_PUBLISHABLE_KEY', 'PORTAL_SUPABASE_SECRET_KEY',
            'PORTAL_AUTH_DATABASE_URL', 'SCOUTING_DATABASE_URL', 'COMET_DATABASE_URL')


def check_config(env, *, get=requests.get, connect=psycopg.connect):
    results = []
    for key in REQUIRED:
        value = env.get(key, '').strip()
        valid = bool(value) and value not in ('replace-me', 'YOUR_SERVER_KEY') and 'PROJECT.supabase.co' not in value
        results.append((key, valid, 'configurada' if valid else 'ausente o contiene el ejemplo'))
    if not all(ok for _, ok, _ in results):
        return results
    url = env['PORTAL_SUPABASE_URL'].rstrip('/')
    try:
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
            raise ValueError('URL inválida')
    except ValueError:
        return results + [('Supabase Auth URL', False, 'usar la URL HTTPS del proyecto, sin ruta ni credenciales')]
    for name, path, key in (
        ('Auth clave pública / conexión', 'settings', env['PORTAL_SUPABASE_PUBLISHABLE_KEY']),
        ('Auth clave de administración', 'admin/users?page=1&per_page=1', env['PORTAL_SUPABASE_SECRET_KEY']),
    ):
        headers = {'apikey': key}
        if key.startswith('eyJ') and path.startswith('admin/'):
            headers['Authorization'] = 'Bearer ' + key
        try:
            response = get(url + '/auth/v1/' + path, headers=headers, timeout=10)
            results.append((name, response.status_code == 200, f'HTTP {response.status_code}'))
        except requests.RequestException as exc:
            results.append((name, False, type(exc).__name__ + ': revisar DNS, TLS o salida HTTPS del servidor'))
    for key, query in (
        ('PORTAL_AUTH_DATABASE_URL', 'SELECT count(*) FROM portal.accounts WHERE active'),
        ('SCOUTING_DATABASE_URL', 'SELECT count(*) FROM scouting.scouting_reports'),
        ('COMET_DATABASE_URL', 'SELECT count(*) FROM public.partidos'),
    ):
        try:
            with connect(env[key], connect_timeout=10) as db:
                db.execute('SET TRANSACTION READ ONLY')
                db.execute("SET LOCAL statement_timeout='10000'")
                db.execute(query).fetchone()
            results.append((key + ' lectura', True, 'conexión y permisos correctos'))
        except Exception as exc:
            results.append((key + ' lectura', False, type(exc).__name__ + ': revisar DSN, password, pooler, SSL y permisos'))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, help='archivo privado explícito; dentro del contenedor usar el entorno existente')
    args = parser.parse_args(argv)
    if args.env_file:
        from dotenv import load_dotenv
        if not args.env_file.is_file():
            parser.error('No existe el archivo de entorno')
        load_dotenv(args.env_file, override=False)
    results = check_config(os.environ)
    for name, ok, detail in results:
        print(f'{"PASS" if ok else "FAIL"} {name}: {detail}')
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
