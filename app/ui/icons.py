"""Iconografía discreta (SVG inline) + etiquetas para botones Streamlit."""

from __future__ import annotations

from typing import Literal

IconName = Literal[
    "dashboard",
    "report",
    "player",
    "compare",
    "hidden",
    "chart",
    "search",
    "save",
    "clear",
    "edit",
    "hide",
    "restore",
    "delete",
    "refresh",
    "logout",
    "scout",
    "activity",
    "filter",
    "match",
    "admin",
    "users",
    "document",
    "spark",
]

# Glifos tipográficos sobrios para st.button / labels (sin emojis).
_GLYPH: dict[str, str] = {
    "dashboard": "▦",
    "report": "✎",
    "player": "◎",
    "compare": "⇄",
    "hidden": "◌",
    "chart": "◫",
    "search": "⌕",
    "save": "☑",
    "clear": "↺",
    "edit": "✎",
    "hide": "⊘",
    "restore": "↩",
    "delete": "⌫",
    "refresh": "↻",
    "logout": "⎋",
    "scout": "▹",
    "activity": "▣",
    "filter": "☰",
    "match": "⋈",
    "admin": "⚙",
    "users": "◎",
    "document": "▤",
    "spark": "✦",
}

PAGE_ICON_KEYS: dict[str, IconName] = {
    "Dashboard": "dashboard",
    "Nuevo informe": "report",
    "Consultar jugador": "player",
    "Comparación": "compare",
    "Informes ocultos": "hidden",
    "Datos objetivos": "chart",
    "Matching": "match",
    "Administración": "admin",
}

