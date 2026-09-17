"""Objective metrics persistence."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg.types.json import Json

from scouting.config.metric_direction import (
    COHORT_RADAR_SCALE_P_HIGH,
    COHORT_RADAR_SCALE_P_LOW,
    linear_percentile_value,
    performance_percentile_from_raw,
)


PLAYER_TYPE_ALL = "all"
PLAYER_TYPE_HYBRID = "hybrid"
PLAYER_TYPE_OBJECTIVE_ONLY = "objective_only"
PLAYER_TYPE_WITH_REPORT = "with_report"


def count_metrics(
    conn: Connection,
    *,
    season: str | None = None,
    source_type: str | None = None,
) -> int:
    clauses: list[str] = []
    params: list[Any] = []
    if season is not None and str(season).strip():
        clauses.append("season IS NOT DISTINCT FROM %s")
        params.append(str(season).strip())
    if source_type is not None and str(source_type).strip():
        st = str(source_type).strip()
        if st == "sofascore":
            clauses.append(
                "(source_type = 'sofascore' OR (source_type IS NULL AND import_batch_id IS NOT NULL))"
            )
        elif st == "demo":
            clauses.append(
                """(
                    source_type = 'demo'
                    OR source_name IN ('StatsDemo', 'examples_generated', 'DEMO')
                    OR (
                        source_type IS NULL
                        AND import_batch_id IS NULL
                        AND source_name = 'Sofascore'
                    )
                )"""
            )
        else:
            clauses.append("source_type IS NOT DISTINCT FROM %s")
            params.append(st)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM objective_metrics {where}", tuple(params))
        row = cur.fetchone()
        return int(row[0]) if row else 0


def create_metric(
    conn: Connection,
    player_id: int,
    source_name: str,
    metric_name: str,
    season: str | None = None,
    competition: str | None = None,
    metric_value: Decimal | float | None = None,
    metric_unit: str | None = None,
    raw_payload: dict[str, Any] | None = None,
    import_batch_id: UUID | str | None = None,
    source_type: str | None = None,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO objective_metrics (
                player_id, source_name, season, competition, metric_name,
                metric_value, metric_unit, raw_payload, import_batch_id, source_type
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                player_id,
                source_name,
                season,
                competition,
                metric_name,
                metric_value,
                metric_unit,
                Json(raw_payload) if raw_payload is not None else None,
                str(import_batch_id) if import_batch_id is not None else None,
                source_type,
            ),
        )
        mid = int(cur.fetchone()[0])
        conn.commit()
        return mid


def create_metrics_batch(
    conn: Connection,
    rows: list[dict[str, Any]],
) -> int:
    """Inserta varias métricas en una sola transacción. Cada dict: player_id, source_name, metric_name, ..."""
    if not rows:
        return 0
    sql = """
        INSERT INTO objective_metrics (
            player_id, source_name, season, competition, metric_name,
            metric_value, metric_unit, raw_payload, import_batch_id, source_type
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = []
    for r in rows:
        params.append(
            (
                r["player_id"],
                r["source_name"],
                r.get("season"),
                r.get("competition"),
                r["metric_name"],
                r.get("metric_value"),
                r.get("metric_unit"),
                Json(r["raw_payload"]) if r.get("raw_payload") is not None else None,
                str(r["import_batch_id"]) if r.get("import_batch_id") is not None else None,
                r.get("source_type"),
            )
        )
    with conn.cursor() as cur:
        cur.executemany(sql, params)
    conn.commit()
    return len(params)


def delete_metrics_by_batch_ids(conn: Connection, batch_ids: list[UUID]) -> int:
    if not batch_ids:
        return 0
    ids = [str(b) for b in batch_ids]
    placeholders = ",".join(["%s"] * len(ids))
    with conn.cursor() as cur:
        cur.execute(
            f"DELETE FROM objective_metrics WHERE import_batch_id IN ({placeholders})",
            ids,
        )
        n = cur.rowcount
    conn.commit()
    return int(n)


def delete_metrics_by_source_scope(
    conn: Connection,
    *,
    source_name: str,
    season: str,
    competition: str,
) -> int:
    """
    Elimina métricas Sofascore reales del ámbito.

    Nunca borra source_type='demo' (seed de demostración).
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM objective_metrics
            WHERE source_name = %s
              AND season IS NOT DISTINCT FROM %s
              AND competition IS NOT DISTINCT FROM %s
              AND (
                source_type = 'sofascore'
                OR (source_type IS NULL AND import_batch_id IS NOT NULL)
              )
            """,
            (source_name, season, competition),
        )
        n = cur.rowcount
    conn.commit()
    return int(n)


def count_metrics_by_player(
    conn: Connection,
    player_id: int,
    *,
    season: str | None = None,
) -> int:
    with conn.cursor() as cur:
        if season is not None and str(season).strip():
            cur.execute(
                """
                SELECT COUNT(*)::int FROM objective_metrics
                WHERE player_id = %s AND season IS NOT DISTINCT FROM %s
                """,
                (player_id, str(season).strip()),
            )
        else:
            cur.execute(
                "SELECT COUNT(*)::int FROM objective_metrics WHERE player_id = %s",
                (player_id,),
            )
        row = cur.fetchone()
        return int(row[0]) if row else 0


