"""Lógica de valoraciones por atributo ligadas a informes."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from psycopg import Connection

from scouting.config.attribute_rating_scale import RATING_DEFAULT, RATING_MAX
from scouting.repositories import attribute_ratings_repository
from scouting.services import templates_service
from scouting.templates.position_templates import resolve_template_key_for_position


def replace_attribute_ratings_for_report(
    conn: Connection,
    report_id: int,
    ratings: list[dict[str, Any]],
    default_max_rating: float = RATING_MAX,
) -> int:
    """Borra valoraciones previas del informe e inserta las nuevas (carga idempotente)."""
    attribute_ratings_repository.delete_attribute_ratings_by_report(conn, report_id)
    return save_attribute_ratings_for_report(
        conn, report_id, ratings, default_max_rating=default_max_rating
    )


def save_attribute_ratings_for_report(
    conn: Connection,
    report_id: int,
    ratings: list[dict[str, Any]],
    default_max_rating: float = RATING_MAX,
) -> int:
    """
    Inserta todas las valoraciones para un informe.

    Cada elemento de `ratings` puede incluir:
    attribute_group, attribute_name, rating, max_rating (opcional), notes (opcional).
    Devuelve el número de filas insertadas.
    """
    inserted = 0
    for row in ratings:
        group = row.get("attribute_group")
        name = row.get("attribute_name")
        rating = row.get("rating")
        if not group or not name or rating is None:
            continue
        max_r = float(row.get("max_rating") or default_max_rating)
        attribute_ratings_repository.create_attribute_rating(
            conn,
            report_id=report_id,
            attribute_group=str(group).strip(),
            attribute_name=str(name).strip(),
            rating=float(rating),
            max_rating=max_r,
            notes=row.get("notes"),
        )
        inserted += 1
    return inserted


def get_report_attribute_ratings(conn: Connection, report_id: int) -> list[dict[str, Any]]:
    return attribute_ratings_repository.get_attribute_ratings_by_report(conn, report_id)


def get_player_attribute_summary(conn: Connection, player_id: int) -> list[dict[str, Any]]:
    return attribute_ratings_repository.get_average_attribute_ratings_by_player(conn, player_id)


def get_position_attribute_benchmark(
    conn: Connection,
    position: str,
    player_id: int,
) -> list[dict[str, Any]]:
    """
    Cruza la media del jugador con la media de informes de jugadores con la misma plantilla
    (p. ej. Lateral izquierdo y Lateral derecho → plantilla Lateral).

    Devuelve filas con attribute_group, attribute_name, player_avg_rating, position_avg_rating, difference.
    """
    if not position or not str(position).strip():
        return []

    player_rows = attribute_ratings_repository.get_average_attribute_ratings_by_player(conn, player_id)
    try:
        template_key = resolve_template_key_for_position(position.strip())
        cohort_positions = templates_service.positions_for_template_key(template_key)
    except KeyError:
        cohort_positions = [position.strip()]
    pos_rows = attribute_ratings_repository.get_average_attribute_ratings_by_positions(
        conn, cohort_positions, exclude_player_id=player_id
    )

    def key(r: dict[str, Any]) -> tuple[str, str]:
        return (str(r["attribute_group"]), str(r["attribute_name"]))

    pos_map: dict[tuple[str, str], Decimal] = {}
    for r in pos_rows:
        avg = r.get("avg_rating")
        if avg is None:
            continue
        pos_map[key(r)] = Decimal(str(avg))

    out: list[dict[str, Any]] = []
    for r in player_rows:
        k = key(r)
        pavg = r.get("avg_rating")
        if pavg is None:
            continue
        p_dec = Decimal(str(pavg))
        pos_avg = pos_map.get(k)
        if pos_avg is None:
            continue
        out.append(
            {
                "attribute_group": r["attribute_group"],
                "attribute_name": r["attribute_name"],
                "player_avg_rating": float(p_dec),
                "position_avg_rating": float(pos_avg),
                "difference": float(p_dec - pos_avg),
            }
        )
    return templates_service.sort_attributes_by_position_template(position.strip(), out)


def audit_template_benchmark(
    conn: Connection,
    position: str,
    exclude_player_id: int | None = None,
) -> list[dict[str, Any]]:
    """
    Auditoría temporal de «Media plantilla»: estadísticas por atributo.
    Los atributos ausentes en un informe no entran en AVG (solo filas en report_attribute_ratings).
    """
    if not position or not str(position).strip():
        return []
    try:
        template_key = resolve_template_key_for_position(position.strip())
        cohort_positions = templates_service.positions_for_template_key(template_key)
    except KeyError:
        template_key = position.strip()
        cohort_positions = [position.strip()]

    raw = attribute_ratings_repository.audit_template_benchmark_stats(
        conn, cohort_positions, exclude_player_id=exclude_player_id
    )
    out: list[dict[str, Any]] = []
    for r in raw:
        total_reports = int(r.get("total_reports") or 0)
        reports_count = int(r.get("reports_count") or 0)
        coverage = round(100.0 * reports_count / total_reports, 1) if total_reports else None
        avg = r.get("avg_rating")
        zero_n = int(r.get("zero_ratings") or 0)
        out.append(
            {
                "template_key": template_key,
                "attribute_group": r["attribute_group"],
                "attribute_name": r["attribute_name"],
                "avg_rating": round(float(avg), 3) if avg is not None else None,
                "min_rating": round(float(r["min_rating"]), 3) if r.get("min_rating") is not None else None,
                "max_rating": round(float(r["max_rating"]), 3) if r.get("max_rating") is not None else None,
                "stddev_rating": round(float(r["stddev_rating"]), 3)
                if r.get("stddev_rating") is not None
                else None,
                "reports_count": reports_count,
                "players_count": int(r.get("players_count") or 0),
                "total_cohort_reports": total_reports,
                "coverage_pct": coverage,
                "zero_ratings": zero_n,
                "notes": (
                    f"{zero_n} valoración(es) = 0 (valor real, no imputación por ausencia)"
                    if zero_n
                    else "Sin ceros explícitos"
                ),
            }
        )
    return out
