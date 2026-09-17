"""Enlace y consulta de jugadores O'Higgins entre temporadas (comparación histórica).

Criterio de comparación:
- Solo estadísticas asociadas a O'Higgins en cada temporada (no el total de
  la competición si el jugador jugó en otro club).
- Relación de identidad: provider Sofascore + external_id (o mismo player_id).
- No se empareja por nombre si existen external_ids distintos.
- Por defecto exige source_type='sofascore' en ambas temporadas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from psycopg import Connection

from scouting.config.sofascore_seasons import (
    OHIGGINS_HISTORICAL_COMPETITION,
    get_active_season,
    get_historical_season,
    season_ui_label,
)
from scouting.repositories import metrics_repository, player_external_ids_repository, players_repository
from scouting.services.objective_origin_policy import (
    SOURCE_TYPE_SOFASCORE,
    can_compare_seasons,
    resolve_scope_origin,
)

SOFASCORE_PROVIDER = "Sofascore"

MatchStatus = Literal[
    "comparable",
    "no_historical_data",
    "not_ohiggins_historical",
    "missing_external_id",
]


def is_ohiggins_team_name(team_name: str | None) -> bool:
    raw = (team_name or "").strip().lower()
    if not raw:
        return False
    compact = raw.replace(" ", "").replace(".", "")
    return "ohiggins" in compact or "o'higgins" in raw


@dataclass(frozen=True)
class SeasonComparisonGate:
    """Estado de la comparación histórica (origen de datos)."""

    allowed: bool
    message: str | None
    origin_active: str
    origin_historical: str
    demo_mode_active: bool
    demo_mode_historical: bool
    warning: str | None = None


@dataclass(frozen=True)
class SeasonComparisonCandidate:
    """Jugador O'Higgins de la temporada activa + estado vs histórica."""

    display_name: str
    position: str
    status: MatchStatus
    link_method: str | None
    player_id_active: int
    player_id_historical: int | None
    external_id: str | None
    team_active: str
    team_historical: str | None
    row_active: dict[str, Any]
    row_historical: dict[str, Any] | None
    status_message: str


# Compatibilidad con código que espera pares comparables
@dataclass(frozen=True)
class SeasonComparisonPair:
    display_name: str
    position: str
    link_method: str
    player_id_active: int
    player_id_historical: int
    external_id: str | None
    row_active: dict[str, Any]
    row_historical: dict[str, Any]


def assess_season_comparison_gate(
    conn: Connection,
    *,
    allow_demo_fallback: bool = False,
    competition: str = OHIGGINS_HISTORICAL_COMPETITION,
) -> SeasonComparisonGate:
    active = get_active_season()
    historical = get_historical_season()
    origin_a = resolve_scope_origin(conn, season=active, competition=competition)
    origin_h = resolve_scope_origin(conn, season=historical, competition=competition)
    allowed, message = can_compare_seasons(
        origin_a, origin_h, allow_demo_fallback=allow_demo_fallback
    )
    warning = None
    if allowed and allow_demo_fallback and (
        origin_a.demo_mode or origin_h.demo_mode
    ):
        warning = (
            "Estás usando datos demo como referencia. "
            "La comparación no es oficial hasta sincronizar Sofascore en ambas temporadas."
        )
    return SeasonComparisonGate(
        allowed=allowed,
        message=message,
        origin_active=origin_a.origin,
        origin_historical=origin_h.origin,
        demo_mode_active=origin_a.demo_mode,
        demo_mode_historical=origin_h.demo_mode,
        warning=warning,
    )


def _summary_rows(
    conn: Connection,
    *,
    season: str,
    competition: str,
    source_type: str | None,
) -> list[dict[str, Any]]:
    return metrics_repository.get_objective_players_summary(
        conn,
        season=season,
        competition=competition,
        prefer_real=source_type is None,
        source_type=source_type,
    )


