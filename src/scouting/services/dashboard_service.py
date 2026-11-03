"""Aggregated read models for the Streamlit dashboard."""

from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any

from psycopg import Connection

from scouting.repositories import dashboard_repository
from scouting.services import metrics_service, nationality_service, players_service, reports_service


def get_position_counts(conn: Connection) -> list[dict[str, Any]]:
    return dashboard_repository.get_position_counts(conn)


def get_position_counts_by_origin(conn: Connection) -> dict[str, list[dict[str, Any]]]:
    """Conteos por posición para los dos campogramas: `chilean`, `foreign` y `unknown` (sin nacionalidad)."""
    return nationality_service.split_position_counts(dashboard_repository.get_position_counts_by_nationality(conn))


def get_hidden_position_counts(conn: Connection) -> list[dict[str, Any]]:
    """Conteos por posición de los informes ocultos (campograma de informes ocultos); `position=None`: sin posición en la ficha."""
    if os.environ.get("PORTAL_MODE") == "1":
        from scouting.portal.security import require_user

        require_user()
    return dashboard_repository.get_hidden_position_counts(conn)


def split_hidden_position_counts(rows: list[dict[str, Any]], map_positions: Iterable[str]) -> dict[str, Any]:
    """Reparte los conteos de informes ocultos entre lo que se puede ubicar en el campograma y lo que no.

    * `on_map`: posiciones que existen en el campograma.
    * `off_map`: posiciones de la ficha que el campograma no reconoce (la posición es texto libre y puede venir de otra fuente).
    * `no_position`: jugadores sin posición en la ficha, sumados en una sola fila (o `None` si no hay).
    Ningún informe se pierde: lo que no cabe en el campo se cuenta aparte en vez de desaparecer.
    """
    known = set(map_positions)
    on_map: list[dict[str, Any]] = []
    off_map: list[dict[str, Any]] = []
    no_position: dict[str, Any] | None = None
    for row in rows:
        position = row.get("position")
        if not position:
            if no_position is None:
                no_position = {"position": None, "players_count": 0, "reports_count": 0}
            no_position["players_count"] += int(row.get("players_count") or 0)
            no_position["reports_count"] += int(row.get("reports_count") or 0)
        elif position in known:
            on_map.append(row)
        else:
            off_map.append(row)
    return {"on_map": on_map, "off_map": off_map, "no_position": no_position}


def get_position_summary(conn: Connection, position: str, *, origin: str | None = None) -> list[dict[str, Any]]:
    """Jugadores de una posición; con `origin` ('chilean' o 'foreign') solo los de ese grupo de nacionalidad."""
    rows = dashboard_repository.get_position_summary(conn, position)
    if origin is None:
        return rows
    return [r for r in rows if nationality_service.nationality_group(r.get("nationality")) == origin]


def get_dashboard_snapshot(conn: Connection, recent_reports_limit: int = 5) -> dict[str, Any]:
    """Conteos y últimos informes solo de scouting subjetivo visible (scouting_reports)."""
    from scouting.repositories import dashboard_repository, players_repository

    sofascore_n = metrics_service.count_metrics(conn, source_type="sofascore")
    demo_n = metrics_service.count_demo_metrics(conn)
    if sofascore_n > 0:
        metric_count = sofascore_n
        metrics_are_demo = False
        metrics_label = "Métricas objetivas"
    else:
        metric_count = demo_n
        metrics_are_demo = demo_n > 0
        metrics_label = "Métricas demo" if metrics_are_demo else "Métricas objetivas"

    return {
        "player_count": players_repository.count_players_with_subjective_reports(conn),
        "report_count": reports_service.count_reports(conn, include_hidden=False),
        "hidden_report_count": reports_service.count_hidden_reports(conn),
        "scout_count": dashboard_repository.count_distinct_scouts(conn),
        "hybrid_player_count": dashboard_repository.count_players_hybrid(conn),
        "metric_count": metric_count,
        "demo_metric_count": demo_n,
        "sofascore_metric_count": sofascore_n,
        "metrics_are_demo": metrics_are_demo,
        "metrics_label": metrics_label,
        "total_players_in_db": players_service.count_players(conn),
        "recent_reports": reports_service.fetch_recent_reports(conn, limit=recent_reports_limit),
    }
