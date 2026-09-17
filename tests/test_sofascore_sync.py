"""Pruebas de evaluación sync Sofascore y clasificación de eventos (sin red)."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _load_incremental_module():
    """Carga update_sofascore_incremental con stubs mínimos de scraper/pipeline."""
    # Stubs para imports pesados del script.
    if "sofascore_scraper" not in sys.modules:
        scraper = types.ModuleType("sofascore_scraper")
        sys.modules["sofascore_scraper"] = scraper
    else:
        scraper = sys.modules["sofascore_scraper"]

    def compute_event_checksum(event):
        return f"chk-{event.get('id')}"

    def is_event_finished(event):
        return (event.get("status") or {}).get("type") == "finished"

    def event_datetime_utc(event):
        return None

    scraper.compute_event_checksum = compute_event_checksum
    scraper.is_event_finished = is_event_finished
    scraper.event_datetime_utc = event_datetime_utc
    scraper.DEFAULT_DELAY_DETAILS = 0
    scraper.DEFAULT_DELAY_EVENTS = 0
    scraper.DEFAULT_DELAY_FALLBACK = 0
    scraper.DEFAULT_DELAY_INCIDENTS = 0
    scraper.DEFAULT_DELAY_LINEUP = 0
    scraper.ScraperConfig = getattr(scraper, "ScraperConfig", object)
    scraper.build_driver = getattr(scraper, "build_driver", lambda **kw: None)
    scraper.get_all_events = getattr(scraper, "get_all_events", lambda *a, **k: [])
    scraper.init_fetch_context = getattr(scraper, "init_fetch_context", lambda **kw: None)
    scraper.load_checkpoint = getattr(scraper, "load_checkpoint", lambda *a, **k: [])
    scraper.merge_events_by_id = getattr(scraper, "merge_events_by_id", lambda a, b: b)
    scraper.process_finished_event = getattr(
        scraper, "process_finished_event", lambda *a, **k: ([], None)
    )
    scraper.remove_event_from_checkpoint = getattr(
        scraper, "remove_event_from_checkpoint", lambda a, b: a
    )
    scraper.append_entries_to_checkpoint = getattr(
        scraper, "append_entries_to_checkpoint", lambda a, b: a
    )
    scraper.save_json = getattr(scraper, "save_json", lambda *a, **k: None)

    if "run_all_sofascore_pipeline" not in sys.modules:
        pipe = types.ModuleType("run_all_sofascore_pipeline")

        class LeagueConfig:
            def __init__(self, **kw):
                self.__dict__.update(kw)
                self.season = kw.get("season")

        pipe.LeagueConfig = LeagueConfig
        pipe.LEAGUES = []
        pipe.filter_leagues = lambda x: []
        pipe.import_league = lambda *a, **k: None
        pipe.league_output_dir = lambda root, lg: Path("/tmp")
        pipe.project_root = lambda: ROOT
        pipe.reaggregate_league_from_checkpoint = lambda *a, **k: (True, "ok")
        pipe.stage_league = lambda *a, **k: Path("/tmp")
        pipe.validate_sofascore_output = lambda *a, **k: (True, "ok")
        sys.modules["run_all_sofascore_pipeline"] = pipe

    path = SCRIPTS / "update_sofascore_incremental.py"
    # Recargar siempre para enlazar compute_event_checksum actualizado.
    mod_name = "update_sofascore_incremental"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


class FakeCursor:
    def __init__(self, shared_responses: list):
        self._responses = shared_responses
        self._current = None

    def execute(self, sql, params=None):
        self._current = self._responses.pop(0) if self._responses else None

    def fetchone(self):
        if self._current is None:
            return (0,)
        if isinstance(self._current, list):
            return None
        return self._current

    def fetchall(self):
        if isinstance(self._current, list):
            return self._current
        return []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeConn:
    def __init__(self, responses: list):
        self._responses = list(responses)

    def cursor(self):
        return FakeCursor(self._responses)


class AssessSeasonSyncTests(unittest.TestCase):
    def test_demo_only_needs_backfill(self):
        from scouting.services import sofascore_sync_assessment as mod

        # origins: sofascore=0, demo=424, total=424; ingestion empty; batches=0
        responses = [
            (0,),  # sofascore metrics
            (424,),  # demo
            (424,),  # total
            [],  # ingestion group by
            (0,),  # batches
            (0,),  # sofascore players
            (10,),  # demo only players
        ]
        conn = FakeConn(responses)
        result = mod.assess_season_sync(conn, "2025")
        self.assertTrue(result.needs_initial_backfill)
        self.assertEqual(result.demo_metrics, 424)
        self.assertEqual(result.sofascore_metrics, 0)
        self.assertTrue(any("demo" in r.lower() for r in result.reasons))

    def test_real_metrics_no_backfill(self):
        from scouting.services import sofascore_sync_assessment as mod

        responses = [
            (8000,),  # sofascore
            (424,),  # demo
            (8424,),  # total
            [("processed", 120)],  # ingestion
            (3,),  # batches
            (300,),  # players
            (5,),  # demo only
        ]
        conn = FakeConn(responses)
        result = mod.assess_season_sync(conn, "2025")
        self.assertFalse(result.needs_initial_backfill)
        self.assertEqual(result.sofascore_metrics, 8000)

    def test_processed_events_without_metrics_needs_backfill(self):
        from scouting.services import sofascore_sync_assessment as mod

        responses = [
            (0,),
            (0,),
            (0,),
            [("processed", 50)],
            (0,),
            (0,),
            (0,),
        ]
        conn = FakeConn(responses)
        result = mod.assess_season_sync(conn, "2025")
        self.assertTrue(result.needs_initial_backfill)
        self.assertTrue(any("processed" in r.lower() for r in result.reasons))


class ClassifyEventsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inc = _load_incremental_module()

    def _finished(self, event_id: int) -> dict:
        return {"id": event_id, "status": {"type": "finished"}}

    def test_force_all_finished_treats_processed_as_candidates(self):
        events = [self._finished(1), self._finished(2)]
        known = {
            1: {"processing_status": "processed", "checksum": "chk-1"},
            2: {"processing_status": "processed", "checksum": "chk-2"},
        }
        candidates, stats = self.inc.classify_events(
            events, known, force_event_ids=None, since=None, force_all_finished=True
        )
        self.assertEqual(len(candidates), 2)
        self.assertEqual(stats["updated_events"], 2)
        pending = stats["new_events"] + stats["updated_events"] + stats["pending_events"]
        self.assertEqual(pending, 2)

    def test_without_force_skips_already_processed(self):
        events = [self._finished(1)]
        known = {1: {"processing_status": "processed", "checksum": "chk-1"}}
        candidates, stats = self.inc.classify_events(
            events, known, force_event_ids=None, since=None, force_all_finished=False
        )
        self.assertEqual(candidates, [])
        self.assertEqual(stats["already_processed"], 1)

    def test_new_event_is_candidate(self):
        events = [self._finished(9)]
        candidates, stats = self.inc.classify_events(
            events, {}, force_event_ids=None, since=None, force_all_finished=False
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(stats["new_events"], 1)

    def test_figures_independent_payload_totals(self):
        from scouting.services import sofascore_incremental_runner as runner

        payload = {
            "leagues": [
                {
                    "downloaded": 10,
                    "players_updated": 5,
                    "metrics_imported": 100,
                    "errors": 1,
                    "total_calendar": 20,
                    "new_events": 4,
                    "updated_events": 2,
                },
                {
                    "downloaded": 3,
                    "players_updated": 1,
                    "metrics_imported": 50,
                    "errors": 0,
                    "total_calendar": 8,
                    "new_events": 1,
                    "updated_events": 0,
                },
            ]
        }
        totals = runner._payload_totals(payload)
        self.assertEqual(totals["downloaded"], 13)
        self.assertEqual(totals["metrics_imported"], 150)
        self.assertEqual(totals["errors"], 1)
        self.assertEqual(totals["remote_events"], 28)


class RunnerDecisionTests(unittest.TestCase):
    def test_incremental_forces_backfill_when_assessment_needs_it(self):
        from scouting.services import sofascore_incremental_runner as runner

        calls: list[list[str]] = []

        def fake_exec(args, **kwargs):
            calls.append(list(args))
            return runner.WorkerRunOutput(
                ok=True,
                command="fake",
                stdout="",
                stderr="",
                returncode=0,
                log_path=None,
                json_payload={
                    "active_season": "2025",
                    "historical_leagues_skipped": 1,
                    "leagues_checked": ["cl_primera_2025"],
                    "leagues": [
                        {
                            "slug": "cl_primera_2025",
                            "competition": "Primera",
                            "tournament_id": 11653,
                            "season_id": 88493,
                            "downloaded": 5,
                            "players_updated": 40,
                            "metrics_imported": 200,
                            "errors": 0,
                            "total_calendar": 10,
                            "new_events": 10,
                            "updated_events": 0,
                            "pending_events": 0,
                            "pending_total": 10,
                        }
                    ],
                },
            )

        orig_exec = runner._execute_worker
        orig_docker = runner.check_docker_runtime
        orig_assess = runner._load_season_assessment
        orig_progress = runner.is_update_in_progress
        orig_save = runner.save_ui_state
        orig_lock = runner.LOCK_PATH
        try:
            runner._execute_worker = fake_exec  # type: ignore[assignment]
            runner.check_docker_runtime = lambda: runner.DockerRuntimeInfo(  # type: ignore[assignment]
                ok=True,
                docker_path="/usr/bin/docker",
                docker_version="1",
                compose_invocation=("docker", "compose"),
                compose_version="1",
                socket_present=True,
                socket_readable=True,
            )
            runner._load_season_assessment = lambda season: {  # type: ignore[assignment]
                "season": season,
                "sofascore_metrics": 0,
                "demo_metrics": 424,
                "needs_initial_backfill": True,
                "reasons": ["Solo hay métricas demo"],
            }
            runner.is_update_in_progress = lambda: False  # type: ignore[assignment]
            runner.save_ui_state = lambda result: None  # type: ignore[assignment]
            tmp_lock = Path("/tmp/sofascore_test_update.lock")
            runner.LOCK_PATH = tmp_lock  # type: ignore[assignment]
            result = runner.run_incremental_all_for_ui()
            self.assertTrue(result.ok)
            self.assertIn("--force-backfill", calls[0])
            self.assertEqual(result.matches_downloaded, 5)
            self.assertEqual(result.metrics_imported, 200)
            self.assertNotEqual(result.status, "no_news")
        finally:
            runner._execute_worker = orig_exec  # type: ignore[assignment]
            runner.check_docker_runtime = orig_docker  # type: ignore[assignment]
            runner._load_season_assessment = orig_assess  # type: ignore[assignment]
            runner.is_update_in_progress = orig_progress  # type: ignore[assignment]
            runner.save_ui_state = orig_save  # type: ignore[assignment]
            runner.LOCK_PATH = orig_lock  # type: ignore[assignment]
            if tmp_lock.is_file():
                tmp_lock.unlink()

    def test_remote_error_is_not_no_news(self):
        from scouting.services import sofascore_incremental_runner as runner

        def fake_exec(args, **kwargs):
            return runner.WorkerRunOutput(
                ok=False,
                command="fake",
                stdout="",
                stderr="boom",
                returncode=1,
                log_path=None,
                error_message="HTTP 403",
                json_payload=None,
            )

        orig_exec = runner._execute_worker
        orig_docker = runner.check_docker_runtime
        orig_assess = runner._load_season_assessment
        orig_progress = runner.is_update_in_progress
        orig_save = runner.save_ui_state
        orig_lock = runner.LOCK_PATH
        tmp_lock = Path("/tmp/sofascore_test_update_err.lock")
        try:
            runner._execute_worker = fake_exec  # type: ignore[assignment]
            runner.check_docker_runtime = lambda: runner.DockerRuntimeInfo(  # type: ignore[assignment]
                ok=True,
                docker_path="/usr/bin/docker",
                docker_version="1",
                compose_invocation=("docker", "compose"),
                compose_version="1",
                socket_present=True,
                socket_readable=True,
            )
            runner._load_season_assessment = lambda season: {  # type: ignore[assignment]
                "season": season,
                "sofascore_metrics": 0,
                "demo_metrics": 10,
                "needs_initial_backfill": True,
                "reasons": ["demo"],
            }
            runner.is_update_in_progress = lambda: False  # type: ignore[assignment]
            runner.save_ui_state = lambda result: None  # type: ignore[assignment]
            runner.LOCK_PATH = tmp_lock  # type: ignore[assignment]
            result = runner.run_incremental_all_for_ui()
            self.assertFalse(result.ok)
            self.assertEqual(result.status, "error")
            self.assertNotEqual(result.status, "no_news")
        finally:
            runner._execute_worker = orig_exec  # type: ignore[assignment]
            runner.check_docker_runtime = orig_docker  # type: ignore[assignment]
            runner._load_season_assessment = orig_assess  # type: ignore[assignment]
            runner.is_update_in_progress = orig_progress  # type: ignore[assignment]
            runner.save_ui_state = orig_save  # type: ignore[assignment]
            runner.LOCK_PATH = orig_lock  # type: ignore[assignment]
            if tmp_lock.is_file():
                tmp_lock.unlink()


if __name__ == "__main__":
    unittest.main()