def _sofascore_external_ids(conn: Connection, player_id: int) -> set[str]:
    rows = player_external_ids_repository.get_external_ids_by_player(conn, player_id)
    return {
        str(r["external_id"]).strip()
        for r in rows
        if str(r.get("provider", "")).strip().lower() == SOFASCORE_PROVIDER.lower()
        and r.get("external_id") is not None
        and str(r["external_id"]).strip()
    }


def _primary_external_id(conn: Connection, player_id: int) -> str | None:
    ids = sorted(_sofascore_external_ids(conn, player_id))
    return ids[0] if ids else None


def list_ohiggins_season_comparison_candidates(
    conn: Connection,
    *,
    allow_demo_fallback: bool = False,
    competition: str = OHIGGINS_HISTORICAL_COMPETITION,
) -> tuple[SeasonComparisonGate, list[SeasonComparisonCandidate]]:
    """
    Lista jugadores O'Higgins de la temporada activa y su vínculo con la histórica.

    Preferencia de origen: Sofascore; demo solo si allow_demo_fallback y no hay real.
    """
    gate = assess_season_comparison_gate(
        conn, allow_demo_fallback=allow_demo_fallback, competition=competition
    )
    active_season = get_active_season()
    historical_season = get_historical_season()

    source_active = (
        SOURCE_TYPE_SOFASCORE
        if gate.origin_active == SOURCE_TYPE_SOFASCORE
        else ("demo" if gate.origin_active == "demo" else None)
    )
    source_hist = (
        SOURCE_TYPE_SOFASCORE
        if gate.origin_historical == SOURCE_TYPE_SOFASCORE
        else ("demo" if gate.origin_historical == "demo" else None)
    )

    # Si el gate bloquea por falta de real y no hay fallback, aún listamos activos
    # con source preferido para explicar el estado.
    if source_active is None and gate.origin_active == "none":
        active_all = _summary_rows(
            conn, season=active_season, competition=competition, source_type=None
        )
    else:
        active_all = _summary_rows(
            conn,
            season=active_season,
            competition=competition,
            source_type=source_active,
        )
    if source_hist is None and gate.origin_historical == "none":
        hist_all = []
    else:
        hist_all = _summary_rows(
            conn,
            season=historical_season,
            competition=competition,
            source_type=source_hist,
        )

    active_rows = [r for r in active_all if is_ohiggins_team_name(r.get("objective_team"))]
    hist_ohiggins = {
        int(r["player_id"]): r
        for r in hist_all
        if is_ohiggins_team_name(r.get("objective_team"))
    }
    hist_any_by_pid = {int(r["player_id"]): r for r in hist_all}

    ext_to_hist_oh: dict[str, int] = {}
    ext_to_hist_any: dict[str, int] = {}
    for hr in hist_all:
        hp = int(hr["player_id"])
        for ext in _sofascore_external_ids(conn, hp):
            ext_to_hist_any.setdefault(ext, hp)
            if is_ohiggins_team_name(hr.get("objective_team")):
                ext_to_hist_oh.setdefault(ext, hp)

    candidates: list[SeasonComparisonCandidate] = []
    for ar in active_rows:
        pid_a = int(ar["player_id"])
        player = players_repository.get_player_by_id(conn, pid_a)
        name = str((player or {}).get("full_name") or ar.get("player_name") or "—")
        position = str(
            (player or {}).get("position")
            or ar.get("objective_position_group")
            or "—"
        )
        team_a = str(ar.get("objective_team") or "—")
        ext_ids = _sofascore_external_ids(conn, pid_a)
        primary_ext = next(iter(sorted(ext_ids)), None)

        hist_row: dict[str, Any] | None = None
        method: str | None = None
        status: MatchStatus
        status_message: str
        pid_h: int | None = None
        team_h: str | None = None

        # 1) Mismo player_id en O'Higgins histórica
        if pid_a in hist_ohiggins:
            hist_row = hist_ohiggins[pid_a]
            method = "same_player_id"
            pid_h = pid_a
            team_h = str(hist_row.get("objective_team") or "—")
            status = "comparable"
            status_message = "Comparable en ambas temporadas (O'Higgins)."
        else:
            # 2) External ID → O'Higgins histórica
            matched_oh = None
            for ext in ext_ids:
                hp = ext_to_hist_oh.get(ext)
                if hp is not None:
                    matched_oh = hp
                    primary_ext = ext
                    break
            if matched_oh is not None:
                hist_row = hist_ohiggins[matched_oh]
                method = "external_id"
                pid_h = matched_oh
                team_h = str(hist_row.get("objective_team") or "—")
                status = "comparable"
                status_message = "Comparable vía Sofascore external_id (O'Higgins)."
            else:
                # 3) External ID en otra plantilla de la misma competición
                matched_any = None
                for ext in ext_ids:
                    hp = ext_to_hist_any.get(ext)
                    if hp is not None:
                        matched_any = hp
                        primary_ext = ext
                        break
                if matched_any is not None:
                    other = hist_any_by_pid.get(matched_any) or {}
                    team_h = str(other.get("objective_team") or "—")
                    pid_h = matched_any
                    status = "not_ohiggins_historical"
                    status_message = (
                        f"No pertenecía a O'Higgins en {season_ui_label(historical_season)} "
                        f"(equipo: {team_h})."
                    )
                elif not ext_ids and pid_a not in hist_any_by_pid:
                    status = "missing_external_id"
                    status_message = (
                        "Sin identificador Sofascore fiable; no se empareja por nombre."
                    )
                else:
                    status = "no_historical_data"
                    status_message = (
                        f"Sin datos en la temporada anterior ({season_ui_label(historical_season)})."
                    )

        candidates.append(
            SeasonComparisonCandidate(
                display_name=name,
                position=position,
                status=status,
                link_method=method,
                player_id_active=pid_a,
                player_id_historical=pid_h,
                external_id=primary_ext,
                team_active=team_a,
                team_historical=team_h,
                row_active=dict(ar),
                row_historical=dict(hist_row) if hist_row else None,
                status_message=status_message,
            )
        )

    candidates.sort(key=lambda c: (0 if c.status == "comparable" else 1, c.display_name.lower()))
    return gate, candidates