def get_sources_by_player(conn: Connection, player_id: int) -> list[str]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT DISTINCT source_name
            FROM objective_metrics
            WHERE player_id = %s AND source_name IS NOT NULL AND trim(source_name) <> ''
            ORDER BY source_name ASC
            """,
            (player_id,),
        )
        return [str(r["source_name"]) for r in cur.fetchall()]


def get_metrics_summary_by_player(conn: Connection, player_id: int) -> list[dict[str, Any]]:
    """Resumen por temporada, competición y fuente."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                season,
                competition,
                source_name,
                COUNT(*)::int AS metrics_count,
                COUNT(DISTINCT metric_name)::int AS distinct_metrics
            FROM objective_metrics
            WHERE player_id = %s
            GROUP BY season, competition, source_name
            ORDER BY season NULLS LAST, competition NULLS LAST, source_name ASC
            """,
            (player_id,),
        )
        return list(cur.fetchall())


def get_metrics_by_player(
    conn: Connection,
    player_id: int,
    *,
    season: str | None = None,
) -> list[dict[str, Any]]:
    clauses = ["player_id = %s"]
    params: list[Any] = [player_id]
    if season is not None and str(season).strip():
        clauses.append("season IS NOT DISTINCT FROM %s")
        params.append(str(season).strip())
    where_sql = " AND ".join(clauses)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT id, player_id, source_name, season, competition, metric_name, metric_value, metric_unit,
                   raw_payload, created_at
            FROM objective_metrics
            WHERE {where_sql}
            ORDER BY season NULLS LAST, competition NULLS LAST, metric_name ASC
            """,
            params,
        )
        return list(cur.fetchall())


def get_all_metrics_with_players(
    conn: Connection,
    *,
    source_name: str | None = None,
    season: str | None = None,
    competition: str | None = None,
    position: str | None = None,
    current_team: str | None = None,
    metric_name: str | None = None,
    player_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    """
    objective_metrics JOIN players con filtros opcionales (todas las filas que cumplan).
    """
    clauses: list[str] = ["1=1"]
    params: list[Any] = []

    if source_name is not None and str(source_name).strip():
        clauses.append("(om.source_name IS NOT DISTINCT FROM %s)")
        params.append(str(source_name).strip())
    if season is not None and str(season).strip():
        clauses.append("(om.season IS NOT DISTINCT FROM %s)")
        params.append(str(season).strip())
    if competition is not None and str(competition).strip():
        clauses.append("(om.competition IS NOT DISTINCT FROM %s)")
        params.append(str(competition).strip())
    if position is not None and str(position).strip():
        clauses.append("(p.position IS NOT DISTINCT FROM %s)")
        params.append(str(position).strip())
    if current_team is not None and str(current_team).strip():
        clauses.append(f"({_OBJECTIVE_TEAM_ROW}) IS NOT DISTINCT FROM %s")
        params.append(str(current_team).strip())
    if metric_name is not None and str(metric_name).strip():
        clauses.append("om.metric_name = %s")
        params.append(str(metric_name).strip())
    if player_ids:
        clauses.append("om.player_id = ANY(%s)")
        params.append(player_ids)

    where_sql = " AND ".join(clauses)

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT
                om.id AS metric_row_id,
                om.player_id,
                p.full_name AS player_name,
                p.position,
                {_OBJECTIVE_TEAM_ROW} AS objective_team,
                om.season,
                om.competition,
                om.source_name,
                om.metric_name,
                om.metric_value,
                om.metric_unit,
                om.created_at
            FROM objective_metrics om
            INNER JOIN players p ON p.id = om.player_id
            WHERE {where_sql}
            ORDER BY p.full_name ASC, om.season NULLS LAST, om.competition NULLS LAST, om.metric_name ASC
            """,
            params,
        )
        return list(cur.fetchall())


def get_metrics_long_aggregated(
    conn: Connection,
    *,
    source_name: str | None = None,
    season: str | None = None,
    competition: str | None = None,
    position: str | None = None,
    current_team: str | None = None,
    nationality: str | None = None,
    preferred_foot: str | None = None,
    player_type: str = PLAYER_TYPE_ALL,
    age_min: int | None = None,
    age_max: int | None = None,
    player_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    """
    Métricas agregadas por jugador + temporada + competición + metric_name.
    Solo jugadores con filas en objective_metrics (INNER JOIN).
    """
    clauses: list[str] = ["om.metric_value IS NOT NULL"]
    params: list[Any] = []

    if source_name is not None and str(source_name).strip():
        clauses.append("(om.source_name IS NOT DISTINCT FROM %s)")
        params.append(str(source_name).strip())
    if season is not None and str(season).strip():
        clauses.append("(om.season IS NOT DISTINCT FROM %s)")
        params.append(str(season).strip())
    if competition is not None and str(competition).strip():
        clauses.append("(om.competition IS NOT DISTINCT FROM %s)")
        params.append(str(competition).strip())
    if position is not None and str(position).strip():
        clauses.append("(p.position IS NOT DISTINCT FROM %s)")
        params.append(str(position).strip())
    if current_team is not None and str(current_team).strip():
        clauses.append(
            f"({_OBJECTIVE_TEAM_ROW}) IS NOT DISTINCT FROM %s"
        )
        params.append(str(current_team).strip())
    if nationality is not None and str(nationality).strip():
        clauses.append("(p.nationality IS NOT DISTINCT FROM %s)")
        params.append(str(nationality).strip())
    if preferred_foot is not None and str(preferred_foot).strip():
        clauses.append("(p.preferred_foot IS NOT DISTINCT FROM %s)")
        params.append(str(preferred_foot).strip())
    if player_type == PLAYER_TYPE_HYBRID or player_type == PLAYER_TYPE_WITH_REPORT:
        clauses.append("COALESCE(sr_summary.reports_count, 0) > 0")
    elif player_type == PLAYER_TYPE_OBJECTIVE_ONLY:
        clauses.append("COALESCE(sr_summary.reports_count, 0) = 0")
    if age_min is not None:
        clauses.append(
            "p.birth_date IS NOT NULL AND EXTRACT(YEAR FROM age(CURRENT_DATE, p.birth_date)) >= %s"
        )
        params.append(int(age_min))
    if age_max is not None:
        clauses.append(
            "p.birth_date IS NOT NULL AND EXTRACT(YEAR FROM age(CURRENT_DATE, p.birth_date)) <= %s"
        )
        params.append(int(age_max))
    if player_ids:
        clauses.append("om.player_id = ANY(%s)")
        params.append(player_ids)

    where_sql = " AND ".join(clauses)

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT
                om.player_id,
                p.full_name AS player_name,
                p.position,
                MAX({_OBJECTIVE_TEAM_ROW}) AS objective_team,
                p.nationality,
                p.preferred_foot,
                p.birth_date,
                om.season,
                om.competition,
                MAX(om.source_name)::text AS source_name,
                om.metric_name,
                AVG(om.metric_value::numeric) AS metric_value,
                MAX(om.metric_unit)::text AS metric_unit,
                MAX(COALESCE(sr_summary.reports_count, 0))::int AS reports_count,
                (MAX(COALESCE(sr_summary.reports_count, 0)) > 0) AS has_subjective_report
            FROM objective_metrics om
            INNER JOIN players p ON p.id = om.player_id
            LEFT JOIN (
                SELECT player_id, COUNT(*)::int AS reports_count
                FROM scouting_reports
                GROUP BY player_id
            ) sr_summary ON sr_summary.player_id = p.id
            WHERE {where_sql}
            GROUP BY om.player_id, p.id, p.full_name, p.position,
                     p.nationality, p.preferred_foot, p.birth_date,
                     om.season, om.competition, om.metric_name
            ORDER BY p.full_name ASC, om.season NULLS LAST, om.competition NULLS LAST,
                     om.metric_name ASC
            """,
            params,
        )
        return list(cur.fetchall())


