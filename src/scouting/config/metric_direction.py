"""Dirección de métricas objetivas para percentiles de rendimiento."""

from __future__ import annotations

from typing import Any

HIGHER_IS_BETTER = "higher_is_better"
LOWER_IS_BETTER = "lower_is_better"

# Métricas donde un valor alto en la cohorte implica peor rendimiento.
# Métricas positivas: nunca deben figurar en LOWER_IS_BETTER_METRICS.
HIGHER_IS_BETTER_POSITIVE_METRICS: frozenset[str] = frozenset({
    "outfielderBlock_per90",
    "totalTackle_per90",
    "wonTackle_per90",
    "interceptionWon_per90",
    "totalClearance_per90",
    "ballRecovery_per90",
    "duelWon_per90",
    "aerialWon_per90",
})

LOWER_IS_BETTER_METRICS: frozenset[str] = frozenset({
    "duelLost_per90",
    "aerialLost_per90",
    "challengeLost_per90",
    "possessionLostCtrl_per90",
    "dispossessed_per90",
    "unsuccessfulTouch_per90",
    "foulsCommited_per90",
    "foulsCommitted_per90",
    "yellowCard_total",
    "redCard_total",
    "yellowRedCard_total",
    "yellowCard_per90",
    "redCard_per90",
    "yellowRedCard_per90",
    "penaltyConceded_per90",
    "errorLeadToAGoal_per90",
    "errorLeadToAShot_per90",
    "ownGoals_per90",
    "bigChanceMissed_per90",
    "goalsConceded_per90",
    "goalsConcededInsideTheBox_per90",
    "goalsConcededOutsideTheBox_per90",
})

_METRIC_ALIASES: dict[str, str] = {
    "foulsCommitted_per90": "foulsCommited_per90",
}


def normalize_metric_name(metric_name: str) -> str:
    name = str(metric_name or "").strip()
    return _METRIC_ALIASES.get(name, name)


def positive_metrics_in_lower_registry() -> list[str]:
    """Métricas positivas erróneamente marcadas como lower-is-better (debe ser vacío)."""
    return sorted(HIGHER_IS_BETTER_POSITIVE_METRICS & LOWER_IS_BETTER_METRICS)


def is_lower_better_metric(metric_name: str) -> bool:
    """True si un valor alto indica peor rendimiento (menor es mejor)."""
    name = normalize_metric_name(metric_name)
    if name in HIGHER_IS_BETTER_POSITIVE_METRICS:
        return False
    return name in LOWER_IS_BETTER_METRICS


def metric_direction_label(metric_name: str) -> str:
    return LOWER_IS_BETTER if is_lower_better_metric(metric_name) else HIGHER_IS_BETTER


COHORT_RADAR_SCALE_P_LOW = 5.0
COHORT_RADAR_SCALE_P_HIGH = 95.0
POSITION_AVG_RADAR_MAX_RATIO = 2.0


def linear_percentile_value(values: list[float], percentile: float) -> float | None:
    """Percentil lineal (0–100) sobre valores de cohorte."""
    if not values:
        return None
    if len(values) == 1:
        return float(values[0])
    sorted_vals = sorted(float(v) for v in values)
    p = max(0.0, min(100.0, float(percentile)))
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def normalize_to_cohort_scale(
    value: float,
    min_value: float,
    max_value: float,
    *,
    clip: bool = True,
) -> float | None:
    """Normaliza un valor entre P5 y P95 de la cohorte (0 = P5, 1 = P95)."""
    span = float(max_value) - float(min_value)
    if span <= 0:
        return None
    norm = (float(value) - float(min_value)) / span
    if clip:
        return max(0.0, min(1.0, norm))
    return norm


def ratio_to_position_avg(
    player_value: float,
    position_avg_value: float,
    metric_name: str,
    *,
    max_ratio: float = POSITION_AVG_RADAR_MAX_RATIO,
) -> float | None:
    """
    Ratio jugador vs media de posición para radar (1.0 = media).
    higher-is-better: player / avg; lower-is-better: avg / player; tope en max_ratio.
    """
    avg = float(position_avg_value)
    val = float(player_value)
    if avg <= 0:
        return None
    if is_lower_better_metric(metric_name):
        if val <= 0:
            return max_ratio
        ratio = avg / val
    else:
        if val < 0:
            return None
        ratio = val / avg
    return min(max(ratio, 0.0), max_ratio)


def performance_percentile_from_raw(raw_percentile: float, metric_name: str) -> float:
    """
    Percentil de rendimiento: P100 = mejor, P0 = peor.
    Para métricas lower-is-better invierte el percentil estadístico.
    """
    raw = max(0.0, min(100.0, float(raw_percentile)))
    if is_lower_better_metric(metric_name):
        return 100.0 - raw
    return raw


def enrich_percentile_row(row: dict[str, Any]) -> dict[str, Any]:
    """Añade raw_percentile, performance_percentile y lower_is_better; percentile = rendimiento."""
    mname = str(row.get("metric_name") or "")
    raw = row.get("percentile")
    if raw is None:
        return row
    raw_f = float(raw)
    row["raw_percentile"] = round(raw_f, 1)
    row["lower_is_better"] = is_lower_better_metric(mname)
    perf = performance_percentile_from_raw(raw_f, mname)
    row["performance_percentile"] = round(perf, 1)
    row["percentile"] = round(perf, 1)
    row["metric_direction"] = metric_direction_label(mname)
    return row


def enrich_percentile_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for row in rows:
        enrich_percentile_row(row)
    return rows
