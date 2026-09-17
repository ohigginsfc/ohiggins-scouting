"""Pruebas de construcción del campograma Plotly (figura independiente y tamaño estable)."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


def _load_pitch_map():
    root = Path(__file__).resolve().parents[1]
    app_dir = root / "app"
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))
    module_path = app_dir / "ui" / "pitch_map.py"
    spec = importlib.util.spec_from_file_location("pitch_map", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pitch_map"] = module
    spec.loader.exec_module(module)
    return module


pitch_map = _load_pitch_map()


def _sample_counts() -> dict[str, dict[str, int]]:
    return {
        "Portero": {"reports_count": 2},
        "Delantero": {"reports_count": 5},
    }


def _sample_labels() -> dict[str, str]:
    return {pos: pos[:3].upper() for pos in pitch_map.PITCH_COORDS}


class PitchFigureBuildTests(unittest.TestCase):
    def test_successive_builds_are_independent(self) -> None:
        labels = _sample_labels()
        counts = _sample_counts()
        fig_a = pitch_map.build_pitch_figure(
            short_labels=labels, counts=counts, selected=None
        )
        fig_b = pitch_map.build_pitch_figure(
            short_labels=labels, counts=counts, selected="Delantero"
        )

        self.assertIsNot(fig_a, fig_b)
        self.assertEqual(fig_a.layout.height, fig_b.layout.height)
        self.assertEqual(fig_a.layout.height, 540)
        self.assertIsNone(fig_a.layout.width)
        self.assertIsNone(fig_b.layout.width)

        fig_a.update_layout(height=100)
        self.assertEqual(fig_b.layout.height, 540)

    def test_height_constant_across_many_builds(self) -> None:
        labels = _sample_labels()
        counts = _sample_counts()
        heights = []
        widths = []
        for i in range(8):
            selected = "Portero" if i % 2 == 0 else "Delantero"
            fig = pitch_map.build_pitch_figure(
                short_labels=labels, counts=counts, selected=selected
            )
            heights.append(fig.layout.height)
            widths.append(fig.layout.width)
        self.assertTrue(all(h == 540 for h in heights))
        self.assertTrue(all(w is None for w in widths))

    def test_scaleanchor_uses_domain_constrain(self) -> None:
        fig = pitch_map.build_pitch_figure(
            short_labels=_sample_labels(),
            counts=_sample_counts(),
            selected=None,
        )
        yaxis = fig.layout.yaxis
        xaxis = fig.layout.xaxis
        self.assertEqual(yaxis.scaleanchor, "x")
        self.assertEqual(yaxis.scaleratio, 1)
        self.assertEqual(yaxis.constrain, "domain")
        self.assertEqual(xaxis.constrain, "domain")
        self.assertTrue(fig.layout.autosize)


if __name__ == "__main__":
    unittest.main()
