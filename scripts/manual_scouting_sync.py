"""Explicit collect/validate/publish commands for manual Chile 2026 updates."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from scouting import manual_sync as sync
from scouting.sofascore_leagues import DEFAULT_LEAGUE, LEAGUES


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['probe', 'bootstrap', 'collect', 'validate', 'publish', 'weekly'])
    parser.add_argument('--league', choices=list(LEAGUES), default=DEFAULT_LEAGUE.key)
    parser.add_argument('--folder', type=Path)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--lookback-days', type=int, default=14)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--max-requests', type=int, default=1200)
    parser.add_argument('--seconds', type=int, default=14400)
    parser.add_argument('--http-profile', default='chrome')
    args = parser.parse_args(argv)
    league = LEAGUES[args.league]
    args.folder = args.folder or Path(league.folder)
    options = {} if league == DEFAULT_LEAGUE else {'league': league}
    if not 1 <= args.lookback_days <= 365:
        parser.error('lookback-days must be 1..365')
    if not 1 <= args.max_requests <= 1200 or not 1 <= args.seconds <= 14400:
        parser.error('max-requests must be 1..1200; seconds must be 1..14400')
    if args.command == 'bootstrap':
        if not args.source:
            parser.error('bootstrap requires --source')
        print(json.dumps({'cached_matches': sync.bootstrap(args.source, args.folder, **options)}))
    elif args.command in ('probe', 'collect', 'weekly'):
        if args.command == 'weekly' and args.apply:
            import os
            if not os.environ.get('SCOUTING_DATABASE_URL') or os.environ.get('DB_SCHEMA') != 'scouting':
                parser.error('weekly --apply requires SCOUTING_DATABASE_URL and DB_SCHEMA=scouting')
        client = sync.Http(budget=1 if args.command == 'probe' else args.max_requests,
                           seconds=min(args.seconds, 40) if args.command == 'probe' else args.seconds,
                           profile=args.http_profile)
        try:
            if args.command == 'probe':
                result = sync.probe(client.fetch, **options)
            elif args.command == 'weekly':
                from scouting.scheduled_sync import run
                result = run(args.folder, client.fetch, apply=args.apply, lookback_days=args.lookback_days, **options)
            else:
                state, frame = sync.collect(args.folder, client.fetch, resume=args.resume, lookback_days=args.lookback_days, **options)
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
        frame = sync.validate(state, **options)
        print(json.dumps({'validated': True, 'matches': len(state['events']), 'players': len(frame)}))
    else:
        print(json.dumps(sync.publish(args.folder, apply=args.apply, **options)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
