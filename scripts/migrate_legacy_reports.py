"""Copy subjective scouting reports from an old PostgreSQL to Supabase.

The source is always read-only. The destination is read-only unless --apply is
given. This is a one-time migration; a nonempty destination reports table is
rejected rather than guessing whether records are duplicates.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from scouting.db import get_connection

TABLES = ("players", "scouting_reports", "report_attribute_ratings")


def rows(conn, table):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql.SQL("SELECT * FROM {}").format(sql.Identifier(table)))
        return [dict(row) for row in cur]


def columns(conn, table):
    with conn.cursor() as cur:
        cur.execute(sql.SQL("SELECT * FROM {} LIMIT 0").format(sql.Identifier(table)))
        return {col.name for col in cur.description}


def insert(conn, table, row):
    names = list(row)
    values = [Jsonb(value) if name == "raw_payload" and value is not None else value
              for name, value in row.items()]
    query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, names)),
        sql.SQL(", ").join(sql.Placeholder() for _ in names),
    )
    if table == "players":
        query += sql.SQL(" RETURNING id")
        return conn.execute(query, values).fetchone()[0]
    conn.execute(query, values)
    return row["id"]


def prepare(source, target, *, include_seed_demo=False):
    source_tables = {table: rows(source, table) for table in TABLES}
    seed_ids = {
        row["id"] for row in source_tables["scouting_reports"]
        if row.get("source_type") == "demo" or (
            isinstance(row.get("raw_payload"), dict) and (
                row["raw_payload"].get("loader") == "scripts/seed_demo_data.py"
                or row["raw_payload"].get("source") == "demo"
            )
        )
    }
    if not include_seed_demo:
        source_tables["scouting_reports"] = [
            row for row in source_tables["scouting_reports"] if row["id"] not in seed_ids
        ]
        source_tables["report_attribute_ratings"] = [
            row for row in source_tables["report_attribute_ratings"] if row["report_id"] not in seed_ids
        ]
    source_players = {row["id"]: row for row in source_tables["players"]}
    report_ids = {row["id"] for row in source_tables["scouting_reports"]}
    if not report_ids:
        raise ValueError("Legacy database contains no scouting reports")
    if len(report_ids) != len(source_tables["scouting_reports"]):
        raise ValueError("Duplicate source report IDs")
    if not {row["player_id"] for row in source_tables["scouting_reports"]} <= source_players.keys():
        raise ValueError("A report references an absent player")
    if not {row["report_id"] for row in source_tables["report_attribute_ratings"]} <= report_ids:
        raise ValueError("An attribute rating references an absent report")
    for table in TABLES:
        missing = set(source_tables[table][0]) - columns(target, table) if source_tables[table] else set()
        if missing:
            raise ValueError(f"Destination {table} lacks columns: {sorted(missing)}")
    if target.execute("SELECT count(*) FROM scouting_reports").fetchone()[0]:
        raise ValueError("Destination already has scouting reports; review overlap before migrating")
    dest_players = rows(target, "players")
    by_name = {row["normalized_name"]: row for row in dest_players}
    required_players = {source_players[row["player_id"]]["normalized_name"]: source_players[row["player_id"]]
                        for row in source_tables["scouting_reports"]}
    for name, player in required_players.items():
        existing = by_name.get(name)
        if existing and existing.get("birth_date") and player.get("birth_date") \
                and existing["birth_date"] != player["birth_date"]:
            raise ValueError(f"Player identity conflict for {name}")
    kinds = {}
    for report in source_tables["scouting_reports"]:
        kinds[report["source_type"]] = kinds.get(report["source_type"], 0) + 1
    return source_tables, required_players, by_name, dict(
        reports=len(report_ids), ratings=len(source_tables["report_attribute_ratings"]),
        source_players=len(required_players), existing_players=sum(n in by_name for n in required_players),
        new_players=sum(n not in by_name for n in required_players), report_types=kinds,
        image_paths=sum(bool(p.get("image_path")) for p in required_players.values()),
        seed_demo_excluded=0 if include_seed_demo else len(seed_ids),
    )


def apply_migration(target, tables, source_players, dest_players, plan):
    player_id_map = {}
    for old_id, player in ((row["id"], row) for row in tables["players"]
                           if row["normalized_name"] in source_players):
        existing = dest_players.get(player["normalized_name"])
        if existing:
            player_id_map[old_id] = existing["id"]
        else:
            player_id_map[old_id] = insert(target, "players", {k: v for k, v in player.items() if k != "id"})
    for report in tables["scouting_reports"]:
        insert(target, "scouting_reports", {**report, "player_id": player_id_map[report["player_id"]]})
    for rating in tables["report_attribute_ratings"]:
        insert(target, "report_attribute_ratings", rating)
    for table in ("scouting_reports", "report_attribute_ratings"):
        # Both IDs are preserved; advance their sequences before normal UI writes.
        target.execute(sql.SQL("SELECT setval(pg_get_serial_sequence(%s, 'id'), %s, true)"),
                       (f"scouting.{table}", max(row["id"] for row in tables[table]) if tables[table] else 1))
    actual = (target.execute("SELECT count(*) FROM scouting_reports").fetchone()[0],
              target.execute("SELECT count(*) FROM report_attribute_ratings").fetchone()[0])
    if actual != (plan["reports"], plan["ratings"]):
        raise ValueError("Post-import counts differ; rolling back")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Commit the one-time migration")
    parser.add_argument("--include-seed-demo", action="store_true",
                        help="Also copy reports explicitly marked as demo seed data")
    args = parser.parse_args()
    source_url = os.environ.get("SCOUTING_LEGACY_DATABASE_URL", "").strip()
    if not source_url or not os.environ.get("SCOUTING_DATABASE_URL") or os.environ.get("DB_SCHEMA") != "scouting":
        parser.error("Set SCOUTING_LEGACY_DATABASE_URL, SCOUTING_DATABASE_URL and DB_SCHEMA=scouting")
    with psycopg.connect(source_url, options="-c search_path=public") as source:
        source.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        if source.execute("SELECT current_schema()").fetchone()[0] != "public":
            raise ValueError("Legacy source must use public schema")
        with get_connection() as target:
            if target.execute("SELECT current_schema()").fetchone()[0] != "scouting":
                raise ValueError("Destination must use scouting schema")
            target.commit()
            if args.apply:
                with target.transaction():
                    target.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                                   ("scouting_legacy_reports_migration",))
                    tables, players, existing, plan = prepare(source, target, include_seed_demo=args.include_seed_demo)
                    apply_migration(target, tables, players, existing, plan)
            else:
                target.execute("SET TRANSACTION READ ONLY")
                _, _, _, plan = prepare(source, target, include_seed_demo=args.include_seed_demo)
            print(json.dumps({"applied": args.apply, **plan}, ensure_ascii=False))


if __name__ == "__main__":
    main()
