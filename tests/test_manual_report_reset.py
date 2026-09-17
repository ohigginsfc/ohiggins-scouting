"""Pruebas del reset diferido del formulario de alta manual."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import date
from pathlib import Path


def _load_manual_report_state():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "app" / "ui" / "manual_report_state.py"
    spec = importlib.util.spec_from_file_location("manual_report_state", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["manual_report_state"] = module
    spec.loader.exec_module(module)
    return module


mrs = _load_manual_report_state()


class ManualReportResetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.template = {
            "DEFENSIVO": ["Entradas", "Coberturas"],
            "OFENSIVO": ["Centros"],
        }
        self.position = "Lateral izquierdo"
        self.attr_keys = mrs.manual_report_attribute_keys(self.template, self.position)

    def test_attribute_keys_are_stable_and_prefixed(self) -> None:
        self.assertEqual(len(self.attr_keys), 3)
        self.assertTrue(all(k.startswith("attr_") for k in self.attr_keys))
        self.assertEqual(
            self.attr_keys[0],
            mrs.attribute_slider_key(self.position, "DEFENSIVO", "Entradas"),
        )

    def test_mark_pending_does_not_clear_widget_values_yet(self) -> None:
        state: dict = {
            "mr_player_name": "João Silva",
            "mr_scout_name": "Scout Demo",
            self.attr_keys[0]: 4.0,
        }
        mrs.mark_manual_report_reset_pending(
            state,
            success_message="Informe #42 guardado correctamente.",
            template_position=self.position,
            template=self.template,
        )
        self.assertEqual(state["mr_player_name"], "João Silva")
        self.assertTrue(state["manual_report_reset_pending"])
        self.assertEqual(state["manual_report_success_message"], "Informe #42 guardado correctamente.")
        self.assertEqual(state["manual_report_reset_attr_keys"], self.attr_keys)

    def test_apply_pending_clears_form_before_widgets(self) -> None:
        state: dict = {
            "mr_player_name": "João Silva",
            "mr_scout_name": "Scout Demo",
            "mr_minutes": 90,
            "mr_rating_scout": 8.5,
            "mr_strengths": "Buena conducción",
            "mr_recommendation": "Seguir",
            self.attr_keys[0]: 4.0,
            self.attr_keys[1]: 3.75,
            self.attr_keys[2]: 1.0,
            "manual_report_reset_pending": True,
            "manual_report_reset_template_position": self.position,
            "manual_report_reset_attr_keys": list(self.attr_keys),
            "manual_report_success_message": "Informe #42 guardado correctamente.",
        }

        applied = mrs.apply_pending_manual_report_reset(
            state,
            recommendation_default="Observar",
            preferred_foot_default="Derecho",
            rating_default=2.5,
        )
        self.assertTrue(applied)
        self.assertNotIn("manual_report_reset_pending", state)
        self.assertNotIn("manual_report_reset_attr_keys", state)
        self.assertEqual(state["mr_player_name"], "")
        self.assertEqual(state["mr_scout_name"], "")
        self.assertEqual(state["mr_minutes"], 0)
        self.assertEqual(state["mr_rating_scout"], 6.0)
        self.assertEqual(state["mr_strengths"], "")
        self.assertEqual(state["mr_recommendation"], "Observar")
        self.assertEqual(state["mr_report_date"], date.today())
        for key in self.attr_keys:
            self.assertEqual(state[key], 2.5)
        self.assertEqual(state["manual_report_success_message"], "Informe #42 guardado correctamente.")

    def test_apply_pending_is_noop_without_flag(self) -> None:
        state = {"mr_player_name": "Keep me"}
        applied = mrs.apply_pending_manual_report_reset(
            state,
            recommendation_default="Observar",
            preferred_foot_default="Derecho",
            rating_default=2.5,
        )
        self.assertFalse(applied)
        self.assertEqual(state["mr_player_name"], "Keep me")

    def test_save_then_reset_flow_simulates_single_insert_cycle(self) -> None:
        """Simula: guardar → marcar pending → rerun → reset → widgets limpios."""
        inserts = []
        state: dict = {
            "mr_player_name": "Nuevo Jugador",
            "mr_scout_name": "Scout",
            self.attr_keys[0]: 3.5,
        }

        inserts.append({"player": state["mr_player_name"]})
        mrs.mark_manual_report_reset_pending(
            state,
            success_message="Informe #7 guardado correctamente (3 atributos).",
            template_position=self.position,
            template=self.template,
        )
        self.assertEqual(len(inserts), 1)

        mrs.apply_pending_manual_report_reset(
            state,
            recommendation_default="Observar",
            preferred_foot_default="Derecho",
            rating_default=2.5,
        )
        success = state.pop("manual_report_success_message", None)
        self.assertEqual(success, "Informe #7 guardado correctamente (3 atributos).")
        self.assertEqual(state["mr_player_name"], "")
        self.assertEqual(len(inserts), 1)

    def test_widget_defaults_cover_expected_keys(self) -> None:
        defaults = mrs.manual_report_widget_defaults(
            recommendation_default="Observar",
            preferred_foot_default="Derecho",
        )
        expected = {
            "mr_player_name",
            "mr_current_team",
            "mr_nationality",
            "mr_scout_name",
            "mr_competition",
            "mr_match_observed",
            "mr_position_observed",
            "mr_minutes",
            "mr_rating_scout",
            "mr_strengths",
            "mr_weaknesses",
            "mr_summary",
            "mr_recommendation",
            "mr_register_birth",
            "mr_preferred_foot",
            "mr_height_cm",
            "mr_video_url",
            "mr_alternative_positions",
            "mr_report_date",
            "mr_birth_date",
        }
        self.assertEqual(set(defaults), expected)


if __name__ == "__main__":
    unittest.main()