def find_ohiggins_season_comparison_pairs(
    conn: Connection,
    *,
    allow_demo_fallback: bool = False,
) -> list[SeasonComparisonPair]:
    """Solo pares comparables (O'Higgins en ambas temporadas, ID fiable)."""
    gate, candidates = list_ohiggins_season_comparison_candidates(
        conn, allow_demo_fallback=allow_demo_fallback
    )
    if not gate.allowed:
        return []
    pairs: list[SeasonComparisonPair] = []
    for c in candidates:
        if c.status != "comparable" or c.row_historical is None or c.player_id_historical is None:
            continue
        pairs.append(
            SeasonComparisonPair(
                display_name=c.display_name,
                position=c.position,
                link_method=c.link_method or "external_id",
                player_id_active=c.player_id_active,
                player_id_historical=c.player_id_historical,
                external_id=c.external_id,
                row_active=c.row_active,
                row_historical=c.row_historical,
            )
        )
    return pairs


def season_pair_selector_label(pair: SeasonComparisonPair) -> str:
    active_l = season_ui_label(get_active_season())
    hist_l = season_ui_label(get_historical_season())
    return f"{pair.display_name} · {pair.position} · {active_l} vs {hist_l}"


def season_candidate_selector_label(candidate: SeasonComparisonCandidate) -> str:
    suffix = {
        "comparable": "✓ comparable",
        "no_historical_data": "sin datos anteriores",
        "not_ohiggins_historical": "otro club en histórica",
        "missing_external_id": "sin ID externo",
    }.get(candidate.status, candidate.status)
    return f"{candidate.display_name} · {candidate.position} · {suffix}"
