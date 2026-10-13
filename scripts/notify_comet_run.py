"""Envío explícito de aviso técnico de la ejecución; nunca incluye registros deportivos."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from scouting.comet_reports.notify import send_status, check_smtp


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--status', choices=['success', 'failure'])
    mode.add_argument('--check-smtp', action='store_true', help='verifica TLS y login sin mandar correo')
    args = parser.parse_args(argv)
    try:
        if args.check_smtp:
            check_smtp()
            print('SMTP COMET: TLS y autenticación correctos; sin envío.')
            return 0
        count = send_status(args.status)
        print(f'Aviso técnico COMET: {count} entrega(s) aceptadas por SMTP.')
        return 0
    except Exception as exc:
        print(f'Aviso técnico COMET fallido: {type(exc).__name__}; revisar configuración o servicio SMTP.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
