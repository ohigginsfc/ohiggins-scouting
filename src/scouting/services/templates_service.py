"""Acceso a plantillas de posición (sin I/O)."""

from __future__ import annotations

from typing import Any

from scouting.templates.position_templates import (
    POSITION_TEMPLATES,
    resolve_template_key_for_position,
)

# Legacy (informes antiguos Físico/Técnico/Táctico/Mental); se añaden al final si aparecen.
LEGACY_GROUP_ORDER = ("Físico", "Técnico", "Táctico", "Mental")

# Posiciones ofrecidas en formularios (ficha scouting).
PRIMARY_POSITIONS_ORDER: tuple[str, ...] = (
    "Portero",
    "Central derecho",
    "Central izquierdo",
    "Lateral derecho",
    "Lateral izquierdo",
    "Mediocentro defensivo",
    "Mediocentro",
    "Mediocentro ofensivo",
    "Extremo derecho",
    "Extremo izquierdo",
    "Delantero",
)

# Compatibilidad: código que importaba GROUP_ORDER
GROUP_ORDER = LEGACY_GROUP_ORDER


def get_available_positions() -> list[str]:
    return list(PRIMARY_POSITIONS_ORDER)


def positions_for_template_key(template_key: str) -> list[str]:
    """Posiciones de ficha que comparten la misma plantilla de atributos."""
    out: list[str] = []
    seen: set[str] = set()
    for ui_pos in PRIMARY_POSITIONS_ORDER:
        try:
            if resolve_template_key_for_position(ui_pos) == template_key:
                out.append(ui_pos)
                seen.add(ui_pos)
        except KeyError:
            continue
    if template_key not in seen and template_key in POSITION_TEMPLATES:
        out.append(template_key)
    return out


def get_template_key_for_position(position: str) -> str:
    """Clave de plantilla (Portero, Lateral, Volante central, …)."""
    return resolve_template_key_for_position(position)


def get_template_for_position(position: str) -> dict[str, list[str]]:
    """Plantilla de atributos para una posición de ficha."""
    key = get_template_key_for_position(position)
    return dict(POSITION_TEMPLATES[key])


def get_template_group_order(template_key: str) -> tuple[str, ...]:
    """Orden de bloques (CONSTRUCCIÓN EN SALIDA, DEFENSIVO, …) en la plantilla."""
    if template_key not in POSITION_TEMPLATES:
        return ()
    return tuple(POSITION_TEMPLATES[template_key].keys())


def get_flat_attributes_for_position(position: str) -> list[tuple[str, str]]:
    """Lista de (attribute_group, attribute_name) en el orden definido en la plantilla."""
    template = get_template_for_position(position)
    rows: list[tuple[str, str]] = []
    for group, attrs in template.items():
        for name in attrs:
            rows.append((group, name))
    return rows


def sort_attributes_by_position_template(
    position: str,
    rows: list[dict[str, Any]],
    group_key: str = "attribute_group",
    name_key: str = "attribute_name",
) -> list[dict[str, Any]]:
    """Ordena filas según la plantilla resuelta para `position`."""
    try:
        template_key = get_template_key_for_position(position)
    except KeyError:
        return sorted(rows, key=lambda r: (str(r.get(group_key)), str(r.get(name_key))))

    order: list[tuple[str, str]] = []
    for g, attrs in POSITION_TEMPLATES[template_key].items():
        for a in attrs:
            order.append((g, a))
    idx = {(g, a): i for i, (g, a) in enumerate(order)}

    ranked: list[tuple[int, dict[str, Any]]] = []
    tail: list[dict[str, Any]] = []
    for r in rows:
        k = (str(r.get(group_key)), str(r.get(name_key)))
        if k in idx:
            ranked.append((idx[k], r))
        else:
            tail.append(r)
    ranked.sort(key=lambda x: x[0])
    out = [r for _, r in ranked]
    out.extend(sorted(tail, key=lambda r: (str(r.get(group_key)), str(r.get(name_key)))))
    return out


def attribute_order_index_within_group(position: str, group: str) -> dict[str, int]:
    """Índice de orden de atributos dentro de un bloque según plantilla."""
    try:
        template_key = get_template_key_for_position(position)
    except KeyError:
        return {}
    attrs = POSITION_TEMPLATES[template_key].get(group, [])
    return {name: i for i, name in enumerate(attrs)}


def ordered_attribute_groups_for_position(
    groups_present: set[str],
    position: str | None,
) -> list[str]:
    """Orden de bloques para UI: plantilla actual + legacy al final."""
    order: list[str] = []
    remaining = set(groups_present)
    if position:
        try:
            template_key = get_template_key_for_position(position)
            for g in get_template_group_order(template_key):
                if g in remaining:
                    order.append(g)
                    remaining.remove(g)
        except KeyError:
            pass
    for g in LEGACY_GROUP_ORDER:
        if g in remaining:
            order.append(g)
            remaining.remove(g)
    order.extend(sorted(remaining))
    return order
