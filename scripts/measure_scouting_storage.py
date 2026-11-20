"""Measure PostgreSQL storage before/after a coverage expansion, using read-only aggregates."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from scouting.db import get_connection
from scouting.storage_measure import compare, measure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--compare', type=Path)
    args = parser.parse_args()
    try:
        with get_connection() as conn:
            snapshot = measure(conn)
        if args.compare:
            snapshot['comparison'] = compare(json.loads(args.compare.read_text(encoding='utf-8')), snapshot)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(snapshot, indent=2), encoding='utf-8')
        print(json.dumps(snapshot))
        return 0
    except Exception as exc:
        print(json.dumps(dict(status='failed', error_type=type(exc).__name__)))
        return 1


if __name__ == '__main__':
    sys.exit(main())
