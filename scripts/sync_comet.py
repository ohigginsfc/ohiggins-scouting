"""Sincronización COMET del repo unificado. Por defecto solo descarga y valida."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from scouting.comet_ingest.sync import run_sync


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--dry-run', action='store_true', help='Descarga y transforma sin escribir')
    modes.add_argument('--publish', action='store_true', help='Upsert de las doce tablas COMET en Supabase')
    parser.add_argument('--env-file', type=Path, help='Archivo privado explícito; no se carga el .env del portal')
    parser.add_argument('--summary-json', type=Path, help='Resumen de conteos, sin registros personales ni claves')
    args = parser.parse_args(argv)
    if args.env_file:
        if not args.env_file.is_file():
            parser.error('No existe el archivo de entorno indicado')
        from dotenv import load_dotenv
        load_dotenv(args.env_file, override=False)
    try:
        summary = run_sync(dry_run=not args.publish)
    except (ValueError, RuntimeError, KeyError) as exc:
        print(f'Sync COMET fallida: {exc}', file=sys.stderr)
        return 1
    except Exception as exc:
        # Unexpected provider/serialization exceptions must not expose raw data.
        print(f'Sync COMET fallida: {type(exc).__name__}; revisar configuración y contrato', file=sys.stderr)
        return 1
    if args.summary_json:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf8')
    if not args.publish:
        print('Sin escrituras ni correos. El dry-run no verifica permisos de publicación ni FK remotas.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
