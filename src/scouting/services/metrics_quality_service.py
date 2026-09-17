"""Calidad e informatividad de métricas objetivas (sin I/O)."""

from __future__ import annotations

from typing import Any

from scouting.config import metric_quality_config as qc


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_metric_informative(
    values: list[float | None],
    *,
    min_nonzero_ratio: float = qc.MIN_NONZERO_RATIO,
    min_unique_values: int = qc.MIN_UNIQUE_VALUES,
) -> bool:
    """False si la serie es vacía, todo null, todo cero, poca varianza o casi todo cero."""
    nums = [v for v in (_to_float(x) for x in values) if v is not None]
    if not nums:
        return False
    positive = [v for v in nums if abs(v) > qc.COMPARISON_EPSILON]
    if not positive:
        return False
    positive_ratio = len(positive) / len(nums)
    if positive_ratio < min_nonzero_ratio:
        return False
    distinct = len({round(v, 6) for v in nums})
    if distinct < min_unique_values:
        return False
    return True


def comparison_row_has_signal(row: dict[str, Any], *, epsilon: float = qc.COMPARISON_EPSILON) -> bool:
    pv = _to_float(row.get("player_value"))
    pa = _to_float(row.get("position_avg_value"))
    if pv is not None and abs(pv) >= epsilon:
        return True
    if pa is not None and abs(pa) >= epsilon:
        return True
    return False


def block_metric_has_signal(
    metric_name: str,
    metrics_rows: list[dict[str, Any]],
    *,
    epsilon: float = qc.COMPARISON_EPSILON,
) -> bool:
    for r in metrics_rows:
        if str(r.get("metric_name") or "") != metric_name:
            continue
        v = _to_float(r.get("metric_value"))
        if v is not None and abs(v) >= epsilon:
            return True
    return False


def filter_non_informative_comparison_rows(
    rows: list[dict[str, Any]],
    *,
    position_group: str | None = None,
    min_peers: int = qc.MIN_COHORT_PLAYERS,
) -> list[dict[str, Any]]:
    """
    Excluye filas sin señal para gráficos por defecto.
    Mantiene filas con player_value > 0 o position_avg_value > 0 aunque estén en lista excluida.
    """
    excluded = qc.default_excluded_metrics_for_position(position_group)
    out: list[dict[str, Any]] = []
    for r in rows:
        name = str(r.get("metric_name") or "").strip()
        if not name:
            continue
        peers = int(r.get("players_count") or 0)
        if peers < min_peers:
            continue
        if name in excluded and not comparison_row_has_signal(r):
            continue
        pv = _to_float(r.get("player_value"))
        pa = _to_float(r.get("position_avg_value"))
        if pv is None and pa is None:
            continue
        if (pv is None or abs(pv) < qc.COMPARISON_EPSILON) and (
            pa is None or abs(pa) < qc.COMPARISON_EPSILON
        ):
            continue
        out.append(r)
    return out


def is_metric_recommended_for_charts(
    metric_name: str,
    comparison_rows: list[dict[str, Any]],
    metrics_rows: list[dict[str, Any]],
    *,
    position_group: str | None = None,
) -> bool:
    """True = métrica recomendada; False = técnica / poco informativa."""
    name = str(metric_name).strip()
    if not name:
        return False
    base = name[:-5] if name.endswith("_per90") else name
    if base in qc.LINEUP_ABSENT_CANONICAL_STATS and not name.endswith("_total"):
        block_names = {
            str(r.get("metric_name") or "") for r in metrics_rows if r.get("metric_name")
        }
        if name not in block_names:
            return False
    excluded = qc.default_excluded_metrics_for_position(position_group)
    row = next((r for r in comparison_rows if str(r.get("metric_name") or "") == name), None)
    if name in excluded:
        if row and comparison_row_has_signal(row):
            return True
        if block_metric_has_signal(name, metrics_rows):
            return True
        return False
    if row:
        if comparison_row_has_signal(row):
            return True
        if block_metric_has_signal(name, metrics_rows):
            return True
        return False
    return block_metric_has_signal(name, metrics_rows)


def partition_metrics_for_ui(
    available_metrics: list[str],
    comparison_rows: list[dict[str, Any]],
    metrics_rows: list[dict[str, Any]],
    *,
    position_group: str | None = None,
) -> tuple[list[str], list[str]]:
    """(recomendadas, técnicas/poco informativas) preservando orden."""
    recommended: list[str] = []
    technical: list[str] = []
    for m in available_metrics:
        if is_metric_recommended_for_charts(
            m, comparison_rows, metrics_rows, position_group=position_group
        ):
            recommended.append(m)
        else:
            technical.append(m)
    return recommended, technical


def applied_metrics_have_chart_content(
    selected_metrics: list[str],
    metrics_rows: list[dict[str, Any]],
    comparison_rows: list[dict[str, Any]],
) -> bool:
    """True si al menos una métrica aplicada tiene valor o señal en comparativa."""
    for name in selected_metrics:
        if block_metric_has_signal(name, metrics_rows):
            return True
        row = next((r for r in comparison_rows if str(r.get("metric_name") or "") == name), None)
        if row and comparison_row_has_signal(row):
            return True
    return False


def metric_presence_status(
    *,
    rows: int,
    non_null_count: int,
    positive_count: int,
) -> str:
    """
    not_in_db | all_null | all_zero | mostly_zero | low_variance | informative
    """
    if rows <= 0:
        return "not_in_db"
    if non_null_count <= 0:
        return "all_null"
    if positive_count <= 0:
        return "all_zero"
    positive_ratio = positive_count / non_null_count if non_null_count else 0.0
    if positive_ratio < qc.MIN_NONZERO_RATIO:
        return "mostly_zero"
    return "informative"


def classify_metric_quality_row(
    *,
    rows: int,
    non_null_count: int,
    positive_count: int,
    max_value: float | None,
    distinct_values: int,
    positive_ratio: float,
) -> str:
    status = metric_presence_status(
        rows=rows,
        non_null_count=non_null_count,
        positive_count=positive_count,
    )
    if status in ("not_in_db", "all_null", "all_zero", "mostly_zero"):
        return status
    if distinct_values < qc.MIN_UNIQUE_VALUES:
        return "low_variance"
    return "informative"
