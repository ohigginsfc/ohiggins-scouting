#!/usr/bin/env python3
"""Comprobación operativa del tema Streamlit (no se muestra al usuario final).

Verifica config.toml, ausencia de STREAMLIT_THEME_* conflictivas y versión.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG = PROJECT_ROOT / ".streamlit" / "config.toml"


def main() -> int:
    errors: list[str] = []

    if not CONFIG.is_file():
        errors.append(f"Falta {CONFIG}")
    else:
        text = CONFIG.read_text(encoding="utf-8")
        if 'base = "light"' not in text:
            errors.append('config.toml no tiene base = "light"')
        if 'base = "auto"' in text or 'base = "dark"' in text:
            errors.append("config.toml define auto/dark")

    theme_env = {k: v for k, v in os.environ.items() if k.startswith("STREAMLIT_THEME_")}
    if theme_env:
        # Informativo: no fallar si coinciden con light, pero avisar.
        for key, value in sorted(theme_env.items()):
            print(f"INFO: {key}={value!r} (puede sobrescribir config.toml)")

    try:
        import streamlit as st

        print(f"streamlit_version={st.__version__}")
    except Exception as exc:  # noqa: BLE001
        print(f"streamlit_import_error={exc}")

    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(PROJECT_ROOT),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        print(f"git_commit={commit}")
    except Exception:  # noqa: BLE001
        print("git_commit=unknown")

    print(f"config_toml_exists={CONFIG.is_file()}")
    print(f"config_toml_path={CONFIG}")

    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1
    print("OK: tema claro configurado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
