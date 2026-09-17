"""Temporada activa vs histórica Sofascore (aislamiento en UI y queries)."""

from __future__ import annotations

import os

from scouting.config.metric_labels import format_season_label

OHIGGINS_HISTORICAL_COMPETITION = "Primera División Chile"


def get_active_season() -> str:
    return os.environ.get("SOFASCORE_ACTIVE_SEASON", "2025").strip() or "2025"


def get_historical_season() -> str:
    explicit = os.environ.get("SOFASCORE_HISTORICAL_SEASON", "").strip()
    if explicit:
        return explicit
    try:
        return str(int(get_active_season()) - 1)
    except ValueError:
        return "2024"


def season_ui_label(season: str | None) -> str:
    return format_season_label(season)


def is_active_season(season: str | None) -> bool:
    if season is None:
        return False
    return str(season).strip() == get_active_season()


def resolve_query_season(season: str | None, *, allow_historical: bool = False) -> str | None:
    """Por defecto restringe queries a la temporada activa."""
    if allow_historical:
        return season
    if season is not None and str(season).strip():
        return str(season).strip()
    return get_active_season()
