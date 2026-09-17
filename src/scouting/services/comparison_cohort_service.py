"""Resolución de cohorte para comparación de percentiles entre jugadores."""

from __future__ import annotations

from typing import Any

COHORT_SAME_LEAGUE = "same_league"
COHORT_COMBINED_LEAGUES = "combined_leagues"
COHORT_COMBINED_SEASONS = "combined_seasons"
COHORT_PER_SEASON = "per_season"
COHORT_DIFFERENT_POSITIONS = "different_positions"

COHORT_MODE_COMBINED_SEASONS = "combined_seasons"
COHORT_MODE_PER_SEASON = "per_season"

COHORT_UI_MESSAGES: dict[str, str] = {
    COHORT_SAME_LEAGUE: "Percentiles vs jugadores de la misma posición en la misma liga.",
    COHORT_COMBINED_LEAGUES: (
        "Percentiles calculados sobre cohorte común: misma posición en ambas ligas."
    ),
    COHORT_COMBINED_SEASONS: (
        "Percentiles calculados sobre una cohorte común para comparar evolución."
    ),
    COHORT_PER_SEASON: "Cada temporada se compara contra su propia cohorte.",
    COHORT_DIFFERENT_POSITIONS: "Comparación orientativa: posiciones distintas.",
}


def _norm_str(value: Any) -> str:
    return str(value or "").strip()


def _seasons_label(seasons: list[str]) -> str:
    ordered = sorted({str(s).strip() for s in seasons if str(s).strip()})
    if not ordered:
        return "—"
    if len(ordered) == 1:
        return ordered[0]
    return " y ".join(ordered)


def resolve_player_comparison_cohort(
    *,
    season_a: str | None,
    season_b: str | None,
    competition_a: str | None,
    competition_b: str | None,
    position_group_a: str | None,
    position_group_b: str | None,
) -> dict[str, Any]:
    """
    Define cohorte para comparar dos jugadores (pestaña Comparar jugadores).

    - Misma temporada + misma posición + misma liga → same_league
    - Misma temporada + misma posición + ligas distintas → combined_leagues
    - Temporadas distintas → per_season (cohorte propia por jugador)
    - Posiciones distintas → different_positions (cohorte propia por jugador)
    """
    pos_a = _norm_str(position_group_a)
    pos_b = _norm_str(position_group_b)
    season_a_n = _norm_str(season_a)
    season_b_n = _norm_str(season_b)
    comp_a = _norm_str(competition_a)
    comp_b = _norm_str(competition_b)

    if not pos_a or not pos_b or pos_a != pos_b:
        return {
            "cohort_type": COHORT_DIFFERENT_POSITIONS,
            "position_group": pos_a or pos_b or None,
            "season": None,
            "cohort_seasons": None,
            "peer_competitions": None,
            "competitions": [c for c in [comp_a, comp_b] if c],
            "ui_message": COHORT_UI_MESSAGES[COHORT_DIFFERENT_POSITIONS],
            "use_shared_peer_pool": False,
        }

    if season_a_n != season_b_n:
        return {
            "cohort_type": COHORT_PER_SEASON,
            "position_group": pos_a,
            "season": None,
            "cohort_seasons": None,
            "peer_competitions": None,
            "competitions": [c for c in [comp_a, comp_b] if c],
            "ui_message": COHORT_UI_MESSAGES[COHORT_PER_SEASON],
            "use_shared_peer_pool": False,
        }

    if comp_a and comp_b and comp_a == comp_b:
        return {
            "cohort_type": COHORT_SAME_LEAGUE,
            "position_group": pos_a,
            "season": season_a_n or season_b_n or None,
            "cohort_seasons": [season_a_n] if season_a_n else None,
            "peer_competitions": [comp_a],
            "competitions": [comp_a],
            "ui_message": COHORT_UI_MESSAGES[COHORT_SAME_LEAGUE],
            "use_shared_peer_pool": True,
        }

    leagues = sorted({c for c in [comp_a, comp_b] if c})
    return {
        "cohort_type": COHORT_COMBINED_LEAGUES,
        "position_group": pos_a,
        "season": season_a_n or season_b_n or None,
        "cohort_seasons": [season_a_n] if season_a_n else None,
        "peer_competitions": leagues,
        "competitions": leagues,
        "ui_message": COHORT_UI_MESSAGES[COHORT_COMBINED_LEAGUES],
        "use_shared_peer_pool": True,
    }


