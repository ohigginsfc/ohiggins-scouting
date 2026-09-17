"""Consultas agregadas para el Dashboard (solo scouting subjetivo / scouting_reports)."""

from __future__ import annotations

from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row

from scouting.repositories.players_repository import sql_player_has_subjective_report


def get_position_counts(conn: Connection) -> list[dict[str, Any]]:
    """
    Por posición de ficha: jugadores con informes subjetivos visibles e informes asociados.
    Solo jugadores que aparecen en scouting_reports visibles (excluye imports Sofascore sin informe).
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                p.position,
                COUNT(DISTINCT p.id)::int AS players_count,
                COUNT(DISTINCT sr.id)::int AS reports_count
            FROM players p
            INNER JOIN scouting_reports sr ON sr.player_id = p.id
            WHERE p.position IS NOT NULL AND trim(p.position) <> ''
              AND COALESCE(sr.is_hidden, FALSE) = FALSE
            GROUP BY p.position
            ORDER BY p.position ASC
            """
        )
        return list(cur.fetchall())


def get_position_summary(conn: Connection, position: str, *, season: str | None = None) -> list[dict[str, Any]]:
    """
    Una fila por jugador scouteado con la posición indicada en ficha.
    Orden: rating último informe visible DESC NULLS LAST, fecha último informe DESC.
    """
    from scouting.config.sofascore_seasons import get_active_season

    pos = str(position).strip()
    metrics_season = season if season is not None else get_active_season()
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            WITH latest AS (
                SELECT DISTINCT ON (sr.player_id)
                    sr.player_id,
                    sr.report_date AS latest_report_date,
                    sr.scout_name AS latest_scout_name,
                    sr.rating AS latest_rating,
                    sr.recommendation AS latest_recommendation
                FROM scouting_reports sr
                INNER JOIN players p ON p.id = sr.player_id
                WHERE p.position IS NOT DISTINCT FROM %s
                  AND COALESCE(sr.is_hidden, FALSE) = FALSE
                ORDER BY sr.player_id, sr.report_date DESC NULLS LAST, sr.id DESC
            )
            SELECT
                p.id AS player_id,
                p.full_name,
                p.current_team,
                p.birth_date,
                p.nationality,
                p.position,
                l.latest_report_date,
                l.latest_scout_name,
                l.latest_rating,
                l.latest_recommendation,
                (SELECT COUNT(*)::int FROM scouting_reports sr2
                 WHERE sr2.player_id = p.id
                   AND COALESCE(sr2.is_hidden, FALSE) = FALSE) AS reports_count,
                (SELECT COUNT(*)::int FROM objective_metrics om
                 WHERE om.player_id = p.id
                   AND om.season IS NOT DISTINCT FROM %s) AS metrics_count
            FROM players p
            INNER JOIN latest l ON l.player_id = p.id
            WHERE p.position IS NOT DISTINCT FROM %s
            ORDER BY l.latest_rating DESC NULLS LAST, l.latest_report_date DESC NULLS LAST, p.full_name ASC
            """,
            (pos, metrics_season, pos),
        )
        return list(cur.fetchall())


def count_distinct_scouts(conn: Connection) -> int:
    """Scouts distintos con al menos un informe visible registrado."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(DISTINCT scout_name)::int
            FROM scouting_reports
            WHERE scout_name IS NOT NULL AND trim(scout_name) <> ''
              AND COALESCE(is_hidden, FALSE) = FALSE
            """
        )
        row = cur.fetchone()
        return int(row[0]) if row else 0


def count_players_hybrid(conn: Connection, *, season: str | None = None) -> int:
    """Jugadores con informes subjetivos y métricas objetivas (opcional / badge)."""
    from scouting.config.sofascore_seasons import get_active_season

    metrics_season = season if season is not None else get_active_season()
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT COUNT(*)::int
            FROM players p
            WHERE {sql_player_has_subjective_report("p")}
              AND EXISTS (
                  SELECT 1 FROM objective_metrics om
                  WHERE om.player_id = p.id
                    AND om.season IS NOT DISTINCT FROM %s
              )
            """,
            (metrics_season,),
        )
        row = cur.fetchone()
        return int(row[0]) if row else 0
