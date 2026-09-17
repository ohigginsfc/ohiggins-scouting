"""Métricas objetivas excluidas por defecto en gráficos (todo-cero o poco informativas)."""

from __future__ import annotations

from scouting.config.metric_comparison_profiles import GOALKEEPER_ONLY_METRICS

from scouting.config.metric_comparison_profiles import GOALKEEPER_ONLY_METRICS
from scouting.config.card_disciplinary_metrics import CARD_PER90_METRICS

# Eventos raros: se conservan en BD y en el expander técnico, pero no se preseleccionan.
RARE_EVENT_TECHNICAL_METRICS: frozenset[str] = frozenset({
    "ownGoals_per90",
    "errorLeadToAGoal_per90",
    "errorLeadToAShot_per90",
    "penaltyMiss_per90",
    "penaltyConceded_per90",
    "hitWoodwork_per90",
    "clearanceOffLine_per90",
    "lastManTackle_per90",
})

# Tarjetas /90: se conservan en BD pero no se preseleccionan (poco interpretables).
DEFAULT_EXCLUDED_OBJECTIVE_METRICS: frozenset[str] = (
    CARD_PER90_METRICS | RARE_EVENT_TECHNICAL_METRICS
)

# Solo existen tras scrape con /incidents (checkpoints antiguos no las tienen).
LINEUP_ABSENT_CANONICAL_STATS: frozenset[str] = frozenset(
    {"yellowCard", "redCard", "yellowRedCard"}
)

# Subconjunto de portero: no mostrar en jugadores de campo por defecto.
DEFAULT_EXCLUDED_GOALKEEPER_METRICS: frozenset[str] = frozenset(
    m
    for m in GOALKEEPER_ONLY_METRICS
    if m
    in {
        "goalkeeperValueNormalized_per90",
        "keeperSaveValue_per90",
        "saves_per90",
        "savedShotsFromInsideTheBox_per90",
        "savedShotsFromOutsideTheBox_per90",
        "goalsPrevented_per90",
        "goodHighClaim_per90",
        "punches_per90",
    }
)

MIN_NONZERO_RATIO = 0.02
MIN_UNIQUE_VALUES = 2
COMPARISON_EPSILON = 0.0005
MIN_COHORT_PLAYERS = 2


def default_excluded_metrics_for_position(position_group: str | None) -> frozenset[str]:
    """Métricas que no se preseleccionan (el usuario puede activarlas en técnicas)."""
    excluded = set(DEFAULT_EXCLUDED_OBJECTIVE_METRICS)
    if position_group and str(position_group).strip() != "Portero":
        excluded |= set(DEFAULT_EXCLUDED_GOALKEEPER_METRICS)
    return frozenset(excluded)
