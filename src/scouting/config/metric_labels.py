"""Etiquetas en español para métricas objetivas, temporadas y formateo de valores."""

from __future__ import annotations

import re
from decimal import Decimal

from scouting.config.card_disciplinary_metrics import is_card_minutes_per_metric

METRIC_LABELS_ES: dict[str, str] = {
    "avg_rating": "Valoración media",
    "minutesPlayed": "Minutos jugados",
    "matches_played": "Partidos jugados",
    "market_value": "Valor de mercado",
    "goals_per90": "Goles / 90",
    "goalAssist_per90": "Asistencias / 90",
    "assists_per90": "Asistencias / 90",
    "shots_per90": "Tiros / 90",
    "totalShots_per90": "Tiros / 90",
    "onTargetScoringAttempt_per90": "Tiros a puerta / 90",
    "blockedScoringAttempt_per90": "Tiros bloqueados / 90",
    "shotOffTarget_per90": "Tiros fuera / 90",
    "totalPass_per90": "Pases intentados / 90",
    "accuratePass_per90": "Pases completados / 90",
    "pass_accuracy_pct": "Precisión de pase",
    "totalLongBalls_per90": "Balones largos intentados / 90",
    "accurateLongBalls_per90": "Balones largos completados / 90",
    "accurateLongBalls": "Balones largos completados",
    "totalLongBalls": "Balones largos intentados",
    "accuratePass": "Pases completados",
    "totalPass": "Pases intentados",
    "goalAssist": "Asistencias",
    "saves": "Paradas",
    "long_ball_accuracy_pct": "Precisión en balones largos",
    "accurateOwnHalfPasses_per90": "Pases completados en campo propio / 90",
    "totalOwnHalfPasses_per90": "Pases intentados en campo propio / 90",
    "accurateOppositionHalfPasses_per90": "Pases completados en campo rival / 90",
    "totalOppositionHalfPasses_per90": "Pases intentados en campo rival / 90",
    "keyPass_per90": "Pases clave / 90",
    "totalChanceCreated_per90": "Ocasiones creadas / 90",
    "bigChanceCreated_per90": "Grandes ocasiones creadas / 90",
    "totalTackle_per90": "Entradas / 90",
    "interceptionWon_per90": "Intercepciones / 90",
    "totalClearance_per90": "Despejes / 90",
    "duelWon_per90": "Duelos ganados / 90",
    "duelLost_per90": "Duelos perdidos / 90",
    "duel_win_pct": "Éxito en duelos",
    "aerialWon_per90": "Duelos aéreos ganados / 90",
    "aerialLost_per90": "Duelos aéreos perdidos / 90",
    "ballRecovery_per90": "Recuperaciones / 90",
    "touches_per90": "Toques / 90",
    "possessionLostCtrl_per90": "Pérdidas de posesión / 90",
    "totalDribbles_per90": "Regates intentados / 90",
    "successfulDribble_per90": "Regates exitosos / 90",
    "dribble_success_pct": "Éxito en regate",
    "foulsCommited_per90": "Faltas cometidas / 90",
    "foulsCommitted_per90": "Faltas cometidas / 90",
    "wasFouled_per90": "Faltas recibidas / 90",
    "totalOffside_per90": "Fueras de juego / 90",
    "yellowCard_per90": "Amarillas / 90",
    "redCard_per90": "Rojas / 90",
    "yellowRedCard_per90": "Doble amarilla / 90",
    "yellowCard_total": "Amarillas",
    "redCard_total": "Rojas",
    "yellowRedCard_total": "Dobles amarillas",
    "minutes_per_yellow_card": "Minutos por amarilla",
    "minutes_per_red_card": "Minutos por roja",
    "minutes_per_yellow_red_card": "Minutos por doble amarilla",
    # Expected goals / assists
    "expectedGoals_per90": "xG / 90",
    "expectedAssists_per90": "xA / 90",
    "expectedGoalsOnTarget_per90": "xG a puerta / 90",
    # Ataque / eventos
    "bigChanceMissed_per90": "Grandes ocasiones falladas / 90",
    "hitWoodwork_per90": "Tiros al palo / 90",
    "penaltyWon_per90": "Penaltis provocados / 90",
    "penaltyMiss_per90": "Penaltis fallados / 90",
    "ownGoals_per90": "Goles en propia / 90",
    # Centros / bandas
    "totalCross_per90": "Centros intentados / 90",
    "accurateCross_per90": "Centros precisos / 90",
    "cross_accuracy_pct": "Precisión de centros",
    "crossNotClaimed_per90": "Centros no blocados / 90",
    # Defensa avanzada
    "wonTackle_per90": "Entradas ganadas / 90",
    "tackle_success_pct": "Éxito en entradas",
    "challengeLost_per90": "Duelos perdidos / 90",
    "outfielderBlock_per90": "Bloqueos / 90",
    "clearanceOffLine_per90": "Despejes bajo palos / 90",
    "lastManTackle_per90": "Entradas de último hombre / 90",
    "penaltyConceded_per90": "Penaltis cometidos / 90",
    "errorLeadToAShot_per90": "Errores que acaban en tiro / 90",
    "errorLeadToAGoal_per90": "Errores que acaban en gol / 90",
    # Control / pérdidas
    "dispossessed_per90": "Desposesiones / 90",
    "unsuccessfulTouch_per90": "Controles fallidos / 90",
    # Portero / penaltis
    "penaltySave_per90": "Penaltis parados / 90",
    "penaltyFaced_per90": "Penaltis recibidos / 90",
    "penalty_save_pct": "% penaltis parados",
    "totalKeeperSweeper_per90": "Acciones de líbero / 90",
    "accurateKeeperSweeper_per90": "Acciones de líbero precisas / 90",
    "keeper_sweeper_accuracy_pct": "Precisión como líbero",
    # Conducción / progresión
    "totalProgressiveBallCarriesDistance_per90": "Distancia progresiva en conducción / 90",
    "bestBallCarryProgression_max": "Mejor progresión en conducción",
    # Value models
    "avg_shotValueNormalized": "Valor medio de tiro",
    "saves_per90": "Paradas / 90",
    "goodHighClaim_per90": "Salidas aéreas exitosas / 90",
    "savedShotsFromInsideTheBox_per90": "Paradas dentro del área / 90",
    "savedShotsFromOutsideTheBox_per90": "Paradas fuera del área / 90",
    "goalsPrevented_per90": "Goles evitados / 90",
    "punches_per90": "Despejes de puños / 90",
    "keeperSaveValue_per90": "Valor de paradas / 90",
    "totalBallCarriesDistance_per90": "Distancia conduciendo balón / 90",
    "ballCarriesCount_per90": "Conducciones / 90",
    "totalProgression_per90": "Progresión total / 90",
    "progressiveBallCarriesCount_per90": "Conducciones progresivas / 90",
    "passValueNormalized_per90": "Valor de pase / 90",
    "dribbleValueNormalized_per90": "Valor de regate / 90",
    "defensiveValueNormalized_per90": "Valor defensivo / 90",
    "goalkeeperValueNormalized_per90": "Valor de portero / 90",
}

