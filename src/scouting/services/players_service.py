"""Player-related helpers (normalization and thin orchestration for the UI)."""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Any

from psycopg import Connection


def normalize_player_name(name: str) -> str:
    """Lowercase, trim, collapse spaces, remove accents."""
    if name is None:
        return ""
    s = str(name).strip().lower()
    if not s:
        return ""
    s = re.sub(r"\s+", " ", s)
    decomposed = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def calculate_age(birth_date: date | None, reference_date: date | None = None) -> int | None:
    """
    Edad en años cumplidos respecto a reference_date (hoy por defecto).
    Devuelve None si no hay fecha de nacimiento o la fecha es posterior al referencia.
    """
    if birth_date is None:
        return None
    ref = reference_date or date.today()
    if birth_date > ref:
        return None
    age = ref.year - birth_date.year
    if (ref.month, ref.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def list_players(conn: Connection) -> list[dict[str, Any]]:
    from scouting.repositories import players_repository

    return players_repository.get_all_players(conn)


def list_players_for_lookup(
    conn: Connection,
    *,
    include_objective_only: bool = False,
) -> list[dict[str, Any]]:
    """
    Lista para Consultar jugador: por defecto solo jugadores con informes subjetivos.
    Con include_objective_only=True añade jugadores solo con datos objetivos (sin informes).
    """
    from scouting.config.sofascore_seasons import get_active_season
    from scouting.repositories import players_repository

    scouted = players_repository.get_players_with_reports(conn)
    if not include_objective_only:
        return scouted
    objective_only = players_repository.get_players_objective_only(
        conn, season=get_active_season()
    )
    seen = {int(p["id"]) for p in scouted}
    merged = list(scouted)
    for p in objective_only:
        pid = int(p["id"])
        if pid not in seen:
            merged.append(p)
            seen.add(pid)
    merged.sort(key=lambda r: (str(r.get("full_name") or "")).lower())
    return merged


def get_player_objective_data_status(conn: Connection, player_id: int) -> dict[str, Any]:
    """
    Estado de vinculación subjetivo/objetivo para un players.id (sin matching por nombre).
    """
    from scouting.repositories import (
        metrics_repository,
        player_external_ids_repository,
        reports_repository,
    )

    reports = reports_repository.get_reports_by_player(conn, player_id)
    reports_count = len(reports)
    has_reports = reports_count > 0

    objective_metrics_count = metrics_repository.count_metrics_by_player(conn, player_id)
    has_objective_metrics = objective_metrics_count > 0

    providers = metrics_repository.get_sources_by_player(conn, player_id)
    external_rows = player_external_ids_repository.get_external_ids_by_player(conn, player_id)
    external_ids = [
        {
            "provider": r.get("provider"),
            "external_id": r.get("external_id"),
            "external_name": r.get("external_name"),
        }
        for r in external_rows
    ]

    origin = derive_player_origin(
        has_subjective_reports=has_reports,
        has_objective_metrics=has_objective_metrics,
    )

    return {
        "has_reports": has_reports,
        "reports_count": reports_count,
        "has_objective_metrics": has_objective_metrics,
        "objective_metrics_count": objective_metrics_count,
        "providers": providers,
        "external_ids": external_ids,
        "origin": origin,
    }


def origin_badge_label(origin: str) -> str:
    labels = {
        "subjective_only": "Scouting manual",
        "objective_only": "Solo datos objetivos",
        "hybrid": "Perfil híbrido",
        "unknown": "Sin datos vinculados",
    }
    return labels.get(origin, origin)


def fetch_player(conn: Connection, player_id: int) -> dict[str, Any] | None:
    from scouting.repositories import players_repository

    return players_repository.get_player_by_id(conn, player_id)


def fetch_reports_for_player(conn: Connection, player_id: int) -> list[dict[str, Any]]:
    from scouting.repositories import reports_repository

    return reports_repository.get_reports_by_player(conn, player_id)


def fetch_metrics_for_player(conn: Connection, player_id: int) -> list[dict[str, Any]]:
    from scouting.repositories import metrics_repository

    return metrics_repository.get_metrics_by_player(conn, player_id)


def count_players(conn: Connection) -> int:
    from scouting.repositories import players_repository

    return players_repository.count_players(conn)


def count_players_with_subjective_reports(conn: Connection) -> int:
    from scouting.repositories import players_repository

    return players_repository.count_players_with_subjective_reports(conn)


def derive_player_origin(*, has_subjective_reports: bool, has_objective_metrics: bool) -> str:
    """
    Origen derivado para UI (sin columna en BD).
    subjective_only | objective_only | hybrid
    """
    if has_subjective_reports and has_objective_metrics:
        return "hybrid"
    if has_subjective_reports:
        return "subjective_only"
    if has_objective_metrics:
        return "objective_only"
    return "unknown"


def update_player_image_path(conn: Connection, player_id: int, image_path: str) -> None:
    from scouting.repositories import players_repository

    players_repository.update_player_image_path(conn, player_id, image_path)