def get_available_metric_filters(conn: Connection) -> dict[str, list[Any]]:
    """Valores distintos para poblar filtros en la UI."""
    out: dict[str, list[Any]] = {
        "source_names": [],
        "seasons": [],
        "competitions": [],
        "positions": [],
        "teams": [],
        "metric_names": [],
        "players": [],
    }
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT DISTINCT source_name FROM objective_metrics
            WHERE source_name IS NOT NULL AND trim(source_name) <> ''
            ORDER BY source_name ASC
            """
        )
        out["source_names"] = [r["source_name"] for r in cur.fetchall()]

        cur.execute(
            """
            SELECT DISTINCT season FROM objective_metrics WHERE season IS NOT NULL AND trim(season) <> ''
            ORDER BY season ASC
            """
        )
        out["seasons"] = [r["season"] for r in cur.fetchall()]

        cur.execute(
            """
            SELECT DISTINCT competition FROM objective_metrics
            WHERE competition IS NOT NULL AND trim(competition) <> ''
            ORDER BY competition ASC
            """
        )
        out["competitions"] = [r["competition"] for r in cur.fetchall()]

        cur.execute(
            """
            SELECT DISTINCT p.position
            FROM objective_metrics om
            INNER JOIN players p ON p.id = om.player_id
            WHERE p.position IS NOT NULL AND trim(p.position) <> ''
            ORDER BY p.position ASC
            """
        )
        out["positions"] = [r["position"] for r in cur.fetchall()]

        cur.execute(
            f"""
            SELECT DISTINCT team_name
            FROM (
                SELECT {_OBJECTIVE_TEAM_AGG} AS team_name
                FROM objective_metrics om
                GROUP BY om.player_id, om.season, om.competition
            ) blocks
            WHERE team_name IS NOT NULL AND trim(team_name) <> ''
            ORDER BY team_name ASC
            """
        )
        out["teams"] = [r["team_name"] for r in cur.fetchall()]

        cur.execute(
            """
            SELECT DISTINCT p.nationality
            FROM objective_metrics om
            INNER JOIN players p ON p.id = om.player_id
            WHERE p.nationality IS NOT NULL AND trim(p.nationality) <> ''
            ORDER BY p.nationality ASC
            """
        )
        out["nationalities"] = [r["nationality"] for r in cur.fetchall()]

        cur.execute(
            """
            SELECT DISTINCT p.preferred_foot
            FROM objective_metrics om
            INNER JOIN players p ON p.id = om.player_id
            WHERE p.preferred_foot IS NOT NULL AND trim(p.preferred_foot) <> ''
            ORDER BY p.preferred_foot ASC
            """
        )
        out["preferred_feet"] = [r["preferred_foot"] for r in cur.fetchall()]

        cur.execute(
            """
            SELECT DISTINCT metric_name FROM objective_metrics
            WHERE metric_name IS NOT NULL AND trim(metric_name) <> ''
            ORDER BY metric_name ASC
            """
        )
        out["metric_names"] = [r["metric_name"] for r in cur.fetchall()]

        cur.execute(
            """
            SELECT p.id, p.full_name
            FROM players p
            WHERE EXISTS (SELECT 1 FROM objective_metrics om WHERE om.player_id = p.id)
            ORDER BY p.full_name ASC
            """
        )
        out["players"] = [{"id": int(r["id"]), "full_name": r["full_name"]} for r in cur.fetchall()]

    from scouting.config.position_analysis import STANDARD_POSITIONS, standardize_position_for_analysis

    std_set: set[str] = set()
    for pos in out["positions"]:
        std = standardize_position_for_analysis(pos)
        if std:
            std_set.add(std)
    out["standardized_positions"] = [s for s in STANDARD_POSITIONS if s in std_set] or sorted(std_set)

    return out


def get_metric_comparison(
    conn: Connection,
    metric_name: str,
    *,
    source_name: str | None = None,
    player_ids: list[int] | None = None,
    position: str | None = None,
    season: str | None = None,
    competition: str | None = None,
    current_team: str | None = None,
) -> list[dict[str, Any]]:
    """
    Media de metric_value por jugador (y dimensión season/competition cuando aplica).
    Una fila por (player_id, season, competition, metric_name) tras agregar.
    """
    clauses: list[str] = ["om.metric_name = %s", "om.metric_value IS NOT NULL"]
    params: list[Any] = [str(metric_name).strip()]

    if source_name is not None and str(source_name).strip():
        clauses.append("(om.source_name IS NOT DISTINCT FROM %s)")
        params.append(str(source_name).strip())
    if position is not None and str(position).strip():
        clauses.append("(p.position IS NOT DISTINCT FROM %s)")
        params.append(str(position).strip())
    if season is not None and str(season).strip():
        clauses.append("(om.season IS NOT DISTINCT FROM %s)")
        params.append(str(season).strip())
    if competition is not None and str(competition).strip():
        clauses.append("(om.competition IS NOT DISTINCT FROM %s)")
        params.append(str(competition).strip())
    if current_team is not None and str(current_team).strip():
        clauses.append(f"({_OBJECTIVE_TEAM_ROW}) IS NOT DISTINCT FROM %s")
        params.append(str(current_team).strip())
    if player_ids:
        clauses.append("om.player_id = ANY(%s)")
        params.append(player_ids)

    where_sql = " AND ".join(clauses)

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT
                om.player_id,
                p.full_name AS player_name,
                p.position,
                MAX({_OBJECTIVE_TEAM_ROW}) AS objective_team,
                om.season,
                om.competition,
                MAX(om.source_name)::text AS source_name,
                om.metric_name,
                AVG(om.metric_value::numeric) AS metric_value,
                MAX(om.metric_unit)::text AS metric_unit
            FROM objective_metrics om
            INNER JOIN players p ON p.id = om.player_id
            WHERE {where_sql}
            GROUP BY om.player_id, p.full_name, p.position,
                     om.season, om.competition, om.metric_name
            ORDER BY AVG(om.metric_value::numeric) DESC NULLS LAST, p.full_name ASC
            """,
            params,
        )
        return list(cur.fetchall())


