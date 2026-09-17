"""Scouting report persistence."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg.types.json import Json

_REPORT_COLS = """
    id, player_id, source_type, source_name, scout_name, report_date, competition,
    match_observed, position_observed, minutes_observed,
    summary, strengths, weaknesses, recommendation, rating, video_url,
    alternative_positions, raw_payload, is_hidden, hidden_at, hidden_by, created_at
"""

_REPORT_LIST_COLS = """
    sr.id, sr.player_id, sr.source_type, sr.source_name, sr.scout_name, sr.report_date,
    sr.competition, sr.match_observed, sr.position_observed, sr.minutes_observed,
    sr.summary, sr.strengths, sr.weaknesses, sr.recommendation, sr.rating,
    sr.video_url, sr.raw_payload, sr.is_hidden, sr.hidden_at, sr.hidden_by, sr.created_at,
    p.full_name AS player_full_name, p.position AS player_position
"""


def create_report(
    conn: Connection,
    player_id: int,
    source_type: str,
    source_name: str | None = None,
    scout_name: str | None = None,
    report_date: date | None = None,
    competition: str | None = None,
    match_observed: str | None = None,
    position_observed: str | None = None,
    minutes_observed: int | None = None,
    summary: str | None = None,
    strengths: str | None = None,
    weaknesses: str | None = None,
    recommendation: str | None = None,
    rating: Decimal | float | None = None,
    video_url: str | None = None,
    alternative_positions: list[str] | None = None,
    raw_payload: dict[str, Any] | None = None,
) -> int:
    alt = alternative_positions if alternative_positions else None
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO scouting_reports (
                player_id, source_type, source_name, scout_name, report_date, competition,
                match_observed, position_observed, minutes_observed,
                summary, strengths, weaknesses, recommendation, rating, video_url,
                alternative_positions, raw_payload
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id
            """,
            (
                player_id,
                source_type,
                source_name,
                scout_name,
                report_date,
                competition,
                match_observed,
                position_observed,
                minutes_observed,
                summary,
                strengths,
                weaknesses,
                recommendation,
                rating,
                video_url,
                alt,
                Json(raw_payload) if raw_payload is not None else None,
            ),
        )
        rid = int(cur.fetchone()[0])
        conn.commit()
        return rid


def get_report_by_id(conn: Connection, report_id: int) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_REPORT_LIST_COLS}
            FROM scouting_reports sr
            JOIN players p ON p.id = sr.player_id
            WHERE sr.id = %s
            """,
            (report_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_reports_by_player(
    conn: Connection,
    player_id: int,
    *,
    include_hidden: bool = True,
) -> list[dict[str, Any]]:
    sql = f"""
        SELECT {_REPORT_COLS}
        FROM scouting_reports
        WHERE player_id = %s
    """
    if not include_hidden:
        sql += " AND COALESCE(is_hidden, FALSE) = FALSE"
    sql += " ORDER BY report_date DESC NULLS LAST, created_at DESC"
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, (player_id,))
        return list(cur.fetchall())


def find_report_by_player_and_date(
    conn: Connection, player_id: int, report_date: date
) -> dict[str, Any] | None:
    """Devuelve un informe del jugador en esa fecha (el más antiguo por id si hubiera duplicados)."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_REPORT_COLS}
            FROM scouting_reports
            WHERE player_id = %s AND report_date = %s
            ORDER BY id ASC
            LIMIT 1
            """,
            (player_id, report_date),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def find_report_by_player_source_and_date(
    conn: Connection,
    player_id: int,
    source_name: str | None,
    report_date: date,
) -> dict[str, Any] | None:
    """Informe canónico: player_id + source_name + report_date (menor id si hay duplicados)."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_REPORT_COLS}
            FROM scouting_reports
            WHERE player_id = %s
              AND report_date = %s
              AND source_name IS NOT DISTINCT FROM %s
            ORDER BY id ASC
            LIMIT 1
            """,
            (player_id, report_date, source_name),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def delete_duplicate_reports_same_key(
    conn: Connection,
    player_id: int,
    source_name: str | None,
    report_date: date,
    keep_report_id: int,
) -> int:
    """Elimina informes duplicados con la misma clave, excepto keep_report_id."""
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM scouting_reports
            WHERE player_id = %s
              AND report_date = %s
              AND source_name IS NOT DISTINCT FROM %s
              AND id <> %s
            """,
            (player_id, report_date, source_name, keep_report_id),
        )
        deleted = cur.rowcount if cur.rowcount is not None else 0
        conn.commit()
        return int(deleted)