def resolve_season_comparison_cohort(
    *,
    season_active: str | None,
    season_historical: str | None,
    competition_active: str | None,
    competition_historical: str | None,
    position_group_active: str | None,
    position_group_historical: str | None,
    cohort_mode: str = COHORT_MODE_COMBINED_SEASONS,
) -> dict[str, Any]:
    """
    Cohorte para Comparar rendimiento por temporada (mismo jugador, dos años).

    Por defecto: combined_seasons (cohorte 2024+2025, misma liga y posición).
    """
    pos_a = _norm_str(position_group_active)
    pos_b = _norm_str(position_group_historical)
    comp_a = _norm_str(competition_active)
    comp_b = _norm_str(competition_historical)
    s_act = _norm_str(season_active)
    s_hist = _norm_str(season_historical)

    if cohort_mode == COHORT_MODE_PER_SEASON:
        return {
            "cohort_type": COHORT_PER_SEASON,
            "position_group": pos_a or pos_b or None,
            "season": None,
            "cohort_seasons": None,
            "peer_competitions": None,
            "competitions": [c for c in [comp_a, comp_b] if c],
            "ui_message": COHORT_UI_MESSAGES[COHORT_PER_SEASON],
            "use_shared_peer_pool": False,
        }

    if not pos_a or not pos_b or pos_a != pos_b:
        return {
            "cohort_type": COHORT_DIFFERENT_POSITIONS,
            "position_group": pos_a or pos_b or None,
            "season": None,
            "cohort_seasons": None,
            "peer_competitions": None,
            "competitions": [c for c in [comp_a, comp_b] if c],
            "ui_message": COHORT_UI_MESSAGES[COHORT_DIFFERENT_POSITIONS],
            "use_shared_peer_pool": False,
        }

    seasons = sorted({s for s in [s_act, s_hist] if s})
    if comp_a and comp_b and comp_a == comp_b:
        leagues = [comp_a]
        league_txt = comp_a
    else:
        leagues = sorted({c for c in [comp_a, comp_b] if c})
        league_txt = " · ".join(leagues) if leagues else "—"

    seasons_txt = _seasons_label(seasons)
    ui_message = (
        f"Percentiles vs jugadores de la misma posición en {league_txt}, "
        f"temporadas {seasons_txt}."
    )
    if len(seasons) >= 2:
        ui_message = (
            f"Percentiles calculados sobre cohorte común {seasons_txt} "
            f"para comparar evolución ({league_txt}, {pos_a})."
        )

    return {
        "cohort_type": COHORT_COMBINED_SEASONS,
        "position_group": pos_a,
        "season": None,
        "cohort_seasons": seasons,
        "peer_competitions": leagues,
        "competitions": leagues,
        "ui_message": ui_message,
        "use_shared_peer_pool": True,
    }


def season_comparison_cohort_context(
    *,
    position_group: str | None,
    season: str | None,
    competition: str | None,
) -> dict[str, Any]:
    """Cohorte de una sola temporada (modo per_season / fallback)."""
    comp = _norm_str(competition)
    s = _norm_str(season)
    return {
        "cohort_type": COHORT_PER_SEASON,
        "position_group": _norm_str(position_group) or None,
        "season": s or None,
        "cohort_seasons": [s] if s else None,
        "peer_competitions": [comp] if comp else None,
        "competitions": [comp] if comp else [],
        "ui_message": COHORT_UI_MESSAGES[COHORT_PER_SEASON],
        "use_shared_peer_pool": False,
    }
