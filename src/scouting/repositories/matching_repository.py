"""Manual matching between scouted players and Sofascore objective data."""

from __future__ import annotations

from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row

from scouting.repositories.players_repository import sql_player_has_subjective_report

SOFASCORE_PROVIDER = "sofascore"
SOFASCORE_SOURCE = "Sofascore"


def _player_has_sofascore_link_sql(player_alias: str = "p") -> str:
    a = player_alias.strip() or "p"
    return f"""(
        EXISTS (
            SELECT 1 FROM player_external_ids pei
            WHERE pei.player_id = {a}.id AND pei.provider = %s
        )
        OR EXISTS (
            SELECT 1 FROM objective_metrics om
            WHERE om.player_id = {a}.id AND om.source_name = %s
        )
    )"""


def get_scouted_players_without_sofascore_match(conn: Connection) -> list[dict[str, Any]]:
    """
    Jugadores con informes subjetivos sin vínculo Sofascore (ni external_id ni métricas).
    """
    link = _player_has_sofascore_link_sql("p")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT
                p.id AS player_id,
                p.full_name,
                p.normalized_name,
                p.current_team,
                p.position,
                p.nationality,
                p.birth_date,
                COUNT(DISTINCT sr.id)::int AS reports_count
            FROM players p
            INNER JOIN scouting_reports sr ON sr.player_id = p.id
            WHERE {sql_player_has_subjective_report("p")}
              AND NOT {link}
            GROUP BY p.id, p.full_name, p.normalized_name, p.current_team,
                     p.position, p.nationality, p.birth_date
            ORDER BY p.full_name ASC
            """,
            (SOFASCORE_PROVIDER, SOFASCORE_SOURCE),
        )
        return list(cur.fetchall())


def get_player_row(conn: Connection, player_id: int) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id AS player_id, full_name, normalized_name, current_team, position,
                   nationality, birth_date
            FROM players
            WHERE id = %s
            """,
            (player_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_sofascore_candidate_pool(conn: Connection, *, exclude_player_id: int) -> list[dict[str, Any]]:
    """
    Jugadores en BD con datos Sofascore (external_id o métricas), excluyendo un id.
    """
    link = _player_has_sofascore_link_sql("p")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT
                p.id AS candidate_player_id,
                p.full_name,
                p.normalized_name,
                p.current_team,
                p.position,
                p.nationality,
                p.birth_date,
                (
                    SELECT pei.external_id
                    FROM player_external_ids pei
                    WHERE pei.player_id = p.id AND pei.provider = %s
                    ORDER BY pei.id ASC
                    LIMIT 1
                ) AS sofascore_external_id
            FROM players p
            WHERE p.id <> %s
              AND {link}
            ORDER BY p.full_name ASC
            """,
            (SOFASCORE_PROVIDER, exclude_player_id, SOFASCORE_PROVIDER, SOFASCORE_SOURCE),
        )
        return list(cur.fetchall())


def get_candidate_metric_extras(conn: Connection, candidate_player_id: int) -> dict[str, Any]:
    """Competiciones, minutos y rating desde objective_metrics del candidato."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT DISTINCT competition
            FROM objective_metrics
            WHERE player_id = %s AND source_name = %s
              AND competition IS NOT NULL AND trim(competition) <> ''
            ORDER BY competition ASC
            """,
            (candidate_player_id, SOFASCORE_SOURCE),
        )
        competitions = [str(r["competition"]) for r in cur.fetchall()]

        cur.execute(
            """
            SELECT metric_name, metric_value
            FROM objective_metrics
            WHERE player_id = %s
              AND metric_name IN ('minutesPlayed', 'avg_rating')
            """,
            (candidate_player_id,),
        )
        minutes_played = None
        avg_rating = None
        for r in cur.fetchall():
            name = str(r["metric_name"])
            val = r["metric_value"]
            if name == "minutesPlayed":
                minutes_played = val
            elif name == "avg_rating":
                avg_rating = val

    return {
        "competitions": competitions,
        "minutes_played": minutes_played,
        "avg_rating": avg_rating,
    }


def count_sofascore_metrics_for_player(conn: Connection, player_id: int) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*)::int FROM objective_metrics
            WHERE player_id = %s AND source_name = %s
            """,
            (player_id, SOFASCORE_SOURCE),
        )
        row = cur.fetchone()
        return int(row[0]) if row else 0


def get_sofascore_external_ids_for_player(conn: Connection, player_id: int) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id, external_id, external_name
            FROM player_external_ids
            WHERE player_id = %s AND provider = %s
            ORDER BY id ASC
            """,
            (player_id, SOFASCORE_PROVIDER),
        )
        return list(cur.fetchall())


def scouted_player_has_sofascore_external(conn: Connection, player_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM player_external_ids
            WHERE player_id = %s AND provider = %s
            LIMIT 1
            """,
            (player_id, SOFASCORE_PROVIDER),
        )
        return cur.fetchone() is not None


def merge_sofascore_candidate_into_scouted_player(
    conn: Connection,
    scouted_player_id: int,
    candidate_player_id: int,
) -> dict[str, int]:
    """
    Mueve métricas Sofascore y external_ids del candidato al jugador scouteado.
    No borra el jugador candidato.
    """
    if scouted_player_id == candidate_player_id:
        raise ValueError("El jugador scouteado y el candidato deben ser distintos.")

    if scouted_player_has_sofascore_external(conn, scouted_player_id):
        raise ValueError(
            "El jugador scouteado ya tiene un external_id Sofascore. "
            "No se puede vincular otro candidato sin revisión manual avanzada."
        )

    metrics_before = count_sofascore_metrics_for_player(conn, candidate_player_id)
    external_before = get_sofascore_external_ids_for_player(conn, candidate_player_id)

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE objective_metrics
                SET player_id = %s
                WHERE player_id = %s AND source_name = %s
                """,
                (scouted_player_id, candidate_player_id, SOFASCORE_SOURCE),
            )
            metrics_moved = cur.rowcount

            cur.execute(
                """
                UPDATE player_external_ids
                SET player_id = %s
                WHERE player_id = %s AND provider = %s
                """,
                (scouted_player_id, candidate_player_id, SOFASCORE_PROVIDER),
            )
            external_moved = cur.rowcount

        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return {
        "metrics_moved": int(metrics_moved),
        "external_ids_moved": int(external_moved),
        "metrics_expected": metrics_before,
        "external_ids_expected": len(external_before),
    }
