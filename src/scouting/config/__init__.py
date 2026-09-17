"""
Paquete de configuración scouting.

- database: conexión PostgreSQL (variables de entorno)
- metric_profiles: perfiles de métricas por posición para Datos objetivos
"""

from __future__ import annotations

from . import metric_profiles
from .database import get_db_connection_params
from .metric_profiles import (
    ANALYSIS_PROFILE_LABELS,
    ANALYSIS_PROFILE_METRICS,
    METRIC_PROFILES,
    POSITION_TO_ANALYSIS_PROFILE,
    PROFILE_AUTO,
    PROFILE_CUSTOM,
    RANKING_METRIC_PRIORITY,
    default_radar_for_profile,
    default_ranking_metric_for_profile,
    filter_present_metrics,
    metrics_for_analysis_profile,
    metrics_for_position,
    resolve_analysis_profile_key,
)

__all__ = [
    "ANALYSIS_PROFILE_LABELS",
    "ANALYSIS_PROFILE_METRICS",
    "METRIC_PROFILES",
    "POSITION_TO_ANALYSIS_PROFILE",
    "PROFILE_AUTO",
    "PROFILE_CUSTOM",
    "RANKING_METRIC_PRIORITY",
    "default_radar_for_profile",
    "default_ranking_metric_for_profile",
    "filter_present_metrics",
    "get_db_connection_params",
    "metric_profiles",
    "metrics_for_analysis_profile",
    "metrics_for_position",
    "resolve_analysis_profile_key",
]
