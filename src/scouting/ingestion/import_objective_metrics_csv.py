"""CLI: import objective metrics from a CSV file into PostgreSQL."""

from __future__ import annotations

import argparse
import sys
from typing import Any

import pandas as pd

from scouting.db import get_connection
from scouting.services.metrics_service import create_objective_metric_from_dict

REQUIRED_COLUMNS = [
    "player_name",
    "season",
    "competition",
    "source_name",
    "metric_name",
    "metric_value",
    "metric_unit",
]


def _cell(row: pd.Series, column: str) -> Any:
    if column not in row.index:
        return None
    value = row[column]
    if pd.isna(value):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


def _series_to_payload(row: pd.Series) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, val in row.items():
        key_str = str(key)
        if pd.isna(val):
            payload[key_str] = None
        elif hasattr(val, "isoformat") and not isinstance(val, (bytes, str, bool)):
            payload[key_str] = val.isoformat()
        else:
            try:
                import numpy as np

                if isinstance(val, (np.integer, np.floating)):
                    val = val.item()
                elif isinstance(val, np.bool_):
                    val = bool(val)
            except ImportError:
                pass
            payload[key_str] = val
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Import objective metrics from CSV.")
    parser.add_argument("csv_path", help="Path to the CSV file")
    args = parser.parse_args()

    try:
        df = pd.read_csv(args.csv_path)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: could not read CSV file: {exc}", file=sys.stderr)
        sys.exit(1)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        print(
            "ERROR: missing required column(s): "
            + ", ".join(missing)
            + f"\nExpected at least: {', '.join(REQUIRED_COLUMNS)}",
            file=sys.stderr,
        )
        sys.exit(1)

    metrics_imported = 0
    players_created = 0
    players_reused = 0
    row_errors: list[str] = []

    with get_connection() as conn:
        for idx, row in df.iterrows():
            label = f"row index {idx}"
            try:
                player_name = _cell(row, "player_name")
                if not player_name:
                    raise ValueError("player_name is empty")

                payload = {
                    "player_name": player_name,
                    "source_name": _cell(row, "source_name"),
                    "season": _cell(row, "season"),
                    "competition": _cell(row, "competition"),
                    "metric_name": _cell(row, "metric_name"),
                    "metric_value": _cell(row, "metric_value"),
                    "metric_unit": _cell(row, "metric_unit"),
                    "nationality": _cell(row, "nationality"),
                    "position": _cell(row, "position"),
                    "current_team": _cell(row, "current_team"),
                    "raw_payload": _series_to_payload(row),
                }

                _metric_id, created_player = create_objective_metric_from_dict(conn, payload)
                metrics_imported += 1
                if created_player:
                    players_created += 1
                else:
                    players_reused += 1
            except Exception as exc:  # noqa: BLE001
                row_errors.append(f"{label}: {exc}")

    print(f"Metrics imported: {metrics_imported}")
    print(f"Players created: {players_created}")
    print(f"Players reused: {players_reused}")
    if row_errors:
        print("Row errors:")
        for err in row_errors:
            print(f"  - {err}")
        sys.exit(2)


if __name__ == "__main__":
    main()
