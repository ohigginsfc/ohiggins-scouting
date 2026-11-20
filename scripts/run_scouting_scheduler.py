"""Run the weekly scouting scheduler in a foreground process managed by Docker."""
import argparse
import os
from pathlib import Path
import signal
import sys
from threading import Event

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from scouting.sync_scheduler import serve
from scouting.sofascore_leagues import DEFAULT_LEAGUE, LEAGUES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--league', choices=list(LEAGUES), default=DEFAULT_LEAGUE.key)
    parser.add_argument('--folder', type=Path)
    args = parser.parse_args()
    league = LEAGUES[args.league]
    args.folder = args.folder or Path(league.folder)
    if not os.environ.get('SCOUTING_DATABASE_URL') or os.environ.get('DB_SCHEMA') != 'scouting':
        parser.error('SCOUTING_DATABASE_URL and DB_SCHEMA=scouting are required')
    stop = Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    serve(args.folder.resolve(), stop, league=league)


if __name__ == '__main__':
    main()