# Equipo objetivo: solo raw_payload (nunca players.current_team).
# Ver docs/sofascore_objective_team_context.md — TODO: player_team_seasons.
_OBJECTIVE_TEAM_AGG = """
    COALESCE(
        NULLIF(trim(MAX(om.raw_payload->>'team_name')), ''),
        NULLIF(trim(MAX(om.raw_payload->>'team')), ''),
        NULLIF(trim(MAX(om.raw_payload->'raw_row'->>'team_name')), ''),
        NULLIF(trim(MAX(om.raw_payload->'raw_row'->>'team')), '')
    )
"""

_OBJECTIVE_TEAM_ROW = """
    COALESCE(
        NULLIF(trim(om.raw_payload->>'team_name'), ''),
        NULLIF(trim(om.raw_payload->>'team'), ''),
        NULLIF(trim(om.raw_payload->'raw_row'->>'team_name'), ''),
        NULLIF(trim(om.raw_payload->'raw_row'->>'team'), '')
    )
"""

# Posición objetiva: raw_payload (nunca players.position).
_OBJECTIVE_POSITION_CODE_AGG = """
    UPPER(NULLIF(trim(COALESCE(
        MAX(om.raw_payload->>'sofascore_position'),
        MAX(om.raw_payload->>'original_position'),
        MAX(om.raw_payload->'raw_row'->>'position')
    )), ''))
"""

_OBJECTIVE_POSITION_GROUP_AGG = f"""
    COALESCE(
        NULLIF(trim(MAX(om.raw_payload->>'objective_position_group')), ''),
        CASE {_OBJECTIVE_POSITION_CODE_AGG}
            WHEN 'G' THEN 'Portero'
            WHEN 'D' THEN 'Defensa'
            WHEN 'M' THEN 'Mediocampo'
            WHEN 'F' THEN 'Delantero'
            ELSE NULL
        END
    )
"""


