#!/usr/bin/env python3
"""
Aplica migraciones SQL pendientes en db/migrations/ sobre una BD existente.

No borra datos. Usa schema_migrations para registrar versiones ya aplicadas.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from psycopg import errors as pg_errors

from scouting.db import get_connection

MIGRATIONS_DIR = _ROOT / "db" / "migrations"

ENSURE_MIGRATIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT now()
);
"""


def _migration_files() -> list[Path]:
    if not MIGRATIONS_DIR.is_dir():
        return []
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def _applied_versions(conn) -> set[str]:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT version FROM schema_migrations ORDER BY version")
            return {str(row[0]) for row in cur.fetchall()}
    except pg_errors.UndefinedTable:
        return set()


def _apply_one(conn, path: Path, *, dry_run: bool) -> None:
    version = path.stem
    sql = path.read_text(encoding="utf-8")
    print(f"  → {path.name}")

    if dry_run:
        return

    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            cur.execute(
                "INSERT INTO schema_migrations (version) VALUES (%s) ON CONFLICT (version) DO NOTHING",
                (version,),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply pending SQL migrations from db/migrations/."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List pending migrations without executing them",
    )
    args = parser.parse_args()

    files = _migration_files()
    if not files:
        print(f"No migration files in {MIGRATIONS_DIR}")
        return 0

    print(f"Migrations directory: {MIGRATIONS_DIR}")
    if args.dry_run:
        print("DRY RUN — no SQL will be executed\n")

    applied_ok: list[str] = []
    skipped: list[str] = []
    failed: str | None = None

    try:
        with get_connection() as conn:
            if not args.dry_run:
                with conn.cursor() as cur:
                    cur.execute(ENSURE_MIGRATIONS_TABLE_SQL)
                conn.commit()

            done = _applied_versions(conn)
            pending = [p for p in files if p.stem not in done]
            if not pending:
                print("No pending migrations.")
                print(f"Already applied ({len(files)}):")
                for p in files:
                    print(f"  ✓ {p.name}")
                return 0

            print(f"Pending: {len(pending)} / {len(files)}\n")

            for path in files:
                version = path.stem
                if version in done:
                    skipped.append(version)
                    continue
                if path not in pending:
                    continue
                try:
                    _apply_one(conn, path, dry_run=args.dry_run)
                    applied_ok.append(version)
                except Exception as exc:
                    failed = version
                    print(f"\nERROR applying {path.name}: {exc}", file=sys.stderr)
                    if not args.dry_run:
                        print("Transaction rolled back for this migration.", file=sys.stderr)
                    break

    except Exception as exc:
        print(f"Database error: {exc}", file=sys.stderr)
        return 1

    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"Applied:  {len(applied_ok)}")
    for v in applied_ok:
        print(f"  ✓ {v}")
    print(f"Skipped (already applied): {len(skipped)}")
    if failed:
        print(f"Failed:   {failed}")
        return 1
    if args.dry_run and applied_ok:
        print("(dry-run — none were written to schema_migrations)")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
