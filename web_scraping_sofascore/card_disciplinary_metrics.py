"""Totales y minutos/tarjeta (espejo de scouting.config.card_disciplinary_metrics)."""

from __future__ import annotations

CARD_STAT_SPECS: tuple[tuple[str, str, str], ...] = (
    ("yellowCard", "yellowCard_total", "minutes_per_yellow_card"),
    ("redCard", "redCard_total", "minutes_per_red_card"),
    ("yellowRedCard", "yellowRedCard_total", "minutes_per_yellow_red_card"),
)


def apply_card_derived_to_row(row: dict, minutes_played: float) -> None:
    """Añade *_total y minutes_per_* al dict agregado (in-place)."""
    mp = float(minutes_played or 0)
    for base, total_name, mins_name in CARD_STAT_SPECS:
        if base not in row:
            continue
        try:
            total = float(row[base])
        except (TypeError, ValueError):
            continue
        if total <= 0:
            continue
        if row.get(f"{base}_present_count", 0) <= 0:
            continue
        row[total_name] = total
        if mp > 0:
            row[mins_name] = round(mp / total, 2)