def get_objective_data_filter_options(
    conn: Connection,
    *,
    source_name: str = "Sofascore",
    season: str | None = None,
) -> dict[str, list[Any]]:
    """Valores distintos para filtros de la vista simple Datos objetivos."""
    out: dict[str, list[Any]] = {
        "seasons": [],
        "competitions": [],
        "teams": [],
        "positions": [],
    }
    src = str(source_name).strip()
    season_clause = ""
    season_params: list[Any] = [src]
    if season is not None and str(season).strip():
        season_clause = " AND om.season IS NOT DISTINCT FROM %s"
        season_params.append(str(season).strip())
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT DISTINCT om.season
            FROM objective_metrics om
            WHERE om.source_name = %s
              AND om.season IS NOT NULL AND trim(om.season) <> ''
              {season_clause}
            ORDER BY om.season ASC
            """,
            season_params,
        )
        out["seasons"] = [r["season"] for r in cur.fetchall()]

        cur.execute(
            f"""
            SELECT DISTINCT om.competition
            FROM objective_metrics om
            WHERE om.source_name = %s
              AND om.competition IS NOT NULL AND trim(om.competition) <> ''
              {season_clause}
            ORDER BY om.competition ASC
            """,
            season_params,
        )
        out["competitions"] = [r["competition"] for r in cur.fetchall()]

        cur.execute(
            f"""
            SELECT DISTINCT team_name
            FROM (
                SELECT {_OBJECTIVE_TEAM_AGG} AS team_name
                FROM objective_metrics om
                WHERE om.source_name = %s
                  {season_clause}
                GROUP BY om.player_id, om.season, om.competition
            ) blocks
            WHERE team_name IS NOT NULL
              AND trim(team_name) <> ''
            ORDER BY team_name ASC
            """,
            season_params,
        )
        out["teams"] = [r["team_name"] for r in cur.fetchall()]

        cur.execute(
            f"""
            SELECT DISTINCT position_group
            FROM (
                SELECT {_OBJECTIVE_POSITION_GROUP_AGG} AS position_group
                FROM objective_metrics om
                WHERE om.source_name = %s
                  {season_clause}
                GROUP BY om.player_id, om.season, om.competition
            ) blocks
            WHERE position_group IS NOT NULL
              AND trim(position_group) <> ''
            ORDER BY position_group ASC
            """,
            season_params,
        )
        out["positions"] = [r["position_group"] for r in cur.fetchall()]

    return out


def get_objective_players_summary(
    conn: Connection,
    *,
    source_name: str | None = "Sofascore",
    season: str | None = None,
    competition: str | None = None,
    position: str | None = None,
    team: str | None = None,
    search_text: str | None = None,
    prefer_real: bool = True,
    source_type: str | None = None,
) -> list[dict[str, Any]]:
    """
    Una fila por jugador + temporada + competición (sin pivot, sin scouting_reports).

    prefer_real=True: solo Sofascore si existen en el ámbito temporada/competición;
    si no hay reales, usa demo. source_type fuerza un origen concreto.
    """
    from scouting.services.objective_origin_policy import (
        SOURCE_TYPE_DEMO,
        SOURCE_TYPE_SOFASCORE,
        origin_sql_for,
        resolve_scope_origin,
    )

    src = str(source_name or "Sofascore").strip()
    clauses: list[str] = ["om.source_name = %s"]
    params: list[Any] = [src]
    team_expr = _OBJECTIVE_TEAM_AGG
    if season is not None and str(season).strip():
        clauses.append("om.season IS NOT DISTINCT FROM %s")
        params.append(str(season).strip())
    if competition is not None and str(competition).strip():
        clauses.append("om.competition IS NOT DISTINCT FROM %s")
        params.append(str(competition).strip())

    origin_kind = source_type
    if origin_kind is None and prefer_real:
        resolution = resolve_scope_origin(
            conn, season=season, competition=competition, source_name=src
        )
        origin_kind = None if resolution.origin == "none" else resolution.origin
    origin_clause = origin_sql_for(origin_kind or "", alias="om") if origin_kind else None
    if origin_clause:
        clauses.append(origin_clause)

    having_parts: list[str] = []
    if team is not None and str(team).strip():
        having_parts.append(f"{team_expr} IS NOT DISTINCT FROM %s")
        params.append(str(team).strip())
    if position is not None and str(position).strip():
        from scouting.config.position_analysis import standardize_sofascore_position

        pos_group = standardize_sofascore_position(str(position).strip())
        if pos_group:
            having_parts.append(
                f"({_OBJECTIVE_POSITION_GROUP_AGG}) IS NOT DISTINCT FROM %s"
            )
            params.append(pos_group)
    having_sql = f"HAVING {' AND '.join(having_parts)}" if having_parts else ""
    if search_text is not None and str(search_text).strip():
        clauses.append("LOWER(p.full_name) LIKE LOWER(%s)")
        params.append(f"%{str(search_text).strip()}%")

    where_sql = " AND ".join(clauses)

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT
                p.id AS player_id,
                p.full_name AS player_name,
                p.position AS scouting_position,
                {team_expr} AS objective_team,
                p.nationality,
                om.season,
                om.competition,
                {_OBJECTIVE_POSITION_CODE_AGG} AS sofascore_position_code,
                {_OBJECTIVE_POSITION_GROUP_AGG} AS objective_position_group,
                COUNT(*)::int AS metrics_count,
                MAX(CASE WHEN om.metric_name = 'minutesPlayed'
                    THEN om.metric_value::numeric END) AS minutes_played,
                MAX(CASE WHEN om.metric_name = 'matches_played'
                    THEN om.metric_value::numeric END) AS matches_played,
                MAX(CASE WHEN om.metric_name = 'avg_rating'
                    THEN om.metric_value::numeric END) AS avg_rating,
                MAX(om.source_type)::text AS source_type
            FROM objective_metrics om
            INNER JOIN players p ON p.id = om.player_id
            WHERE {where_sql}
            GROUP BY
                p.id, p.full_name, p.position, p.nationality,
                om.season, om.competition
            {having_sql}
            ORDER BY om.competition NULLS LAST, objective_team NULLS LAST, p.full_name ASC
            """,
            params,
        )
        return list(cur.fetchall())