UNIT_LABELS_ES: dict[str, str] = {
    "per90": "por 90 min",
    "pct": "%",
    "%": "%",
    "rating": "valoración",
    "count": "total",
    "total": "total",
    "eur": "€",
    "minutes": "min",
    "min": "min",
    "value": "valor",
}

# Métricas excluidas de gráficos de barras rápidos (escala distorsionada)
CHART_EXCLUDED_METRICS: frozenset[str] = frozenset({
    "market_value",
    "minutesPlayed",
    "matches_played",
})

CHART_EXCLUDED_UNITS: frozenset[str] = frozenset({"eur"})

METRIC_GROUP_ORDER: tuple[str, ...] = (
    "General",
    "Ataque",
    "Pase / creación",
    "Conducción / regate",
    "Defensa / duelos",
    "Disciplina",
    "Portero",
    "Valor / contexto",
)

# Orden de radares comparativos (percentiles) por tipo de jugador
FIELD_PLAYER_COMPARISON_RADAR_GROUPS: tuple[str, ...] = (
    "General",
    "Ataque",
    "Pase / creación",
    "Conducción / regate",
    "Defensa / duelos",
    "Disciplina",
)

GOALKEEPER_COMPARISON_RADAR_GROUPS: tuple[str, ...] = (
    "General",
    "Pase / creación",
    "Defensa / duelos",
    "Disciplina",
    "Portero",
)

