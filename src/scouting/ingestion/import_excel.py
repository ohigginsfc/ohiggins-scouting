"""CLI: import subjective reports from an Excel file into PostgreSQL."""

from __future__ import annotations

import argparse
import sys
from typing import Any

import pandas as pd

from scouting.db import get_connection
from scouting.services.reports_service import create_scouting_report_from_dict

REQUIRED_COLUMNS = [
    "player_name",
    "scout_name",
    "report_date",
    "position_observed",
    "summary",
    "strengths",
    "weaknesses",
    "recommendation",
    "rating",
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


def _parse_report_date(row: pd.Series) -> Any:
    raw = _cell(row, "report_date")
    if raw is None:
        return None
    ts = pd.to_datetime(row["report_date"], errors="coerce")
    if pd.isna(ts):
        return None
    return ts.to_pydatetime()


def _parse_minutes(row: pd.Series) -> int | None:
    raw = row.get("minutes_observed") if "minutes_observed" in row.index else None
    if raw is None or pd.isna(raw):
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Import scouting reports from Excel (.xlsx).")
    parser.add_argument("excel_path", help="Path to the Excel file")
    args = parser.parse_args()

    try:
        df = pd.read_excel(args.excel_path, engine="openpyxl")
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: could not read Excel file: {exc}", file=sys.stderr)
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

    reports_imported = 0
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
                    "source_type": "excel",
                    "source_name": _cell(row, "source_name"),
                    "scout_name": _cell(row, "scout_name"),
                    "report_date": _parse_report_date(row),
                    "competition": _cell(row, "competition"),
                    "match_observed": _cell(row, "match_observed"),
                    "position_observed": _cell(row, "position_observed"),
                    "minutes_observed": _parse_minutes(row),
                    "summary": _cell(row, "summary"),
                    "strengths": _cell(row, "strengths"),
                    "weaknesses": _cell(row, "weaknesses"),
                    "recommendation": _cell(row, "recommendation"),
                    "rating": _cell(row, "rating"),
                    "nationality": _cell(row, "nationality"),
                    "position": _cell(row, "position"),
                    "current_team": _cell(row, "current_team"),
                    "birth_date": _cell(row, "birth_date"),
                    "preferred_foot": _cell(row, "preferred_foot"),
                    "height_cm": _cell(row, "height_cm"),
                    "video_url": _cell(row, "video_url"),
                    "raw_payload": _series_to_payload(row),
                }

                _report_id, created_player, _player_id = create_scouting_report_from_dict(conn, payload)
                reports_imported += 1
                if created_player:
                    players_created += 1
                else:
                    players_reused += 1
            except Exception as exc:  # noqa: BLE001
                row_errors.append(f"{label}: {exc}")

    print(f"Reports imported: {reports_imported}")
    print(f"Players created: {players_created}")
    print(f"Players reused: {players_reused}")
    if row_errors:
        print("Row errors:")
        for err in row_errors:
            print(f"  - {err}")
        sys.exit(2)


if __name__ == "__main__":
    main()
