"""Stop a real synthetic process tree, without provider or database access."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Event, Timer
import unittest
from unittest.mock import patch


@unittest.skipUnless(sys.platform == 'linux', 'Linux Docker process group semantics')
class ShutdownTests(unittest.TestCase):
    def test_shutdown_stops_parent_and_child(self):
        from scouting import sync_scheduler as scheduler
        with tempfile.TemporaryDirectory() as folder:
            child_file = Path(folder) / 'child.pid'
            command = ['bash', '-c', 'sleep 3600 & echo $! > "$1"; wait', 'synthetic', str(child_file)]
            stop = Event()
            timer = Timer(0.5, stop.set)
            processes = []
            real_popen = subprocess.Popen

            def start(*args, **kwargs):
                process = real_popen(*args, **kwargs)
                processes.append(process)
                return process

            timer.start()
            try:
                with patch.object(scheduler, 'worker_command', return_value=command), \
                     patch.object(scheduler.subprocess, 'Popen', side_effect=start):
                    self.assertEqual(scheduler.execute_worker(Path(folder), stop), 130)
                self.assertIsNotNone(processes[0].poll())
                self.assertTrue(child_file.exists(), 'the synthetic child must actually have started')
                child = Path('/proc') / child_file.read_text().strip() / 'stat'
                if child.exists():
                    self.assertEqual(child.read_text().split()[2], 'Z', 'child must not be running')
            finally:
                timer.cancel()
                for process in processes:
                    if process.poll() is None:
                        os.killpg(process.pid, 9)
                        process.wait()
