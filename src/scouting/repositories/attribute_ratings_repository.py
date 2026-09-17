"""Persistencia de valoraciones por atributo (flexible por informe)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row

from scouting.config.attribute_rating_scale import (
    RATING_MAX,
    RATING_MIN,
    _quantize_rating,
    snap_rating_to_quarters,
    validate_rating,
)


def delete_attribute_ratings_by_report(conn: Connection, report_id: int) -> int:
    """Elimina todas las valoraciones de un informe. Devuelve filas borradas."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM report_attribute_ratings WHERE report_id = %s", (report_id,))
        deleted = cur.rowcount if cur.rowcount is not None else 0
        conn.commit()
        return int(deleted)


def create_attribute_rating(
    conn: Connection,
    report_id: int,
    attribute_group: str,
    attribute_name: str,
    rating: float | Decimal | int,
    max_rating: float | Decimal | int = RATING_MAX,
    notes: str | None = None,
) -> int:
    mx = float(max_rating)
    r = float(rating)
    validate_rating(r, mx)

    r_q = _quantize_rating(snap_rating_to_quarters(r, min_value=RATING_MIN, max_value=min(mx, RATING_MAX)))
    mx_q = _quantize_rating(min(mx, RATING_MAX))

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO report_attribute_ratings (
                report_id, attribute_group, attribute_name, rating, max_rating, notes
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (report_id, attribute_group, attribute_name, r_q, mx_q, notes),
        )
        rid = int(cur.fetchone()[0])
        conn.commit()
        return rid


def get_attribute_ratings_by_report(conn: Connection, report_id: int) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id, report_id, attribute_group, attribute_name, rating, max_rating, notes, created_at
            FROM report_attribute_ratings
            WHERE report_id = %s
            ORDER BY attribute_group ASC, attribute_name ASC
            """,
            (report_id,),
        )
        return list(cur.fetchall())


def get_average_attribute_ratings_by_player(conn: Connection, player_id: int) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                rar.attribute_group,
                rar.attribute_name,
                AVG(rar.rating::numeric) AS avg_rating,
                COUNT(DISTINCT rar.report_id) AS reports_count
            FROM report_attribute_ratings rar
            INNER JOIN scouting_reports sr ON sr.id = rar.report_id
            WHERE sr.player_id = %s
            GROUP BY rar.attribute_group, rar.attribute_name
            ORDER BY rar.attribute_group ASC, rar.attribute_name ASC
            """,
            (player_id,),
        )
        return list(cur.fetchall())


def get_average_attribute_ratings_by_position(
    conn: Connection, position: str, exclude_player_id: int | None = None
) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        if exclude_player_id is None:
            cur.execute(
                """
                SELECT
                    rar.attribute_group,
                    rar.attribute_name,
                    AVG(rar.rating::numeric) AS avg_rating,
                    COUNT(DISTINCT sr.player_id) AS players_count,
                    COUNT(DISTINCT rar.report_id) AS reports_count
                FROM report_attribute_ratings rar
                INNER JOIN scouting_reports sr ON sr.id = rar.report_id
                INNER JOIN players p ON p.id = sr.player_id
                WHERE p.position IS NOT NULL AND p.position = %s
                GROUP BY rar.attribute_group, rar.attribute_name
                ORDER BY rar.attribute_group ASC, rar.attribute_name ASC
                """,
                (position,),
            )
        else:
            cur.execute(
                """
                SELECT
                    rar.attribute_group,
                    rar.attribute_name,
                    AVG(rar.rating::numeric) AS avg_rating,
                    COUNT(DISTINCT sr.player_id) AS players_count,
                    COUNT(DISTINCT rar.report_id) AS reports_count
                FROM report_attribute_ratings rar
                INNER JOIN scouting_reports sr ON sr.id = rar.report_id
                INNER JOIN players p ON p.id = sr.player_id
                WHERE p.position IS NOT NULL AND p.position = %s AND p.id <> %s
                GROUP BY rar.attribute_group, rar.attribute_name
                ORDER BY rar.attribute_group ASC, rar.attribute_name ASC
                """,
                (position, exclude_player_id),
            )
        return list(cur.fetchall())


