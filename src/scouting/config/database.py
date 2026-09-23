"""Database connection settings from environment (and optional local .env)."""

from __future__ import annotations

import os
import re
from pathlib import Path
from psycopg.conninfo import conninfo_to_dict

from dotenv import load_dotenv

# Local (fuera de Compose): carga .env si falta alguna variable.
# En Docker, Compose ya inyecta DB_* vía interpolación; override=False no las pisa.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_PROJECT_ROOT / ".env", override=False)


def get_db_connection_params() -> dict[str, object]:
    """Return keyword arguments for psycopg.connect (no credentials hardcoded)."""
    url = os.environ.get("SCOUTING_DATABASE_URL", "").strip()
    if url:
        params = conninfo_to_dict(url)
        return _with_schema(params)
    host = os.environ.get("DB_HOST")
    port = os.environ.get("DB_PORT", "5432")
    dbname = os.environ.get("DB_NAME")
    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")

    missing = [
        k
        for k, v in [
            ("DB_HOST", host),
            ("DB_NAME", dbname),
            ("DB_USER", user),
            ("DB_PASSWORD", password),
        ]
        if not v
    ]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    return _with_schema({
        "host": host,
        "port": int(port),
        "dbname": dbname,
        "user": user,
        "password": password,
    })


def _with_schema(params: dict[str, object]) -> dict[str, object]:
    schema = os.environ.get("DB_SCHEMA", "").strip()
    if schema:
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", schema):
            raise ValueError("DB_SCHEMA must be a lowercase PostgreSQL identifier")
        params["options"] = (str(params.get("options", "")) + f" -c search_path={schema}").strip()
    params.setdefault("connect_timeout", 15)
    return params