MIN_COMPARISON_RADAR_METRICS = 3

_METRIC_GROUP_BY_NAME: dict[str, str] = {}
for _name in (
    "avg_rating",
    "minutesPlayed",
    "matches_played",
    "market_value",
    "touches_per90",
    "ballRecovery_per90",
):
    _METRIC_GROUP_BY_NAME[_name] = "General"

for _name in (
    "goals_per90",
    "goalAssist_per90",
    "assists_per90",
    "shots_per90",
    "totalShots_per90",
    "onTargetScoringAttempt_per90",
    "blockedScoringAttempt_per90",
    "shotOffTarget_per90",
    "totalOffside_per90",
    "expectedGoals_per90",
    "expectedGoalsOnTarget_per90",
    "bigChanceMissed_per90",
    "hitWoodwork_per90",
    "penaltyWon_per90",
    "penaltyMiss_per90",
    "ownGoals_per90",
    "avg_shotValueNormalized",
):
    _METRIC_GROUP_BY_NAME[_name] = "Ataque"

for _name in (
    "totalPass_per90",
    "accuratePass_per90",
    "pass_accuracy_pct",
    "totalLongBalls_per90",
    "accurateLongBalls_per90",
    "long_ball_accuracy_pct",
    "accurateOwnHalfPasses_per90",
    "totalOwnHalfPasses_per90",
    "accurateOppositionHalfPasses_per90",
    "totalOppositionHalfPasses_per90",
    "keyPass_per90",
    "totalChanceCreated_per90",
    "bigChanceCreated_per90",
    "passValueNormalized_per90",
    "expectedAssists_per90",
    "totalCross_per90",
    "accurateCross_per90",
    "cross_accuracy_pct",
    "crossNotClaimed_per90",
):
    _METRIC_GROUP_BY_NAME[_name] = "Pase / creación"

for _name in (
    "totalDribbles_per90",
    "successfulDribble_per90",
    "dribble_success_pct",
    "totalBallCarriesDistance_per90",
    "ballCarriesCount_per90",
    "totalProgression_per90",
    "progressiveBallCarriesCount_per90",
    "dribbleValueNormalized_per90",
    "possessionLostCtrl_per90",
    "totalProgressiveBallCarriesDistance_per90",
    "bestBallCarryProgression_max",
    "dispossessed_per90",
    "unsuccessfulTouch_per90",
):
    _METRIC_GROUP_BY_NAME[_name] = "Conducción / regate"

for _name in (
    "totalTackle_per90",
    "interceptionWon_per90",
    "totalClearance_per90",
    "duelWon_per90",
    "duelLost_per90",
    "duel_win_pct",
    "aerialWon_per90",
    "aerialLost_per90",
    "defensiveValueNormalized_per90",
    "wonTackle_per90",
    "tackle_success_pct",
    "challengeLost_per90",
    "outfielderBlock_per90",
    "clearanceOffLine_per90",
    "lastManTackle_per90",
    "penaltyConceded_per90",
    "errorLeadToAShot_per90",
    "errorLeadToAGoal_per90",
):
    _METRIC_GROUP_BY_NAME[_name] = "Defensa / duelos"

for _name in (
    "saves_per90",
    "goodHighClaim_per90",
    "savedShotsFromInsideTheBox_per90",
    "savedShotsFromOutsideTheBox_per90",
    "goalsPrevented_per90",
    "punches_per90",
    "keeperSaveValue_per90",
    "goalkeeperValueNormalized_per90",
    "penaltySave_per90",
    "penaltyFaced_per90",
    "penalty_save_pct",
    "totalKeeperSweeper_per90",
    "accurateKeeperSweeper_per90",
    "keeper_sweeper_accuracy_pct",
):
    _METRIC_GROUP_BY_NAME[_name] = "Portero"

