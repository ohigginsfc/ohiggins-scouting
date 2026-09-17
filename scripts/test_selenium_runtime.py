#!/usr/bin/env python3
"""
Smoke test del runtime Selenium/Chromium en Docker.

Uso:
    python scripts/test_selenium_runtime.py
    docker compose exec app python scripts/test_selenium_runtime.py
    docker compose run --rm --profile worker sofascore-worker \
        python scripts/test_selenium_runtime.py

No escribe en PostgreSQL.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SCRAPER = _ROOT / "web_scraping_sofascore"
if str(_SCRAPER) not in sys.path:
    sys.path.insert(0, str(_SCRAPER))

SOFASCORE_HOME = "https://www.sofascore.com/"


def main() -> int:
    chrome_binary = (os.environ.get("CHROME_BINARY") or os.environ.get("CHROME_BIN") or "").strip()
    chromedriver = (os.environ.get("CHROMEDRIVER_PATH") or "").strip()

    print("=== Selenium runtime smoke test ===")
    print(f"CHROME_BINARY / CHROME_BIN: {chrome_binary or '(no configurado)'}")
    print(f"CHROMEDRIVER_PATH:          {chromedriver or '(no configurado)'}")

    from sofascore_scraper import build_driver

    driver = None
    try:
        driver = build_driver(headless=True)
        driver.get(SOFASCORE_HOME)
        title = driver.title or ""
        final_url = driver.current_url or ""
        print(f"title: {title}")
        print(f"url:   {final_url}")
        if "sofascore" not in final_url.lower() and "sofascore" not in title.lower():
            print("ERROR: la página abierta no parece Sofascore", file=sys.stderr)
            return 1
        print("OK")
        return 0
    except Exception as exc:  # noqa: BLE001 — smoke test: mostrar fallo y exit != 0
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:  # noqa: BLE001
                pass


if __name__ == "__main__":
    raise SystemExit(main())
