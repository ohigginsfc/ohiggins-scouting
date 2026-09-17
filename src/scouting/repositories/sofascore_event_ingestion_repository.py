"""Persistencia de estado por evento Sofascore (ingestión incremental)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg import Connection
from psycopg.rows import dict_row


SOURCE_NAME = "Sofascore"
VALID_STATUSES = frozenset({"pending", "downloaded", "processed", "failed", "skipped"})


def list_events_for_scope(
    conn: Connection,
    *,
    country: str,
    division: str,
    competition: str,
    season: int,
    source_name: str = SOURCE_NAME,
) -> dict[int, dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT *
            FROM sofascore_event_ingestion
            WHERE source_name = %s
              AND country = %s
              AND division = %s
              AND competition = %s
              AND season = %s
            """,
            (source_name, country, division, competition, season),
        )
        rows = cur.fetchall()
    return {int(row["event_id"]): dict(row) for row in rows}


def count_by_status(
    conn: Connection,
    *,
    country: str,
    division: str,
    competition: str,
    season: int,
    source_name: str = SOURCE_NAME,
) -> dict[str, int]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT processing_status, COUNT(*) AS n
            FROM sofascore_event_ingestion
            WHERE source_name = %s
              AND country = %s
              AND division = %s
              AND competition = %s
              AND season = %s
            GROUP BY processing_status
            """,
            (source_name, country, division, competition, season),
        )
        rows = cur.fetchall()
    out = {status: 0 for status in VALID_STATUSES}
    for row in rows:
        out[str(row["processing_status"])] = int(row["n"])
    return out


def upsert_event(
    conn: Connection,
    *,
    country: str,
    division: str,
    competition: str,
    season: int,
    event_id: int,
    home_team: str | None = None,
    away_team: str | None = None,
    event_date: datetime | None = None,
    status: str | None = None,
    has_lineups: bool | None = None,
    has_xg: bool | None = None,
    checksum: str | None = None,
    processing_status: str = "pending",
    scraped_at: datetime | None = None,
    import_batch_id: UUID | None = None,
    error_message: str | None = None,
    source_name: str = SOURCE_NAME,
) -> None:
    if processing_status not in VALID_STATUSES:
        raise ValueError(f"Invalid processing_status: {processing_status}")

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO sofascore_event_ingestion (
                source_name, country, division, competition, season, event_id,
                home_team, away_team, event_date, status, has_lineups, has_xg,
                checksum, processing_status, scraped_at, import_batch_id, error_message
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
            ON CONFLICT (source_name, competition, season, event_id)
            DO UPDATE SET
                country = EXCLUDED.country,
                division = EXCLUDED.division,
                home_team = EXCLUDED.home_team,
                away_team = EXCLUDED.away_team,
                event_date = EXCLUDED.event_date,
                status = EXCLUDED.status,
                has_lineups = EXCLUDED.has_lineups,
                has_xg = EXCLUDED.has_xg,
                checksum = EXCLUDED.checksum,
                processing_status = EXCLUDED.processing_status,
                scraped_at = EXCLUDED.scraped_at,
                import_batch_id = EXCLUDED.import_batch_id,
                error_message = EXCLUDED.error_message,
                updated_at = NOW()
            """,
            (
                source_name,
                country,
                division,
                competition,
                season,
                event_id,
                home_team,
                away_team,
                event_date,
                status,
                has_lineups,
                has_xg,
                checksum,
                processing_status,
                scraped_at,
                str(import_batch_id) if import_batch_id else None,
                error_message,
            ),
        )
    conn.commit()


def seed_processed_events(
    conn: Connection,
    *,
    country: str,
    division: str,
    competition: str,
    season: int,
    events: list[dict[str, Any]],
    source_name: str = SOURCE_NAME,
) -> int:
    """Marca eventos existentes como processed (bootstrap tras primera migración)."""
    if not events:
        return 0

    inserted = 0
    for event in events:
        event_id = event.get("id")
        if event_id is None:
            continue
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sofascore_event_ingestion (
                    source_name, country, division, competition, season, event_id,
                    home_team, away_team, event_date, status, has_lineups, has_xg,
                    checksum, processing_status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'processed')
                ON CONFLICT (source_name, competition, season, event_id) DO NOTHING
                """,
                (
                    source_name,
                    country,
                    division,
                    competition,
                    season,
                    int(event_id),
                    (event.get("homeTeam") or {}).get("name"),
                    (event.get("awayTeam") or {}).get("name"),
                    _event_date_from_payload(event),
                    (event.get("status") or {}).get("type"),
                    event.get("hasLineups"),
                    event.get("hasXg"),
                    event.get("_bootstrap_checksum"),
                ),
            )
            inserted += cur.rowcount
    conn.commit()
    return inserted


def update_events_status_for_scope(
    conn: Connection,
    *,
    country: str,
    division: str,
    competition: str,
    season: int,
    from_statuses: set[str] | frozenset[str],
    to_status: str,
    error_message: str | None = None,
    import_batch_id: UUID | None = None,
    event_ids: list[int] | None = None,
    source_name: str = SOURCE_NAME,
) -> int:
    """Actualiza processing_status filtrando por ámbito (y opcionalmente event_ids)."""
    if to_status not in VALID_STATUSES:
        raise ValueError(f"Invalid processing_status: {to_status}")
    statuses = [s for s in from_statuses if s in VALID_STATUSES]
    if not statuses:
        return 0

    clauses = [
        "source_name = %s",
        "country = %s",
        "division = %s",
        "competition = %s",
        "season = %s",
        "processing_status = ANY(%s)",
    ]
    params: list[Any] = [source_name, country, division, competition, season, statuses]
    if event_ids is not None:
        if not event_ids:
            return 0
        clauses.append("event_id = ANY(%s)")
        params.append([int(x) for x in event_ids])

    set_parts = ["processing_status = %s", "updated_at = NOW()"]
    set_params: list[Any] = [to_status]
    if error_message is not None:
        set_parts.append("error_message = %s")
        set_params.append(error_message)
    elif to_status == "processed":
        set_parts.append("error_message = NULL")
    if import_batch_id is not None:
        set_parts.append("import_batch_id = %s")
        set_params.append(str(import_batch_id))

    sql = f"""
        UPDATE sofascore_event_ingestion
        SET {', '.join(set_parts)}
        WHERE {' AND '.join(clauses)}
    """
    with conn.cursor() as cur:
        cur.execute(sql, tuple(set_params + params))
        n = int(cur.rowcount or 0)
    conn.commit()
    return n


def demote_processed_without_import(
    conn: Connection,
    *,
    country: str,
    division: str,
    competition: str,
    season: int,
    error_message: str,
    source_name: str = SOURCE_NAME,
) -> int:
    """
    Corrige eventos marcados processed sin lote/métricas reales.
    Solo toca el ámbito indicado.
    """
    return update_events_status_for_scope(
        conn,
        country=country,
        division=division,
        competition=competition,
        season=season,
        from_statuses={"processed"},
        to_status="downloaded",
        error_message=error_message,
        source_name=source_name,
    )


def _event_date_from_payload(event: dict[str, Any]) -> datetime | None:
    ts = event.get("startTimestamp")
    if not ts:
        return None
    return datetime.utcfromtimestamp(int(ts))
