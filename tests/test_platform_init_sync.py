"""Pruebas del plan de sync plataforma e init demo."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from scouting.services.platform_sync_plan import (  # noqa: E402
    assess_platform_sync,
)
from scouting.services.sofascore_sync_assessment import SeasonSyncAssessment  # noqa: E402


class PlatformSyncPlanTests(unittest.TestCase):
    def _assessment(self, season: str, sofascore: int, demo: int = 0) -> SeasonSyncAssessment:
        return SeasonSyncAssessment(
            season=season,
            sofascore_metrics=sofascore,
            demo_metrics=demo,
            needs_initial_backfill=sofascore <= 0,
        )

    @patch("scouting.services.platform_sync_plan.count_metrics_by_origin")
    @patch("scouting.services.platform_sync_plan.assess_season_sync")
    @patch("scouting.services.platform_sync_plan.get_historical_season", return_value="2024")
    @patch("scouting.services.platform_sync_plan.get_active_season", return_value="2025")
    def test_demo_only_plan_downloads_both(self, _a, _h, mock_assess, mock_totals):
        mock_assess.side_effect = [
            self._assessment("2025", 0, 424),
            self._assessment("2024", 0, 201),
        ]
        mock_totals.return_value = {"demo": 625, "sofascore": 0, "other": 0, "total": 625}
        plan = assess_platform_sync(MagicMock())
        self.assertEqual(plan.state, "initial_sync_required")
        self.assertEqual(plan.button_label, "Descargar datos reales")
        self.assertEqual(len(plan.worker_steps), 2)
        self.assertIn("--force-backfill", plan.worker_steps[0])
        self.assertIn("cl_primera_2024", plan.worker_steps[0])
        self.assertIn("2025", plan.worker_steps[1])

    @patch("scouting.services.platform_sync_plan.count_metrics_by_origin")
    @patch("scouting.services.platform_sync_plan.assess_season_sync")
    @patch("scouting.services.platform_sync_plan.get_historical_season", return_value="2024")
    @patch("scouting.services.platform_sync_plan.get_active_season", return_value="2025")
    def test_missing_historical_plan(self, _a, _h, mock_assess, mock_totals):
        mock_assess.side_effect = [
            self._assessment("2025", 1000, 0),
            self._assessment("2024", 0, 201),
        ]
        mock_totals.return_value = {"demo": 201, "sofascore": 1000, "other": 0, "total": 1201}
        plan = assess_platform_sync(MagicMock())
        self.assertEqual(plan.state, "historical_sync_required")
        self.assertEqual(plan.button_label, "Completar datos históricos")

    @patch("scouting.services.platform_sync_plan.count_metrics_by_origin")
    @patch("scouting.services.platform_sync_plan.assess_season_sync")
    @patch("scouting.services.platform_sync_plan.get_historical_season", return_value="2024")
    @patch("scouting.services.platform_sync_plan.get_active_season", return_value="2025")
    def test_fully_initialized_incremental(self, _a, _h, mock_assess, mock_totals):
        mock_assess.side_effect = [
            self._assessment("2025", 1000, 0),
            self._assessment("2024", 500, 0),
        ]
        mock_totals.return_value = {"demo": 625, "sofascore": 1500, "other": 0, "total": 2125}
        plan = assess_platform_sync(MagicMock())
        self.assertEqual(plan.state, "fully_initialized")
        self.assertEqual(plan.button_label, "Buscar nuevos partidos")
        self.assertEqual(plan.worker_steps, [])

    @patch("scouting.services.sofascore_sync_assessment.count_sofascore_players", return_value=0)
    @patch("scouting.services.platform_sync_plan.count_metrics_by_origin")
    @patch("scouting.services.platform_sync_plan.assess_season_sync")
    @patch("scouting.services.platform_sync_plan.get_historical_season", return_value="2024")
    @patch("scouting.services.platform_sync_plan.get_active_season", return_value="2025")
    def test_current_sync_required_only_active_backfill(
        self, _a, _h, mock_assess, mock_totals, _players
    ):
        mock_assess.side_effect = [
            self._assessment("2025", 0, 424),
            self._assessment("2024", 19607, 201),
        ]
        mock_totals.return_value = {"demo": 625, "sofascore": 19607, "other": 0, "total": 20232}
        plan = assess_platform_sync(MagicMock())
        self.assertEqual(plan.state, "current_sync_required")
        self.assertEqual(plan.button_label, "Descargar temporada actual")
        self.assertEqual(len(plan.worker_steps), 1)
        step = plan.worker_steps[0]
        self.assertIn("--all", step)
        self.assertIn("--season", step)
        self.assertIn("2025", step)
        self.assertIn("--force-backfill", step)
        self.assertNotIn("cl_primera_2024", step)
        self.assertIn("2024 están disponibles", plan.banner_message)
        self.assertEqual(plan.historical_sofascore_metrics, 19607)


class ShouldSeedDemoTests(unittest.TestCase):
    def test_skip_when_sofascore_present(self):
        from init_database import should_seed_demo

        with patch(
            "scouting.services.sofascore_sync_assessment.count_metrics_by_origin",
            return_value={"sofascore": 10, "demo": 625, "other": 0, "total": 635},
        ):
            do_seed, reason = should_seed_demo(MagicMock())
        self.assertFalse(do_seed)
        self.assertIn("Sofascore", reason)

    def test_seed_when_empty(self):
        from init_database import should_seed_demo

        with patch(
            "scouting.services.sofascore_sync_assessment.count_metrics_by_origin",
            return_value={"sofascore": 0, "demo": 0, "other": 0, "total": 0},
        ):
            do_seed, reason = should_seed_demo(MagicMock())
        self.assertTrue(do_seed)
        self.assertIn("sin métricas", reason.lower())

    def test_skip_when_demo_complete(self):
        from init_database import should_seed_demo

        with patch(
            "scouting.services.sofascore_sync_assessment.count_metrics_by_origin",
            return_value={"sofascore": 0, "demo": 625, "other": 0, "total": 625},
        ):
            do_seed, reason = should_seed_demo(MagicMock())
        self.assertFalse(do_seed)


class BackgroundLockTests(unittest.TestCase):
    def test_start_background_respects_existing_lock(self):
        from scouting.services import sofascore_incremental_runner as runner

        with patch.object(runner, "is_update_in_progress", return_value=True):
            with patch.object(runner, "load_platform_sync_plan", return_value={
                "state": "initial_sync_required",
                "button_label": "Descargar datos reales",
            }):
                with patch.object(
                    runner,
                    "check_docker_runtime",
                    return_value=type("R", (), {"ok": True, "diagnostics_text": "ok"})(),
                ):
                    result = runner.start_dashboard_sync_background()
        self.assertEqual(result.status, "running")
        self.assertTrue(result.locked)


if __name__ == "__main__":
    unittest.main()