def get_objective_metrics_for_player_block(
    conn: Connection,
    player_id: int,
    season: str | None,
    competition: str | None,
    *,
    source_name: str | None = "Sofascore",
    prefer_real: bool = True,
) -> list[dict[str, Any]]:
    """
    Métricas de un jugador para temporada + competición.

    Si prefer_real=True: primero source_type sofascore; si no hay, fallback demo.
    Nunca mezcla ambos orígenes en el mismo resultado.
    """
    src = str(source_name or "Sofascore").strip()

    def _fetch(source_type_filter: str | None) -> list[dict[str, Any]]:
        clauses: list[str] = [
            "om.player_id = %s",
            "om.season IS NOT DISTINCT FROM %s",
            "om.competition IS NOT DISTINCT FROM %s",
            "om.metric_value IS NOT NULL",
            "om.source_name = %s",
        ]
        params: list[Any] = [player_id, season, competition, src]
        if source_type_filter == "sofascore":
            clauses.append(
                "(om.source_type = 'sofascore' OR "
                "(om.source_type IS NULL AND om.import_batch_id IS NOT NULL))"
            )
        elif source_type_filter == "demo":
            clauses.append(
                """(
                    om.source_type = 'demo'
                    OR (
                        om.source_type IS NULL
                        AND om.import_batch_id IS NULL
                    )
                )"""
            )
        where_sql = " AND ".join(clauses)
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                SELECT
                    om.metric_name,
                    om.metric_value,
                    om.metric_unit,
                    om.source_name,
                    om.source_type,
                    om.raw_payload,
                    p.position AS player_position
                FROM objective_metrics om
                INNER JOIN players p ON p.id = om.player_id
                WHERE {where_sql}
                ORDER BY om.metric_name ASC
                """,
                params,
            )
            return list(cur.fetchall())

    if not prefer_real:
        return _fetch(None)

    real_rows = _fetch("sofascore")
    if real_rows:
        return real_rows
    return _fetch("demo")


def _objective_position_from_row(row: dict[str, Any], *, source_name: str) -> str | None:
    from scouting.config.position_analysis import (
        position_label_from_payload,
        standardize_sofascore_position,
    )

    _ = source_name
    payload = row.get("raw_payload")
    raw_pos = position_label_from_payload(payload if isinstance(payload, dict) else None)
    return standardize_sofascore_position(str(raw_pos) if raw_pos else None)


def _cohort_origin_sql(
    conn: Connection,
    *,
    season: str | None,
    competition: str | None,
    cohort_seasons: list[str] | None = None,
    prefer_real: bool = True,
    source_type: str | None = None,
    alias: str = "om",
) -> str | None:
    """Filtro de origen para cohortes: nunca mezcla demo y Sofascore."""
    from scouting.services.objective_origin_policy import (
        SOURCE_TYPE_DEMO,
        SOURCE_TYPE_SOFASCORE,
        origin_sql_for,
        resolve_scope_origin,
    )

    if source_type:
        return origin_sql_for(str(source_type).strip(), alias=alias)
    if not prefer_real:
        return None

    seasons: list[str] = []
    if cohort_seasons:
        seasons = [str(s).strip() for s in cohort_seasons if str(s).strip()]
    elif season is not None and str(season).strip():
        seasons = [str(season).strip()]

    if not seasons:
        return origin_sql_for(SOURCE_TYPE_SOFASCORE, alias=alias)

    has_sofa = False
    has_demo = False
    for s in seasons:
        resolution = resolve_scope_origin(conn, season=s, competition=competition)
        if resolution.origin == SOURCE_TYPE_SOFASCORE:
            has_sofa = True
        elif resolution.origin == SOURCE_TYPE_DEMO:
            has_demo = True
    if has_sofa:
        return origin_sql_for(SOURCE_TYPE_SOFASCORE, alias=alias)
    if has_demo:
        return origin_sql_for(SOURCE_TYPE_DEMO, alias=alias)
    return origin_sql_for(SOURCE_TYPE_SOFASCORE, alias=alias)


def _cohort_competition_sql(
    competition: str | None,
    peer_competitions: list[str] | None,
) -> tuple[str, list[Any]]:
    """Filtro SQL de competición para cohorte (una liga o varias)."""
    if peer_competitions:
        leagues = [str(c).strip() for c in peer_competitions if str(c).strip()]
        if len(leagues) > 1:
            return "om.competition = ANY(%s)", [leagues]
        if len(leagues) == 1:
            return "om.competition IS NOT DISTINCT FROM %s", [leagues[0]]
    return "om.competition IS NOT DISTINCT FROM %s", [competition]


def _cohort_season_sql(
    season: str | None,
    cohort_seasons: list[str] | None,
) -> tuple[str, list[Any]]:
    """Filtro SQL de temporada para cohorte (una o varias)."""
    if cohort_seasons:
        seasons = [str(s).strip() for s in cohort_seasons if str(s).strip()]
        if len(seasons) > 1:
            return "om.season = ANY(%s)", [seasons]
        if len(seasons) == 1:
            return "om.season IS NOT DISTINCT FROM %s", [seasons[0]]
    return "om.season IS NOT DISTINCT FROM %s", [season]


def count_objective_comparison_cohort(
    conn: Connection,
    player_id: int,
    season: str | None,
    competition: str | None,
    position_group: str,
    scope: str,
    *,
    source_name: str = "Sofascore",
    peer_competitions: list[str] | None = None,
    cohort_seasons: list[str] | None = None,
    prefer_real: bool = True,
    source_type: str | None = None,
) -> int:
    """Jugadores distintos en la cohorte (excluye el propio jugador)."""
    src = str(source_name).strip()
    season_sql, season_params = _cohort_season_sql(season, cohort_seasons)
    cohort_clauses = [
        "om.source_name = %s",
        season_sql,
        "om.metric_value IS NOT NULL",
    ]
    cohort_params: list[Any] = [src, *season_params]
    if scope == "same_competition" or peer_competitions:
        comp_sql, comp_params = _cohort_competition_sql(competition, peer_competitions)
        cohort_clauses.append(comp_sql)
        cohort_params.extend(comp_params)
    origin_sql = _cohort_origin_sql(
        conn,
        season=season,
        competition=competition,
        cohort_seasons=cohort_seasons,
        prefer_real=prefer_real,
        source_type=source_type,
    )
    if origin_sql:
        cohort_clauses.append(origin_sql)

    cohort_where = " AND ".join(cohort_clauses)

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT DISTINCT om.player_id, p.position, om.raw_payload
            FROM objective_metrics om
            INNER JOIN players p ON p.id = om.player_id
            WHERE {cohort_where}
            """,
            cohort_params,
        )
        rows = list(cur.fetchall())

    peers: set[int] = set()
    for row in rows:
        pid = int(row["player_id"])
        if pid == player_id:
            continue
        grp = _objective_position_from_row(row, source_name=src)
        if grp == position_group:
            peers.add(pid)
    return len(peers)


