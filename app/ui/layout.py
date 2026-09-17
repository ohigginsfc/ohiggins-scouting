"""Layout principal: cabecera superior (sin sidebar)."""

from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import Callable, Sequence

import streamlit as st

from ui.components import page_header
from ui.icons import labeled, page_icon_key
from ui.navigation import (
    PAGE_SUBTITLES,
    ensure_current_page,
    nav_button_key,
    navigate_to,
)


def _data_uri(path: Path | None) -> str | None:
    if path is None or not path.is_file():
        return None
    suffix = path.suffix.lower()
    mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
    }.get(suffix, "image/png")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def render_top_header(
    *,
    pages: Sequence[str],
    username: str | None,
    sport_logo_path: Path | None = None,
    crest_path: Path | None = None,
    on_logout: Callable[[], None] | None = None,
) -> str:
    """
    Banda superior única (marca + chip usuario) y navegación pills debajo.
    Sin columnas anidadas en la zona de sesión.
    """
    current_page = ensure_current_page(pages)

    campus_src = _data_uri(sport_logo_path)
    club_src = _data_uri(crest_path)
    logos_html = ""
    if campus_src:
        logos_html += (
            f'<img class="scouting-brand-logo scouting-campus-logo" '
            f'src="{campus_src}" alt="Sports Data Campus"/>'
        )
    if club_src:
        logos_html += (
            f'<img class="scouting-brand-logo scouting-club-logo" '
            f'src="{club_src}" alt="O\'Higgins"/>'
        )

    display_user = html.escape((username or "").strip() or "Usuario")

    brand_col, session_col = st.columns([5.2, 1.9], gap="medium")
    with brand_col:
        st.markdown(
            f"""
            <div class="scouting-chrome-brand">
              <div class="scouting-brand">
                {logos_html}
                <div class="scouting-brand-copy">
                  <span class="scouting-brand-title">Scouting Platform</span>
                  <span class="scouting-brand-subtitle">Digital Scouting &amp; Analysis</span>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with session_col:
        st.markdown(
            f"""
            <div class="scouting-chrome-session">
              <span class="scouting-user-chip">{display_user}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button(
            labeled("logout", "Cerrar sesión"),
            key="top_header_logout",
            use_container_width=False,
            type="secondary",
            on_click=on_logout if on_logout is not None else (lambda: None),
        )

    st.markdown('<div class="scouting-nav-strip"></div>', unsafe_allow_html=True)
    nav_cols = st.columns(len(pages), gap="small")
    for col, page_name in zip(nav_cols, pages):
        is_active = page_name == current_page
        icon_key = page_icon_key(page_name) or "dashboard"
        with col:
            st.button(
                labeled(icon_key, page_name),
                key=nav_button_key(page_name),
                help=page_name,
                use_container_width=True,
                type="primary" if is_active else "secondary",
                on_click=navigate_to,
                args=(page_name,),
            )

    return ensure_current_page(pages)


def render_page_heading(page: str) -> None:
    """Título de sección en el contenido (sin repetir la marca)."""
    page_header(page, PAGE_SUBTITLES.get(page))
