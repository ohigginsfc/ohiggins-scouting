"""Tema visual global O'Higgins para Streamlit y Plotly."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st

from ui.theme_css import build_ohiggins_css

# --- Colores oficiales ---
OHIGGINS_BLUE = "#5091CD"
OHIGGINS_GREEN = "#49A942"
OHIGGINS_YELLOW = "#FFDD00"
OHIGGINS_BLACK = "#000000"
OHIGGINS_WHITE = "#FFFFFF"
OHIGGINS_LIGHT_BG = "#F4F8FC"
OHIGGINS_CARD_BG = "#FFFFFF"
OHIGGINS_BORDER = "#D7E3EF"
OHIGGINS_TEXT = "#111827"
OHIGGINS_MUTED_TEXT = "#64748B"
OHIGGINS_BLUE_DARK = "#3D7AB5"
OHIGGINS_BLUE_LIGHT = "#E8F2FA"
OHIGGINS_GREEN_LIGHT = "#EAF6E9"
OHIGGINS_YELLOW_LIGHT = "#FFF9CC"
OHIGGINS_RED_SOFT = "#FEE2E2"
OHIGGINS_RED_TEXT = "#991B1B"
OHIGGINS_ORANGE = "#F59E0B"

OHIGGINS_FONT = (
    'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
)
APP_PRIMARY = "#4F8FCC"
APP_PRIMARY_HOVER = "#2F6FAE"
APP_BG = "#F4F7FB"

PLOTLY_COLORWAY: list[str] = [
    APP_PRIMARY,
    OHIGGINS_BLUE,
    OHIGGINS_GREEN,
    "#64748B",
    "#8BAED8",
    "#8AD184",
]

RADAR_PLAYER_LINE = OHIGGINS_BLUE
RADAR_PLAYER_FILL = "rgba(80, 145, 205, 0.20)"
RADAR_COHORT_LINE = "#475569"
RADAR_COHORT_FILL = "rgba(71, 85, 105, 0.12)"


def ohiggins_percentile_color(percentile: float) -> str:
    """Color de percentil alineado con la marca (rojo → amarillo → verde)."""
    pct = float(percentile)
    if pct < 25:
        return "#E57373"
    if pct < 50:
        return OHIGGINS_ORANGE
    if pct < 75:
        return OHIGGINS_YELLOW
    if pct < 90:
        return "#7BC96F"
    return OHIGGINS_GREEN


def ohiggins_percentile_cell_style(val: object) -> str:
    if isinstance(val, str) and val.startswith("P"):
        try:
            n = int(val[1:])
        except ValueError:
            return ""
        if n > 80:
            return f"background-color: {OHIGGINS_GREEN_LIGHT}; color: #1B5E20; font-weight: 600"
        if n >= 50:
            return f"background-color: {OHIGGINS_YELLOW_LIGHT}; color: #854D0E; font-weight: 600"
        return f"background-color: {OHIGGINS_RED_SOFT}; color: {OHIGGINS_RED_TEXT}; font-weight: 600"
    return ""


def plotly_radar_chart_config() -> dict[str, bool]:
    return {"displayModeBar": False}


def apply_ohiggins_plotly_theme(fig: go.Figure, **layout_overrides: Any) -> go.Figure:
    """Aplica tipografía, fondo y paleta del sistema visual a una figura Plotly."""
    fig.update_layout(
        font=dict(
            family="Inter, ui-sans-serif, system-ui, sans-serif",
            color=OHIGGINS_TEXT,
            size=12,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=PLOTLY_COLORWAY,
        legend=dict(
            orientation="h",
            yanchor="top",
            font=dict(color=OHIGGINS_TEXT, size=11),
        ),
        margin=dict(l=40, r=40, t=36, b=36),
    )
    if layout_overrides:
        fig.update_layout(**layout_overrides)
    return fig


def inject_ohiggins_theme() -> None:
    """Inyecta CSS legacy + sistema visual moderno. Llamar una vez al inicio."""
    from ui.styles import build_design_system_css, build_forced_light_theme_css

    st.markdown(build_ohiggins_css(), unsafe_allow_html=True)
    st.markdown(build_design_system_css(), unsafe_allow_html=True)
    st.markdown(build_forced_light_theme_css(), unsafe_allow_html=True)