def get_player_vs_position_average(
    conn: Connection,
    player_id: int,
    season: str | None,
    competition: str | None,
    position_group: str,
    metric_names: list[str],
    scope: str,
    *,
    source_name: str = "Sofascore",
    min_peers: int = 2,
) -> tuple[list[dict[str, Any]], int]:
    """
    Compara valores del jugador con la media de su grupo de posición objetiva.
    scope: same_competition | all_competitions
    Returns (rows, cohort_peer_count).
    """
    if not metric_names or not position_group:
        return [], 0

    src = str(source_name).strip()
    names = [str(n).strip() for n in metric_names if str(n).strip()]
    if not names:
        return [], 0

    cohort_peer_count = count_objective_comparison_cohort(
        conn,
        player_id,
        season,
        competition,
        position_group,
        scope,
        source_name=src,
    )

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT om.metric_name, om.metric_value::numeric AS metric_value
            FROM objective_metrics om
            WHERE om.source_name = %s
              AND om.player_id = %s
              AND om.season IS NOT DISTINCT FROM %s
              AND om.competition IS NOT DISTINCT FROM %s
              AND om.metric_name = ANY(%s)
              AND om.metric_value IS NOT NULL
            """,
            (src, player_id, season, competition, names),
        )
        player_rows = list(cur.fetchall())

    player_vals: dict[str, float] = {}
    for r in player_rows:
        mname = str(r["metric_name"])
        player_vals[mname] = float(r["metric_value"])

    cohort_clauses = [
        "om.source_name = %s",
        "om.season IS NOT DISTINCT FROM %s",
        "om.metric_name = ANY(%s)",
        "om.metric_value IS NOT NULL",
    ]
    cohort_params: list[Any] = [src, season, names]
    if scope == "same_competition":
        cohort_clauses.append("om.competition IS NOT DISTINCT FROM %s")
        cohort_params.append(competition)

    cohort_where = " AND ".join(cohort_clauses)

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT
                om.player_id,
                p.position AS player_position,
                om.raw_payload,
                om.metric_name,
                om.metric_value::numeric AS metric_value
            FROM objective_metrics om
            INNER JOIN players p ON p.id = om.player_id
            WHERE {cohort_where}
            """,
            cohort_params,
        )
        cohort_rows = list(cur.fetchall())

    cohort_by_metric: dict[str, dict[int, float]] = {n: {} for n in names}
    for row in cohort_rows:
        pid = int(row["player_id"])
        grp = _objective_position_from_row(row, source_name=src)
        if grp != position_group:
            continue
        mname = str(row["metric_name"])
        if mname not in cohort_by_metric:
            continue
        cohort_by_metric[mname][pid] = float(row["metric_value"])

    out: list[dict[str, Any]] = []
    for mname in names:
        pval = player_vals.get(mname)
        if pval is None:
            continue
        cohort_vals = cohort_by_metric.get(mname) or {}
        peers_excl = {
            pid: val for pid, val in cohort_vals.items() if pid != player_id
        }
        avg_includes_player_fallback = False
        if len(peers_excl) >= min_peers:
            avg = sum(peers_excl.values()) / len(peers_excl)
            players_count = len(peers_excl)
        elif len(cohort_vals) >= min_peers:
            avg = sum(cohort_vals.values()) / len(cohort_vals)
            players_count = len(cohort_vals)
            avg_includes_player_fallback = True
        else:
            continue
        cohort_values = list(cohort_vals.values())
        scale_min = linear_percentile_value(cohort_values, COHORT_RADAR_SCALE_P_LOW)
        scale_max = linear_percentile_value(cohort_values, COHORT_RADAR_SCALE_P_HIGH)
        if scale_min is None or scale_max is None or scale_max <= scale_min:
            continue
        out.append(
            {
                "metric_name": mname,
                "player_value": pval,
                "position_avg_value": avg,
                "players_count": players_count,
                "avg_includes_player_fallback": avg_includes_player_fallback,
                "cohort_scale_min": scale_min,
                "cohort_scale_max": scale_max,
                "cohort_scale_p_low": COHORT_RADAR_SCALE_P_LOW,
                "cohort_scale_p_high": COHORT_RADAR_SCALE_P_HIGH,
            }
        )
    return out, cohort_peer_count


def _team_from_objective_row(row: dict[str, Any]) -> str:
    payload = row.get("raw_payload")
    if isinstance(payload, dict):
        return str(
            payload.get("objective_team")
            or payload.get("team_name")
            or payload.get("team")
            or ""
        ).strip()
    return ""


def _percentile_rank_among_peers(player_value: float, peer_values: list[float]) -> float | None:
    """Percentil del jugador dentro de la cohorte (0–100, método rank promedio)."""
    if not peer_values:
        return None
    below = sum(1 for v in peer_values if v < player_value)
    equal = sum(1 for v in peer_values if v == player_value)
    return (below + 0.5 * equal) / len(peer_values) * 100.0


def get_player_vs_position_percentiles(
    conn: Connection,
    player_id: int,
    season: str | None,
    competition: str | None,
    position_group: str,
    metric_names: list[str],
    *,
    source_name: str = "Sofascore",
    min_peers: int = 2,
    peer_competitions: list[str] | None = None,
    cohort_seasons: list[str] | None = None,
    prefer_real: bool = True,
    source_type: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """
    Percentiles del jugador vs cohorte de posición/temporada (y liga o ligas combinadas).
    Returns (rows, cohort_peer_count).
    """
    if not metric_names or not position_group:
        return [], 0

    src = str(source_name).strip()
    names = [str(n).strip() for n in metric_names if str(n).strip()]
    if not names:
        return [], 0

    scope = "same_competition"
    cohort_peer_count = count_objective_comparison_cohort(
        conn,
        player_id,
        season,
        competition,
        position_group,
        scope,
        source_name=src,
        peer_competitions=peer_competitions,
        cohort_seasons=cohort_seasons,
        prefer_real=prefer_real,
        source_type=source_type,
    )

    origin_sql = _cohort_origin_sql(
        conn,
        season=season,
        competition=competition,
        prefer_real=prefer_real,
        source_type=source_type,
    )
    player_clauses = [
        "om.source_name = %s",
        "om.player_id = %s",
        "om.season IS NOT DISTINCT FROM %s",
        "om.competition IS NOT DISTINCT FROM %s",
        "om.metric_name = ANY(%s)",
        "om.metric_value IS NOT NULL",
    ]
    player_params: list[Any] = [src, player_id, season, competition, names]
    if origin_sql:
        player_clauses.append(origin_sql)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT om.metric_name, om.metric_value::numeric AS metric_value, om.metric_unit
            FROM objective_metrics om
            WHERE {' AND '.join(player_clauses)}
            """,
            player_params,
        )
        player_rows = list(cur.fetchall())

    player_vals: dict[str, float] = {}
    player_units: dict[str, str | None] = {}
    for r in player_rows:
        mname = str(r["metric_name"])
        player_vals[mname] = float(r["metric_value"])
        player_units[mname] = r.get("metric_unit")

    season_sql, season_params = _cohort_season_sql(season, cohort_seasons)
    cohort_clauses = [
        "om.source_name = %s",
        season_sql,
        "om.metric_name = ANY(%s)",
        "om.metric_value IS NOT NULL",
    ]
    cohort_params: list[Any] = [src, *season_params, names]
    comp_sql, comp_params = _cohort_competition_sql(competition, peer_competitions)
    cohort_clauses.append(comp_sql)
    cohort_params.extend(comp_params)
    origin_cohort_sql = _cohort_origin_sql(
        conn,
        season=season,
        competition=competition,
        cohort_seasons=cohort_seasons,
        prefer_real=prefer_real,
        source_type=source_type,
    )
    if origin_cohort_sql:
        cohort_clauses.append(origin_cohort_sql)
    cohort_where = " AND ".join(cohort_clauses)

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT
                om.player_id,
                p.full_name AS player_name,
                p.position AS player_position,
                om.raw_payload,
                om.metric_name,
                om.metric_value::numeric AS metric_value
            FROM objective_metrics om
            INNER JOIN players p ON p.id = om.player_id
            WHERE {cohort_where}
            """,
            cohort_params,
        )
        cohort_rows = list(cur.fetchall())

    multi_season = bool(cohort_seasons and len(cohort_seasons) > 1)
    peer_lists: dict[str, list[float]] = {n: [] for n in names}
    peer_rows_by_metric: dict[str, list[dict[str, Any]]] = {n: [] for n in names}
    peer_players: dict[str, set[int]] = {n: set() for n in names}
    for row in cohort_rows:
        pid = int(row["player_id"])
        if pid == player_id:
            continue
        grp = _objective_position_from_row(row, source_name=src)
        if grp != position_group:
            continue
        mname = str(row["metric_name"])
        if mname not in peer_lists:
            continue
        val = float(row["metric_value"])
        peer_lists[mname].append(val)
        peer_players[mname].add(pid)
        peer_rows_by_metric[mname].append(
            {
                "player_id": pid,
                "player_name": str(row.get("player_name") or "").strip(),
                "team": _team_from_objective_row(row),
                "value": val,
            }
        )

    out: list[dict[str, Any]] = []
    for mname in names:
        pval = player_vals.get(mname)
        if pval is None:
            continue
        peer_values = peer_lists.get(mname) or []
        if len(peer_values) < min_peers:
            continue
        pct = _percentile_rank_among_peers(pval, peer_values)
        if pct is None:
            continue
        rank = sum(1 for v in peer_values if v < pval) + 1
        players_n = len(peer_players.get(mname) or set())
        cohort_peer_rows = peer_rows_by_metric.get(mname) or []
        out.append(
            {
                "metric_name": mname,
                "player_value": pval,
                "percentile": round(pct, 1),
                "cohort_values": peer_values,
                "cohort_peer_rows": cohort_peer_rows,
                "players_count": players_n if multi_season else len(peer_values),
                "cohort_observations": len(peer_values),
                "cohort_rank": rank,
                "metric_unit": player_units.get(mname),
            }
        )
    return out, cohort_peer_count


