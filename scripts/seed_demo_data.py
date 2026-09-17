#!/usr/bin/env python3
"""
Carga idempotente del conjunto de demostración usado en desarrollo.

Uso:
    python scripts/seed_demo_data.py
    docker compose exec app python scripts/seed_demo_data.py

Inserta Jason León y Marcelo Flores (informes + atributos + métricas objetivas),
pares de cohorte para percentiles/radares y jugadores O'Higgins en dos temporadas
para comparación histórica. Todo mediante INSERT/UPDATE en PostgreSQL.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = Path(__file__).resolve().parent
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from demo_seed_payload import DEMO_SEED_PAYLOAD
from psycopg.types.json import Json

from scouting.db import get_connection
from scouting.repositories import player_external_ids_repository, players_repository
from scouting.services import attribute_ratings_service, reports_service
from scouting.services.sofascore_import_service import PROVIDER, SOURCE_NAME

SOFASCORE_PROVIDER = PROVIDER
OBJECTIVE_SOURCE = SOURCE_NAME
DEMO_COMPETITION = DEMO_SEED_PAYLOAD["competition"]


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _ensure_player(conn, spec: dict[str, Any]) -> tuple[int, bool]:
    pid, created = players_repository.get_or_create_player(
        conn,
        full_name=spec["full_name"],
        birth_date=_parse_date(spec.get("birth_date")),
        nationality=spec.get("nationality"),
        position=spec.get("position"),
        current_team=spec.get("current_team"),
        preferred_foot=spec.get("preferred_foot"),
        height_cm=spec.get("height_cm"),
        image_path=spec.get("image_path"),
    )
    if not created:
        players_repository.merge_player_empty_fields(
            conn,
            pid,
            birth_date=_parse_date(spec.get("birth_date")),
            nationality=spec.get("nationality"),
            position=spec.get("position"),
            current_team=spec.get("current_team"),
            preferred_foot=spec.get("preferred_foot"),
            height_cm=spec.get("height_cm"),
        )
        if spec.get("image_path"):
            row = players_repository.get_player_by_id(conn, pid)
            if row and not row.get("image_path"):
                players_repository.update_player_image_path(conn, pid, spec["image_path"])
    return pid, created


def _upsert_report(conn, player_id: int, spec: dict[str, Any]) -> tuple[int, str]:
    report = spec["report"]
    report_date = _parse_date(report["report_date"])
    if report_date is None:
        raise ValueError(f"report_date inválida para {spec['full_name']}")

    raw_payload = {
        "loader": "scripts/seed_demo_data.py",
        "player": {
            k: spec.get(k)
            for k in (
                "full_name",
                "birth_date",
                "nationality",
                "position",
                "current_team",
                "preferred_foot",
                "height_cm",
                "image_path",
            )
            if spec.get(k) is not None
        },
        "report": report,
        "attribute_ratings": spec.get("attributes"),
    }

    payload = {
        "player_name": spec["full_name"],
        "birth_date": _parse_date(spec.get("birth_date")),
        "nationality": spec.get("nationality"),
        "position": spec.get("position"),
        "current_team": spec.get("current_team"),
        "preferred_foot": spec.get("preferred_foot"),
        "height_cm": spec.get("height_cm"),
        "source_type": report["source_type"],
        "source_name": report["source_name"],
        "scout_name": report.get("scout_name"),
        "report_date": report_date,
        "position_observed": report.get("position_observed"),
        "alternative_positions": report.get("alternative_positions"),
        "summary": report.get("summary"),
        "strengths": report.get("strengths"),
        "weaknesses": report.get("weaknesses"),
        "recommendation": report.get("recommendation"),
        "rating": report.get("rating"),
        "video_url": report.get("video_url"),
        "raw_payload": raw_payload,
    }

    report_id, _, _, action, _ = reports_service.upsert_scouting_report_from_dict(conn, payload)
    attribute_ratings_service.replace_attribute_ratings_for_report(conn, report_id, spec["attributes"])
    return report_id, action


def _upsert_external_id(conn, player_id: int, external_id: str, external_name: str) -> None:
    player_external_ids_repository.create_or_update_external_id(
        conn,
        player_id,
        SOFASCORE_PROVIDER,
        external_id,
        external_name,
    )


def _upsert_objective_metrics(
    conn,
    player_id: int,
    metrics_by_season: dict[str, list[dict[str, Any]]],
) -> int:
    inserted = 0
    with conn.cursor() as cur:
        for season, metrics in metrics_by_season.items():
            for metric in metrics:
                name = metric["metric_name"]
                cur.execute(
                    """
                    SELECT id FROM objective_metrics
                    WHERE player_id = %s
                      AND source_name = %s
                      AND season IS NOT DISTINCT FROM %s
                      AND competition IS NOT DISTINCT FROM %s
                      AND metric_name = %s
                      AND (
                        source_type = 'demo'
                        OR (
                            source_type IS NULL
                            AND import_batch_id IS NULL
                        )
                      )
                    LIMIT 1
                    """,
                    (player_id, OBJECTIVE_SOURCE, season, DEMO_COMPETITION, name),
                )
                row = cur.fetchone()
                value = metric.get("metric_value")
                dec_value = Decimal(str(value)) if value is not None else None
                unit = metric.get("metric_unit")
                payload = metric.get("raw_payload") or {}
                if isinstance(payload, dict):
                    payload = {**payload, "source": "demo", "loader": "scripts/seed_demo_data.py"}
                if row:
                    cur.execute(
                        """
                        UPDATE objective_metrics
                        SET metric_value = %s, metric_unit = %s, raw_payload = %s,
                            source_type = 'demo'
                        WHERE id = %s
                        """,
                        (dec_value, unit, Json(payload), int(row[0])),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO objective_metrics (
                            player_id, source_name, season, competition,
                            metric_name, metric_value, metric_unit, raw_payload, source_type
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            player_id,
                            OBJECTIVE_SOURCE,
                            season,
                            DEMO_COMPETITION,
                            name,
                            dec_value,
                            unit,
                            Json(payload),
                            "demo",
                        ),
                    )
                    inserted += 1
    conn.commit()
    return inserted


def _seed_player_bundle(
    conn,
    spec: dict[str, Any],
    *,
    with_report: bool,
    stats: dict[str, int],
) -> int:
    pid, created = _ensure_player(conn, spec)
    if created:
        stats["players_created"] += 1

    if with_report and spec.get("report") and spec.get("attributes"):
        _, action = _upsert_report(conn, pid, spec)
        if action == "created":
            stats["reports_created"] += 1
        else:
            stats["reports_updated"] += 1

    if spec.get("external_id"):
        _upsert_external_id(conn, pid, str(spec["external_id"]), spec["full_name"])

    if spec.get("objective_metrics"):
        stats["metrics_inserted"] += _upsert_objective_metrics(conn, pid, spec["objective_metrics"])

    return pid


def seed_demo_data(*, dry_run: bool = False) -> dict[str, int]:
    stats = {
        "players_created": 0,
        "reports_created": 0,
        "reports_updated": 0,
        "metrics_inserted": 0,
        "demo_players": len(DEMO_SEED_PAYLOAD["demo_players"]),
        "cohort_players": len(DEMO_SEED_PAYLOAD["cohort_players"]),
        "ohiggins_players": len(DEMO_SEED_PAYLOAD["ohiggins_season_players"]),
    }

    if dry_run:
        print("DRY RUN — no se escribirá en la base de datos")
        print(f"  Jugadores principales: {stats['demo_players']}")
        print(f"  Cohortes objetivas: {stats['cohort_players']}")
        print(f"  O'Higgins (2 temporadas): {stats['ohiggins_players']}")
        return stats

    with get_connection() as conn:
        for spec in DEMO_SEED_PAYLOAD["demo_players"]:
            _seed_player_bundle(conn, spec, with_report=True, stats=stats)

        for spec in DEMO_SEED_PAYLOAD["cohort_players"]:
            _seed_player_bundle(conn, spec, with_report=False, stats=stats)

        for spec in DEMO_SEED_PAYLOAD["ohiggins_season_players"]:
            _seed_player_bundle(conn, spec, with_report=False, stats=stats)

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed demo data (Jason León / Marcelo Flores + cohortes).")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without writing")
    args = parser.parse_args()

    print("Scouting Platform — seed demo data")
    print(f"  Competición objetiva: {DEMO_COMPETITION}")
    print(f"  Fuente objetivos: {OBJECTIVE_SOURCE}\n")

    stats = seed_demo_data(dry_run=args.dry_run)
    if args.dry_run:
        return 0

    print("Resultado:")
    print(f"  Jugadores nuevos: {stats['players_created']}")
    print(f"  Informes creados: {stats['reports_created']}")
    print(f"  Informes actualizados: {stats['reports_updated']}")
    print(f"  Métricas objetivas insertadas (nuevas): {stats['metrics_inserted']}")
    print("\nPrueba en http://localhost:8501")
    print("  Consultar jugador → Jason León / Marcelo Flores")
    print("  Comparación → laterales izquierdos")
    print("  Comparación por temporadas → jugadores O'Higgins")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
