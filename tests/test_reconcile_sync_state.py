"""Reconciliación del estado UI persistido frente al assessment de PostgreSQL."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
APP = ROOT / "app"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

from scouting.services import sofascore_incremental_runner as runner  # noqa: E402
from ui.data_sync_card import build_sync_card_view  # noqa: E402


def _failed_historical(**kwargs) -> runner.FriendlyUpdateResult:
    base = dict(
        ok=False,
        status="failed",
        headline="Error en Backfill histórico cl_primera_2024",
        message="Falló Backfill histórico cl_primera_2024",
        last_check_at="23/07/2026 13:39",
        platform_state="initial_sync_required",
        button_label="Descargar datos reales",
        mode="dashboard",
        log_paths=["data/logs/sofascore_incremental/20260723_133919_dashboard_step1.log"],
        technical_details="validate: Missing teams.json",
        summary_lines=["Falló: Primera División de Chile · Temporada 2024"],
    )
    base.update(kwargs)
    return runner.FriendlyUpdateResult(**base)


class ReconcileSyncStateTests(unittest.TestCase):
    def test_persisted_historical_error_without_sofascore_stays_error(self):
        plan = {
            "state": "initial_sync_required",
            "has_historical_sofascore": False,
            "has_active_sofascore": False,
            "button_label": "Descargar datos reales",
            "banner_message": "Demo",
            "active_season": "2025",
            "historical_season": "2024",
        }
        out = runner.reconcile_sync_state(plan, _failed_historical(), persist=False)
        self.assertEqual(out.status, "failed")
        self.assertFalse(out.reconciled)
        view = build_sync_card_view(plan, out, in_progress=False)
        self.assertTrue(view.is_error)
        self.assertEqual(view.primary_label, "Reintentar")

    def test_persisted_historical_error_with_2024_real_becomes_current_sync(self):
        plan = {
            "state": "current_sync_required",
            "has_historical_sofascore": True,
            "has_active_sofascore": False,
            "button_label": "Descargar temporada actual",
            "banner_message": (
                "Los datos históricos de 2024 están disponibles. "
                "Falta descargar la temporada activa 2025."
            ),
            "active_season": "2025",
            "historical_season": "2024",
            "historical_sofascore_metrics": 19607,
            "sofascore_metrics": 19607,
        }
        failed = _failed_historical()
        out = runner.reconcile_sync_state(plan, failed, persist=False)
        self.assertEqual(out.status, "idle")
        self.assertTrue(out.ok)
        self.assertTrue(out.reconciled)
        self.assertEqual(out.platform_state, "current_sync_required")
        self.assertEqual(out.button_label, "Descargar temporada actual")
        self.assertTrue(
            any("completado posteriormente" in n for n in out.history_notes)
        )
        self.assertEqual(
            out.log_paths,
            ["data/logs/sofascore_incremental/20260723_133919_dashboard_step1.log"],
        )
        self.assertIn("superseded_error", out.assessment)

        view = build_sync_card_view(plan, out, in_progress=False)
        self.assertFalse(view.is_error)
        self.assertEqual(view.badge_label, "Temporada pendiente")
        self.assertEqual(view.primary_label, "Descargar temporada 2025")
        self.assertTrue(any("20260723_133919" in ln for ln in view.technical_lines))

    def test_stale_running_without_process_is_reconciled(self):
        plan = {
            "state": "current_sync_required",
            "has_historical_sofascore": True,
            "has_active_sofascore": False,
            "button_label": "Descargar temporada actual",
            "banner_message": "Histórico ok",
            "active_season": "2025",
            "historical_season": "2024",
        }
        running = runner.FriendlyUpdateResult(
            ok=True,
            status="running",
            headline="Sincronización en curso",
            message="Descargando…",
            platform_state="initial_sync_required",
            background_pid=99999999,
        )
        with patch.object(runner, "is_update_in_progress", return_value=False):
            with patch.object(runner, "_pid_is_alive", return_value=False):
                with patch.object(
                    runner,
                    "clear_orphan_sync_lock",
                    return_value={"cleared": True, "reason": "orphan"},
                ):
                    out = runner.reconcile_sync_state(plan, running, persist=False)
        self.assertEqual(out.status, "idle")
        self.assertTrue(out.reconciled)
        self.assertIsNone(out.background_pid)

    def test_orphan_lock_cleared_when_no_live_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / "sofascore_update.lock"
            lock.write_text(
                json.dumps({"pid": 99999999, "started_at": "2020-01-01T00:00:00"}),
                encoding="utf-8",
            )
            with patch.object(runner, "LOCK_PATH", lock):
                with patch.object(runner, "_pid_is_alive", return_value=False):
                    report = runner.clear_orphan_sync_lock()
            self.assertTrue(report["cleared"])
            self.assertFalse(lock.exists())

    def test_live_lock_not_cleared(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / "sofascore_update.lock"
            lock.write_text(
                json.dumps({"pid": 1, "started_at": "2026-07-22T00:00:00"}),
                encoding="utf-8",
            )
            with patch.object(runner, "LOCK_PATH", lock):
                with patch.object(runner, "_pid_is_alive", return_value=True):
                    report = runner.clear_orphan_sync_lock()
            self.assertFalse(report["cleared"])
            self.assertEqual(report["reason"], "process_alive")
            self.assertTrue(lock.exists())


if __name__ == "__main__":
    unittest.main()
