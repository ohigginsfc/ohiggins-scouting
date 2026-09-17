"""Evaluación del estado real de sincronización Sofascore vs datos demo."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from psycopg import Connection

from scouting.services.sofascore_import_service import PROVIDER, SOURCE_NAME

SOURCE_TYPE_SOFASCORE = "sofascore"
SOURCE_TYPE_DEMO = "demo"


@dataclass
class SeasonSyncAssessment:
    """Estado verificable de sync para una temporada (no usa COUNT total a ciegas)."""

    season: str
    sofascore_metrics: int = 0
    demo_metrics: int = 0
    other_metrics: int = 0
    total_metrics: int = 0
    sofascore_players: int = 0
    demo_only_players: int = 0
    processed_events: int = 0
    pending_events: int = 0
    failed_events: int = 0
    total_ingestion_events: int = 0
    completed_import_batches: int = 0
    needs_initial_backfill: bool = False
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _count(conn: Connection, sql: str, params: tuple[Any, ...] = ()) -> int:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else 0


def count_metrics_by_origin(
    conn: Connection,
    *,
    season: str | None = None,
) -> dict[str, int]:
    """
    Cuenta métricas por origen.

    Real Sofascore: source_type='sofascore' O (legacy) import_batch_id NOT NULL.
    Demo: source_type='demo' O (legacy) Sofascore sin lote.
    """
    season_clause = ""
    params: list[Any] = []
    if season is not None and str(season).strip():
        season_clause = " AND season IS NOT DISTINCT FROM %s"
        params.append(str(season).strip())

    sofascore = _count(
        conn,
        f"""
        SELECT COUNT(*) FROM objective_metrics
        WHERE (
            source_type = %s
            OR (source_type IS NULL AND import_batch_id IS NOT NULL)
        )
        {season_clause}
        """,
        tuple([SOURCE_TYPE_SOFASCORE, *params]),
    )
    demo = _count(
        conn,
        f"""
        SELECT COUNT(*) FROM objective_metrics
        WHERE (
            source_type = %s
            OR (
                source_type IS NULL
                AND import_batch_id IS NULL
                AND source_name = %s
            )
            OR source_name IN ('StatsDemo', 'examples_generated', 'DEMO')
        )
        {season_clause}
        """,
        tuple([SOURCE_TYPE_DEMO, SOURCE_NAME, *params]),
    )
    total = _count(
        conn,
        f"SELECT COUNT(*) FROM objective_metrics WHERE TRUE {season_clause}",
        tuple(params),
    )
    other = max(0, total - sofascore - demo)
    return {
        "sofascore": sofascore,
        "demo": demo,
        "other": other,
        "total": total,
    }


def count_sofascore_players(conn: Connection) -> int:
    return _count(
        conn,
        """
        SELECT COUNT(DISTINCT player_id)
        FROM player_external_ids
        WHERE provider = %s
        """,
        (PROVIDER,),
    )


def count_players_with_demo_metrics_only(conn: Connection, *, season: str | None = None) -> int:
    season_clause = ""
    params: list[Any] = [SOURCE_TYPE_DEMO, SOURCE_NAME]
    if season is not None and str(season).strip():
        season_clause = " AND om.season IS NOT DISTINCT FROM %s"
        params.append(str(season).strip())
    return _count(
        conn,
        f"""
        SELECT COUNT(DISTINCT om.player_id)
        FROM objective_metrics om
        WHERE (
            om.source_type = %s
            OR (
                om.source_type IS NULL
                AND om.import_batch_id IS NULL
                AND om.source_name = %s
            )
        )
        {season_clause}
        AND NOT EXISTS (
            SELECT 1 FROM objective_metrics r
            WHERE r.player_id = om.player_id
              AND (
                r.source_type = 'sofascore'
                OR (r.source_type IS NULL AND r.import_batch_id IS NOT NULL)
              )
        )
        """,
        tuple(params),
    )


def count_ingestion_by_status(conn: Connection, *, season: int | str) -> dict[str, int]:
    season_int = int(str(season).strip())
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT processing_status, COUNT(*)::int AS n
            FROM sofascore_event_ingestion
            WHERE season = %s AND source_name = %s
            GROUP BY processing_status
            """,
            (season_int, SOURCE_NAME),
        )
        rows = cur.fetchall()
    out = {
        "processed": 0,
        "pending": 0,
        "downloaded": 0,
        "failed": 0,
        "skipped": 0,
        "total": 0,
    }
    for row in rows:
        status = str(row[0] or "")
        n = int(row[1] or 0)
        out["total"] += n
        if status in out:
            out[status] = n
        else:
            out["pending"] += n  # estados desconocidos → pendientes
    return out


