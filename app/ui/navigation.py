"""Navegación de la aplicación (session_state, sin sidebar)."""

from __future__ import annotations

from typing import Iterable

import streamlit as st

PAGE_SESSION_KEY = "page"
PREVIOUS_PAGE_KEY = "previous_page"

NAV_PAGES_BASE: tuple[str, ...] = (
    "Dashboard",
    "Nuevo informe",
    "Consultar jugador",
    "Comparación",
    "Informes ocultos",
    "Datos objetivos",
)

# Keys estables para botones de navegación (nunca reutilizar como key de widget "page").
NAV_BUTTON_KEYS: dict[str, str] = {
    "Dashboard": "nav_dashboard",
    "Nuevo informe": "nav_nuevo_informe",
    "Consultar jugador": "nav_consultar_jugador",
    "Comparación": "nav_comparacion",
    "Informes ocultos": "nav_informes_ocultos",
    "Datos objetivos": "nav_datos_objetivos",
    "Matching": "nav_matching",
    "Administración": "nav_administracion",
}

PAGE_SUBTITLES: dict[str, str] = {
    "Dashboard": "Resumen de la actividad de scouting.",
    "Nuevo informe": "Registra una evaluación de un jugador.",
    "Consultar jugador": "Explora informes, atributos y estadísticas.",
    "Comparación": "Compara perfiles entre jugadores y temporadas.",
    "Informes ocultos": "Restaura o elimina informes ocultos.",
    "Datos objetivos": "Explora estadísticas por temporada.",
    "Matching": "Herramientas de vinculación (modo depuración).",
    "Administración": "Mantenimiento e información técnica.",
}


def build_nav_pages(*, debug_mode: bool = False, show_admin: bool = False) -> tuple[str, ...]:
    pages = list(NAV_PAGES_BASE)
    if debug_mode:
        pages.insert(pages.index("Comparación") + 1, "Matching")
    if show_admin:
        pages.append("Administración")
    return tuple(pages)


def ensure_current_page(pages: Iterable[str], *, default: str = "Dashboard") -> str:
    pages_tuple = tuple(pages)
    current = st.session_state.get(PAGE_SESSION_KEY)
    if current not in pages_tuple:
        st.session_state[PAGE_SESSION_KEY] = default if default in pages_tuple else pages_tuple[0]
    return str(st.session_state[PAGE_SESSION_KEY])


def navigate_to(page: str) -> None:
    """Callback de navegación: no usa href ni limpia autenticación."""
    st.session_state[PAGE_SESSION_KEY] = page


def nav_button_key(page: str) -> str:
    return NAV_BUTTON_KEYS.get(page, f"nav_{page.lower().replace(' ', '_')}")
