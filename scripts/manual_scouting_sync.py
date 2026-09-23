"""Explicit collect/validate/publish commands for manual Chile 2026 updates."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from scouting import manual_sync as sync


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['bootstrap', 'collect', 'validate', 'publish'])
    parser.add_argument('--folder', type=Path, default=Path('data/recovery/manual-2026'))
    parser.add_argument('--source', type=Path)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--lookback-days', type=int, default=14)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.lookback_days <= 365:
        parser.error('lookback-days must be 1..365')
    if args.command == 'bootstrap':
        if not args.source:
            parser.error('bootstrap requires --source')
        print(json.dumps({'cached_matches': sync.bootstrap(args.source, args.folder)}))
    elif args.command == 'collect':
        client = sync.Http()
        try:
            state, frame = sync.collect(args.folder, client.fetch, resume=args.resume, lookback_days=args.lookback_days)
            print(json.dumps({'validated': True, 'matches': len(state['events']), 'players': len(frame)}))
        finally:
            client.close()
    elif args.command == 'validate':
        state = sync.read(args.folder / 'candidate.json')
        frame = sync.validate(state)
        print(json.dumps({'validated': True, 'matches': len(state['events']), 'players': len(frame)}))
    else:
        print(json.dumps(sync.publish(args.folder, apply=args.apply)))


if __name__ == '__main__':
    main()
