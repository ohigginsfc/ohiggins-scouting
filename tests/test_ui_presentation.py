"""Pruebas de presentación orientada al usuario final."""

from __future__ import annotations

import sys
import unittest
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

from ui.presentation import (  # noqa: E402
    format_date_for_ui,
    format_datetime_for_ui,
    format_number_for_ui,
    humanize_status,
    render_data_source_notice,
    render_report_metadata,
    report_option_label,
)
from ui.data_sync_card import build_sync_card_view  # noqa: E402
from types import SimpleNamespace  # noqa: E402


def _ui(**kwargs):
    defaults = dict(
        ok=True,
        status="idle",
        headline="",
        message="",
        last_check_at="24/07/2026 10:53",
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


class FormatHelpersTests(unittest.TestCase):
    def test_number_spanish_thousands(self):
        self.assertEqual(format_number_for_ui(160160), "160.160")
        self.assertEqual(format_number_for_ui(179767), "179.767")
        self.assertEqual(format_number_for_ui(19607), "19.607")

    def test_date_long_spanish(self):
        self.assertEqual(format_date_for_ui("2026-05-22"), "22 de mayo de 2026")
        self.assertEqual(format_date_for_ui(date(2026, 5, 22)), "22 de mayo de 2026")
        self.assertEqual(format_date_for_ui("2026-05-22", long=False), "22/05/2026")

    def test_datetime_without_iso(self):
        txt = format_datetime_for_ui(datetime(2026, 7, 24, 10, 53))
        self.assertEqual(txt, "24/07/2026 10:53")
        self.assertNotIn("T", txt)
        self.assertNotIn("+", txt)

    def test_humanize_status_hides_snake_case_raw(self):
        self.assertEqual(humanize_status("processed"), "Procesado")
        self.assertEqual(humanize_status("failed"), "Error")
        self.assertNotEqual(humanize_status("current_sync_required"), "current_sync_required")


class ReportPresentationTests(unittest.TestCase):
    def test_report_metadata_without_id_or_manual_origin(self):
        report = {
            "id": 2,
            "scout_name": "Juan Pérez",
            "report_date": "2026-05-22",
            "source_type": "manual",
            "player_full_name": "Jugador Demo",
        }
        meta = render_report_metadata(report)
        self.assertEqual(meta, "Informe de Juan Pérez · 22 de mayo de 2026")
        self.assertNotIn("ID", meta)
        self.assertNotIn("#2", meta)
        self.assertNotIn("manual", meta.lower())
        self.assertNotIn("Origen", meta)

        label = report_option_label(report)
        self.assertNotIn("ID", label)
        self.assertNotIn("#2", label)
        self.assertNotIn("manual", label.lower())


class KpiNoticeTests(unittest.TestCase):
    def test_real_data_notice_mentions_season_not_source_type(self):
        notice = render_data_source_notice(metrics_are_demo=False, active_season="2025")
        self.assertEqual(notice, "Estadísticas de la temporada 2025.")
        self.assertNotIn("source_type", notice.lower())
        self.assertNotIn("demo", notice.lower())
        self.assertNotIn("sofascore", notice.lower())

    def test_demo_only_notice(self):
        notice = render_data_source_notice(metrics_are_demo=True, active_season="2025")
        self.assertEqual(notice, "Estás utilizando datos de demostración.")


class SyncCardCopyTests(unittest.TestCase):
    def test_fully_initialized_user_copy(self):
        plan = {
            "state": "fully_initialized",
            "active_season": "2025",
            "historical_season": "2024",
            "sofascore_metrics": 179767,
            "historical_sofascore_metrics": 19607,
            "active_sofascore_metrics": 160160,
        }
        view = build_sync_card_view(plan, _ui(), in_progress=False)
        self.assertEqual(view.badge_label, "Datos actualizados")
        self.assertIn("Temporadas 2024 y 2025", view.summary_line)
        self.assertIn("179.767", view.message)
        self.assertIn("estadísticas", view.message.lower())
        blob = f"{view.summary_line} {view.message} {view.badge_label}".lower()
        self.assertNotIn("sofascore", blob)
        self.assertNotIn("source_type", blob)
        self.assertNotIn("current_sync", blob)
        self.assertNotIn("backfill", blob)
        self.assertNotIn("/app/", blob)
        self.assertNotIn(".log", blob)

    def test_demo_only_shows_demo_message(self):
        plan = {
            "state": "initial_sync_required",
            "active_season": "2025",
            "historical_season": "2024",
            "demo_metrics": 625,
            "sofascore_metrics": 0,
        }
        view = build_sync_card_view(plan, _ui(), in_progress=False)
        self.assertEqual(view.badge_label, "Datos de demostración")
        self.assertIn("demostración", view.message.lower())
        self.assertFalse(view.show_advanced)


if __name__ == "__main__":
    unittest.main()
