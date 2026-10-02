"""Explicit collect/validate/publish commands for manual Chile 2026 updates."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from scouting import manual_sync as sync


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['probe', 'bootstrap', 'collect', 'validate', 'publish'])
    parser.add_argument('--folder', type=Path, default=Path('data/recovery/manual-2026'))
    parser.add_argument('--source', type=Path)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--lookback-days', type=int, default=14)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--max-requests', type=int, default=1200)
    parser.add_argument('--seconds', type=int, default=14400)
    parser.add_argument('--http-profile', default='chrome')
    args = parser.parse_args(argv)
    if not 1 <= args.lookback_days <= 365:
        parser.error('lookback-days must be 1..365')
    if not 1 <= args.max_requests <= 1200 or not 1 <= args.seconds <= 14400:
        parser.error('max-requests must be 1..1200; seconds must be 1..14400')
    if args.command == 'bootstrap':
        if not args.source:
            parser.error('bootstrap requires --source')
        print(json.dumps({'cached_matches': sync.bootstrap(args.source, args.folder)}))
    elif args.command in ('probe', 'collect'):
        client = sync.Http(budget=1 if args.command == 'probe' else args.max_requests,
                           seconds=min(args.seconds, 40) if args.command == 'probe' else args.seconds,
                           profile=args.http_profile)
        try:
            if args.command == 'probe':
                result = sync.probe(client.fetch)
            else:
                state, frame = sync.collect(args.folder, client.fetch, resume=args.resume, lookback_days=args.lookback_days)
                result = {'validated': True, 'matches': len(state['events']), 'players': len(frame)}
            result.update(requests=client.requests, http_profile=client.profile)
            print(json.dumps(result))
        except sync.r.ProviderBlocked as exc:
            print(json.dumps({'status': 'blocked', 'http_status': exc.status,
                              'retry_at': exc.retry_at, 'requests': client.requests,
                              'http_profile': client.profile, 'database_writes': False}))
            return 2
        except (sync.r.BudgetReached, RuntimeError, ValueError) as exc:
            print(json.dumps({'status': 'stopped', 'error_type': type(exc).__name__,
                              'requests': client.requests, 'database_writes': False}))
            return 1
        finally:
            client.close()
    elif args.command == 'validate':
        state = sync.read(args.folder / 'candidate.json')
        frame = sync.validate(state)
        print(json.dumps({'validated': True, 'matches': len(state['events']), 'players': len(frame)}))
    else:
        print(json.dumps(sync.publish(args.folder, apply=args.apply)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
