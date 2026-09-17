"""Posiciones: scouting manual (fina) vs Sofascore objetivo (gruesa)."""

from __future__ import annotations

from typing import Any

# --- Scouting manual (ficha / informes) — NO mezclar con códigos G/D/M/F ---

STANDARD_POSITIONS: tuple[str, ...] = (
    "Portero",
    "Central",
    "Lateral",
    "Mediocentro",
    "Extremo",
    "Delantero",
)

_FICHA_TO_STANDARD: dict[str, str] = {
    "portero": "Portero",
    "central": "Central",
    "central derecho": "Central",
    "central izquierdo": "Central",
    "lateral": "Lateral",
    "lateral derecho": "Lateral",
    "lateral izquierdo": "Lateral",
    "mediocentro defensivo": "Mediocentro",
    "mediocentro": "Mediocentro",
    "mediocentro ofensivo": "Mediocentro",
    "extremo": "Extremo",
    "extremo derecho": "Extremo",
    "extremo izquierdo": "Extremo",
    "delantero": "Delantero",
}

# --- Sofascore objetivo (solo 4 grupos) ---

SOFASCORE_RAW_CODES: frozenset[str] = frozenset({"G", "D", "M", "F"})

SOFASCORE_OBJECTIVE_GROUPS: tuple[str, ...] = (
    "Portero",
    "Defensa",
    "Mediocampo",
    "Delantero",
)

_SOFASCORE_RAW_TO_GROUP: dict[str, str] = {
    "G": "Portero",
    "D": "Defensa",
    "M": "Mediocampo",
    "F": "Delantero",
}

_GROUP_TO_RAW: dict[str, str] = {v: k for k, v in _SOFASCORE_RAW_TO_GROUP.items()}


def normalize_sofascore_raw_code(position: str | None) -> str | None:
    """Devuelve G, D, M o F si la entrada es un código Sofascore válido."""
    if position is None or not str(position).strip():
        return None
    key = str(position).strip().upper()
    if key in SOFASCORE_RAW_CODES:
        return key
    return None


def standardize_sofascore_position(position: str | None) -> str | None:
    """
    Posición objetiva Sofascore → grupo grueso.
    G→Portero, D→Defensa, M→Mediocampo, F→Delantero.
    No infiere laterales/centrales ni posiciones de scouting.
    """
    if position is None or not str(position).strip():
        return None
    raw = normalize_sofascore_raw_code(position)
    if raw:
        return _SOFASCORE_RAW_TO_GROUP[raw]
    low = str(position).strip().lower()
    for label in SOFASCORE_OBJECTIVE_GROUPS:
        if low == label.lower():
            return label
    return None


def objective_group_to_raw_codes(group: str | None) -> list[str]:
    """Código(s) G/D/M/F para filtrar en SQL."""
    if not group or not str(group).strip():
        return []
    g = str(group).strip()
    if g in _GROUP_TO_RAW:
        return [_GROUP_TO_RAW[g]]
    raw = normalize_sofascore_raw_code(g)
    return [raw] if raw else []


def standardize_position_for_analysis(position: str | None) -> str | None:
    """Solo posiciones de ficha scouting (sin códigos Sofascore)."""
    if position is None or not str(position).strip():
        return None
    if normalize_sofascore_raw_code(position):
        return None
    key = str(position).strip().lower()
    return _FICHA_TO_STANDARD.get(key)


def standardize_position_for_objective_comparison(
    position: str | None,
    *,
    source_name: str = "Sofascore",
) -> str | None:
    """Alias: comparativas objetivas usan solo grupos Sofascore."""
    _ = source_name
    return standardize_sofascore_position(position)


def position_label_from_payload(payload: dict[str, Any] | None) -> str | None:
    """Código o posición cruda Sofascore desde raw_payload (no scouting)."""
    if not isinstance(payload, dict):
        return None
    for key in ("sofascore_position", "original_position"):
        val = payload.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    raw_row = payload.get("raw_row")
    if isinstance(raw_row, dict):
        val = raw_row.get("position")
        if val is not None and str(val).strip():
            return str(val).strip()
    return None


def raw_positions_for_standard(standard: str | None) -> list[str]:
    """Valores crudos de ficha scouting que mapean a un rol estándar."""
    if standard is None or not str(standard).strip():
        return []
    out: set[str] = {str(standard).strip()}
    for raw, std in _FICHA_TO_STANDARD.items():
        if std == standard:
            out.add(raw)
    return sorted(out)


# Compatibilidad con nombre anterior en documentación
OBJECTIVE_COMPARISON_POSITIONS = SOFASCORE_OBJECTIVE_GROUPS
