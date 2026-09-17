#!/usr/bin/env python3
"""
Inicialización idempotente de la base de datos para instalaciones nuevas.

1. Espera a que PostgreSQL acepte conexiones
2. Aplica migraciones (scripts/apply_migrations.py)
3. Upsert de competiciones externas Sofascore
4. Inserta datos demo solo si corresponde (sin datos reales y demo incompleto/ausente)
5. Sale con código 0

No borra datos existentes. No se ejecuta en cada rerun de Streamlit.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = Path(__file__).resolve().parent
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

# Mínimo esperado del fixture demo (201 en 2024 + 424 en 2025).
EXPECTED_DEMO_METRICS_MIN = 600


def _wait_for_postgres(*, timeout_sec: int = 120, interval_sec: float = 2.0) -> None:
    from scouting.db import get_connection

    deadline = time.time() + timeout_sec
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            print("PostgreSQL listo.")
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"Esperando PostgreSQL… ({exc})")
            time.sleep(interval_sec)
    raise RuntimeError(f"PostgreSQL no disponible tras {timeout_sec}s: {last_error}")


def _run_script(script_name: str, *extra_args: str) -> int:
    cmd = [sys.executable, str(_SCRIPTS / script_name), *extra_args]
    print(f"\n$ {' '.join(cmd)}")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(_ROOT / "src")
    result = subprocess.run(cmd, cwd=str(_ROOT), env=env)
    return int(result.returncode)


def should_seed_demo(conn) -> tuple[bool, str]:
    """
    Seed solo si no hay Sofascore real y faltan datos demo mínimos.

    No ejecuta seed automático cuando ya existen métricas reales.
    """
    from scouting.services.sofascore_sync_assessment import count_metrics_by_origin

    origins = count_metrics_by_origin(conn, season=None)
    sofascore_n = int(origins.get("sofascore") or 0)
    demo_n = int(origins.get("demo") or 0)

    if sofascore_n > 0:
        return (
            False,
            f"Existen {sofascore_n} métricas Sofascore reales; no se ejecuta seed automático.",
        )
    if demo_n >= EXPECTED_DEMO_METRICS_MIN:
        return False, f"Datos demo ya presentes ({demo_n} métricas); seed omitido."
    if demo_n > 0:
        return (
            True,
            f"Datos demo incompletos ({demo_n} < {EXPECTED_DEMO_METRICS_MIN}); se completa el seed.",
        )
    return True, "Base sin métricas demo ni reales; se insertan datos de demostración."


def init_database(*, skip_seed: bool = False, dry_run: bool = False) -> int:
    print("Scouting Platform — init_database")
    print(f"  ROOT={_ROOT}")
    if dry_run:
        print("DRY RUN — no se escribirá en la base")

    _wait_for_postgres()

    if dry_run:
        print("DRY RUN: apply_migrations + seed_external_competitions + seed_demo_data (condicional)")
        return 0

    code = _run_script("apply_migrations.py")
    if code != 0:
        print("ERROR: falló apply_migrations.py", file=sys.stderr)
        return code

    code = _run_script("seed_external_competitions.py")
    if code != 0:
        print("ERROR: falló seed_external_competitions.py", file=sys.stderr)
        return code

    from scouting.db import get_connection

    with get_connection() as conn:
        do_seed, reason = should_seed_demo(conn)
        print(f"\nCriterio seed demo: {reason}")

    if skip_seed:
        print("Seed omitido (--skip-seed).")
        return 0

    if not do_seed:
        print("Inicialización completada (sin seed).")
        return 0

    code = _run_script("seed_demo_data.py")
    if code != 0:
        print("ERROR: falló seed_demo_data.py", file=sys.stderr)
        return code

    with get_connection() as conn:
        from scouting.services.sofascore_sync_assessment import count_metrics_by_origin

        origins = count_metrics_by_origin(conn, season=None)
        print(
            "\nPost-seed:"
            f" demo={origins.get('demo', 0)}"
            f" sofascore={origins.get('sofascore', 0)}"
            f" total={origins.get('total', 0)}"
        )
    print("Inicialización completada.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-seed",
        action="store_true",
        help="Solo migraciones y competiciones; no inserta demo",
    )
    parser.add_argument("--dry-run", action="store_true", help="No escribe en la BD")
    args = parser.parse_args()
    try:
        return init_database(skip_seed=args.skip_seed, dry_run=args.dry_run)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR init_database: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
