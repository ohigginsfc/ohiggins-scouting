"""CLI: import Sofascore player_stats.csv (wide) into PostgreSQL objective_metrics."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import pandas as pd
from psycopg.pq import TransactionStatus

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
            conn, pid, PROVIDER, external_id, external_name=player_name, commit=False
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
        commit=False,
    )
    if created:
        stats["players_created"] = stats.get("players_created", 0) + 1
    else:
        stats["players_reused"] = stats.get("players_reused", 0) + 1

    player_external_ids_repository.create_or_update_external_id(
        conn, pid, PROVIDER, external_id, external_name=player_name, commit=False
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
        commit=False,
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
        competition=competition,
        commit=False,
    )
    old_ids = import_batches_repository.list_batch_ids_for_scope(
        conn,
        provider=PROVIDER,
        country=country,
        division=division,
        season=season,
        exclude_batch_id=batch_id,
        competition=competition,
    )
    metrics_repository.delete_metrics_by_batch_ids(conn, old_ids, commit=False)


def import_dataframe(
    conn, df: pd.DataFrame, *, country: str, division: str, season: str,
    competition: str, source_file: str, replace: bool = False,
    teams_lookup: dict[str, str] | None = None,
    publication_hook=None,
) -> tuple[UUID, dict[str, Any]]:
    """Publish the complete CSV atomically; retain the previous version on any error.

    Requires a fresh connection with no caller-owned transaction. The running/failed
    batch record is durable, but all player, identity and metric changes roll back.
    """
    if conn.info.transaction_status != TransactionStatus.IDLE:
        raise ValueError("Import requires a connection without an active transaction")
    if df.empty:
        raise ValueError("Empty CSV cannot replace a published version")
    if not all(str(x).strip() for x in (country, division, season, competition)):
        raise ValueError("Import scope must be complete")
    run_stats: dict[str, Any] = {
        "rows_total": len(df),
        "players_created": 0,
        "players_reused": 0,
        "players_matched_external": 0,
        "players_matched_name": 0,
        "metrics_inserted": 0,
        "row_errors": [],
    }

    batch_id = import_batches_repository.create_import_batch(
        conn, provider=PROVIDER, country=country, division=division,
        competition=competition, season=season, source_file=source_file,
        scraped_at=datetime.now(timezone.utc),
    )
    try:
        with conn.transaction():
            # Serialise publications of the same exact scope across processes.
            scope = json.dumps([PROVIDER, country, division, season, competition])
            conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (scope,))
            if replace:
                # Legacy rows cannot safely be attributed to country/division.
                legacy = conn.execute(
                    """SELECT 1 FROM objective_metrics
                       WHERE source_name = %s AND season = %s AND competition = %s
                         AND import_batch_id IS NULL AND source_type = 'sofascore'
                       LIMIT 1""", (SOURCE_NAME, season, competition),
                ).fetchone()
                if legacy:
                    raise ValueError("Unbatched Sofascore metrics require explicit reconciliation before replacement")
            metric_buffer = []
            for idx, row in df.iterrows():
                try:
                    player_id, _ = _resolve_player_id(conn, row, stats=run_stats, teams_lookup=teams_lookup)
                    _apply_profile_merge(conn, player_id, row, teams_lookup=teams_lookup)
                    metrics = convert_row_to_metrics(row, season=season, competition=competition, teams_lookup=teams_lookup)
                    if not metrics:
                        raise ValueError("Row produced no metrics")
                    for metric in metrics:
                        metric.update(player_id=player_id, import_batch_id=batch_id, source_type="sofascore")
                        metric_buffer.append(metric)
                    if len(metric_buffer) >= 500:
                        run_stats["metrics_inserted"] += metrics_repository.create_metrics_batch(conn, metric_buffer, commit=False)
                        metric_buffer.clear()
                except Exception as exc:
                    run_stats["row_errors"].append(f"row index {idx}: {type(exc).__name__}")
                    raise ValueError(f"Import aborted at row index {idx}; previous data retained") from exc
            if metric_buffer:
                run_stats["metrics_inserted"] += metrics_repository.create_metrics_batch(conn, metric_buffer, commit=False)
            if run_stats["metrics_inserted"] == 0:
                raise ValueError("CSV produced no metrics; previous data retained")
            # The candidate is complete but invisible outside this transaction.
            if replace:
                _replace_previous_data(conn, batch_id=batch_id, country=country,
                                       division=division, season=season, competition=competition)
            if publication_hook is not None:
                publication_hook(conn, batch_id)
            import_batches_repository.complete_import_batch(conn, batch_id, run_stats, commit=False)
    except Exception as exc:
        run_stats["metrics_attempted"] = run_stats["metrics_inserted"]
        run_stats["metrics_inserted"] = 0
        run_stats["rolled_back"] = True
        import_batches_repository.fail_import_batch(conn, batch_id, {"error_type": type(exc).__name__, **run_stats})
        raise
    return batch_id, run_stats


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
        help="Atomically replace previous metrics for this country/division/competition/season",
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

    with get_connection() as conn:
        batch_id, run_stats = import_dataframe(
            conn, df, country=country, division=division, season=season,
            competition=competition, source_file=str(csv_path.resolve()),
            replace=args.replace, teams_lookup=teams_lookup,
        )

    print(f"Import batch: {batch_id}")
    print(f"Rows in CSV: {run_stats['rows_total']}")
    print(f"Metrics inserted: {run_stats['metrics_inserted']}")
    print(f"Players created: {run_stats['players_created']}")
    print(f"Matched by external_id: {run_stats['players_matched_external']}")
    print(f"Matched by name: {run_stats['players_matched_name']}")



if __name__ == "__main__":
    main()
