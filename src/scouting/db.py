"""PostgreSQL connection helpers."""

from __future__ import annotations

from contextlib import contextmanager
import os
from typing import Iterator

import psycopg
from psycopg import Connection

from scouting.config.database import get_db_connection_params


def get_connection() -> Connection:
    """Open a new PostgreSQL connection. Caller is responsible for closing (or use context manager)."""
    params = get_db_connection_params()
    conn = psycopg.connect(**params)
    schema = os.environ.get("DB_SCHEMA", "").strip()
    if schema:
        try:
            actual = conn.execute("SELECT current_schema()").fetchone()[0]
            conn.commit()
            if actual != schema:
                raise ValueError("Configured DB_SCHEMA is absent or inaccessible")
        except Exception:
            conn.close()
            raise
    return conn


@contextmanager
def connection_ctx() -> Iterator[Connection]:
    """Context manager that opens a connection and always closes it."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def check_database_connection() -> tuple[bool, str]:
    """Return (ok, message) after running SELECT 1."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return True, "Connected to PostgreSQL."
    except Exception as exc:  # noqa: BLE001 — surface any connection/query error to the UI
        return False, f"Database connection failed: {exc}"
