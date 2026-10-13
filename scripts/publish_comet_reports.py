"""Reportes y alertas en Google Sheets. Sin --publish solo calcula; no escribe ni envía correo."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from scouting.comet_reports.job import run_reports


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--season')
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--summary-json', type=Path)
    args = parser.parse_args(argv)
    if args.env_file:
        from dotenv import load_dotenv
        if not args.env_file.is_file():
            parser.error('No existe el archivo privado de entorno')
        load_dotenv(args.env_file, override=False)
    try:
        summary = run_reports(publish=args.publish, season=args.season)
        if args.summary_json:
            args.summary_json.parent.mkdir(parents=True, exist_ok=True)
            args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf8')
        print(json.dumps(summary, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f'Reportes COMET: {type(exc).__name__}. Revisar permisos, temporada y contrato; no se confirma publicación completa.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
