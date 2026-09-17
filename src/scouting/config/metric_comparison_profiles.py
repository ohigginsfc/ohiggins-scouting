"""
Perfiles de métricas para comparativas jugador vs media de posición (Sofascore objetivo).

Solo aplica a cohortes por grupo objetivo: Portero, Defensa, Mediocampo, Delantero.
"""

from __future__ import annotations

from typing import Iterable

# Métricas de portero: nunca en comparativas de jugadores de campo
GOALKEEPER_ONLY_METRICS: frozenset[str] = frozenset({
    "saves_per90",
    "savedShotsFromInsideTheBox_per90",
    "savedShotsFromOutsideTheBox_per90",
    "goalsPrevented_per90",
    "goalkeeperValueNormalized_per90",
    "keeperSaveValue_per90",
    "goodHighClaim_per90",
    "punches_per90",
    "penaltySave_per90",
    "penaltyFaced_per90",
    "penalty_save_pct",
    "totalKeeperSweeper_per90",
    "accurateKeeperSweeper_per90",
    "keeper_sweeper_accuracy_pct",
})

OBJECTIVE_COMPARISON_METRICS: dict[str, tuple[str, ...]] = {
    "Portero": (
        "avg_rating",
        "saves_per90",
        "savedShotsFromInsideTheBox_per90",
        "savedShotsFromOutsideTheBox_per90",
        "goalsPrevented_per90",
        "goodHighClaim_per90",
        "punches_per90",
        "penaltySave_per90",
        "penalty_save_pct",
        "totalKeeperSweeper_per90",
        "keeper_sweeper_accuracy_pct",
        "totalPass_per90",
        "pass_accuracy_pct",
    ),
    "Defensa": (
        "avg_rating",
        "totalTackle_per90",
        "wonTackle_per90",
        "tackle_success_pct",
        "challengeLost_per90",
        "interceptionWon_per90",
        "totalClearance_per90",
        "outfielderBlock_per90",
        "duelWon_per90",
        "aerialWon_per90",
        "ballRecovery_per90",
        "totalCross_per90",
        "accurateCross_per90",
        "cross_accuracy_pct",
        "totalPass_per90",
        "pass_accuracy_pct",
    ),
    "Mediocampo": (
        "avg_rating",
        "touches_per90",
        "totalPass_per90",
        "accuratePass_per90",
        "pass_accuracy_pct",
        "keyPass_per90",
        "totalChanceCreated_per90",
        "expectedAssists_per90",
        "ballRecovery_per90",
        "interceptionWon_per90",
        "duelWon_per90",
        "successfulDribble_per90",
        "totalProgressiveBallCarriesDistance_per90",
        "dispossessed_per90",
        "unsuccessfulTouch_per90",
    ),
    "Delantero": (
        "avg_rating",
        "goals_per90",
        "assists_per90",
        "expectedGoals_per90",
        "expectedGoalsOnTarget_per90",
        "expectedAssists_per90",
        "shots_per90",
        "onTargetScoringAttempt_per90",
        "bigChanceMissed_per90",
        "totalChanceCreated_per90",
        "successfulDribble_per90",
        "totalCross_per90",
        "cross_accuracy_pct",
        "wasFouled_per90",
        "aerialWon_per90",
    ),
}

FALLBACK_COMPARISON_METRICS: tuple[str, ...] = (
    "avg_rating",
    "totalPass_per90",
    "duelWon_per90",
    "ballRecovery_per90",
)

MIN_PROFILE_METRICS = 2


def _normalize_available(available_metric_names: Iterable[str]) -> set[str]:
    return {str(m).strip() for m in available_metric_names if m and str(m).strip()}


def _resolve_metric_name(name: str, available: set[str]) -> str | None:
    """Devuelve el nombre de métrica presente en el bloque (alias asistencias / faltas)."""
    if name in available:
        return name
    if name == "assists_per90" and "goalAssist_per90" in available:
        return "goalAssist_per90"
    if name == "foulsCommited_per90" and "foulsCommitted_per90" in available:
        return "foulsCommitted_per90"
    if name == "foulsCommitted_per90" and "foulsCommited_per90" in available:
        return "foulsCommited_per90"
    return None


def _metrics_from_list(
    names: tuple[str, ...] | list[str],
    available: set[str],
    *,
    exclude_goalkeeper: bool,
) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for name in names:
        if exclude_goalkeeper and name in GOALKEEPER_ONLY_METRICS:
            continue
        resolved = _resolve_metric_name(name, available)
        if resolved and resolved not in seen:
            out.append(resolved)
            seen.add(resolved)
    return out


def get_objective_comparison_metrics_for_group(
    position_group: str | None,
    available_metric_names: Iterable[str],
) -> list[str]:
    """
    Métricas comparables para un grupo objetivo Sofascore.

    - Solo métricas del perfil del grupo que existan en el bloque.
    - Excluye métricas de portero si el grupo no es Portero.
    - Si el perfil aporta pocas métricas, completa con fallback genérico (sin GK).
    """
    available = _normalize_available(available_metric_names)
    if not available:
        return []

    group = (position_group or "").strip()
    profile = OBJECTIVE_COMPARISON_METRICS.get(group, ())
    exclude_gk = group != "Portero"

    present = _metrics_from_list(profile, available, exclude_goalkeeper=exclude_gk)

    if len(present) < MIN_PROFILE_METRICS:
        for name in FALLBACK_COMPARISON_METRICS:
            if exclude_gk and name in GOALKEEPER_ONLY_METRICS:
                continue
            resolved = _resolve_metric_name(name, available)
            if resolved and resolved not in present:
                present.append(resolved)

    if group == "Portero":
        allowed = set(OBJECTIVE_COMPARISON_METRICS["Portero"])
        present = [m for m in present if m in allowed or m == "goalAssist_per90"]
    elif exclude_gk:
        present = [m for m in present if m not in GOALKEEPER_ONLY_METRICS]

    return present
