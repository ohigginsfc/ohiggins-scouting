"""Import batch persistence (Sofascore and other providers)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg.types.json import Json


def create_import_batch(
    conn: Connection,
    *,
    provider: str,
    country: str,
    division: str,
    competition: str,
    season: str,
    source_file: str,
    scraped_at: datetime | None = None,
) -> UUID:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO data_import_batches (
                provider, country, division, competition, season, source_file, scraped_at, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'running')
            RETURNING id
            """,
            (
                provider,
                country,
                division,
                competition,
                season,
                source_file,
                scraped_at,
            ),
        )
        batch_id = cur.fetchone()[0]
    conn.commit()
    return UUID(str(batch_id))


def complete_import_batch(conn: Connection, batch_id: UUID, stats: dict[str, Any] | None = None, *, commit: bool = True) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE data_import_batches
            SET status = 'completed', stats = %s
            WHERE id = %s
            """,
            (Json(stats) if stats is not None else None, str(batch_id)),
        )
    if commit:
        conn.commit()


def fail_import_batch(conn: Connection, batch_id: UUID, stats: dict[str, Any] | None = None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE data_import_batches
            SET status = 'failed', stats = %s
            WHERE id = %s
            """,
            (Json(stats) if stats is not None else None, str(batch_id)),
        )
    conn.commit()


def list_batch_ids_for_scope(
    conn: Connection,
    *,
    provider: str,
    country: str,
    division: str,
    season: str,
    exclude_batch_id: UUID | None = None,
    competition: str | None = None,
) -> list[UUID]:
    clauses = [
        "provider = %s",
        "country = %s",
        "division = %s",
        "season = %s",
        "status IN ('completed', 'replaced')",
    ]
    params: list[Any] = [provider, country, division, season]
    if competition is not None:
        clauses.append("competition = %s")
        params.append(competition)
    if exclude_batch_id is not None:
        clauses.append("id <> %s")
        params.append(str(exclude_batch_id))

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT id FROM data_import_batches
            WHERE {' AND '.join(clauses)}
            """,
            params,
        )
        return [UUID(str(row[0])) for row in cur.fetchall()]


def mark_previous_batches_replaced(
    conn: Connection,
    *,
    provider: str,
    country: str,
    division: str,
    season: str,
    current_batch_id: UUID,
    competition: str | None = None,
    commit: bool = True,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE data_import_batches
            SET status = 'replaced'
            WHERE provider = %s AND country = %s AND division = %s AND season = %s
              AND id <> %s AND status = 'completed'
              AND (%s::text IS NULL OR competition = %s)
            """,
            (provider, country, division, season, str(current_batch_id), competition, competition),
        )
        n = cur.rowcount
    if commit:
        conn.commit()
    return int(n)


def get_batch_by_id(conn: Connection, batch_id: UUID) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM data_import_batches WHERE id = %s",
            (str(batch_id),),
        )
        row = cur.fetchone()
        return dict(row) if row else None
