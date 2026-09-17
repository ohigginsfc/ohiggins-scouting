"""
Compatibilidad: nombres canónicos y aliases de statistics Sofascore.

El contenido real vive en sofascore_metric_registry (módulo ligero, sin dependencias
del runtime del scraper). Este módulo se mantiene por compatibilidad de imports.

Validado en checkpoint_raw: fouls, totalContest, wonContest, bigChanceCreated.
Tarjetas individuales: /event/{id}/incidents → yellowCard, redCard, yellowRedCard en statistics.
"""

from __future__ import annotations

from sofascore_metric_registry import (
    AVERAGE_STATS,
    CUMULATIVE_STATS,
    MAX_STATS,
    NON_METRIC_RAW_KEYS,
    STAT_ALIASES,
    STATS_ABSENT_IN_LINEUPS,
    aliases_for_canonical,
    resolve_stat_from_match_statistics,
)

__all__ = [
    "AVERAGE_STATS",
    "CUMULATIVE_STATS",
    "MAX_STATS",
    "NON_METRIC_RAW_KEYS",
    "STAT_ALIASES",
    "STATS_ABSENT_IN_LINEUPS",
    "aliases_for_canonical",
    "resolve_stat_from_match_statistics",
]
