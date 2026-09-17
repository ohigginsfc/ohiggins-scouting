"""CLI: import Sofascore player_stats.csv (wide) into PostgreSQL objective_metrics."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import pandas as pd

from scouting.db import get_connection
from scouting.repositories import (
    import_batches_repository,
    metrics_repository,
    player_external_ids_repository,
    players_repository,
)
from scouting.services.players_service import normalize_player_name
from scouting.services.sofascore_import_service import (
    PROVIDER,
    SOURCE_NAME,
    build_player_profile_updates,
    convert_row_to_metrics,
    load_teams_lookup,
)


def _resolve_player_id(
    conn,
    row: pd.Series,
    *,
    stats: dict[str, Any],
    teams_lookup: dict[str, str] | None = None,
) -> tuple[int, bool]:
    """
    Matching: external_id → normalized_name → create.
    Returns (player_id, created).
    """
    ext_raw = row.get("player_id")
    if ext_raw is None or (isinstance(ext_raw, float) and pd.isna(ext_raw)):
        raise ValueError("player_id (Sofascore) is empty")

    external_id = str(int(ext_raw)) if isinstance(ext_raw, (int, float)) else str(ext_raw).strip()
    player_name = str(row.get("player_name") or "").strip()
    if not player_name:
        raise ValueError("player_name is empty")

    link = player_external_ids_repository.find_player_by_external_id(conn, PROVIDER, external_id)
    if link:
        stats["players_matched_external"] = stats.get("players_matched_external", 0) + 1
        return int(link["player_id"]), False

    normalized = normalize_player_name(player_name)
    existing = players_repository.find_player_by_normalized_name(conn, normalized)
    if existing:
        pid = int(existing["id"])
        stats["players_matched_name"] = stats.get("players_matched_name", 0) + 1
        player_external_ids_repository.create_or_update_external_id(
            conn, pid, PROVIDER, external_id, external_name=player_name
        )
        return pid, False

    profile = build_player_profile_updates(row)
    pid, created = players_repository.get_or_create_player(
        conn,
        full_name=player_name,
        birth_date=profile.get("birth_date"),
        nationality=profile.get("nationality"),
        preferred_foot=profile.get("preferred_foot"),
        height_cm=profile.get("height_cm"),
    )
    if created:
        stats["players_created"] = stats.get("players_created", 0) + 1
    else:
        stats["players_reused"] = stats.get("players_reused", 0) + 1

    player_external_ids_repository.create_or_update_external_id(
        conn, pid, PROVIDER, external_id, external_name=player_name
    )
    return pid, created


def _apply_profile_merge(
    conn,
    player_id: int,
    row: pd.Series,
    *,
    teams_lookup: dict[str, str] | None = None,
) -> None:
    profile = build_player_profile_updates(row)
    players_repository.merge_player_empty_fields(
        conn,
        player_id,
        birth_date=profile.get("birth_date"),
        preferred_foot=profile.get("preferred_foot"),
        height_cm=profile.get("height_cm"),
        nationality=profile.get("nationality"),
    )


def _replace_previous_data(
    conn,
    *,
    batch_id: UUID,
    country: str,
    division: str,
    season: str,
    competition: str,
) -> None:
    import_batches_repository.mark_previous_batches_replaced(
        conn,
        provider=PROVIDER,
        country=country,
        division=division,
        season=season,
        current_batch_id=batch_id,
    )
    old_ids = import_batches_repository.list_batch_ids_for_scope(
        conn,
        provider=PROVIDER,
        country=country,
        division=division,
        season=season,
        exclude_batch_id=batch_id,
    )
    metrics_repository.delete_metrics_by_batch_ids(conn, old_ids)
    metrics_repository.delete_metrics_by_source_scope(
        conn,
        source_name=SOURCE_NAME,
        season=season,
        competition=competition,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Sofascore player_stats.csv into PostgreSQL.")
    parser.add_argument("csv_path", help="Path to player_stats.csv")
    parser.add_argument("--country", required=True)
    parser.add_argument("--division", required=True)
    parser.add_argument("--season", required=True)
    parser.add_argument("--competition", required=True)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace previous Sofascore metrics for this country/division/season",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    if not csv_path.is_file():
        print(f"ERROR: file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: could not read CSV: {exc}", file=sys.stderr)
        sys.exit(1)

    country = args.country.strip().lower()
    division = args.division.strip().lower()
    season = str(args.season).strip()
    competition = str(args.competition).strip()
    teams_lookup = load_teams_lookup(csv_path)

    run_stats: dict[str, Any] = {
        "rows_total": len(df),
        "players_created": 0,
        "players_reused": 0,
        "players_matched_external": 0,
        "players_matched_name": 0,
        "metrics_inserted": 0,
        "row_errors": [],
    }

    with get_connection() as conn:
        batch_id = import_batches_repository.create_import_batch(
            conn,
            provider=PROVIDER,
            country=country,
            division=division,
            competition=competition,
            season=season,
            source_file=str(csv_path.resolve()),
            scraped_at=datetime.now(timezone.utc),
        )

        try:
            if args.replace:
                _replace_previous_data(
                    conn,
                    batch_id=batch_id,
                    country=country,
                    division=division,
                    season=season,
                    competition=competition,
                )

            metric_buffer: list[dict[str, Any]] = []
            batch_size = 500

            for idx, row in df.iterrows():
                label = f"row index {idx}"
                try:
                    player_id, _ = _resolve_player_id(
                        conn, row, stats=run_stats, teams_lookup=teams_lookup
                    )
                    _apply_profile_merge(
                        conn, player_id, row, teams_lookup=teams_lookup
                    )

                    for metric in convert_row_to_metrics(
                        row,
                        season=season,
                        competition=competition,
                        teams_lookup=teams_lookup,
                    ):
                        metric["player_id"] = player_id
                        metric["import_batch_id"] = batch_id
                        metric["source_type"] = "sofascore"
                        metric_buffer.append(metric)

                    if len(metric_buffer) >= batch_size:
                        n = metrics_repository.create_metrics_batch(conn, metric_buffer)
                        run_stats["metrics_inserted"] += n
                        metric_buffer.clear()

                except Exception as exc:  # noqa: BLE001
                    run_stats["row_errors"].append(f"{label}: {exc}")

            if metric_buffer:
                n = metrics_repository.create_metrics_batch(conn, metric_buffer)
                run_stats["metrics_inserted"] += n

            import_batches_repository.complete_import_batch(conn, batch_id, run_stats)

        except Exception as exc:  # noqa: BLE001
            import_batches_repository.fail_import_batch(conn, batch_id, {"error": str(exc), **run_stats})
            raise

    print(f"Import batch: {batch_id}")
    print(f"Rows in CSV: {run_stats['rows_total']}")
    print(f"Metrics inserted: {run_stats['metrics_inserted']}")
    print(f"Players created: {run_stats['players_created']}")
    print(f"Matched by external_id: {run_stats['players_matched_external']}")
    print(f"Matched by name: {run_stats['players_matched_name']}")
    if run_stats["row_errors"]:
        print("Row errors:")
        for err in run_stats["row_errors"][:20]:
            print(f"  - {err}")
        if len(run_stats["row_errors"]) > 20:
            print(f"  ... and {len(run_stats['row_errors']) - 20} more")
        sys.exit(2)


if __name__ == "__main__":
    main()
