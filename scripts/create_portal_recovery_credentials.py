"""Enroll two EXISTING profiles with new server-local credentials, without DB writes."""
import argparse
import getpass
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))


def main():
    from scouting.portal import accounts, local_pilot
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--admin-email', default='pcalandria@ohigginsfc.cl')
    parser.add_argument('--scout-email', default='scouting@ohigginsfc.cl')
    args = parser.parse_args()
    try:
        if os.environ.get('PORTAL_AUTH_PROVIDER') != 'local_recovery':
            raise ValueError('Selecciona local_recovery explícitamente.')
        if not args.output.is_absolute() or args.output.exists():
            raise ValueError('El archivo debe ser nuevo y tener ruta absoluta.')
        with accounts.connect() as db:
            if db.execute('SHOW transaction_read_only').fetchone()['transaction_read_only'] != 'on':
                raise RuntimeError('La conexión debe ser de solo lectura.')
            profiles = db.execute('SELECT id::text,email AS username,role,active FROM portal.accounts '
                                  'WHERE email IN (%s,%s)', (args.admin_email, args.scout_email)).fetchall()
        by_email = {p['username']: p for p in profiles if p['active']}
        if (by_email.get(args.admin_email, {}).get('role') != 'admin'
                or by_email.get(args.scout_email, {}).get('role') != 'scout'):
            raise ValueError('Faltan los dos perfiles activos con sus roles esperados.')
        enrolled = []
        for email in (args.admin_email, args.scout_email):
            password = getpass.getpass(f'Contraseña NUEVA para {email} (12-128 caracteres): ')
            if password != getpass.getpass('Repetir contraseña: '):
                raise ValueError('Las contraseñas no coinciden.')
            enrolled.append((by_email[email], password))
        local_pilot.write_credentials(args.output, enrolled)
        print('PASS: archivo privado creado. Supabase Auth y la BD no se han modificado.')
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        print(f'FAIL {type(exc).__name__}: no se completó el alta local; revisar configuración y entradas.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