def get_position_group_percentile_averages(
    conn: Connection,
    player_id: int,
    season: str | None,
    competition: str | None,
    position_group: str,
    metric_names: list[str],
    *,
    source_name: str = "Sofascore",
    min_peers: int = 2,
) -> tuple[list[dict[str, Any]], int]:
    """
    Media de percentiles de rendimiento de la cohorte (misma posición, liga y temporada).
    Solo jugadores con valor en la métrica; no imputa ausentes.
    """
    if not metric_names or not position_group:
        return [], 0

    src = str(source_name).strip()
    names = [str(n).strip() for n in metric_names if str(n).strip()]
    if not names:
        return [], 0

    cohort_peer_count = count_objective_comparison_cohort(
        conn,
        player_id,
        season,
        competition,
        position_group,
        "same_competition",
        source_name=src,
    )

    season_sql, season_params = _cohort_season_sql(season, None)
    cohort_clauses = [
        "om.source_name = %s",
        season_sql,
        "om.metric_name = ANY(%s)",
        "om.metric_value IS NOT NULL",
    ]
    cohort_params: list[Any] = [src, *season_params, names]
    comp_sql, comp_params = _cohort_competition_sql(competition, None)
    cohort_clauses.append(comp_sql)
    cohort_params.extend(comp_params)
    cohort_where = " AND ".join(cohort_clauses)

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT
                om.player_id,
                p.position AS player_position,
                om.raw_payload,
                om.metric_name,
                om.metric_value::numeric AS metric_value
            FROM objective_metrics om
            INNER JOIN players p ON p.id = om.player_id
            WHERE {cohort_where}
            """,
            cohort_params,
        )
        cohort_rows = list(cur.fetchall())

    peer_values_by_metric: dict[str, dict[int, float]] = {n: {} for n in names}
    for row in cohort_rows:
        pid = int(row["player_id"])
        grp = _objective_position_from_row(row, source_name=src)
        if grp != position_group:
            continue
        mname = str(row["metric_name"])
        if mname not in peer_values_by_metric:
            continue
        peer_values_by_metric[mname][pid] = float(row["metric_value"])

    out: list[dict[str, Any]] = []
    for mname in names:
        player_map = peer_values_by_metric.get(mname) or {}
        if len(player_map) < min_peers + 1:
            continue
        all_values = list(player_map.values())
        perf_pcts: list[float] = []
        for pid, val in player_map.items():
            if pid == player_id:
                continue
            raw_pct = _percentile_rank_among_peers(val, all_values)
            if raw_pct is None:
                continue
            perf_pcts.append(performance_percentile_from_raw(raw_pct, mname))
        if len(perf_pcts) < min_peers:
            continue
        out.append(
            {
                "metric_name": mname,
                "avg_performance_percentile": round(sum(perf_pcts) / len(perf_pcts), 1),
                "n_players": len(perf_pcts),
            }
        )
    return out, cohort_peer_count


def get_metrics_by_player_grouped(
    conn: Connection,
    player_id: int,
    *,
    season: str | None = None,
) -> list[dict[str, Any]]:
    """
    Group metrics by (season, competition). Each item: season, competition, metrics (list of row dicts).
    """
    rows = get_metrics_by_player(conn, player_id, season=season)
    groups: dict[tuple[str | None, str | None], list[dict[str, Any]]] = {}
    order_keys: list[tuple[str | None, str | None]] = []

    for row in rows:
        key = (row.get("season"), row.get("competition"))
        if key not in groups:
            groups[key] = []
            order_keys.append(key)
        groups[key].append(dict(row))

    return [{"season": k[0], "competition": k[1], "metrics": groups[k]} for k in order_keys]
