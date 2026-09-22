"""External player ID mappings (Sofascore, etc.)."""

from __future__ import annotations

from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row


def get_external_ids_by_player(conn: Connection, player_id: int) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id, player_id, provider, external_id, external_name, created_at
            FROM player_external_ids
            WHERE player_id = %s
            ORDER BY provider ASC, external_id ASC
            """,
            (player_id,),
        )
        return list(cur.fetchall())


def find_player_by_external_id(
    conn: Connection,
    provider: str,
    external_id: str,
) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id, player_id, provider, external_id, external_name, created_at
            FROM player_external_ids
            WHERE provider = %s AND external_id = %s
            """,
            (provider, str(external_id).strip()),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def create_or_update_external_id(
    conn: Connection,
    player_id: int,
    provider: str,
    external_id: str,
    external_name: str | None = None,
    commit: bool = True,
) -> None:
    ext = str(external_id).strip()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO player_external_ids (player_id, provider, external_id, external_name)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (provider, external_id) DO UPDATE SET
                player_id = EXCLUDED.player_id,
                external_name = COALESCE(EXCLUDED.external_name, player_external_ids.external_name)
            """,
            (player_id, provider, ext, external_name),
        )
    if commit:
        conn.commit()