# Paths SVG 24x24 (stroke), estilo outline profesional.
_SVG_PATHS: dict[str, str] = {
    "dashboard": (
        '<rect x="3" y="3" width="8" height="8" rx="1.5"/>'
        '<rect x="13" y="3" width="8" height="5" rx="1.5"/>'
        '<rect x="13" y="10" width="8" height="11" rx="1.5"/>'
        '<rect x="3" y="13" width="8" height="8" rx="1.5"/>'
    ),
    "report": (
        '<path d="M5 3.5h10l4 4V20.5H5z"/>'
        '<path d="M15 3.5V8h4"/>'
        '<path d="M8 12h8M8 15.5h6"/>'
    ),
    "player": (
        '<circle cx="12" cy="8" r="3.2"/>'
        '<path d="M5.5 19.5c1.2-3.2 3.4-4.8 6.5-4.8s5.3 1.6 6.5 4.8"/>'
    ),
    "compare": (
        '<path d="M7 7h10M7 12h7M7 17h10"/>'
        '<path d="M17 5l3 2-3 2M7 15l-3 2 3 2"/>'
    ),
    "hidden": (
        '<path d="M3.5 12s3.2-5.5 8.5-5.5S20.5 12 20.5 12s-3.2 5.5-8.5 5.5S3.5 12 3.5 12z"/>'
        '<circle cx="12" cy="12" r="2.4"/>'
        '<path d="M4 20L20 4"/>'
    ),
    "chart": (
        '<path d="M4 19.5h16"/>'
        '<path d="M7 16V10M12 16V7M17 16v-4"/>'
    ),
    "search": (
        '<circle cx="11" cy="11" r="5.5"/>'
        '<path d="M16 16l4 4"/>'
    ),
    "save": (
        '<path d="M5 4.5h11l3 3V19.5H5z"/>'
        '<path d="M8 4.5v5h7v-5"/>'
        '<path d="M8 19.5v-6h8v6"/>'
    ),
    "clear": (
        '<path d="M4.5 12a7.5 7.5 0 1 0 2.2-5.3"/>'
        '<path d="M4.5 4.5v5h5"/>'
    ),
    "edit": (
        '<path d="M5 19l.8-3.8L16.6 4.4a1.6 1.6 0 0 1 2.3 2.3L8.1 17.5z"/>'
        '<path d="M13.5 6.5l3.8 3.8"/>'
    ),
    "hide": (
        '<path d="M3.5 12s3.2-5.5 8.5-5.5S20.5 12 20.5 12s-3.2 5.5-8.5 5.5S3.5 12 3.5 12z"/>'
        '<path d="M4 20L20 4"/>'
    ),
    "restore": (
        '<path d="M8 7H4.5v3.5"/>'
        '<path d="M5 10.5A7.5 7.5 0 1 0 6.2 7"/>'
    ),
    "delete": (
        '<path d="M5 7.5h14"/>'
        '<path d="M9 7.5V5.5h6v2"/>'
        '<path d="M7.5 7.5l.8 12h7.4l.8-12"/>'
    ),
    "refresh": (
        '<path d="M4.5 12a7.5 7.5 0 0 0 12.8 5.3M19.5 12A7.5 7.5 0 0 0 6.7 6.7"/>'
        '<path d="M19.5 5.5v5h-5M4.5 18.5v-5h5"/>'
    ),
    "logout": (
        '<path d="M10 5.5H6.5A2 2 0 0 0 4.5 7.5v9a2 2 0 0 0 2 2H10"/>'
        '<path d="M14 12H21"/>'
        '<path d="M18 8.5L21.5 12 18 15.5"/>'
    ),
    "scout": (
        '<rect x="5" y="4.5" width="14" height="15" rx="2"/>'
        '<path d="M9 4.5v-1h6v1M8 10h8M8 13.5h8M8 17h5"/>'
    ),
    "activity": (
        '<path d="M4 19.5h16"/>'
        '<path d="M6 15.5l3-5 3 3 4-7 2 2"/>'
    ),
    "filter": (
        '<path d="M4.5 6.5h15l-5.5 6.5v5l-4 1.5v-6.5z"/>'
    ),
    "match": (
        '<circle cx="8" cy="12" r="4"/>'
        '<circle cx="16" cy="12" r="4"/>'
    ),
    "admin": (
        '<circle cx="12" cy="12" r="3"/>'
        '<path d="M12 3.5v2.2M12 18.3v2.2M3.5 12h2.2M18.3 12h2.2'
        'M6.1 6.1l1.6 1.6M16.3 16.3l1.6 1.6M17.9 6.1l-1.6 1.6M7.7 16.3l-1.6 1.6"/>'
    ),
    "users": (
        '<circle cx="9" cy="9" r="2.6"/>'
        '<circle cx="16" cy="10" r="2.2"/>'
        '<path d="M3.8 18.5c.9-2.6 2.7-4 5.2-4s4.3 1.4 5.2 4"/>'
        '<path d="M14 18.5c.5-1.5 1.5-2.4 3.2-2.4 1.4 0 2.4.7 3 .2"/>'
    ),
    "document": (
        '<path d="M7 4.5h7l3 3V19.5H7z"/>'
        '<path d="M14 4.5V8h3"/>'
        '<path d="M9.5 12h5M9.5 15h4"/>'
    ),
    "spark": (
        '<path d="M12 3.5l1.4 5.1L18.5 10l-5.1 1.4L12 16.5l-1.4-5.1L5.5 10l5.1-1.4z"/>'
    ),
}


def glyph(name: str) -> str:
    """Símbolo tipográfico para etiquetas de botones Streamlit."""
    return _GLYPH.get(name, "•")


def labeled(name: str, text: str) -> str:
    """Texto de botón con icono tipográfico discreto."""
    return f"{glyph(name)}  {text}"


def svg_icon(name: str, *, size: int = 18, class_name: str = "scouting-icon") -> str:
    """SVG outline listo para insertar en HTML (sin escapar)."""
    paths = _SVG_PATHS.get(name)
    if not paths:
        return ""
    return (
        f'<svg class="{class_name}" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
        f'<g stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
        f'stroke-linejoin="round">{paths}</g></svg>'
    )


def page_icon_key(page: str) -> IconName | None:
    return PAGE_ICON_KEYS.get(page)
