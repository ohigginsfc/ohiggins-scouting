"""Pruebas de presentación de la tarjeta Datos deportivos."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
SRC = ROOT / "src"
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ui.data_sync_card import (  # noqa: E402
    METHOD_AUTO,
    METHOD_DOWNLOAD,
    METHOD_REUSE,
    build_sync_card_view,
    checkpoint_info_for_slug,
    friendly_platform_state,
    resolve_import_method,
    sports_data_panel_html,
)


def _ui(**kwargs):
    defaults = dict(
        ok=True,
        status="idle",
        headline="",
        message="",
        last_check_at="23/07/2026 13:51",
        last_update_at=None,
        summary_lines=[],
        log_paths=[],
        mode="dashboard",
        platform_state="",
        technical_details="",
        assessment={},
        reconciled=False,
        history_notes=[],
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class FriendlyLabelsTests(unittest.TestCase):
    def test_internal_codes_are_translated(self):
        self.assertEqual(friendly_platform_state("initial_sync_required"), "Datos de demostración")
        self.assertEqual(friendly_platform_state("fully_initialized"), "Datos actualizados")
        self.assertEqual(friendly_platform_state("current_sync_required"), "Temporada pendiente")
        self.assertEqual(friendly_platform_state("running"), "Descargando")
        self.assertEqual(friendly_platform_state("failed"), "Error")
        self.assertNotIn("initial_sync", friendly_platform_state("initial_sync_required"))
        self.assertNotIn("sincronización", friendly_platform_state("failed").lower())


class SyncCardViewTests(unittest.TestCase):
    def test_demo_only_compact(self):
        plan = {
            "state": "initial_sync_required",
            "active_season": "2025",
            "historical_season": "2024",
            "demo_metrics": 625,
            "sofascore_metrics": 0,
            "sofascore_players": 0,
            "step_labels": ["a", "b"],
            "button_label": "Descargar datos reales",
        }
        view = build_sync_card_view(plan, _ui(), in_progress=False)
        self.assertEqual(view.primary_label, "Descargar datos reales")
        self.assertEqual(view.badge_label, "Datos de demostración")
        self.assertEqual(view.message, "Estás usando datos de demostración.")
        self.assertFalse(view.show_advanced)
        self.assertFalse(view.show_refresh)
        self.assertFalse(view.show_error_details)
        self.assertEqual(view.primary_type, "primary")
        self.assertNotIn("sincronización", view.message.lower())

    def test_running_shows_progress_refresh_hides_admin(self):
        plan = {
            "state": "current_sync_required",
            "active_season": "2025",
            "historical_season": "2024",
            "demo_metrics": 0,
            "sofascore_metrics": 19607,
            "historical_sofascore_metrics": 19607,
            "step_labels": ["Ligas activas · Temporada 2025"],
        }
        ui = _ui(
            status="running",
            headline="Paso 1/1",
            message="Descargando…",
            summary_lines=["Liga 2 de 6 · partido 48 de 120"],
        )
        view = build_sync_card_view(plan, ui, in_progress=True)
        self.assertTrue(view.in_progress)
        self.assertFalse(view.show_primary)
        self.assertFalse(view.show_advanced)
        self.assertTrue(view.show_refresh)
        self.assertEqual(view.refresh_label, "Actualizar progreso")
        self.assertEqual(view.badge_label, "Descargando")
        self.assertIn("2025", view.message)
        self.assertIn("Liga 2 de 6", view.progress_detail)
        self.assertNotIn("sincroniz", view.badge_label.lower())

    def test_fully_initialized_compact(self):
        plan = {
            "state": "fully_initialized",
            "active_season": "2025",
            "historical_season": "2024",
            "demo_metrics": 625,
            "sofascore_metrics": 173556,
            "sofascore_players": 3664,
        }
        view = build_sync_card_view(plan, _ui(status="success"), in_progress=False)
        self.assertEqual(view.primary_label, "Buscar nuevos partidos")
        self.assertEqual(view.badge_label, "Datos actualizados")
        self.assertIn("173.556", view.message)
        self.assertIn("Temporadas 2024 y 2025", view.summary_line)
        self.assertFalse(view.show_advanced)
        self.assertFalse(view.show_refresh)
        self.assertTrue(view.show_last_update)
        self.assertEqual(view.primary_type, "primary")

    def test_missing_historical_compact(self):
        plan = {
            "state": "historical_sync_required",
            "active_season": "2025",
            "historical_season": "2024",
            "demo_metrics": 201,
            "sofascore_metrics": 1000,
        }
        view = build_sync_card_view(plan, _ui(), in_progress=False)
        self.assertEqual(view.primary_label, "Completar temporada 2024")
        self.assertEqual(view.badge_label, "Histórico incompleto")
        self.assertFalse(view.show_advanced)

    def test_current_sync_required_compact(self):
        plan = {
            "state": "current_sync_required",
            "active_season": "2025",
            "historical_season": "2024",
            "demo_metrics": 0,
            "sofascore_metrics": 19607,
            "historical_sofascore_metrics": 19607,
        }
        view = build_sync_card_view(plan, _ui(), in_progress=False)
        self.assertEqual(view.primary_label, "Descargar temporada 2025")
        self.assertEqual(view.badge_label, "Temporada pendiente")
        self.assertIn("19.607", view.summary_line)
        self.assertIn("estadísticas", view.summary_line.lower())
        self.assertEqual(view.message, "Falta descargar los datos de la temporada 2025.")
        self.assertEqual(view.info_rows, [])
        self.assertFalse(view.show_refresh)
        self.assertFalse(view.show_advanced)
        self.assertFalse(view.show_error_details)
        self.assertTrue(view.show_last_update)
        self.assertEqual(view.primary_type, "primary")
        self.assertNotIn("sincroniz", (view.message + view.summary_line).lower())
        self.assertNotIn("sofascore", (view.message + view.summary_line).lower())

    def test_reconciled_failure_does_not_show_active_error(self):
        plan = {
            "state": "current_sync_required",
            "active_season": "2025",
            "historical_season": "2024",
            "has_historical_sofascore": True,
            "historical_sofascore_metrics": 19607,
            "sofascore_metrics": 19607,
        }
        ui = _ui(
            status="idle",
            reconciled=True,
            history_notes=["El paso histórico fue completado posteriormente."],
            assessment={
                "superseded_error": {
                    "message": "Error en Backfill histórico cl_primera_2024",
                    "log_paths": [
                        "data/logs/sofascore_incremental/20260723_133919_dashboard_step1.log"
                    ],
                    "note": "El paso histórico fue completado posteriormente.",
                }
            },
            log_paths=["data/logs/sofascore_incremental/20260723_133919_dashboard_step1.log"],
        )
        view = build_sync_card_view(plan, ui, in_progress=False)
        self.assertFalse(view.is_error)
        self.assertEqual(view.primary_label, "Descargar temporada 2025")
        self.assertEqual(view.badge_label, "Temporada pendiente")
        self.assertFalse(view.show_error_details)

    def test_html_helper_escapes_and_stays_compact(self):
        view = build_sync_card_view(
            {
                "state": "current_sync_required",
                "active_season": "2025",
                "historical_season": "2024",
                "sofascore_metrics": 1,
                "historical_sofascore_metrics": 1,
            },
            _ui(),
            in_progress=False,
        )
        html = sports_data_panel_html(view)
        self.assertNotIn("scouting-sports-rows", html)
        self.assertIn("scouting-sports-summary", html)
        self.assertNotIn("<script>", html)

    def test_error_allows_error_info(self):
        plan = {
            "state": "current_sync_required",
            "active_season": "2025",
            "historical_season": "2024",
            "demo_metrics": 0,
            "sofascore_metrics": 19607,
            "step_labels": ["act"],
        }
        ui = _ui(
            status="failed",
            message="Falló la descarga de 2025",
            summary_lines=["Falló: Ligas activas · Temporada 2025"],
            log_paths=["/tmp/demo.log"],
        )
        view = build_sync_card_view(plan, ui, in_progress=False)
        self.assertEqual(view.primary_label, "Reintentar")
        self.assertTrue(view.is_error)
        self.assertTrue(view.show_error_details)
        self.assertEqual(view.badge_label, "Error")
        self.assertEqual(view.primary_type, "primary")
        self.assertFalse(view.show_advanced)
        self.assertFalse(view.show_refresh)
        self.assertIn("2025", view.message)
        self.assertNotIn("sincroniz", view.primary_label.lower())

    def test_primary_type_never_danger(self):
        states = (
            {
                "state": "initial_sync_required",
                "active_season": "2025",
                "historical_season": "2024",
                "demo_metrics": 10,
                "sofascore_metrics": 0,
            },
            {
                "state": "current_sync_required",
                "active_season": "2025",
                "historical_season": "2024",
                "sofascore_metrics": 10,
                "historical_sofascore_metrics": 10,
            },
            {
                "state": "fully_initialized",
                "active_season": "2025",
                "historical_season": "2024",
                "sofascore_metrics": 100,
            },
        )
        for plan in states:
            view = build_sync_card_view(plan, _ui(), in_progress=False)
            self.assertEqual(view.primary_type, "primary", plan["state"])


class ImportMethodTests(unittest.TestCase):
    def test_auto_uses_checkpoint_when_present(self):
        self.assertTrue(resolve_import_method(METHOD_AUTO, checkpoint_exists=True))
        self.assertFalse(resolve_import_method(METHOD_AUTO, checkpoint_exists=False))

    def test_download_forces_scrape(self):
        self.assertFalse(resolve_import_method(METHOD_DOWNLOAD, checkpoint_exists=True))

    def test_reuse_requires_checkpoint(self):
        self.assertTrue(resolve_import_method(METHOD_REUSE, checkpoint_exists=True))

    def test_missing_checkpoint_reported(self):
        with patch("ui.data_sync_card.SOFASCORE_OUTPUT", Path("/tmp/no-such-sofascore-output")):
            info = checkpoint_info_for_slug("cl_primera_2024")
        self.assertFalse(info["exists"])


if __name__ == "__main__":
    unittest.main()
