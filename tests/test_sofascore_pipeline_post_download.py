"""Pruebas del pipeline post-descarga Sofascore (preflight / process-existing)."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _load_incremental():
    # Minimal stubs already may exist from other tests.
    if "sofascore_scraper" not in sys.modules:
        scraper = types.ModuleType("sofascore_scraper")
        scraper.compute_event_checksum = lambda e: f"chk-{e.get('id')}"
        scraper.is_event_finished = lambda e: (e.get("status") or {}).get("type") == "finished"
        scraper.event_datetime_utc = lambda e: None
        scraper.DEFAULT_DELAY_DETAILS = 0
        scraper.DEFAULT_DELAY_EVENTS = 0
        scraper.DEFAULT_DELAY_FALLBACK = 0
        scraper.DEFAULT_DELAY_INCIDENTS = 0
        scraper.DEFAULT_DELAY_LINEUP = 0
        scraper.ScraperConfig = object
        scraper.build_driver = lambda **kw: None
        scraper.get_all_events = lambda *a, **k: []
        scraper.init_fetch_context = lambda **kw: None
        scraper.load_checkpoint = lambda *a, **k: {}
        scraper.merge_events_by_id = lambda a, b: b or a
        scraper.process_finished_event = lambda *a, **k: ([], None)
        scraper.remove_event_from_checkpoint = lambda a, b: a
        scraper.append_entries_to_checkpoint = lambda a, b: a
        scraper.save_json = lambda *a, **k: None
        sys.modules["sofascore_scraper"] = scraper

    path = SCRIPTS / "update_sofascore_incremental.py"
    name = "update_sofascore_incremental_preflight"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class PreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inc = _load_incremental()

    def test_preflight_fails_when_reaggregate_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "src" / "scouting" / "ingestion").mkdir(parents=True)
            (root / "src" / "scouting" / "ingestion" / "import_sofascore_player_stats_csv.py").write_text(
                "# stub\n", encoding="utf-8"
            )
            (root / "scripts" / "stage_sofascore_output.py").write_text("# stub\n", encoding="utf-8")
            # intentionally no reaggregate script
            with self.assertRaises(SystemExit) as ctx:
                self.inc.preflight_pipeline(root, require_browser=False, require_db=False)
            self.assertEqual(ctx.exception.code, 2)

    def test_preflight_ok_when_scripts_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "reaggregate_sofascore_outputs.py").write_text("# ok\n", encoding="utf-8")
            (scripts / "stage_sofascore_output.py").write_text("# ok\n", encoding="utf-8")
            ing = root / "src" / "scouting" / "ingestion"
            ing.mkdir(parents=True)
            (ing / "import_sofascore_player_stats_csv.py").write_text("# ok\n", encoding="utf-8")
            self.inc.preflight_pipeline(root, require_browser=False, require_db=False)


class ProcessExistingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inc = _load_incremental()

    def test_finalize_without_checkpoint_errors(self):
        from run_all_sofascore_pipeline import LeagueConfig

        league = LeagueConfig(
            country="cl",
            division="primera",
            competition="Primera",
            tournament_id=1,
            season_id=1,
            output_slug="cl_primera_2025",
            season="2025",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "web_scraping_sofascore" / "sofascore_output" / "cl_primera_2025"
            out.mkdir(parents=True)
            result = self.inc.LeagueIncrementalResult(league=league)
            out_res = self.inc.finalize_league_from_checkpoint(
                root, league, "2025", result, skip_import=True, use_replace=True
            )
            self.assertGreaterEqual(out_res.errors, 1)

    def test_reaggregate_missing_script_returns_error(self):
        # Cargar el módulo real por ruta: otros tests pueden haber dejado un stub en sys.modules.
        path = SCRIPTS / "run_all_sofascore_pipeline.py"
        spec = importlib.util.spec_from_file_location("run_all_sofascore_pipeline_real", path)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        sys.modules["run_all_sofascore_pipeline_real"] = mod
        spec.loader.exec_module(mod)
        LeagueConfig = mod.LeagueConfig
        reaggregate_league_from_checkpoint = mod.reaggregate_league_from_checkpoint

        league = LeagueConfig(
            country="cl",
            division="primera",
            competition="Primera",
            tournament_id=1,
            season_id=1,
            output_slug="cl_primera_2025",
            season="2025",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            league_dir = root / "web_scraping_sofascore" / "sofascore_output" / "cl_primera_2025"
            league_dir.mkdir(parents=True)
            (league_dir / "checkpoint_raw.json").write_text("{}", encoding="utf-8")
            ok, reason = reaggregate_league_from_checkpoint(
                root, league, dry_run=False, backup=False
            )
            self.assertFalse(ok)
            self.assertIn("reaggregate_sofascore_outputs.py", reason)


class DemoRealPreferenceTests(unittest.TestCase):
    def test_dashboard_prefers_sofascore_over_demo(self):
        from scouting.services import dashboard_service

        class FakeConn:
            pass

        with patch("scouting.services.metrics_service.count_metrics", return_value=100):
            with patch("scouting.services.metrics_service.count_demo_metrics", return_value=424):
                with patch(
                    "scouting.repositories.players_repository.count_players_with_subjective_reports",
                    return_value=1,
                ):
                    with patch("scouting.services.reports_service.count_reports", return_value=1):
                        with patch(
                            "scouting.services.reports_service.count_hidden_reports", return_value=0
                        ):
                            with patch(
                                "scouting.repositories.dashboard_repository.count_distinct_scouts",
                                return_value=1,
                            ):
                                with patch(
                                    "scouting.repositories.dashboard_repository.count_players_hybrid",
                                    return_value=0,
                                ):
                                    with patch(
                                        "scouting.services.players_service.count_players",
                                        return_value=10,
                                    ):
                                        with patch(
                                            "scouting.services.reports_service.fetch_recent_reports",
                                            return_value=[],
                                        ):
                                            snap = dashboard_service.get_dashboard_snapshot(FakeConn())
        self.assertEqual(snap["metric_count"], 100)
        self.assertFalse(snap["metrics_are_demo"])
        self.assertEqual(snap["metrics_label"], "Métricas objetivas")

    def test_dashboard_falls_back_to_demo_label(self):
        from scouting.services import dashboard_service

        class FakeConn:
            pass

        with patch("scouting.services.metrics_service.count_metrics", return_value=0):
            with patch("scouting.services.metrics_service.count_demo_metrics", return_value=424):
                with patch(
                    "scouting.repositories.players_repository.count_players_with_subjective_reports",
                    return_value=1,
                ):
                    with patch("scouting.services.reports_service.count_reports", return_value=1):
                        with patch(
                            "scouting.services.reports_service.count_hidden_reports", return_value=0
                        ):
                            with patch(
                                "scouting.repositories.dashboard_repository.count_distinct_scouts",
                                return_value=1,
                            ):
                                with patch(
                                    "scouting.repositories.dashboard_repository.count_players_hybrid",
                                    return_value=0,
                                ):
                                    with patch(
                                        "scouting.services.players_service.count_players",
                                        return_value=10,
                                    ):
                                        with patch(
                                            "scouting.services.reports_service.fetch_recent_reports",
                                            return_value=[],
                                        ):
                                            snap = dashboard_service.get_dashboard_snapshot(FakeConn())
        self.assertEqual(snap["metric_count"], 424)
        self.assertTrue(snap["metrics_are_demo"])
        self.assertEqual(snap["metrics_label"], "Métricas demo")


if __name__ == "__main__":
    unittest.main()
