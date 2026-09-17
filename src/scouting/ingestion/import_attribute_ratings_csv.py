"""CLI: import attribute star ratings from CSV into report_attribute_ratings (by player + report date)."""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from typing import Any

import pandas as pd

from scouting.db import get_connection
from scouting.config.attribute_rating_scale import RATING_MAX, RATING_MIN
from scouting.repositories import attribute_ratings_repository, players_repository, reports_repository
from scouting.services.players_service import normalize_player_name

REQUIRED_COLUMNS = [
    "player_name",
    "report_date",
    "attribute_group",
    "attribute_name",
    "rating",
    "max_rating",
    "notes",
]


def _cell(row: pd.Series, column: str) -> Any:
    if column not in row.index:
        return None
    value = row[column]
    if pd.isna(value):
        return None
    if isinstance(value, str):
        s = value.strip()
        return s or None
    return value


def _to_date(value: Any) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    return ts.to_pydatetime().date()


def _to_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import attribute ratings CSV (links rows to scouting_reports by player + report_date)."
    )
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

    ratings_imported = 0
    row_errors: list[str] = []

    grouped = df.groupby(["player_name", "report_date"], sort=False)

    with get_connection() as conn:
        for (raw_name, raw_date), grp in grouped:
            label = f"group ({raw_name!r}, {raw_date!r})"
            try:
                pname = str(raw_name).strip() if raw_name is not None and not pd.isna(raw_name) else ""
                if not pname:
                    raise ValueError("player_name is empty")

                rdate = _to_date(raw_date)
                if rdate is None:
                    raise ValueError(f"invalid report_date: {raw_date!r}")

                normalized = normalize_player_name(pname)
                player = players_repository.find_player_by_normalized_name(conn, normalized)
                if not player:
                    raise ValueError(f"player not found for name={pname!r} (normalized={normalized!r})")

                pid = int(player["id"])
                report = reports_repository.find_report_by_player_and_date(conn, pid, rdate)
                if not report:
                    raise ValueError(f"no scouting_report for player_id={pid} on {rdate}")

                rid = int(report["id"])

                parsed_rows: list[tuple[str, str, float, float, str | None]] = []
                for idx, row in grp.iterrows():
                    g = _cell(row, "attribute_group")
                    n = _cell(row, "attribute_name")
                    rt = _to_float(row.get("rating"))
                    mx_f = _to_float(row.get("max_rating"))
                    if mx_f is None:
                        mx_f = RATING_MAX
                    notes = _cell(row, "notes")
                    if not g or not n:
                        raise ValueError(f"row {idx}: attribute_group and attribute_name are required")
                    if rt is None:
                        raise ValueError(f"row {idx}: rating is required")
                    if rt < RATING_MIN or rt > mx_f or mx_f > RATING_MAX + 1e-6:
                        raise ValueError(
                            f"row {idx}: invalid rating bounds (rating={rt}, max_rating={mx_f}); "
                            f"expected {RATING_MIN}-{RATING_MAX}"
                        )
                    parsed_rows.append((str(g), str(n), rt, mx_f, notes))

                attribute_ratings_repository.delete_attribute_ratings_by_report(conn, rid)

                for g, n, rt, mx, notes in parsed_rows:
                    attribute_ratings_repository.create_attribute_rating(
                        conn,
                        report_id=rid,
                        attribute_group=g,
                        attribute_name=n,
                        rating=rt,
                        max_rating=mx,
                        notes=notes,
                    )
                    ratings_imported += 1
            except Exception as exc:  # noqa: BLE001
                row_errors.append(f"{label}: {exc}")

    print(f"Ratings imported: {ratings_imported}")
    print(f"Row/group errors: {len(row_errors)}")
    if row_errors:
        print("Errors:")
        for err in row_errors:
            print(f"  - {err}")
        sys.exit(2)


if __name__ == "__main__":
    main()