def count_completed_import_batches(conn: Connection, *, season: str) -> int:
    return _count(
        conn,
        """
        SELECT COUNT(*) FROM data_import_batches
        WHERE provider = %s
          AND season IS NOT DISTINCT FROM %s
          AND status = 'completed'
        """,
        (PROVIDER, str(season).strip()),
    )


def assess_season_sync(conn: Connection, season: str) -> SeasonSyncAssessment:
    """
    Decide si hace falta sincronización inicial real.

    NO usa COUNT(*) total de objective_metrics como prueba de sync:
    los datos demo no cuentan como Sofascore real.
    """
    season_str = str(season).strip()
    origins = count_metrics_by_origin(conn, season=season_str)
    ingestion = count_ingestion_by_status(conn, season=season_str)
    batches = count_completed_import_batches(conn, season=season_str)
    sofascore_players = count_sofascore_players(conn)
    demo_only_players = count_players_with_demo_metrics_only(conn, season=season_str)

    reasons: list[str] = []
    needs = False

    if origins["sofascore"] <= 0:
        needs = True
        reasons.append("No hay métricas con origen Sofascore real para esta temporada.")
    if batches <= 0 and origins["sofascore"] <= 0:
        needs = True
        if "No hay lotes" not in " ".join(reasons):
            reasons.append("No hay lotes de importación Sofascore completados para la temporada.")
    if ingestion["processed"] > 0 and origins["sofascore"] <= 0:
        needs = True
        reasons.append(
            "Hay eventos marcados como processed en sofascore_event_ingestion "
            "pero no existen métricas Sofascore reales (posible bootstrap vacío)."
        )
    if origins["demo"] > 0 and origins["sofascore"] <= 0:
        needs = True
        reasons.append(
            f"Solo hay métricas demo ({origins['demo']}); no equivalen a sync remota."
        )
    if ingestion["total"] <= 0 and origins["sofascore"] <= 0:
        needs = True
        reasons.append("No hay eventos Sofascore registrados en la tabla de ingestión.")

    # Deduplicate reasons while preserving order
    seen: set[str] = set()
    unique_reasons: list[str] = []
    for r in reasons:
        if r not in seen:
            seen.add(r)
            unique_reasons.append(r)

    return SeasonSyncAssessment(
        season=season_str,
        sofascore_metrics=origins["sofascore"],
        demo_metrics=origins["demo"],
        other_metrics=origins["other"],
        total_metrics=origins["total"],
        sofascore_players=sofascore_players,
        demo_only_players=demo_only_players,
        processed_events=ingestion["processed"],
        pending_events=ingestion["pending"] + ingestion.get("skipped", 0),
        failed_events=ingestion["failed"],
        total_ingestion_events=ingestion["total"],
        completed_import_batches=batches,
        needs_initial_backfill=needs,
        reasons=unique_reasons,
    )


def has_real_sofascore_metrics_for_scope(
    conn: Connection,
    *,
    competition: str,
    season: int | str,
) -> bool:
    """True si ya hay métricas reales importadas para competición/temporada."""
    season_str = str(season).strip()
    n = _count(
        conn,
        """
        SELECT COUNT(*) FROM objective_metrics
        WHERE competition IS NOT DISTINCT FROM %s
          AND season IS NOT DISTINCT FROM %s
          AND (
            source_type = %s
            OR (source_type IS NULL AND import_batch_id IS NOT NULL)
          )
        """,
        (competition, season_str, SOURCE_TYPE_SOFASCORE),
    )
    return n > 0
