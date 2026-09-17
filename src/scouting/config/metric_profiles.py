"""
Perfiles de métricas por posición de ficha para análisis objetivo (Sofascore).

Las posiciones en BD suelen venir del mapeo grueso G/D/M/F; los perfiles de análisis
permiten afinar ranking y radar sin cambiar el importador.
"""

from __future__ import annotations

# --- Listas base (Sofascore) ---

_GOALKEEPER: tuple[str, ...] = (
    "avg_rating",
    "saves_per90",
    "savedShotsFromInsideTheBox_per90",
    "savedShotsFromOutsideTheBox_per90",
    "goalsPrevented_per90",
    "goodHighClaim_per90",
    "totalPass_per90",
    "pass_accuracy_pct",
)

_DEFENSE: tuple[str, ...] = (
    "avg_rating",
    "totalTackle_per90",
    "interceptionWon_per90",
    "totalClearance_per90",
    "duelWon_per90",
    "aerialWon_per90",
    "ballRecovery_per90",
    "totalPass_per90",
    "pass_accuracy_pct",
)

_MIDFIELD: tuple[str, ...] = (
    "avg_rating",
    "totalPass_per90",
    "pass_accuracy_pct",
    "keyPass_per90",
    "totalChanceCreated_per90",
    "ballRecovery_per90",
    "interceptionWon_per90",
    "duelWon_per90",
    "touches_per90",
)

_ATTACKING_MID: tuple[str, ...] = (
    "avg_rating",
    "keyPass_per90",
    "totalChanceCreated_per90",
    "bigChanceCreated_per90",
    "successfulDribble_per90",
    "dribble_success_pct",
    "goals_per90",
    "assists_per90",
    "shots_per90",
)

_WINGER: tuple[str, ...] = (
    "avg_rating",
    "successfulDribble_per90",
    "dribble_success_pct",
    "keyPass_per90",
    "totalChanceCreated_per90",
    "goals_per90",
    "assists_per90",
    "shots_per90",
    "wasFouled_per90",
)

_STRIKER: tuple[str, ...] = (
    "avg_rating",
    "goals_per90",
    "assists_per90",
    "shots_per90",
    "onTargetScoringAttempt_per90",
    "touches_per90",
    "duelWon_per90",
    "aerialWon_per90",
    "wasFouled_per90",
)

# Métricas por posición exacta en ficha (players.position)
METRIC_PROFILES: dict[str, tuple[str, ...]] = {
    "Portero": _GOALKEEPER,
    "Central derecho": _DEFENSE,
    "Central izquierdo": _DEFENSE,
    "Lateral derecho": _DEFENSE,
    "Lateral izquierdo": _DEFENSE,
    "Mediocentro defensivo": _MIDFIELD,
    "Mediocentro": _MIDFIELD,
    "Mediocentro ofensivo": _ATTACKING_MID,
    "Extremo derecho": _WINGER,
    "Extremo izquierdo": _WINGER,
    "Delantero": _STRIKER,
}

# Perfiles de análisis en UI (selector «Perfil de análisis»)
PROFILE_AUTO = "Automático según posición"
PROFILE_CUSTOM = "Personalizado"

ANALYSIS_PROFILE_LABELS: tuple[str, ...] = (
    PROFILE_AUTO,
    "Portero",
    "Defensa",
    "Mediocentro",
    "Mediocentro ofensivo",
    "Extremo",
    "Delantero",
    PROFILE_CUSTOM,
)

# Métricas por perfil de análisis (agrupación táctica)
ANALYSIS_PROFILE_METRICS: dict[str, tuple[str, ...]] = {
    "Portero": _GOALKEEPER,
    "Defensa": _DEFENSE,
    "Mediocentro": _MIDFIELD,
    "Mediocentro ofensivo": _ATTACKING_MID,
    "Extremo": _WINGER,
    "Delantero": _STRIKER,
}

