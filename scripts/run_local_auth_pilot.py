"""Launch the optional synthetic pilot on 127.0.0.1:18503, in a separate process."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment', type=Path, default=ROOT / '.local_checks/local-auth-pilot/environment.private.json')
    args = parser.parse_args()
    values = json.loads(args.environment.read_text(encoding='utf-8'))
    env = {key: value for key, value in os.environ.items() if not key.startswith(
        ('PORTAL_', 'COMET_', 'SCOUTING_DATABASE', 'SUPABASE_', 'DB_', 'PG'))}
    env.update(values)
    env['PORTAL_AUTH_PROVIDER'] = 'local_pilot'
    env['SCOUTING_TEST_MODE'] = '1'
    return subprocess.call([sys.executable, '-m', 'streamlit', 'run', str(ROOT / 'app/portal.py'),
                            '--server.address=127.0.0.1', '--server.port=18503',
                            '--server.headless=true', '--browser.gatherUsageStats=false'], cwd=ROOT, env=env)


if __name__ == '__main__':
    raise SystemExit(main())
