"""Scouting report business operations."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from psycopg import Connection

from scouting.repositories import players_repository, reports_repository


def count_reports(conn: Connection, *, include_hidden: bool = False) -> int:
    return reports_repository.count_reports(conn, include_hidden=include_hidden)


def count_hidden_reports(conn: Connection) -> int:
    return reports_repository.count_hidden_reports(conn)


def fetch_recent_reports(conn: Connection, limit: int = 5) -> list[dict[str, Any]]:
    return reports_repository.get_recent_reports(conn, limit=limit)


def fetch_visible_reports(conn: Connection, limit: int = 50) -> list[dict[str, Any]]:
    return reports_repository.get_visible_reports(conn, limit=limit)


def fetch_hidden_reports(conn: Connection, limit: int = 100) -> list[dict[str, Any]]:
    return reports_repository.get_hidden_reports(conn, limit=limit)


def get_report(conn: Connection, report_id: int) -> dict[str, Any] | None:
    return reports_repository.get_report_by_id(conn, report_id)


VALID_RECOMMENDATIONS = frozenset(
    {
        "Seguir monitorizando",
        "Interesante",
        "Prioritario",
        "Descartar",
    }
)


def update_report_recommendation(conn: Connection, report_id: int, recommendation: str) -> None:
    value = str(recommendation or "").strip()
    if value not in VALID_RECOMMENDATIONS:
        raise ValueError(f"Recomendación no válida: {recommendation!r}")
    reports_repository.update_report_recommendation(conn, report_id, value)


def hide_report(conn: Connection, report_id: int, hidden_by: str | None = None) -> None:
    reports_repository.hide_report(conn, report_id, hidden_by=hidden_by)


def restore_report(conn: Connection, report_id: int) -> None:
    reports_repository.restore_report(conn, report_id)


def delete_report_permanently(conn: Connection, report_id: int) -> bool:
    """Eliminación permanente. Sin sistema de roles: cualquier sesión autenticada puede usarla."""
    return reports_repository.delete_report_permanently(conn, report_id)


def update_report(conn: Connection, report_id: int, **fields: Any) -> None:
    if "recommendation" in fields and fields["recommendation"] is not None:
        value = str(fields["recommendation"]).strip()
        if value not in VALID_RECOMMENDATIONS:
            raise ValueError(f"Recomendación no válida: {fields['recommendation']!r}")
        fields["recommendation"] = value
    reports_repository.update_report(conn, report_id, **fields)


def _to_date(value: Any) -> date | None:
    if value is None:
        return None
    if hasattr(value, "to_pydatetime"):
        try:
            value = value.to_pydatetime()
        except Exception:  # noqa: BLE001
            pass
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.strip()).date()
        except ValueError:
            return None
    return None


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        if isinstance(value, str) and not value.strip():
            return None
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        if isinstance(value, float) and value != value:  # NaN
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def create_scouting_report_from_dict(conn: Connection, data: dict[str, Any]) -> tuple[int, bool, int]:
    """
    Resolve or create the player, insert a scouting report.

    Returns (report_id, player_created, player_id) where player_created indicates a new players row.

    Expected keys include at least: player_name, source_type, and report fields used by repositories.
    """
    player_name = data.get("player_name")
    if not player_name or not str(player_name).strip():
        raise ValueError("player_name is required")

    birth_date = _to_date(data.get("birth_date"))
    preferred_foot = _optional_str(data.get("preferred_foot"))
    height_cm = _to_decimal(data.get("height_cm"))

    player_id, player_created = players_repository.get_or_create_player(
        conn,
        full_name=str(player_name).strip(),
        birth_date=birth_date,
        nationality=_optional_str(data.get("nationality")),
        position=_optional_str(data.get("position")),
        current_team=_optional_str(data.get("current_team")),
        preferred_foot=preferred_foot,
        height_cm=height_cm,
    )

    if not player_created:
        players_repository.merge_player_empty_fields(
            conn,
            player_id,
            birth_date=birth_date,
            preferred_foot=preferred_foot,
            height_cm=height_cm,
            nationality=_optional_str(data.get("nationality")),
            position=_optional_str(data.get("position")),
            current_team=_optional_str(data.get("current_team")),
        )

    source_type = str(data.get("source_type", "manual")).strip() or "manual"

    alt_raw = data.get("alternative_positions")
    alt_list: list[str] | None = None
    if alt_raw:
        if isinstance(alt_raw, (list, tuple)):
            alt_list = [str(x).strip() for x in alt_raw if str(x).strip()]
        elif isinstance(alt_raw, str) and alt_raw.strip():
            alt_list = [alt_raw.strip()]

    report_id = reports_repository.create_report(
        conn,
        player_id=player_id,
        source_type=source_type,
        source_name=data.get("source_name"),
        scout_name=data.get("scout_name"),
        report_date=_to_date(data.get("report_date")),
        competition=data.get("competition"),
        match_observed=data.get("match_observed"),
        position_observed=data.get("position_observed"),
        minutes_observed=_to_int(data.get("minutes_observed")),
        summary=data.get("summary"),
        strengths=data.get("strengths"),
        weaknesses=data.get("weaknesses"),
        recommendation=data.get("recommendation"),
        rating=_to_decimal(data.get("rating")),
        video_url=_optional_str(data.get("video_url")),
        alternative_positions=alt_list,
        raw_payload=data.get("raw_payload"),
    )
    return report_id, player_created, player_id


def upsert_scouting_report_from_dict(
    conn: Connection, data: dict[str, Any]
) -> tuple[int, bool, int, str, int]:
    """
    Crea o actualiza un informe por (player_id, source_name, report_date).

    Si existe: actualiza campos; elimina duplicados con la misma clave; action='updated'.
    Si no: inserta nuevo; action='created'.

    Returns (report_id, player_created, player_id, action, duplicate_reports_removed).
    """
    player_name = data.get("player_name")
    if not player_name or not str(player_name).strip():
        raise ValueError("player_name is required")

    report_date = _to_date(data.get("report_date"))
    if report_date is None:
        raise ValueError("report_date is required for idempotent upsert")

    source_name = _optional_str(data.get("source_name"))
    birth_date = _to_date(data.get("birth_date"))
    preferred_foot = _optional_str(data.get("preferred_foot"))
    height_cm = _to_decimal(data.get("height_cm"))

    player_id, player_created = players_repository.get_or_create_player(
        conn,
        full_name=str(player_name).strip(),
        birth_date=birth_date,
        nationality=_optional_str(data.get("nationality")),
        position=_optional_str(data.get("position")),
        current_team=_optional_str(data.get("current_team")),
        preferred_foot=preferred_foot,
        height_cm=height_cm,
    )

    if not player_created:
        players_repository.merge_player_empty_fields(
            conn,
            player_id,
            birth_date=birth_date,
            preferred_foot=preferred_foot,
            height_cm=height_cm,
            nationality=_optional_str(data.get("nationality")),
            position=_optional_str(data.get("position")),
            current_team=_optional_str(data.get("current_team")),
        )

    source_type = str(data.get("source_type", "manual")).strip() or "manual"

    alt_raw = data.get("alternative_positions")
    alt_list: list[str] | None = None
    if alt_raw:
        if isinstance(alt_raw, (list, tuple)):
            alt_list = [str(x).strip() for x in alt_raw if str(x).strip()]
        elif isinstance(alt_raw, str) and alt_raw.strip():
            alt_list = [alt_raw.strip()]

    existing = reports_repository.find_report_by_player_source_and_date(
        conn, player_id, source_name, report_date
    )

    report_fields = {
        "source_type": source_type,
        "source_name": source_name,
        "scout_name": data.get("scout_name"),
        "report_date": report_date,
        "competition": data.get("competition"),
        "match_observed": data.get("match_observed"),
        "position_observed": data.get("position_observed"),
        "minutes_observed": _to_int(data.get("minutes_observed")),
        "summary": data.get("summary"),
        "strengths": data.get("strengths"),
        "weaknesses": data.get("weaknesses"),
        "recommendation": data.get("recommendation"),
        "rating": _to_decimal(data.get("rating")),
        "video_url": _optional_str(data.get("video_url")),
        "alternative_positions": alt_list,
        "raw_payload": data.get("raw_payload"),
    }

    if existing:
        report_id = int(existing["id"])
        reports_repository.update_report(conn, report_id, **report_fields)
        removed_dupes = reports_repository.delete_duplicate_reports_same_key(
            conn, player_id, source_name, report_date, report_id
        )
        return report_id, player_created, player_id, "updated", removed_dupes

    report_id = reports_repository.create_report(conn, player_id=player_id, **report_fields)
    return report_id, player_created, player_id, "created", 0
