"""Pruebas unitarias de build_driver (rutas explícitas, sin navegador real)."""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
SCRAPER_DIR = ROOT / "web_scraping_sofascore"


def _load_scraper_module():
    path = SCRAPER_DIR / "sofascore_scraper.py"
    # Evitar side-effects pesados: cargar solo si ya está o con stubs mínimos.
    if str(SCRAPER_DIR) not in sys.path:
        sys.path.insert(0, str(SCRAPER_DIR))
    # Import normal: selenium debe estar instalado en el entorno de tests.
    import sofascore_scraper as mod  # noqa: WPS433

    return mod


class BuildDriverPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = _load_scraper_module()
        self._env_backup = {
            k: os.environ.get(k)
            for k in ("CHROME_BINARY", "CHROME_BIN", "CHROMEDRIVER_PATH")
        }

    def tearDown(self) -> None:
        for key, value in self._env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _touch_exec(self, path: Path) -> None:
        path.write_text("#!/bin/sh\n", encoding="utf-8")
        path.chmod(0o755)

    def test_uses_chrome_binary_and_chromedriver_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            chrome = Path(tmp) / "chromium"
            driver = Path(tmp) / "chromedriver"
            self._touch_exec(chrome)
            self._touch_exec(driver)
            os.environ["CHROME_BINARY"] = str(chrome)
            os.environ.pop("CHROME_BIN", None)
            os.environ["CHROMEDRIVER_PATH"] = str(driver)

            fake_driver = MagicMock()
            with patch.object(self.mod.webdriver, "Chrome", return_value=fake_driver) as chrome_ctor:
                with patch.object(self.mod, "Service") as service_ctor:
                    result = self.mod.build_driver(headless=True)

            self.assertIs(result, fake_driver)
            service_ctor.assert_called_once_with(executable_path=str(driver))
            chrome_ctor.assert_called_once()
            kwargs = chrome_ctor.call_args.kwargs
            self.assertIn("service", kwargs)
            self.assertIn("options", kwargs)
            self.assertEqual(kwargs["options"].binary_location, str(chrome))

    def test_prefers_chrome_binary_over_chrome_bin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            preferred = Path(tmp) / "chromium-new"
            legacy = Path(tmp) / "chromium-old"
            driver = Path(tmp) / "chromedriver"
            self._touch_exec(preferred)
            self._touch_exec(legacy)
            self._touch_exec(driver)
            os.environ["CHROME_BINARY"] = str(preferred)
            os.environ["CHROME_BIN"] = str(legacy)
            os.environ["CHROMEDRIVER_PATH"] = str(driver)

            fake_driver = MagicMock()
            with patch.object(self.mod.webdriver, "Chrome", return_value=fake_driver):
                with patch.object(self.mod, "Service"):
                    self.mod.build_driver(headless=True)
                    # binary_location checked via Options on last Chrome call
            # Re-run capturing options
            with patch.object(self.mod.webdriver, "Chrome", return_value=fake_driver) as chrome_ctor:
                with patch.object(self.mod, "Service"):
                    self.mod.build_driver(headless=True)
            opts = chrome_ctor.call_args.kwargs["options"]
            self.assertEqual(opts.binary_location, str(preferred))

    def test_missing_chrome_raises_clear_error(self) -> None:
        missing = "/tmp/does-not-exist-chromium-xyz"
        os.environ["CHROME_BINARY"] = missing
        os.environ["CHROMEDRIVER_PATH"] = "/tmp/also-missing-driver-xyz"
        with self.assertRaises(FileNotFoundError) as ctx:
            self.mod.build_driver(headless=True)
        self.assertIn(missing, str(ctx.exception))
        self.assertIn("Chromium", str(ctx.exception))

    def test_missing_chromedriver_raises_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            chrome = Path(tmp) / "chromium"
            self._touch_exec(chrome)
            missing_driver = "/tmp/does-not-exist-chromedriver-xyz"
            os.environ["CHROME_BINARY"] = str(chrome)
            os.environ["CHROMEDRIVER_PATH"] = missing_driver
            with self.assertRaises(FileNotFoundError) as ctx:
                self.mod.build_driver(headless=True)
            self.assertIn(missing_driver, str(ctx.exception))
            self.assertIn("ChromeDriver", str(ctx.exception))

    def test_without_paths_falls_back_to_selenium_manager(self) -> None:
        os.environ.pop("CHROME_BINARY", None)
        os.environ.pop("CHROME_BIN", None)
        os.environ.pop("CHROMEDRIVER_PATH", None)
        fake_driver = MagicMock()
        with patch.object(self.mod.webdriver, "Chrome", return_value=fake_driver) as chrome_ctor:
            with patch.object(self.mod, "Service") as service_ctor:
                result = self.mod.build_driver(headless=True)
        self.assertIs(result, fake_driver)
        service_ctor.assert_not_called()
        # Sin Service → Selenium Manager
        self.assertEqual(chrome_ctor.call_args.kwargs.get("service"), None)
        self.assertIn("options", chrome_ctor.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()
