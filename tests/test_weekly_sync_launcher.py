"""Execute the Linux cron launcher with a fake Docker command and no network."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.platform == 'linux' and shutil.which('bash') and shutil.which('flock'),
                     'Linux cron launcher requires bash and flock')
class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'scripts').mkdir()
        self.launcher = self.root / 'scripts/sync_scouting_weekly.sh'
        source = Path(__file__).resolve().parents[1] / 'scripts/sync_scouting_weekly.sh'
        self.launcher.write_text(source.read_text(encoding='utf-8'), encoding='utf-8')
        (self.root / '.env.portal').write_text('# synthetic; never a real connection\n')
        (self.root / 'bin').mkdir()
        docker = self.root / 'bin/docker'
        docker.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$STUB_OUTPUT"\nexit "${STUB_EXIT:-0}"\n')
        docker.chmod(0o700)
        self.output = self.root / 'arguments.txt'
        self.env = dict(os.environ, PATH=str(self.root / 'bin') + os.pathsep + os.environ['PATH'],
                        STUB_OUTPUT=str(self.output))
        self.env.pop('SCOUTING_SYNC_ENV_FILE', None)
        self.env.pop('STUB_EXIT', None)

    def invoke(self):
        return subprocess.run(['bash', str(self.launcher)], cwd='/', env=self.env,
                              capture_output=True, text=True, timeout=15)

    def test_runs_once_from_any_directory_with_explicit_limits_and_apply(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.output.read_text().splitlines(), [
            'compose', '--env-file', '.env.portal', '-f', 'docker-compose.sync.yml',
            'run', '--rm', '-T', '--no-deps', 'publisher', 'weekly', '--apply',
            '--max-requests', '240', '--seconds', '1800'])

    def test_missing_private_environment_stops_before_docker(self):
        (self.root / '.env.portal').unlink()
        self.assertEqual(self.invoke().returncode, 1)
        self.assertFalse(self.output.exists())

    def test_worker_failure_is_returned_to_cron(self):
        self.env['STUB_EXIT'] = '2'
        self.assertEqual(self.invoke().returncode, 2)

    def test_overlapping_run_is_rejected_before_docker(self):
        import fcntl
        (self.root / 'data/recovery/manual-2026').mkdir(parents=True)
        with (self.root / 'data/recovery/manual-2026/weekly.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(self.invoke().returncode, 75)
        self.assertFalse(self.output.exists())
