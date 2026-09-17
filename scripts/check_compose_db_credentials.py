#!/usr/bin/env python3
"""Valida que app, db-init y postgres reciban la misma contraseña efectiva.

Compara solo hashes SHA-256; nunca imprime secretos en claro.
Detecta configuraciones mixtas (env_file vs interpolación) que dividen valores.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _service_env(config: dict, service: str) -> dict[str, str]:
    services = config.get("services") or {}
    if service not in services:
        raise KeyError(f"Servicio ausente en compose config: {service}")
    env = services[service].get("environment") or {}
    if isinstance(env, list):
        parsed: dict[str, str] = {}
        for item in env:
            if isinstance(item, str) and "=" in item:
                key, val = item.split("=", 1)
                parsed[key] = val
            elif isinstance(item, dict):
                parsed.update({str(k): "" if v is None else str(v) for k, v in item.items()})
        return parsed
    if not isinstance(env, dict):
        raise TypeError(f"environment inesperado en {service}: {type(env)!r}")
    return {str(k): "" if v is None else str(v) for k, v in env.items()}


def load_compose_config(
    compose_file: Path,
    *,
    env: dict[str, str] | None = None,
    project_directory: Path | None = None,
) -> dict:
    cmd = ["docker", "compose", "-f", str(compose_file), "config", "--format", "json"]
    cwd = str(project_directory or compose_file.parent)
    result = subprocess.run(
        cmd,
        cwd=cwd,
        env=env or os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "docker compose config falló "
            f"(exit {result.returncode}). stderr omitido si contiene secretos."
        )
    return json.loads(result.stdout)


def extract_password_hashes(config: dict) -> dict[str, str]:
    app_env = _service_env(config, "app")
    init_env = _service_env(config, "db-init")
    pg_env = _service_env(config, "postgres")

    required = {
        "app.DB_PASSWORD": app_env.get("DB_PASSWORD"),
        "db-init.DB_PASSWORD": init_env.get("DB_PASSWORD"),
        "postgres.POSTGRES_PASSWORD": pg_env.get("POSTGRES_PASSWORD"),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError(f"Faltan variables en compose config: {', '.join(missing)}")

    return {name: _sha256(value) for name, value in required.items()}  # type: ignore[arg-type]


def assert_password_hashes_match(hashes: dict[str, str]) -> None:
    unique = set(hashes.values())
    if len(unique) != 1:
        labels = ", ".join(f"{k}={v[:12]}…" for k, v in sorted(hashes.items()))
        raise AssertionError(
            "Contraseñas efectivas distintas entre servicios "
            f"(hashes SHA-256 parciales: {labels}). "
            "Revisa que app, db-init y postgres usen la misma estrategia de Compose."
        )


def check_compose_file(compose_file: Path, *, env: dict[str, str] | None = None) -> dict[str, str]:
    config = load_compose_config(compose_file, env=env)
    hashes = extract_password_hashes(config)
    assert_password_hashes_match(hashes)
    return hashes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-f",
        "--file",
        default="docker-compose.yml",
        help="Fichero Compose a validar (default: docker-compose.yml)",
    )
    args = parser.parse_args(argv)
    compose_file = Path(args.file)
    if not compose_file.is_absolute():
        compose_file = PROJECT_ROOT / compose_file

    try:
        hashes = check_compose_file(compose_file)
    except Exception as exc:  # noqa: BLE001 — CLI surface
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print("OK: app, db-init y postgres comparten el mismo hash de contraseña.")
    for name, digest in sorted(hashes.items()):
        print(f"  {name}: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
