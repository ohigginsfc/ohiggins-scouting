"""Pruebas de política demo/Sofascore y comparación histórica O'Higgins."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scouting.services.objective_origin_policy import (  # noqa: E402
    SOURCE_TYPE_DEMO,
    SOURCE_TYPE_SOFASCORE,
    can_compare_seasons,
    OriginResolution,
)
from scouting.services import season_comparison_service  # noqa: E402


class OriginPolicyTests(unittest.TestCase):
    def test_prefer_sofascore_when_both_exist(self) -> None:
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.return_value = (100, 50)  # sofascore, demo
        conn.cursor.return_value.__enter__.return_value = cur

        from scouting.services.objective_origin_policy import resolve_scope_origin

        res = resolve_scope_origin(conn, season="2025")
        self.assertEqual(res.origin, SOURCE_TYPE_SOFASCORE)
        self.assertFalse(res.demo_mode)

    def test_demo_fallback_when_no_sofascore(self) -> None:
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.return_value = (0, 201)
        conn.cursor.return_value.__enter__.return_value = cur

        from scouting.services.objective_origin_policy import resolve_scope_origin

        res = resolve_scope_origin(conn, season="2024")
        self.assertEqual(res.origin, SOURCE_TYPE_DEMO)
        self.assertTrue(res.demo_mode)

    def test_compare_real_vs_demo_blocked_by_default(self) -> None:
        active = OriginResolution(SOURCE_TYPE_SOFASCORE, False, 100, 0)
        hist = OriginResolution(SOURCE_TYPE_DEMO, True, 0, 50)
        ok, msg = can_compare_seasons(active, hist, allow_demo_fallback=False)
        self.assertFalse(ok)
        self.assertIn("Sofascore", msg or "")

    def test_compare_real_vs_real_allowed(self) -> None:
        active = OriginResolution(SOURCE_TYPE_SOFASCORE, False, 100, 0)
        hist = OriginResolution(SOURCE_TYPE_SOFASCORE, False, 80, 0)
        ok, msg = can_compare_seasons(active, hist)
        self.assertTrue(ok)
        self.assertIsNone(msg)

    def test_compare_with_demo_fallback_warns(self) -> None:
        active = OriginResolution(SOURCE_TYPE_SOFASCORE, False, 100, 0)
        hist = OriginResolution(SOURCE_TYPE_DEMO, True, 0, 50)
        ok, msg = can_compare_seasons(active, hist, allow_demo_fallback=True)
        self.assertTrue(ok)
        self.assertIn("demo", (msg or "").lower())


class SeasonLinkTests(unittest.TestCase):
    def _row(self, pid: int, name: str, team: str, season: str) -> dict:
        return {
            "player_id": pid,
            "player_name": name,
            "objective_team": team,
            "objective_position_group": "MF",
            "season": season,
            "competition": "Primera División Chile",
            "metrics_count": 10,
        }

    @patch("scouting.services.season_comparison_service.players_repository.get_player_by_id")
    @patch("scouting.services.season_comparison_service._sofascore_external_ids")
    @patch("scouting.services.season_comparison_service._summary_rows")
    @patch("scouting.services.season_comparison_service.assess_season_comparison_gate")
    def test_external_id_links_players(
        self, mock_gate, mock_summary, mock_ext, mock_player
    ) -> None:
        mock_gate.return_value = season_comparison_service.SeasonComparisonGate(
            allowed=True,
            message=None,
            origin_active=SOURCE_TYPE_SOFASCORE,
            origin_historical=SOURCE_TYPE_SOFASCORE,
            demo_mode_active=False,
            demo_mode_historical=False,
        )
        mock_summary.side_effect = [
            [self._row(1, "Juan Perez", "O'Higgins", "2025")],
            [self._row(99, "Juan Perez", "O'Higgins", "2024")],
        ]
        mock_ext.side_effect = lambda _c, pid: {"ext-1"} if pid in (1, 99) else set()
        mock_player.return_value = {"full_name": "Juan Perez", "position": "MF"}

        gate, cands = season_comparison_service.list_ohiggins_season_comparison_candidates(
            MagicMock()
        )
        self.assertTrue(gate.allowed)
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0].status, "comparable")
        self.assertEqual(cands[0].link_method, "external_id")
        self.assertEqual(cands[0].player_id_historical, 99)

    @patch("scouting.services.season_comparison_service.players_repository.get_player_by_id")
    @patch("scouting.services.season_comparison_service._sofascore_external_ids")
    @patch("scouting.services.season_comparison_service._summary_rows")
    @patch("scouting.services.season_comparison_service.assess_season_comparison_gate")
    def test_same_name_different_external_id_not_mixed(
        self, mock_gate, mock_summary, mock_ext, mock_player
    ) -> None:
        mock_gate.return_value = season_comparison_service.SeasonComparisonGate(
            allowed=True,
            message=None,
            origin_active=SOURCE_TYPE_SOFASCORE,
            origin_historical=SOURCE_TYPE_SOFASCORE,
            demo_mode_active=False,
            demo_mode_historical=False,
        )
        mock_summary.side_effect = [
            [self._row(1, "Juan Perez", "O'Higgins", "2025")],
            [self._row(99, "Juan Perez", "O'Higgins", "2024")],
        ]
        mock_ext.side_effect = lambda _c, pid: {"ext-a"} if pid == 1 else {"ext-b"}
        mock_player.return_value = {"full_name": "Juan Perez", "position": "MF"}

        _, cands = season_comparison_service.list_ohiggins_season_comparison_candidates(
            MagicMock()
        )
        self.assertEqual(cands[0].status, "no_historical_data")
        self.assertIsNone(cands[0].row_historical)

    @patch("scouting.services.season_comparison_service.players_repository.get_player_by_id")
    @patch("scouting.services.season_comparison_service._sofascore_external_ids")
    @patch("scouting.services.season_comparison_service._summary_rows")
    @patch("scouting.services.season_comparison_service.assess_season_comparison_gate")
    def test_new_signing_no_historical(
        self, mock_gate, mock_summary, mock_ext, mock_player
    ) -> None:
        mock_gate.return_value = season_comparison_service.SeasonComparisonGate(
            allowed=True,
            message=None,
            origin_active=SOURCE_TYPE_SOFASCORE,
            origin_historical=SOURCE_TYPE_SOFASCORE,
            demo_mode_active=False,
            demo_mode_historical=False,
        )
        mock_summary.side_effect = [
            [self._row(1, "Nuevo", "O'Higgins", "2025")],
            [],
        ]
        mock_ext.side_effect = lambda _c, pid: {"ext-new"}
        mock_player.return_value = {"full_name": "Nuevo", "position": "FW"}

        _, cands = season_comparison_service.list_ohiggins_season_comparison_candidates(
            MagicMock()
        )
        self.assertEqual(cands[0].status, "no_historical_data")
        self.assertIn("Sin datos", cands[0].status_message)

    @patch("scouting.services.season_comparison_service.can_compare_seasons")
    @patch("scouting.services.season_comparison_service.resolve_scope_origin")
    def test_gate_blocks_without_historical_sofascore(
        self, mock_resolve, mock_can
    ) -> None:
        mock_resolve.side_effect = [
            OriginResolution(SOURCE_TYPE_SOFASCORE, False, 10, 0),
            OriginResolution(SOURCE_TYPE_DEMO, True, 0, 5),
        ]
        mock_can.return_value = (False, "No hay datos reales de Sofascore para la temporada histórica.")
        gate = season_comparison_service.assess_season_comparison_gate(MagicMock())
        self.assertFalse(gate.allowed)


class DashboardKpiOriginTests(unittest.TestCase):
    def test_kpi_uses_only_sofascore_when_present(self) -> None:
        from scouting.services import dashboard_service

        with patch("scouting.services.metrics_service.count_metrics", return_value=153949):
            with patch("scouting.services.metrics_service.count_demo_metrics", return_value=424):
                with patch(
                    "scouting.services.players_service.count_players", return_value=1
                ):
                    with patch(
                        "scouting.services.reports_service.count_reports", return_value=0
                    ):
                        with patch(
                            "scouting.services.reports_service.count_hidden_reports",
                            return_value=0,
                        ):
                            with patch(
                                "scouting.services.reports_service.fetch_recent_reports",
                                return_value=[],
                            ):
                                with patch(
                                    "scouting.repositories.players_repository.count_players_with_subjective_reports",
                                    return_value=0,
                                ):
                                    with patch(
                                        "scouting.repositories.dashboard_repository.count_distinct_scouts",
                                        return_value=0,
                                    ):
                                        with patch(
                                            "scouting.repositories.dashboard_repository.count_players_hybrid",
                                            return_value=0,
                                        ):
                                            snap = dashboard_service.get_dashboard_snapshot(
                                                MagicMock()
                                            )
        self.assertEqual(snap["metric_count"], 153949)
        self.assertFalse(snap["metrics_are_demo"])


class IncrementalLockTests(unittest.TestCase):
    def test_second_click_sees_running_lock(self) -> None:
        from scouting.services import sofascore_incremental_runner as runner

        with patch.object(runner, "is_update_in_progress", return_value=True):
            with patch.object(
                runner,
                "check_docker_runtime",
                return_value=SimpleNamespace(
                    ok=True, diagnostics_text="ok", messages=()
                ),
            ):
                result = runner.run_incremental_all_for_ui()
        self.assertEqual(result.status, "running")
        self.assertTrue(result.locked)

    def test_worker_error_is_not_no_news(self) -> None:
        from scouting.services import sofascore_incremental_runner as runner

        fake_runtime = SimpleNamespace(ok=True, diagnostics_text="ok", messages=())
        dry = runner.WorkerRunOutput(
            ok=False,
            command="x",
            stdout="",
            stderr="boom",
            returncode=1,
            log_path=None,
            json_payload=None,
            error_message="boom",
        )
        with patch.object(runner, "is_update_in_progress", return_value=False):
            with patch.object(runner, "check_docker_runtime", return_value=fake_runtime):
                with patch.object(runner, "_load_season_assessment", return_value={
                    "needs_initial_backfill": False,
                    "sofascore_metrics": 100,
                }):
                    with patch.object(runner, "_ensure_dirs"):
                        with patch("pathlib.Path.write_text"):
                            with patch("pathlib.Path.is_file", return_value=True):
                                with patch("pathlib.Path.unlink"):
                                    with patch.object(runner, "_execute_worker", return_value=dry):
                                        with patch.object(runner, "save_ui_state"):
                                            result = runner.run_incremental_all_for_ui()
        self.assertEqual(result.status, "error")
        self.assertNotEqual(result.status, "no_news")
        self.assertIn("log", (result.message or "").lower())


if __name__ == "__main__":
    unittest.main()
