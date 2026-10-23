"""Bounded recovery preflight: no Auth HTTP, no writes, no personal data output."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))


def main():
    import os
    import psycopg
    from scouting.portal import accounts, local_pilot, readonly_pilot, recovery_auth
    from psycopg.conninfo import conninfo_to_dict
    stage = 'configuración'
    try:
        if accounts.provider() != 'local_recovery':
            raise RuntimeError('Proveedor incorrecto.')
        config = local_pilot.settings()
        # Exercise the persistent local limiter without consuming a login attempt.
        db = recovery_auth._connect()
        db.close()
        with accounts.connect() as db:
            for entry in config['accounts']:
                row = db.execute('SELECT role,active,email FROM portal.accounts WHERE id=%s', (entry['id'],)).fetchone()
                if not row or not row['active'] or row['email'] != entry['email']:
                    raise RuntimeError('Perfil no disponible.')
            roles = db.execute('SELECT role FROM portal.accounts WHERE active AND id=ANY(%s::uuid[])',
                               ([e['id'] for e in config['accounts']],)).fetchall()
            if {r['role'] for r in roles} != {'admin', 'scout'}:
                raise RuntimeError('Faltan los dos perfiles.')
        for key, schema, table in (
            ('PORTAL_AUTH_DATABASE_URL', 'portal', 'portal.accounts'),
            ('SCOUTING_DATABASE_URL', 'scouting', 'scouting.scouting_reports'),
            ('COMET_DATABASE_URL', 'public', 'public.partidos'),
        ):
            stage = schema
            params = conninfo_to_dict(os.environ[key])
            # The diagnostic never enables writes, even when the app will allow them.
            params.update(connect_timeout=10, options=readonly_pilot.connection_options(schema)
                          + ' -c default_transaction_read_only=on')
            with psycopg.connect(**params) as db:
                db.read_only = True  # BEGIN READ ONLY, including through the pooler.
                if db.execute('SHOW transaction_read_only').fetchone()[0] != 'on':
                    raise RuntimeError('Conexión sin protección de lectura.')
                db.execute(f'SELECT EXISTS(SELECT 1 FROM {table})').fetchone()
                if schema == 'scouting' and readonly_pilot.scouting_writes():
                    for name in ('scouting.players', 'scouting.scouting_reports', 'scouting.report_attribute_ratings'):
                        row = db.execute("SELECT has_table_privilege(current_user,%s,'SELECT') "
                                         "AND has_table_privilege(current_user,%s,'INSERT') "
                                         "AND has_table_privilege(current_user,%s,'UPDATE') "
                                         "AND has_table_privilege(current_user,%s,'DELETE'), "
                                         "has_sequence_privilege(current_user,pg_get_serial_sequence(%s,'id'),'USAGE')",
                                         (name, name, name, name, name)).fetchone()
                        if not all(row):
                            raise RuntimeError('Faltan permisos del escritor de scouting.')
                    print('PASS scouting: privilegios de escritura presentes (sin intentar escribir)')
            print(f'PASS {schema}: conexión y consulta en solo lectura')
        print('PASS: credenciales locales, dos roles y estado persistente configurados.')
        return 0
    except Exception as exc:
        print(f'FAIL {stage} / {type(exc).__name__}: revisar configuración privada de recuperación.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
