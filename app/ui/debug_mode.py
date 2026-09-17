"""Modo depuración: textos técnicos y diagnósticos solo visibles si está activo."""

from __future__ import annotations

import os

# Por defecto oculto para cliente final. Activar con SCOUTING_DEBUG_MODE=1
DEBUG_MODE = os.environ.get("SCOUTING_DEBUG_MODE", "").lower() in (
    "1",
    "true",
    "yes",
)


def is_debug_mode() -> bool:
    return DEBUG_MODE
