"""Player persistence."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from psycopg import Connection
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row

from scouting.services.players_service import normalize_player_name

_PLAYER_SELECT = """
    id, full_name, normalized_name, birth_date, nationality, position, current_team,
    preferred_foot, height_cm, image_path, created_at
"""


def sql_player_has_subjective_report(player_alias: str = "p") -> str:
    """Fragmento SQL: el jugador tiene al menos un informe visible en scouting_reports."""
    alias = player_alias.strip() or "p"
    return f"""EXISTS (
        SELECT 1 FROM scouting_reports sr
        WHERE sr.player_id = {alias}.id
          AND COALESCE(sr.is_hidden, FALSE) = FALSE
    )"""


def count_players_with_subjective_reports(conn: Connection) -> int:
    """Jugadores con al menos un informe subjetivo/manual (excluye solo Sofascore)."""
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT COUNT(*)::int
            FROM players p
            WHERE {sql_player_has_subjective_report("p")}
            """
        )
        row = cur.fetchone()
        return int(row[0]) if row else 0


def count_players(conn: Connection) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM players")
        row = cur.fetchone()
        return int(row[0]) if row else 0


def get_players_with_reports(conn: Connection) -> list[dict[str, Any]]:
    """Jugadores con al menos un informe subjetivo."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_PLAYER_SELECT}
            FROM players p
            WHERE {sql_player_has_subjective_report("p")}
            ORDER BY p.full_name ASC
            """
        )
        return list(cur.fetchall())


def get_players_objective_only(conn: Connection, *, season: str | None = None) -> list[dict[str, Any]]:
    """Jugadores con métricas objetivas pero sin informes subjetivos."""
    season_clause = ""
    params: list[Any] = []
    if season is not None and str(season).strip():
        season_clause = " AND om.season IS NOT DISTINCT FROM %s"
        params.append(str(season).strip())
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_PLAYER_SELECT}
            FROM players p
            WHERE NOT ({sql_player_has_subjective_report("p")})
              AND EXISTS (
                  SELECT 1 FROM objective_metrics om
                  WHERE om.player_id = p.id
                  {season_clause}
              )
            ORDER BY p.full_name ASC
            """,
            params,
        )
        return list(cur.fetchall())


def get_players_with_reports_and_objective_status(conn: Connection) -> list[dict[str, Any]]:
    """Jugadores con informes + flags de métricas objetivas y conteos."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT
                {_PLAYER_SELECT},
                (SELECT COUNT(*)::int FROM scouting_reports sr WHERE sr.player_id = p.id) AS reports_count,
                (SELECT COUNT(*)::int FROM objective_metrics om WHERE om.player_id = p.id) AS objective_metrics_count,
                EXISTS (SELECT 1 FROM objective_metrics om WHERE om.player_id = p.id) AS has_objective_metrics
            FROM players p
            WHERE {sql_player_has_subjective_report("p")}
            ORDER BY p.full_name ASC
            """
        )
        return list(cur.fetchall())


def get_all_players(conn: Connection) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_PLAYER_SELECT}
            FROM players
            ORDER BY full_name ASC
            """
        )
        return list(cur.fetchall())


def get_player_by_id(conn: Connection, player_id: int) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_PLAYER_SELECT}
            FROM players
            WHERE id = %s
            """,
            (player_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def find_player_by_normalized_name(conn: Connection, normalized_name: str) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_PLAYER_SELECT}
            FROM players
            WHERE normalized_name = %s
            """,
            (normalized_name,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def create_player(
    conn: Connection,
    full_name: str,
    normalized_name: str,
    birth_date: date | None = None,
    nationality: str | None = None,
    position: str | None = None,
    current_team: str | None = None,
    preferred_foot: str | None = None,
    height_cm: Decimal | float | None = None,
    image_path: str | None = None,
    commit: bool = True,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO players (
                full_name, normalized_name, birth_date, nationality, position, current_team,
                preferred_foot, height_cm, image_path
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                full_name,
                normalized_name,
                birth_date,
                nationality,
                position,
                current_team,
                preferred_foot,
                height_cm,
                image_path,
            ),
        )
        row = cur.fetchone()
        if commit:
            conn.commit()
        return int(row[0])


def merge_player_empty_fields(
    conn: Connection,
    player_id: int,
    *,
    birth_date: date | None = None,
    preferred_foot: str | None = None,
    height_cm: Decimal | float | None = None,
    nationality: str | None = None,
    position: str | None = None,
    current_team: str | None = None,
    commit: bool = True,
) -> None:
    """
    Actualiza solo columnas que están NULL en BD y reciben valor no vacío.
    No sobrescribe datos ya guardados.
    """
    row = get_player_by_id(conn, player_id)
    if not row:
        return

    sets: list[str] = []
    params: list[Any] = []

    def add(col: str, current: Any, new_val: Any) -> None:
        if current is not None:
            return
        if new_val is None:
            return
        if isinstance(new_val, str) and not new_val.strip():
            return
        sets.append(f"{col} = %s")
        params.append(new_val.strip() if isinstance(new_val, str) else new_val)

    add("birth_date", row.get("birth_date"), birth_date)
    add("preferred_foot", row.get("preferred_foot"), preferred_foot)
    add("height_cm", row.get("height_cm"), height_cm)
    add("nationality", row.get("nationality"), nationality)
    add("position", row.get("position"), position)
    add("current_team", row.get("current_team"), current_team)

    if not sets:
        return

    params.append(player_id)
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE players SET {', '.join(sets)} WHERE id = %s",
            params,
        )
    if commit:
        conn.commit()


def update_player_image_path(conn: Connection, player_id: int, image_path: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE players SET image_path = %s WHERE id = %s",
            (image_path, player_id),
        )
    conn.commit()


def get_or_create_player(
    conn: Connection,
    full_name: str,
    birth_date: date | None = None,
    nationality: str | None = None,
    position: str | None = None,
    current_team: str | None = None,
    preferred_foot: str | None = None,
    height_cm: Decimal | float | None = None,
    image_path: str | None = None,
    commit: bool = True,
) -> tuple[int, bool]:
    """
    Return (player_id, created) where created is True if a new row was inserted.
    """
    normalized = normalize_player_name(full_name)
    if not normalized:
        raise ValueError("full_name is empty after normalization")

    existing = find_player_by_normalized_name(conn, normalized)
    if existing:
        return int(existing["id"]), False

    try:
        pid = create_player(
            conn,
            full_name=str(full_name).strip(),
            normalized_name=normalized,
            birth_date=birth_date,
            nationality=nationality,
            position=position,
            current_team=current_team,
            preferred_foot=preferred_foot,
            height_cm=height_cm,
            image_path=image_path,
            commit=commit,
        )
        return pid, True
    except UniqueViolation:
        if not commit:
            raise
        conn.rollback()
        again = find_player_by_normalized_name(conn, normalized)
        if again:
            return int(again["id"]), False
        raise
