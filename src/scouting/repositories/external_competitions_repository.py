"""External competition catalog (Sofascore tournament/season IDs)."""

from __future__ import annotations

from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row


def get_active_competitions(
    conn: Connection,
    provider: str | None = None,
) -> list[dict[str, Any]]:
    clauses = ["is_active = true"]
    params: list[Any] = []
    if provider:
        clauses.append("provider = %s")
        params.append(provider)

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT id, provider, country, division, competition, tournament_id, season_id, is_active
            FROM external_competitions
            WHERE {' AND '.join(clauses)}
            ORDER BY country, division, competition
            """,
            params,
        )
        return [dict(r) for r in cur.fetchall()]


def upsert_external_competition(
    conn: Connection,
    *,
    provider: str,
    country: str,
    division: str,
    competition: str,
    tournament_id: int,
    season_id: int,
    is_active: bool = True,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO external_competitions (
                provider, country, division, competition, tournament_id, season_id, is_active
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (provider, tournament_id, season_id) DO UPDATE SET
                country = EXCLUDED.country,
                division = EXCLUDED.division,
                competition = EXCLUDED.competition,
                is_active = EXCLUDED.is_active
            RETURNING id
            """,
            (provider, country, division, competition, tournament_id, season_id, is_active),
        )
        cid = int(cur.fetchone()[0])
    conn.commit()
    return cid