# Posición de ficha → perfil de análisis (modo automático)
POSITION_TO_ANALYSIS_PROFILE: dict[str, str] = {
    "Portero": "Portero",
    "Central derecho": "Defensa",
    "Central izquierdo": "Defensa",
    "Lateral derecho": "Defensa",
    "Lateral izquierdo": "Defensa",
    "Mediocentro defensivo": "Mediocentro",
    "Mediocentro": "Mediocentro",
    "Mediocentro ofensivo": "Mediocentro ofensivo",
    "Extremo derecho": "Extremo",
    "Extremo izquierdo": "Extremo",
    "Delantero": "Delantero",
}

# Métrica principal sugerida para ranking (primera disponible en el dataset)
RANKING_METRIC_PRIORITY: dict[str, tuple[str, ...]] = {
    "Portero": ("avg_rating", "saves_per90"),
    "Defensa": ("totalTackle_per90", "duelWon_per90", "avg_rating"),
    "Mediocentro": ("totalPass_per90", "keyPass_per90", "avg_rating"),
    "Mediocentro ofensivo": ("keyPass_per90", "totalChanceCreated_per90", "avg_rating"),
    "Extremo": ("goals_per90", "successfulDribble_per90", "avg_rating"),
    "Delantero": ("goals_per90", "assists_per90", "avg_rating"),
}

FALLBACK_RANKING_METRIC = "avg_rating"


def filter_present_metrics(metrics: tuple[str, ...] | list[str], selectable: list[str]) -> list[str]:
    """Devuelve métricas del perfil que existen en el dataset (ignora el resto)."""
    sel = set(selectable)
    return [m for m in metrics if m in sel]


def resolve_analysis_profile_key(
    profile_choice: str,
    *,
    position: str | None = None,
) -> str | None:
    """
    Resuelve la clave de ANALYSIS_PROFILE_METRICS.

    Returns None si el usuario eligió Personalizado.
    """
    choice = (profile_choice or "").strip()
    if choice == PROFILE_CUSTOM:
        return None
    if choice == PROFILE_AUTO:
        pos = (position or "").strip()
        if not pos:
            return None
        return POSITION_TO_ANALYSIS_PROFILE.get(pos)
    if choice in ANALYSIS_PROFILE_METRICS:
        return choice
    return None


def metrics_for_position(position: str, selectable: list[str]) -> list[str]:
    """Métricas del perfil de la posición exacta en ficha."""
    key = (position or "").strip()
    tpl = METRIC_PROFILES.get(key, ())
    return filter_present_metrics(tpl, selectable)


def metrics_for_analysis_profile(profile_key: str | None, selectable: list[str]) -> list[str]:
    """Métricas radar/comparador para un perfil de análisis resuelto."""
    if not profile_key:
        return []
    tpl = ANALYSIS_PROFILE_METRICS.get(profile_key, ())
    return filter_present_metrics(tpl, selectable)


def default_ranking_metric_for_profile(
    profile_key: str | None,
    selectable: list[str],
) -> str:
    """Primera métrica de prioridad del perfil presente en datos; si no, fallback genérico."""
    if profile_key:
        for m in RANKING_METRIC_PRIORITY.get(profile_key, ()):
            if m in selectable:
                return m
        # Delantero: goals_per90 es prioridad; otros perfiles ya resueltos arriba
        if profile_key == "Delantero" and "goals_per90" in selectable:
            return "goals_per90"
    # Sin posición / perfil automático sin posición: valoración media (no goles)
    if FALLBACK_RANKING_METRIC in selectable:
        return FALLBACK_RANKING_METRIC
    if "goals_per90" in selectable:
        return "goals_per90"
    per90 = [m for m in selectable if m.endswith("_per90")]
    if per90:
        return per90[0]
    return selectable[0] if selectable else FALLBACK_RANKING_METRIC


def default_radar_for_profile(profile_key: str | None, selectable: list[str]) -> list[str]:
    """Métricas por defecto del radar según perfil."""
    present = metrics_for_analysis_profile(profile_key, selectable)
    if present:
        return present
    return selectable[: min(8, len(selectable))]