for _name in (
    "yellowCard_total",
    "redCard_total",
    "yellowRedCard_total",
    "minutes_per_yellow_card",
    "minutes_per_red_card",
    "minutes_per_yellow_red_card",
    "yellowCard_per90",
    "redCard_per90",
    "yellowRedCard_per90",
    "foulsCommited_per90",
    "wasFouled_per90",
):
    _METRIC_GROUP_BY_NAME[_name] = "Disciplina"

# Palabras para fallback de nombres no catalogados
_WORD_ES: dict[str, str] = {
    "accurate": "completados",
    "total": "intentados",
    "long": "largos",
    "ball": "balón",
    "balls": "balones",
    "pass": "pase",
    "passes": "pases",
    "shot": "tiro",
    "shots": "tiros",
    "scoring": "de gol",
    "attempt": "intento",
    "goal": "gol",
    "goals": "goles",
    "assist": "asistencia",
    "key": "clave",
    "chance": "ocasión",
    "created": "creadas",
    "big": "grandes",
    "tackle": "entrada",
    "interception": "intercepción",
    "won": "ganados",
    "lost": "perdidos",
    "clearance": "despeje",
    "duel": "duelo",
    "duels": "duelos",
    "aerial": "aéreos",
    "recovery": "recuperación",
    "touch": "toque",
    "touches": "toques",
    "possession": "posesión",
    "dribble": "regate",
    "dribbles": "regates",
    "successful": "exitosos",
    "foul": "falta",
    "fouls": "faltas",
    "commited": "cometidas",
    "offside": "fuera de juego",
    "card": "tarjeta",
    "yellow": "amarilla",
    "red": "roja",
    "save": "parada",
    "saves": "paradas",
    "keeper": "portero",
    "high": "alta",
    "claim": "salida",
    "inside": "dentro",
    "outside": "fuera",
    "box": "área",
    "prevented": "evitados",
    "punch": "puño",
    "punches": "puños",
    "carry": "conducción",
    "carries": "conducciones",
    "distance": "distancia",
    "progression": "progresión",
    "progressive": "progresivas",
    "normalized": "normalizado",
    "value": "valor",
    "defensive": "defensivo",
    "opposition": "rival",
    "own": "propio",
    "half": "campo",
    "blocked": "bloqueados",
    "target": "puerta",
    "off": "fuera",
    "rating": "valoración",
    "market": "mercado",
    "minutes": "minutos",
    "played": "jugados",
    "matches": "partidos",
    "match": "partido",
    "metric": "métrica",
    "unknown": "desconocido",
}

_CAMEL_RE = re.compile(r"([a-z0-9])([A-Z])")


def format_season_label(season: str | None) -> str:
    """Preserve the provider's season: calendar years are not split seasons."""
    if season is None:
        return "—"
    s = str(season).strip()
    if not s:
        return "—"
    if "-" in s:
        return s
    return s


def comparison_radar_groups_for_position(position_group: str | None) -> tuple[str, ...]:
    """Grupos de radares comparativos según jugador de campo o portero."""
    if str(position_group or "").strip() == "Portero":
        return GOALKEEPER_COMPARISON_RADAR_GROUPS
    return FIELD_PLAYER_COMPARISON_RADAR_GROUPS


def metrics_in_group(
    metric_names: list[str],
    group_name: str,
) -> list[str]:
    """Métricas de un grupo, ordenadas por catálogo."""
    return sorted(
        [m for m in metric_names if metric_group(m) == group_name],
        key=metric_sort_key,
    )


def metric_group(metric_name: str) -> str:
    key = str(metric_name).strip()
    if key in _METRIC_GROUP_BY_NAME:
        return _METRIC_GROUP_BY_NAME[key]
    low = key.lower()
    if any(x in low for x in ("save", "keeper", "goalkeeper", "punch", "highclaim")):
        return "Portero"
    if any(x in low for x in ("card", "foul", "offside")):
        return "Disciplina"
    if any(x in low for x in ("goal", "shot", "scoring")):
        return "Ataque"
    if any(x in low for x in ("pass", "chance", "keypass", "assist")):
        return "Pase / creación"
    if any(x in low for x in ("dribble", "carry", "progression")):
        return "Conducción / regate"
    if any(x in low for x in ("tackle", "duel", "clearance", "interception", "aerial", "defensive")):
        return "Defensa / duelos"
    if "market" in low or "minutes" in low or "match" in low or "rating" in low:
        return "General"
    if "value" in low:
        return "Valor / contexto"
    return "General"


