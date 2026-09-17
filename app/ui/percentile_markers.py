"""Barras de percentiles reutilizables (un jugador o comparación dual)."""

from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Any

OH_BLUE = "#5091CD"
OH_GREEN = "#49A942"
MARKER_BLACK = "#000000"

SHAPE_CIRCLE = "circle"
SHAPE_DIAMOND = "diamond"

ROLE_OHIGGINS = "ohiggins"
ROLE_COMPARED = "compared"

MIN_LEFT_PCT = 2.0
MAX_LEFT_PCT = 98.0


@dataclass(frozen=True)
class DualMarkerSpec:
    percentile: float
    color: str
    label: str
    shape: str = SHAPE_CIRCLE
    role: str = ROLE_OHIGGINS


def _clamp_pct(percentile: float) -> float:
    return max(0.0, min(100.0, float(percentile)))


def _clamp_left(left_pct: float) -> float:
    return max(MIN_LEFT_PCT, min(MAX_LEFT_PCT, float(left_pct)))


def compute_marker_positions(markers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Posición horizontal = percentil real (clamp 2–98). Sin desplazamiento por solape.
    """
    out: list[dict[str, Any]] = []
    for m in markers:
        pct = _clamp_pct(m.get("percentile", 0))
        role = str(m.get("role") or ROLE_OHIGGINS).strip() or ROLE_OHIGGINS
        out.append(
            {
                **m,
                "percentile": pct,
                "role": role,
                "left_pct": _clamp_left(pct),
                "lane": 0,
                "offset_y_px": 0,
                "z_index": 6 if role == ROLE_OHIGGINS else 5,
            }
        )
    return out


def _comparison_marker_html(spec: DualMarkerSpec, pos: dict[str, Any]) -> str:
    pct_i = int(round(float(pos["percentile"])))
    title = html.escape(f"{spec.label} · P{pct_i}")
    left = float(pos["left_pct"])
    z_index = int(pos.get("z_index", 4))
    shape_class = "pct-marker--diamond" if spec.shape == SHAPE_DIAMOND else "pct-marker--dual"
    return (
        f'<div class="pct-marker cmp-pct-marker {shape_class}" '
        f'style="left:{left:.1f}%;z-index:{z_index};background:{spec.color};" '
        f'title="{title}" aria-label="{title}"></div>'
    )


def _marker_html(spec: DualMarkerSpec, pct: float, offset_y: int = 0) -> str:
    """Marcador genérico (fuera de tarjeta comparativa)."""
    pct_i = int(round(pct))
    title = html.escape(f"{spec.label} · P{pct_i}")
    left = _clamp_left(pct)
    if spec.shape == SHAPE_DIAMOND:
        return (
            f'<div class="pct-marker pct-marker--diamond" '
            f'style="left:{left:.1f}%;background:{spec.color};'
            f'transform:translate(-50%, calc(-50% + {offset_y}px)) rotate(45deg);" '
            f'title="{title}" aria-label="{title}"></div>'
        )
    return (
        f'<div class="pct-marker pct-marker--dual" '
        f'style="left:{left:.1f}%;background:{spec.color};'
        f'transform:translate(-50%, calc(-50% + {offset_y}px));" '
        f'title="{title}" aria-label="{title}"></div>'
    )


def single_player_strip_html(percentile: float) -> str:
    """Un jugador: marcador negro en la barra (Pxx en badge de la card, no flotante)."""
    pct = _clamp_pct(percentile)
    left = _clamp_left(pct)
    pct_i = int(round(pct))
    return (
        '<div class="pct-strip-zone">'
        '<div class="pct-strip-wrap pct-strip-wrap--single">'
        '<div class="pct-strip-gradient"></div>'
        f'<div class="pct-marker pct-marker--single" style="left:{left:.1f}%;" '
        f'title="Percentil {pct_i}" aria-label="Percentil {pct_i}"></div>'
        "</div>"
        "</div>"
    )


def dual_player_strip_html(
    spec_a: DualMarkerSpec,
    spec_b: DualMarkerSpec,
) -> str:
    """Dos perfiles: percentil real en barra; leyenda identifica cada jugador."""
    positions = compute_marker_positions(
        [
            {"percentile": spec_a.percentile, "role": spec_a.role or ROLE_OHIGGINS},
            {"percentile": spec_b.percentile, "role": spec_b.role or ROLE_COMPARED},
        ]
    )
    return (
        '<div class="pct-strip-zone">'
        '<div class="pct-strip-wrap pct-strip-wrap--dual">'
        '<div class="pct-strip-gradient"></div>'
        f"{_comparison_marker_html(spec_a, positions[0])}"
        f"{_comparison_marker_html(spec_b, positions[1])}"
        "</div>"
        "</div>"
    )


def comparison_percentile_card_html(
    *,
    metric_label: str,
    pct_a: float,
    pct_b: float,
    value_a: str,
    value_b: str,
    color_a: str,
    color_b: str,
    legend_a: str,
    legend_b: str,
    lower_is_better: bool = False,
) -> str:
    """Tarjeta comparativa: título → barra → leyenda → resumen Pxx vs Pyy."""
    spec_a = DualMarkerSpec(
        percentile=pct_a,
        color=color_a,
        label=legend_a,
        shape=SHAPE_CIRCLE,
        role=ROLE_OHIGGINS,
    )
    spec_b = DualMarkerSpec(
        percentile=pct_b,
        color=color_b,
        label=legend_b,
        shape=SHAPE_DIAMOND,
        role=ROLE_COMPARED,
    )
    strip = dual_player_strip_html(spec_a, spec_b)
    pct_ai = int(round(_clamp_pct(pct_a)))
    pct_bi = int(round(_clamp_pct(pct_b)))
    direction_chip = ""
    if lower_is_better:
        direction_chip = (
            '<span class="cmp-pct-direction-chip" title="En esta métrica, menos es mejor.">'
            "Menor es mejor"
            "</span>"
        )
    return (
        '<div class="cmp-pct-card">'
        f'<p class="pct-metric-title">{html.escape(metric_label)}</p>'
        f'<div class="cmp-pct-strip-block">{strip}</div>'
        '<div class="cmp-pct-legend">'
        f'<p class="cmp-pct-legend-line">'
        f'<span class="cmp-legend-shape cmp-legend-shape--circle" '
        f'style="background:{color_a};"></span>'
        f"<strong>{html.escape(legend_a)}</strong>: P{pct_ai} · {html.escape(value_a)}"
        "</p>"
        f'<p class="cmp-pct-legend-line">'
        f'<span class="cmp-legend-shape cmp-legend-shape--diamond" '
        f'style="background:{color_b};"></span>'
        f"<strong>{html.escape(legend_b)}</strong>: P{pct_bi} · {html.escape(value_b)}"
        "</p>"
        "</div>"
        f'<p class="cmp-pct-summary">P{pct_ai} vs P{pct_bi}</p>'
        f"{direction_chip}"
        "</div>"
    )


def comparison_legend_html(
    *,
    label_a: str,
    label_b: str,
    color_a: str = OH_BLUE,
    color_b: str = OH_GREEN,
) -> str:
    return (
        '<div class="cmp-legend">'
        '<span class="cmp-legend-item">'
        f'<span class="cmp-legend-shape cmp-legend-shape--circle" style="background:{color_a};"></span>'
        f"{html.escape(label_a)}</span>"
        '<span class="cmp-legend-item">'
        f'<span class="cmp-legend-shape cmp-legend-shape--diamond" style="background:{color_b};"></span>'
        f"{html.escape(label_b)}</span>"
        "</div>"
    )