def get_average_attribute_ratings_by_positions(
    conn: Connection,
    positions: list[str],
    exclude_player_id: int | None = None,
) -> list[dict[str, Any]]:
    """Media por atributo para jugadores con cualquiera de las posiciones de ficha dadas."""
    pos_list = [p.strip() for p in positions if p and str(p).strip()]
    if not pos_list:
        return []
    with conn.cursor(row_factory=dict_row) as cur:
        if exclude_player_id is None:
            cur.execute(
                """
                SELECT
                    rar.attribute_group,
                    rar.attribute_name,
                    AVG(rar.rating::numeric) AS avg_rating,
                    COUNT(DISTINCT sr.player_id) AS players_count,
                    COUNT(DISTINCT rar.report_id) AS reports_count
                FROM report_attribute_ratings rar
                INNER JOIN scouting_reports sr ON sr.id = rar.report_id
                INNER JOIN players p ON p.id = sr.player_id
                WHERE p.position IS NOT NULL AND p.position = ANY(%s)
                GROUP BY rar.attribute_group, rar.attribute_name
                ORDER BY rar.attribute_group ASC, rar.attribute_name ASC
                """,
                (pos_list,),
            )
        else:
            cur.execute(
                """
                SELECT
                    rar.attribute_group,
                    rar.attribute_name,
                    AVG(rar.rating::numeric) AS avg_rating,
                    COUNT(DISTINCT sr.player_id) AS players_count,
                    COUNT(DISTINCT rar.report_id) AS reports_count
                FROM report_attribute_ratings rar
                INNER JOIN scouting_reports sr ON sr.id = rar.report_id
                INNER JOIN players p ON p.id = sr.player_id
                WHERE p.position IS NOT NULL AND p.position = ANY(%s) AND p.id <> %s
                GROUP BY rar.attribute_group, rar.attribute_name
                ORDER BY rar.attribute_group ASC, rar.attribute_name ASC
                """,
                (pos_list, exclude_player_id),
            )
        return list(cur.fetchall())


def audit_template_benchmark_stats(
    conn: Connection,
    positions: list[str],
    exclude_player_id: int | None = None,
) -> list[dict[str, Any]]:
    """
    Auditoría de media plantilla por atributo.
    Solo informes con valoración explícita entran en AVG (sin imputar 0 por ausencia).
    """
    pos_list = [p.strip() for p in positions if p and str(p).strip()]
    if not pos_list:
        return []

    params: list[Any] = [pos_list]
    exclude_sql = ""
    if exclude_player_id is not None:
        exclude_sql = " AND p.id <> %s"
        params.append(exclude_player_id)

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            WITH cohort_players AS (
                SELECT p.id AS player_id
                FROM players p
                WHERE p.position IS NOT NULL AND p.position = ANY(%s){exclude_sql}
            ),
            cohort_reports AS (
                SELECT sr.id AS report_id, sr.player_id
                FROM scouting_reports sr
                INNER JOIN cohort_players cp ON cp.player_id = sr.player_id
            ),
            attr_stats AS (
                SELECT
                    rar.attribute_group,
                    rar.attribute_name,
                    AVG(rar.rating::numeric) AS avg_rating,
                    MIN(rar.rating::numeric) AS min_rating,
                    MAX(rar.rating::numeric) AS max_rating,
                    STDDEV_POP(rar.rating::numeric) AS stddev_rating,
                    COUNT(*)::int AS rating_rows,
                    COUNT(DISTINCT rar.report_id)::int AS reports_count,
                    COUNT(DISTINCT cr.player_id)::int AS players_count,
                    COUNT(*) FILTER (WHERE rar.rating = 0)::int AS zero_ratings
                FROM report_attribute_ratings rar
                INNER JOIN cohort_reports cr ON cr.report_id = rar.report_id
                GROUP BY rar.attribute_group, rar.attribute_name
            ),
            cohort_totals AS (
                SELECT
                    COUNT(DISTINCT report_id)::int AS total_reports,
                    COUNT(DISTINCT player_id)::int AS total_players
                FROM cohort_reports
            )
            SELECT
                a.attribute_group,
                a.attribute_name,
                a.avg_rating,
                a.min_rating,
                a.max_rating,
                a.stddev_rating,
                a.rating_rows,
                a.reports_count,
                a.players_count,
                a.zero_ratings,
                t.total_reports,
                t.total_players
            FROM attr_stats a
            CROSS JOIN cohort_totals t
            ORDER BY a.attribute_group ASC, a.attribute_name ASC
            """,
            tuple(params),
        )
        return list(cur.fetchall())