def metric_sort_key(metric_name: str) -> tuple[int, str]:
    group = metric_group(metric_name)
    try:
        gidx = METRIC_GROUP_ORDER.index(group)
    except ValueError:
        gidx = len(METRIC_GROUP_ORDER)
    return (gidx, metric_label(metric_name).lower())


def _split_camel(name: str) -> list[str]:
    spaced = _CAMEL_RE.sub(r"\1 \2", name)
    return [t for t in re.split(r"[\s_]+", spaced) if t]


def _translate_tokens(tokens: list[str]) -> str:
    parts: list[str] = []
    for t in tokens:
        low = t.lower()
        parts.append(_WORD_ES.get(low, t if t.isupper() and len(t) <= 3 else low))
    text = " ".join(parts)
    return text[:1].upper() + text[1:] if text else ""


def format_metric_name(metric_name: str) -> str:
    """Nombre legible en español si no hay entrada explícita en METRIC_LABELS_ES."""
    key = str(metric_name).strip().rstrip("_")
    if key in METRIC_LABELS_ES:
        return METRIC_LABELS_ES[key]

    suffix = ""
    base = key
    if base.endswith("_per90"):
        base = base[:-5].rstrip("_")
        suffix = " / 90"
    elif base.endswith("_pct"):
        base = base[:-4].rstrip("_")
        suffix = " %"

    tokens = _split_camel(base)
    if not tokens:
        return key.replace("_", " ").strip() + suffix

    return _translate_tokens(tokens) + suffix


def metric_label(metric_name: str) -> str:
    key = str(metric_name).strip()
    return METRIC_LABELS_ES.get(key, format_metric_name(key))


def unit_label(unit: str | None) -> str:
    if unit is None or not str(unit).strip():
        return ""
    u = str(unit).strip().lower()
    return UNIT_LABELS_ES.get(u, u)


def display_unit_for_table(metric_name: str, unit: str | None) -> str:
    """Unidad en columna aparte; vacío si la etiqueta ya incluye / 90 o %."""
    label = metric_label(metric_name)
    if "/ 90" in label or label.rstrip().endswith("%"):
        return ""
    ul = unit_label(unit)
    return ul if ul else "—"


def format_metric_value(
    value: Any,
    unit: str | None = None,
    *,
    metric_name: str | None = None,
) -> str:
    if value is None:
        return "—"
    try:
        if isinstance(value, Decimal):
            num = float(value)
        else:
            num = float(value)
    except (TypeError, ValueError):
        return str(value)
    u = (unit or "").strip().lower()
    name = str(metric_name or "").strip()
    if name.endswith("_per90") and u not in ("per90",):
        u = "per90"
    if name.endswith("_pct") and u not in ("pct", "%"):
        u = "pct"
    if u == "eur" or "market" in str(unit or "").lower():
        if num >= 1_000_000:
            return f"{num / 1_000_000:.2f} M€"
        if num >= 1_000:
            return f"{num / 1_000:.1f} k€"
        return f"{num:,.0f} €".replace(",", ".")
    if u in ("pct", "%"):
        return f"{num:.1f}%"
    if u == "per90":
        return f"{num:.2f}"
    if u == "minutes" or is_card_minutes_per_metric(name):
        if abs(num - round(num)) < 0.05:
            return f"{int(round(num))} min"
        return f"{num:.1f} min"
    if u == "rating":
        return f"{num:.2f}"
    if abs(num) < 1 and abs(num) > 0:
        return f"{num:.3f}".rstrip("0").rstrip(".")
    if abs(num - round(num)) < 0.001 and abs(num) >= 1:
        return str(int(round(num)))
    return f"{num:.2f}"


