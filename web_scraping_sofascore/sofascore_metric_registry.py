"""
Registro ligero de métricas Sofascore (sin dependencias de runtime del scraper).

Contiene los nombres canónicos y aliases usados por la agregación y por scripts de
auditoría. NO importa selenium, webdriver, curl_cffi ni requests, así que puede
cargarse dentro del contenedor app sin esas dependencias.
"""

from __future__ import annotations

from typing import Any

# Canónico → claves API (orden: preferencia). Solo el primer alias presente en statistics cuenta.
STAT_ALIASES: dict[str, list[str]] = {
    "foulsCommited": ["fouls"],
    "successfulDribble": ["wonContest"],
    "totalDribbles": ["totalContest"],
    "totalChanceCreated": ["bigChanceCreated"],
    "yellowCard": ["yellowCard"],
    "redCard": ["redCard"],
    "yellowRedCard": ["yellowRedCard"],
}

# Métricas cuyo raw_key ya coincide con el canónico (alias identidad). Se mantiene la
# estructura para añadir variantes si Sofascore cambiara el nombre del campo.
STAT_ALIASES.update({
    "expectedGoals": ["expectedGoals"],
    "expectedAssists": ["expectedAssists"],
    "expectedGoalsOnTarget": ["expectedGoalsOnTarget"],
    "bigChanceMissed": ["bigChanceMissed"],
    "hitWoodwork": ["hitWoodwork"],
    "penaltyWon": ["penaltyWon"],
    "penaltyMiss": ["penaltyMiss"],
    "ownGoals": ["ownGoals"],
    "totalCross": ["totalCross"],
    "accurateCross": ["accurateCross"],
    "crossNotClaimed": ["crossNotClaimed"],
    "wonTackle": ["wonTackle"],
    "challengeLost": ["challengeLost"],
    "outfielderBlock": ["outfielderBlock"],
    "clearanceOffLine": ["clearanceOffLine"],
    "lastManTackle": ["lastManTackle"],
    "penaltyConceded": ["penaltyConceded"],
    "errorLeadToAShot": ["errorLeadToAShot"],
    "errorLeadToAGoal": ["errorLeadToAGoal"],
    "dispossessed": ["dispossessed"],
    "unsuccessfulTouch": ["unsuccessfulTouch"],
    "penaltySave": ["penaltySave"],
    "penaltyFaced": ["penaltyFaced"],
    "totalKeeperSweeper": ["totalKeeperSweeper"],
    "accurateKeeperSweeper": ["accurateKeeperSweeper"],
    "totalProgressiveBallCarriesDistance": ["totalProgressiveBallCarriesDistance"],
    "shotValueNormalized": ["shotValueNormalized"],
    "bestBallCarryProgression": ["bestBallCarryProgression"],
})

# Métricas que lineups no traen y no deben inferirse desde agregados de equipo.
STATS_ABSENT_IN_LINEUPS: frozenset[str] = frozenset()

# Stats canónicos agregados (ver STAT_ALIASES para las claves API equivalentes).
# Acumulativas → se suman por jugador y el importador genera *_per90.
CUMULATIVE_STATS: list[str] = [
    "totalPass", "accuratePass",
    "accurateOwnHalfPasses", "totalOwnHalfPasses",
    "accurateOppositionHalfPasses", "totalOppositionHalfPasses",
    "totalLongBalls", "accurateLongBalls",
    "goalAssist", "goals",
    "aerialWon", "aerialLost",
    "duelWon", "duelLost",
    "ballRecovery", "minutesPlayed", "touches",
    "possessionLostCtrl",
    "totalShots", "onTargetScoringAttempt",
    "blockedScoringAttempt", "shotOffTarget",
    "totalTackle", "interceptionWon", "totalClearance",
    "yellowCard", "redCard", "yellowRedCard",
    "keyPass", "totalChanceCreated", "bigChanceCreated",
    "totalDribbles", "successfulDribble",
    "foulsCommited", "wasFouled", "totalOffside",
    # GK
    "goodHighClaim", "savedShotsFromInsideTheBox",
    "savedShotsFromOutsideTheBox", "goalsPrevented", "punches", "saves",
    # Ball-carry / distance
    "totalBallCarriesDistance", "ballCarriesCount",
    "totalProgression", "progressiveBallCarriesCount",
    "totalProgressiveBallCarriesDistance",
    # Normalised value scores
    "passValueNormalized", "dribbleValueNormalized",
    "defensiveValueNormalized", "goalkeeperValueNormalized", "keeperSaveValue",
    # Expected goals / assists
    "expectedGoals", "expectedAssists", "expectedGoalsOnTarget",
    # Ataque / eventos
    "bigChanceMissed", "hitWoodwork", "penaltyWon", "penaltyMiss", "ownGoals",
    # Centros / bandas
    "totalCross", "accurateCross", "crossNotClaimed",
    # Defensa avanzada
    "wonTackle", "challengeLost", "outfielderBlock", "clearanceOffLine",
    "lastManTackle", "penaltyConceded", "errorLeadToAShot", "errorLeadToAGoal",
    # Control / pérdidas
    "dispossessed", "unsuccessfulTouch",
    # Portero / penaltis
    "penaltySave", "penaltyFaced", "totalKeeperSweeper", "accurateKeeperSweeper",
]

# Métricas promediadas por acción/modelo (no suma, no per90 → avg_{stat}).
AVERAGE_STATS: list[str] = ["shotValueNormalized"]

# Métricas de las que interesa el máximo del jugador (no suma, no per90 → {stat}_max).
MAX_STATS: list[str] = ["bestBallCarryProgression"]

# Metadata/diagnóstico: nunca tratar como métrica.
NON_METRIC_RAW_KEYS: frozenset[str] = frozenset(
    {"statisticsType", "ratingVersions", "cardMinutes"}
)


def aliases_for_canonical(canonical: str) -> list[str]:
    return STAT_ALIASES.get(canonical, [canonical])


def resolve_stat_from_match_statistics(
    statistics: dict[str, Any],
    canonical: str,
) -> tuple[float | int | None, str | None]:
    """
    Devuelve (valor, clave_raw_usada) si algún alias está presente en statistics.
    Si ningún alias aparece, (None, None) — no confundir con cero real.
    """
    if not statistics:
        return None, None
    for key in aliases_for_canonical(canonical):
        if key not in statistics:
            continue
        val = statistics[key]
        if val is None:
            continue
        return val, key
    return None, None