def update_report(
    conn: Connection,
    report_id: int,
    *,
    source_type: str | None = None,
    source_name: str | None = None,
    scout_name: str | None = None,
    report_date: date | None = None,
    competition: str | None = None,
    match_observed: str | None = None,
    position_observed: str | None = None,
    minutes_observed: int | None = None,
    summary: str | None = None,
    strengths: str | None = None,
    weaknesses: str | None = None,
    recommendation: str | None = None,
    rating: Decimal | float | None = None,
    video_url: str | None = None,
    alternative_positions: list[str] | None = None,
    raw_payload: dict[str, Any] | None = None,
) -> None:
    alt = alternative_positions if alternative_positions else None
    payload_json = Json(raw_payload) if raw_payload is not None else None
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE scouting_reports SET
                source_type = %s,
                source_name = %s,
                scout_name = %s,
                report_date = %s,
                competition = %s,
                match_observed = %s,
                position_observed = %s,
                minutes_observed = %s,
                summary = %s,
                strengths = %s,
                weaknesses = %s,
                recommendation = %s,
                rating = %s,
                video_url = %s,
                alternative_positions = %s,
                raw_payload = %s
            WHERE id = %s
            """,
            (
                source_type,
                source_name,
                scout_name,
                report_date,
                competition,
                match_observed,
                position_observed,
                minutes_observed,
                summary,
                strengths,
                weaknesses,
                recommendation,
                rating,
                video_url,
                alt,
                payload_json,
                report_id,
            ),
        )
        conn.commit()


def update_report_recommendation(conn: Connection, report_id: int, recommendation: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE scouting_reports
            SET recommendation = %s
            WHERE id = %s
            """,
            (recommendation, report_id),
        )
        conn.commit()


def hide_report(conn: Connection, report_id: int, hidden_by: str | None = None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE scouting_reports
            SET is_hidden = TRUE,
                hidden_at = NOW(),
                hidden_by = %s
            WHERE id = %s
            """,
            (hidden_by, report_id),
        )
        conn.commit()


def restore_report(conn: Connection, report_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE scouting_reports
            SET is_hidden = FALSE,
                hidden_at = NULL,
                hidden_by = NULL
            WHERE id = %s
            """,
            (report_id,),
        )
        conn.commit()


def delete_report_permanently(conn: Connection, report_id: int) -> bool:
    """
    Elimina el informe y dependientes (report_attribute_ratings tiene ON DELETE CASCADE).
    Devuelve True si se eliminó una fila.
    """
    with conn.transaction():
        with conn.cursor() as cur:
            # Defensa explícita por si alguna BD antigua no tuviera CASCADE.
            cur.execute("DELETE FROM report_attribute_ratings WHERE report_id = %s", (report_id,))
            cur.execute("DELETE FROM scouting_reports WHERE id = %s", (report_id,))
            deleted = cur.rowcount if cur.rowcount is not None else 0
    return int(deleted) > 0


def count_reports(conn: Connection, *, include_hidden: bool = False) -> int:
    with conn.cursor() as cur:
        if include_hidden:
            cur.execute("SELECT COUNT(*) FROM scouting_reports")
        else:
            cur.execute(
                """
                SELECT COUNT(*) FROM scouting_reports
                WHERE COALESCE(is_hidden, FALSE) = FALSE
                """
            )
        row = cur.fetchone()
        return int(row[0]) if row else 0


def count_hidden_reports(conn: Connection) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) FROM scouting_reports
            WHERE COALESCE(is_hidden, FALSE) = TRUE
            """
        )
        row = cur.fetchone()
        return int(row[0]) if row else 0


def get_visible_reports(conn: Connection, limit: int = 50) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_REPORT_LIST_COLS}
            FROM scouting_reports sr
            JOIN players p ON p.id = sr.player_id
            WHERE COALESCE(sr.is_hidden, FALSE) = FALSE
            ORDER BY sr.report_date DESC NULLS LAST, sr.created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        return list(cur.fetchall())


def get_hidden_reports(conn: Connection, limit: int = 100) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_REPORT_LIST_COLS}
            FROM scouting_reports sr
            JOIN players p ON p.id = sr.player_id
            WHERE COALESCE(sr.is_hidden, FALSE) = TRUE
            ORDER BY sr.hidden_at DESC NULLS LAST, sr.created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        return list(cur.fetchall())


def get_recent_reports(conn: Connection, limit: int = 50) -> list[dict[str, Any]]:
    """Últimos informes visibles (compatibilidad con el dashboard)."""
    return get_visible_reports(conn, limit=limit)
