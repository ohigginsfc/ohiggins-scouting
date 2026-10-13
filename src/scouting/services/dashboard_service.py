"""Aggregated read models for the Streamlit dashboard."""

from __future__ import annotations

from typing import Any

from psycopg import Connection

from scouting.repositories import dashboard_repository
from scouting.services import metrics_service, nationality_service, players_service, reports_service


def get_position_counts(conn: Connection) -> list[dict[str, Any]]:
    return dashboard_repository.get_position_counts(conn)


def get_position_counts_by_origin(conn: Connection) -> dict[str, list[dict[str, Any]]]:
    """Conteos por posición para los dos campogramas: `chilean`, `foreign` y `unknown` (sin nacionalidad)."""
    return nationality_service.split_position_counts(dashboard_repository.get_position_counts_by_nationality(conn))


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
