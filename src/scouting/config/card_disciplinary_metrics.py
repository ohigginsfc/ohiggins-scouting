"""Métricas disciplinarias (tarjetas): totales y minutos por tarjeta (no /90)."""

from __future__ import annotations

CARD_STAT_SPECS: tuple[tuple[str, str, str], ...] = (
    ("yellowCard", "yellowCard_total", "minutes_per_yellow_card"),
    ("redCard", "redCard_total", "minutes_per_red_card"),
    ("yellowRedCard", "yellowRedCard_total", "minutes_per_yellow_red_card"),
)

CARD_PER90_METRICS: frozenset[str] = frozenset(
    {
        "yellowCard_per90",
        "redCard_per90",
        "yellowRedCard_per90",
    }
)

CARD_TOTAL_METRICS: frozenset[str] = frozenset(
    spec[1] for spec in CARD_STAT_SPECS
)

CARD_MINUTES_PER_METRICS: frozenset[str] = frozenset(
    spec[2] for spec in CARD_STAT_SPECS
)

CARD_DISCIPLINARY_DISPLAY_METRICS: frozenset[str] = (
    CARD_TOTAL_METRICS | CARD_MINUTES_PER_METRICS
)

# Totales disciplinarios: más alto ≠ mejor rendimiento (nota en comparativas).
DISCIPLINARY_HIGHER_NOT_BETTER: frozenset[str] = frozenset(
    {"yellowCard_total", "redCard_total", "yellowRedCard_total"}
)


def derive_card_metrics(
    *,
    yellow_card: float | int | None = None,
    red_card: float | int | None = None,
    yellow_red_card: float | int | None = None,
    minutes_played: float,
) -> dict[str, float]:
    """Totales y minutos/tarjeta a partir de conteos acumulados."""
    counts = {
        "yellowCard": yellow_card,
        "redCard": red_card,
        "yellowRedCard": yellow_red_card,
    }
    out: dict[str, float] = {}
    mp = float(minutes_played or 0)
    for base, total_name, mins_name in CARD_STAT_SPECS:
        raw = counts.get(base)
        if raw is None:
            continue
        try:
            total = float(raw)
        except (TypeError, ValueError):
            continue
        if total <= 0:
            continue
        out[total_name] = total
        if mp > 0:
            out[mins_name] = round(mp / total, 2)
    return out


def is_card_minutes_per_metric(metric_name: str) -> bool:
    return str(metric_name).strip() in CARD_MINUTES_PER_METRICS
