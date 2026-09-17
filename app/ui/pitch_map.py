"""Campograma interactivo (Plotly): terreno + marcadores en el mismo sistema de coordenadas."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st

from ui.components import filter_chip
from ui.icons import labeled
from ui.theme import APP_PRIMARY, APP_PRIMARY_HOVER

# Metros FIFA (ataque hacia +X; y=0 línea de banda inferior).
PITCH_LENGTH = 105.0
PITCH_WIDTH = 68.0

# Coordenadas (x, y) por posición completa — portería propia a la izquierda.
PITCH_COORDS: dict[str, tuple[float, float]] = {
    "Portero": (8.0, 34.0),
    "Lateral izquierdo": (23.0, 54.0),
    "Central izquierdo": (23.0, 41.0),
    "Central derecho": (23.0, 27.0),
    "Lateral derecho": (23.0, 14.0),
    "Mediocentro defensivo": (44.0, 34.0),
    "Mediocentro": (58.0, 34.0),
    "Mediocentro ofensivo": (71.0, 34.0),
    "Extremo izquierdo": (86.0, 54.0),
    "Delantero": (92.0, 34.0),
    "Extremo derecho": (86.0, 14.0),
}

_LINE = dict(color="rgba(255,255,255,0.68)", width=1.55)
_STRIPE_A = "#3F8F4A"
_STRIPE_B = "#387F42"
_MARKER_FACE = "rgba(255,255,255,0.97)"
_MARKER_LINE = APP_PRIMARY
_SELECTED_FACE = APP_PRIMARY
_SELECTED_LINE = APP_PRIMARY_HOVER


def _pitch_shapes() -> list[dict[str, Any]]:
    length, width = PITCH_LENGTH, PITCH_WIDTH
    mid_x, mid_y = length / 2, width / 2
    shapes: list[dict[str, Any]] = []

    stripe_w = length / 10
    for i in range(10):
        shapes.append(
            dict(
                type="rect",
                xref="x",
                yref="y",
                x0=i * stripe_w,
                y0=0,
                x1=(i + 1) * stripe_w,
                y1=width,
                fillcolor=_STRIPE_A if i % 2 == 0 else _STRIPE_B,
                line=dict(width=0),
                layer="below",
            )
        )

    shapes.append(
        dict(
            type="rect",
            xref="x",
            yref="y",
            x0=0,
            y0=0,
            x1=length,
            y1=width,
            fillcolor="rgba(0,0,0,0)",
            line=_LINE,
            layer="above",
        )
    )
    shapes.append(
        dict(
            type="line",
            xref="x",
            yref="y",
            x0=mid_x,
            y0=0,
            x1=mid_x,
            y1=width,
            line=_LINE,
            layer="above",
        )
    )

    r = 9.15
    shapes.append(
        dict(
            type="circle",
            xref="x",
            yref="y",
            x0=mid_x - r,
            y0=mid_y - r,
            x1=mid_x + r,
            y1=mid_y + r,
            fillcolor="rgba(0,0,0,0)",
            line=_LINE,
            layer="above",
        )
    )

    pen_depth, pen_half = 16.5, 40.32 / 2
    six_depth, six_half = 5.5, 18.32 / 2
    for x0, x1 in ((0.0, pen_depth), (length - pen_depth, length)):
        shapes.append(
            dict(
                type="rect",
                xref="x",
                yref="y",
                x0=x0,
                y0=mid_y - pen_half,
                x1=x1,
                y1=mid_y + pen_half,
                fillcolor="rgba(0,0,0,0)",
                line=_LINE,
                layer="above",
            )
        )
    for x0, x1 in ((0.0, six_depth), (length - six_depth, length)):
        shapes.append(
            dict(
                type="rect",
                xref="x",
                yref="y",
                x0=x0,
                y0=mid_y - six_half,
                x1=x1,
                y1=mid_y + six_half,
                fillcolor="rgba(0,0,0,0)",
                line=_LINE,
                layer="above",
            )
        )

    goal_half = 7.32 / 2
    for x in (0.0, length):
        shapes.append(
            dict(
                type="line",
                xref="x",
                yref="y",
                x0=x,
                y0=mid_y - goal_half,
                x1=x,
                y1=mid_y + goal_half,
                line=dict(color="rgba(255,255,255,0.65)", width=3),
                layer="above",
            )
        )

    return shapes


def build_pitch_figure(
    *,
    short_labels: dict[str, str],
    counts: dict[str, dict[str, int]],
    selected: str | None,
) -> go.Figure:
    """Figura única: terreno (shapes) + marcadores (Scatter) en coords 0–105 × 0–68."""
    positions = list(PITCH_COORDS.keys())
    xs: list[float] = []
    ys: list[float] = []
    texts: list[str] = []
    customdata: list[list[str]] = []
    hover: list[str] = []
    sizes: list[float] = []
    colors: list[str] = []
    line_colors: list[str] = []
    line_widths: list[float] = []

    for position in positions:
        x, y = PITCH_COORDS[position]
        short = short_labels.get(position, position[:3].upper())
        reports = int(counts.get(position, {}).get("reports_count") or 0)
        is_sel = selected == position
        xs.append(x)
        ys.append(y)
        texts.append(f"{short} · {reports}")
        customdata.append([position])
        hover.append(f"<b>{position}</b><br>Informes: {reports}<extra></extra>")
        sizes.append(28 if is_sel else 22)
        colors.append(_SELECTED_FACE if is_sel else _MARKER_FACE)
        line_colors.append(_SELECTED_LINE if is_sel else _MARKER_LINE)
        line_widths.append(3.2 if is_sel else 1.6)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="markers+text",
            text=texts,
            textposition="top center",
            textfont=dict(
                size=11,
                color="#F8FAFC",
                family="Inter, ui-sans-serif, system-ui, sans-serif",
            ),
            customdata=customdata,
            hovertemplate=hover,
            marker=dict(
                size=sizes,
                color=colors,
                line=dict(color=line_colors, width=line_widths),
                symbol="circle",
                opacity=0.98,
            ),
            selected=dict(
                marker=dict(size=30, color=_SELECTED_FACE),
            ),
            unselected=dict(
                marker=dict(opacity=0.92),
            ),
            cliponaxis=True,
        )
    )

    # Puntos de penalti y centro (decorativos, no seleccionables).
    fig.add_trace(
        go.Scatter(
            x=[11.0, PITCH_LENGTH / 2, PITCH_LENGTH - 11.0],
            y=[PITCH_WIDTH / 2, PITCH_WIDTH / 2, PITCH_WIDTH / 2],
            mode="markers",
            marker=dict(size=5, color="rgba(255,255,255,0.92)", line=dict(width=0)),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # height fijo + autosize; NO width numérico (evita encogimiento acumulativo).
    # constrain="domain" con scaleanchor evita el bug de Plotly que reduce el
    # área útil en cada resize/rerun responsive.
    fig.update_layout(
        autosize=True,
        height=540,
        margin=dict(l=8, r=8, t=8, b=8),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        shapes=_pitch_shapes(),
        dragmode=False,
        clickmode="event+select",
        hovermode="closest",
        uirevision="dashboard_pitch_stable",
    )
    fig.update_xaxes(
        range=[-1.5, PITCH_LENGTH + 1.5],
        visible=False,
        fixedrange=True,
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        constrain="domain",
    )
    fig.update_yaxes(
        range=[-1.5, PITCH_WIDTH + 1.5],
        visible=False,
        fixedrange=True,
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        scaleanchor="x",
        scaleratio=1,
        constrain="domain",
    )
    return fig



def _selection_points(event: Any) -> list[dict[str, Any]]:
    if event is None:
        return []
    selection = getattr(event, "selection", None)
    if selection is None and isinstance(event, dict):
        selection = event.get("selection")
    if selection is None:
        return []
    points = getattr(selection, "points", None)
    if points is None and isinstance(selection, dict):
        points = selection.get("points")
    return list(points or [])


def _position_from_point(point: dict[str, Any]) -> str | None:
    custom = point.get("customdata")
    if isinstance(custom, (list, tuple)) and custom:
        value = custom[0]
        return str(value) if value is not None else None
    if isinstance(custom, str) and custom.strip():
        return custom.strip()
    # Fallback: emparejar por coordenadas.
    try:
        px = float(point.get("x"))
        py = float(point.get("y"))
    except (TypeError, ValueError):
        return None
    for position, (x, y) in PITCH_COORDS.items():
        if abs(x - px) < 0.6 and abs(y - py) < 0.6:
            return position
    return None


def apply_pitch_selection(event: Any) -> str | None:
    """
    Lee el evento de st.plotly_chart(..., on_select='rerun') y actualiza
    st.session_state['dashboard_selected_position'] si hay un marcador válido.
    """
    points = _selection_points(event)
    if not points:
        return st.session_state.get("dashboard_selected_position")
    # Preferir el primer punto del trace de posiciones (curveNumber 0).
    ordered = sorted(points, key=lambda p: int(p.get("curveNumber") or 0))
    for point in ordered:
        if int(point.get("curveNumber") or 0) != 0:
            continue
        position = _position_from_point(point)
        if position and position in PITCH_COORDS:
            st.session_state["dashboard_selected_position"] = position
            return position
    return st.session_state.get("dashboard_selected_position")


def _on_pitch_chart_select() -> None:
    """Callback Streamlit: aplica el filtro antes del resto del script (mismo rerun)."""
    apply_pitch_selection(st.session_state.get("dashboard_pitch_chart"))


def render_interactive_pitch(
    *,
    short_labels: dict[str, str],
    counts: dict[str, dict[str, int]],
    selected: str | None,
    on_clear,
) -> str | None:
    """
    Título a la izquierda; gráfico centrado; filtro vía selección Plotly (sin botones absolutos).
    Cada render construye una figura nueva (nunca se reutiliza go.Figure en session_state).
    """
    st.subheader("Mapa de posiciones (scouting manual)")

    fig = build_pitch_figure(
        short_labels=short_labels,
        counts=counts,
        selected=selected,
    )
    chart_config = {
        "displayModeBar": False,
        "doubleClick": "reset",
        "scrollZoom": False,
        "responsive": True,
    }

    _pitch_left, pitch_center, _pitch_right = st.columns([1, 5, 1], gap="small")
    with pitch_center:
        st.plotly_chart(
            fig,
            use_container_width=True,
            theme=None,
            on_select=_on_pitch_chart_select,
            selection_mode="points",
            key="dashboard_pitch_chart",
            config=chart_config,
        )

    chip_col, clear_col = st.columns([3.5, 1.0], gap="small")
    with chip_col:
        if selected:
            st.markdown(filter_chip("Posición", str(selected)), unsafe_allow_html=True)
        else:
            st.caption("Haz clic en una posición del campo para filtrar informes.")
    with clear_col:
        if selected:
            st.button(
                labeled("clear", "Limpiar filtro"),
                key="pitch_clear_all_positions",
                use_container_width=False,
                type="secondary",
                on_click=on_clear,
            )

    return st.session_state.get("dashboard_selected_position")
