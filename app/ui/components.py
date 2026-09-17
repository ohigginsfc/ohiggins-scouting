"""Componentes visuales reutilizables (HTML escapado, sin lógica de negocio)."""

from __future__ import annotations

import html
from typing import Any, Callable

import streamlit as st

from ui.icons import page_icon_key, svg_icon


def _esc(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _icon_html(icon: str | None, *, size: int = 18, class_name: str = "scouting-icon") -> str:
    """Acepta clave de icono SVG o texto/glifo ya resuelto."""
    if not icon:
        return ""
    # Clave conocida → SVG; si no, tratar como glifo/texto escapado.
    rendered = svg_icon(icon, size=size, class_name=class_name)
    if rendered:
        return f'<span class="scouting-icon-wrap">{rendered}</span>'
    return f'<span class="scouting-icon-wrap scouting-icon-glyph">{_esc(icon)}</span>'


def page_header(
    title: str,
    subtitle: str | None = None,
    *,
    icon: str | None = None,
    actions: Callable[[], None] | None = None,
) -> None:
    """Cabecera de página: icono + título + subtítulo; acciones opcionales."""
    resolved_icon = icon if icon is not None else page_icon_key(title)
    icon_block = _icon_html(resolved_icon, size=22, class_name="scouting-icon scouting-icon--page")
    body = f"""
    <div class="scouting-page-header">
      <div class="scouting-page-header-text">
        <div class="scouting-page-title-row">
          {icon_block}
          <h2 class="scouting-page-title">{_esc(title)}</h2>
        </div>
        {f'<p class="scouting-page-subtitle">{_esc(subtitle)}</p>' if subtitle else ''}
      </div>
    </div>
    """
    if actions is None:
        st.markdown(body, unsafe_allow_html=True)
        return

    left, right = st.columns([4.2, 1.4], gap="small")
    with left:
        st.markdown(body, unsafe_allow_html=True)
    with right:
        actions()


def section_header(
    title: str,
    subtitle: str | None = None,
    *,
    icon: str | None = None,
) -> None:
    icon_block = _icon_html(icon, size=16, class_name="scouting-icon scouting-icon--section")
    st.markdown(
        f"""
        <div class="scouting-section-header">
          <div class="scouting-section-title-row">
            {icon_block}
            <h3 class="scouting-section-title">{_esc(title)}</h3>
          </div>
          {f'<p class="scouting-section-subtitle">{_esc(subtitle)}</p>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(
    label: str,
    value: Any,
    *,
    icon: str | None = None,
    tone: str = "blue",
    helper_text: str | None = None,
    trend: str | None = None,
) -> None:
    safe_tone = tone if tone in {"blue", "green", "yellow", "slate", "info"} else "blue"
    icon_html = _icon_html(icon, size=16, class_name="scouting-icon scouting-icon--metric")
    helper_html = (
        f'<p class="scouting-metric-helper">{_esc(helper_text)}</p>' if helper_text else ""
    )
    trend_html = f'<span class="scouting-metric-trend">{_esc(trend)}</span>' if trend else ""
    st.markdown(
        f"""
        <div class="scouting-metric-card scouting-metric-card--{safe_tone}">
          <div class="scouting-metric-top">
            <span class="scouting-metric-label">{_esc(label)}</span>
            {icon_html}
          </div>
          <div class="scouting-metric-value">{_esc(value)}{trend_html}</div>
          {helper_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(label: str, *, tone: str = "neutral", icon: str | None = None) -> str:
    """HTML de badge de estado."""
    safe_tone = (
        tone
        if tone in {"neutral", "info", "success", "warning", "danger", "violet"}
        else "neutral"
    )
    icon_block = _icon_html(icon, size=12, class_name="scouting-icon scouting-icon--badge")
    return (
        f'<span class="scouting-badge scouting-badge--{safe_tone}">'
        f"{icon_block}{_esc(label)}</span>"
    )


def recommendation_badge(recommendation: str | None) -> str:
    """Badge HTML según recomendación de scouting."""
    rec = (recommendation or "").strip()
    mapping = {
        "Seguir monitorizando": "info",
        "Interesante": "violet",
        "Prioritario": "success",
        "Descartar": "danger",
    }
    tone = mapping.get(rec, "neutral")
    return status_badge(rec or "—", tone=tone)


def empty_state(
    title: str,
    description: str | None = None,
    *,
    icon: str | None = None,
    action_label: str | None = None,
) -> None:
    icon_html = _icon_html(icon or "search", size=28, class_name="scouting-icon scouting-icon--empty")
    desc_html = (
        f'<p class="scouting-empty-desc">{_esc(description)}</p>' if description else ""
    )
    action_hint = (
        f'<p class="scouting-empty-action-hint">{_esc(action_label)}</p>'
        if action_label
        else ""
    )
    st.markdown(
        f"""
        <div class="scouting-empty-state">
          <div class="scouting-empty-icon">{icon_html}</div>
          <p class="scouting-empty-title">{_esc(title)}</p>
          {desc_html}
          {action_hint}
        </div>
        """,
        unsafe_allow_html=True,
    )


def player_header(
    *,
    name: str,
    position: str | None = None,
    club: str | None = None,
    nationality: str | None = None,
    recommendation: str | None = None,
    rating: Any = None,
    extras: list[tuple[str, Any]] | None = None,
) -> None:
    meta_parts: list[str] = []
    for label, val in (
        ("Posición", position),
        ("Club", club),
        ("Nacionalidad", nationality),
    ):
        if val:
            meta_parts.append(
                f'<span class="scouting-player-meta-item">'
                f'<span class="scouting-player-meta-label">{_esc(label)}</span> '
                f"{_esc(val)}</span>"
            )
    if extras:
        for label, val in extras:
            if val is None or str(val).strip() == "":
                continue
            meta_parts.append(
                f'<span class="scouting-player-meta-item">'
                f'<span class="scouting-player-meta-label">{_esc(label)}</span> '
                f"{_esc(val)}</span>"
            )

    badges = ""
    if recommendation:
        badges += recommendation_badge(recommendation)
    if rating is not None and str(rating).strip() not in ("", "—"):
        badges += status_badge(f"Valoración {rating}", tone="neutral")

    st.markdown(
        f"""
        <div class="scouting-player-header">
          <div class="scouting-player-header-main">
            <div class="scouting-player-title-row">
              {_icon_html("player", size=20, class_name="scouting-icon scouting-icon--player")}
              <h3 class="scouting-player-name">{_esc(name)}</h3>
            </div>
            <div class="scouting-player-meta">{''.join(meta_parts)}</div>
          </div>
          <div class="scouting-player-badges">{badges}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def info_item(label: str, value: Any) -> None:
    disp = "—" if value is None or (isinstance(value, str) and not value.strip()) else value
    st.markdown(
        f"""
        <div class="scouting-info-item">
          <span class="scouting-info-label">{_esc(label)}</span>
          <span class="scouting-info-value">{_esc(disp)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def toolbar(*parts: str) -> None:
    """Fila de texto/HTML ya escapado o badges."""
    st.markdown(
        f'<div class="scouting-toolbar">{"".join(parts)}</div>',
        unsafe_allow_html=True,
    )


def action_group() -> Any:
    """Contenedor de columnas para acciones compactas (caller usa with)."""
    return st.container()


def success_message(text: str) -> None:
    st.markdown(
        f'<div class="scouting-flash scouting-flash--success">'
        f'{_icon_html("spark", size=14)}{_esc(text)}</div>',
        unsafe_allow_html=True,
    )


def warning_message(text: str) -> None:
    st.markdown(
        f'<div class="scouting-flash scouting-flash--warning">{_esc(text)}</div>',
        unsafe_allow_html=True,
    )


def filter_chip(label: str, value: str, *, icon: str | None = "filter") -> str:
    icon_block = _icon_html(icon, size=13, class_name="scouting-icon scouting-icon--chip")
    return (
        f'<span class="scouting-filter-chip">'
        f"{icon_block}"
        f'<span class="scouting-filter-chip-label">{_esc(label)}</span> '
        f"<strong>{_esc(value)}</strong></span>"
    )


def sofascore_panel_html(
    *,
    season: str,
    status_label: str,
    status_tone: str,
    result_label: str,
    last_check: str,
) -> str:
    badge = status_badge(status_label, tone=status_tone)
    return f"""
    <div class="scouting-sofascore-panel">
      <div class="scouting-sofascore-accent"></div>
      <div class="scouting-sofascore-main">
        <div class="scouting-sofascore-title">
          {_icon_html("refresh", size=15)}
          Datos deportivos
        </div>
        <div class="scouting-sofascore-meta">
          <span>Temporada {_esc(season)}</span>
          <span class="scouting-dot">·</span>
          {badge}
          <span class="scouting-dot">·</span>
          <span class="scouting-muted">{_esc(result_label)}</span>
        </div>
        <div class="scouting-sofascore-date">Última actualización: {_esc(last_check)}</div>
      </div>
    </div>
    """


def recommendation_tone(recommendation: str | None) -> dict[str, str]:
    """Estilos inline para pandas Styler (celda de recomendación)."""
    rec = (recommendation or "").strip()
    styles = {
        "Seguir monitorizando": {
            "background-color": "#EAF3FB",
            "color": "#2F6FAE",
        },
        "Interesante": {
            "background-color": "#EEF4FF",
            "color": "#3B6BB5",
        },
        "Prioritario": {
            "background-color": "#EDF8EC",
            "color": "#2F7A2C",
        },
        "Descartar": {
            "background-color": "#FEF3F2",
            "color": "#B42318",
        },
    }
    base = styles.get(rec, {"background-color": "#F8FAFC", "color": "#667085"})
    return {
        **base,
        "border-radius": "999px",
        "padding": "2px 8px",
        "font-weight": "600",
        "font-size": "0.78rem",
    }


def form_section(title: str, subtitle: str | None = None, *, icon: str | None = None) -> None:
    """Título de sección de formulario con acento e icono."""
    icon_block = _icon_html(icon, size=15, class_name="scouting-icon scouting-icon--form")
    st.markdown(
        f"""
        <div class="scouting-form-section">
          <div class="scouting-form-section-title-row">
            {icon_block}
            <p class="scouting-form-section-title">{_esc(title)}</p>
          </div>
          {f'<p class="scouting-form-section-sub">{_esc(subtitle)}</p>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )
