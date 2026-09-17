#!/usr/bin/env python3
"""Copia la salida del scraper Sofascore a data/staging con manifest.json."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

DEFAULT_COPY_FILES = (
    "player_stats.csv",
    "player_stats.json",
    "teams.json",
    "events.json",
)


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage Sofascore scraper output.")
    parser.add_argument("--source-dir", required=True, help="Directory with scraper output")
    parser.add_argument("--country", required=True, help="Country code, e.g. cl")
    parser.add_argument("--division", required=True, help="Division slug, e.g. primera")
    parser.add_argument("--season", required=True, help="Season label, e.g. 2025")
    parser.add_argument("--competition", required=True, help="Human-readable competition name")
    parser.add_argument("--tournament-id", type=int, required=True)
    parser.add_argument("--season-id", type=int, required=True)
    parser.add_argument(
        "--include-checkpoint",
        action="store_true",
        help="Also copy checkpoint_raw.json",
    )
    args = parser.parse_args()

    source = Path(args.source_dir)
    if not source.is_dir():
        print(f"ERROR: source dir not found: {source}", file=sys.stderr)
        sys.exit(1)

    csv_path = source / "player_stats.csv"
    if not csv_path.is_file():
        print(f"ERROR: missing required file: {csv_path}", file=sys.stderr)
        sys.exit(1)

    scraped_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = (
        _project_root()
        / "data"
        / "staging"
        / "sofascore"
        / args.country.strip().lower()
        / args.division.strip().lower()
        / str(args.season).strip()
        / scraped_at
    )
    dest.mkdir(parents=True, exist_ok=True)

    copy_names = list(DEFAULT_COPY_FILES)
    if args.include_checkpoint:
        copy_names.append("checkpoint_raw.json")

    copied: list[str] = []
    for name in copy_names:
        src = source / name
        if src.is_file():
            shutil.copy2(src, dest / name)
            copied.append(name)

    row_count = len(pd.read_csv(dest / "player_stats.csv"))

    manifest = {
        "provider": "sofascore",
        "country": args.country.strip().lower(),
        "division": args.division.strip().lower(),
        "competition": args.competition.strip(),
        "tournament_id": args.tournament_id,
        "season_id": args.season_id,
        "season": str(args.season).strip(),
        "scraped_at": scraped_at,
        "source_files": copied,
        "row_count": row_count,
    }
    manifest_path = dest / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"Staged to: {dest}")
    print(f"STAGED_DIR={dest.resolve()}")
    print(f"Files: {', '.join(copied)}")
    print(f"row_count: {row_count}")
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    main()