ZERO_CENTERED_NORMALIZED_SUFFIXES: tuple[str, ...] = (
    "ValueNormalized",
    "ValueNormalized_per90",
    "keeperSaveValue",
    "keeperSaveValue_per90",
    "avg_shotValueNormalized",
)


def is_zero_centered_normalized_metric(metric_name: str) -> bool:
    """Métricas Sofascore centradas en 0 (promedio competición ≈ 0)."""
    name = str(metric_name).strip()
    if name in ZERO_CENTERED_NORMALIZED_SUFFIXES:
        return True
    if name.endswith("ValueNormalized") or name.endswith("ValueNormalized_per90"):
        return True
    if "ValueNormalized" in name or name.endswith("_Normalized"):
        return True
    return name in {"keeperSaveValue", "keeperSaveValue_per90"}


def normalized_metric_context_note(metric_name: str) -> str:
    label = metric_label(metric_name)
    return (
        f"**{label}:** 0 ≈ media de la competición · "
        "positivo = por encima · negativo = por debajo."
    )


def interpret_normalized_metric(
    value: float | None,
    percentile: float | None = None,
) -> str:
    if value is None and percentile is None:
        return "—"
    if percentile is not None:
        p = float(percentile)
        if p >= 80:
            return "Muy por encima de la media"
        if p >= 65:
            return "Por encima de la media"
        if p >= 50:
            return "Ligeramente por encima de la media"
        if p >= 35:
            return "Ligeramente por debajo de la media"
        if p >= 20:
            return "Por debajo de la media"
        return "Muy por debajo de la media"
    if value is None:
        return "—"
    v = float(value)
    if abs(v) < 0.05:
        return "En la media de la competición"
    if v > 0:
        return "Por encima de la media"
    return "Por debajo de la media"


_POSITION_PLURAL: dict[str, str] = {
    "portero": "porteros",
    "lateral": "laterales",
    "central": "centrales",
    "mediocentro": "mediocentros",
    "extremo": "extremos",
    "delantero": "delanteros",
}


def _position_cohort_label(position_group: str | None) -> str:
    if not position_group or not str(position_group).strip():
        return "jugadores de su posición"
    raw = str(position_group).strip()
    low = raw.lower()
    return _POSITION_PLURAL.get(low, raw.lower() + "s")


def interpret_percentile(
    percentile: float | None,
    *,
    position_group: str | None = None,
    metric_name: str | None = None,
) -> str:
    """Interpretación legible de un percentil vs cohorte de posición."""
    if percentile is None:
        return "—"
    if metric_name and is_zero_centered_normalized_metric(metric_name):
        return interpret_normalized_metric(None, float(percentile))

    p = float(percentile)
    pos = _position_cohort_label(position_group)
    top_pct = max(1, int(round(100 - p)))

    if p >= 90:
        return f"Elite — top {top_pct}% de {pos} de la competición"
    if p >= 80:
        return f"Top {top_pct}% de {pos} de la competición"
    if p >= 65:
        return f"Por encima de la media de {pos}"
    if p >= 50:
        return "Ligeramente por encima de la media"
    if p >= 35:
        return "Ligeramente por debajo de la media"
    if p >= 20:
        return f"Por debajo de la media de {pos}"
    return f"Entre el {int(round(p))}% inferior de {pos}"


def is_chart_excluded_metric(metric_name: str, metric_unit: str | None = None) -> bool:
    name = str(metric_name).strip()
    if name in CHART_EXCLUDED_METRICS or "market_value" in name.lower():
        return True
    u = (metric_unit or "").strip().lower()
    if u in CHART_EXCLUDED_UNITS:
        return True
    if name.endswith("_per90") or name.endswith("_pct") or name == "avg_rating":
        return False
    if name in ("minutesPlayed", "matches_played"):
        return True
    return False


def should_show_source_column(rows: list[dict[str, Any]], *, key: str = "source_name") -> bool:
    """False si todas las filas son Sofascore (u homogéneas)."""
    sources = {str(r.get(key) or "").strip() for r in rows if r.get(key)}
    if not sources:
        return False
    if sources == {"Sofascore"}:
        return False
    return len(sources) > 1
