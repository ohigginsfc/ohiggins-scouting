#!/usr/bin/env python3
"""
Sofascore League Scraper
Scrapes player statistics for all matches in a league season.

Strategy (confirmed by probing the API):
  • Lineups endpoint already embeds player statistics → 1 call per match
  • If a player's stats are missing from lineup, fall back to individual endpoint
  • Player details (country, foot, dob) fetched once per unique player

Output: {output_dir}/player_stats.json  +  {output_dir}/player_stats.csv  (CLI: --output-dir)
"""

import argparse
import hashlib
import json
import os
import time
import csv
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests as std_requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException

try:
    from curl_cffi import requests as curl_requests
except ImportError:
    curl_requests = None  # type: ignore[misc, assignment]

from card_disciplinary_metrics import apply_card_derived_to_row
from sofascore_incidents import (
    IncidentsScrapeDiagnostics,
    apply_cards_to_lineup_entries,
    extract_player_cards_from_incidents,
)
from sofascore_metric_registry import (
    AVERAGE_STATS,
    CUMULATIVE_STATS,
    MAX_STATS,
    STATS_ABSENT_IN_LINEUPS,
    resolve_stat_from_match_statistics,
)

# ── DEFAULTS (Chile Primera) ─────────────────────────────────────────────────
DEFAULT_TOURNAMENT_ID = 11653
DEFAULT_SEASON_ID = 88493
DEFAULT_OUTPUT_DIR = Path("sofascore_output")

BASE_URL = "https://www.sofascore.com/api/v1"
BASE_URL_ALT = "https://api.sofascore.com/api/v1"
SOFASCORE_HOME = "https://www.sofascore.com/"

RETRY_DELAYS = (2, 5, 10)
DEBUG_DIR_NAME = "debug_sofascore"

DEFAULT_DELAY_LINEUP = 1.5
DEFAULT_DELAY_FALLBACK = 1.0
DEFAULT_DELAY_DETAILS = 1.0
DEFAULT_DELAY_EVENTS = 1.5
DEFAULT_DELAY_INCIDENTS = 0.8


@dataclass(frozen=True)
class ScraperConfig:
    tournament_id: int
    season_id: int
    output_dir: Path
    headless: bool
    delay_lineup: float
    delay_fallback: float
    delay_details: float
    delay_events: float
    delay_incidents: float = DEFAULT_DELAY_INCIDENTS
    debug_fetch: bool = False


@dataclass
class FetchContext:
    debug_fetch: bool = False
    driver: webdriver.Chrome | None = None
    browser_warmed: bool = False
    _http_backend: str = field(default="", repr=False)
    fallback_stats_requested: int = 0
    fallback_stats_404: int = 0
    fallback_stats_success: int = 0
    last_fetch_expected_missing_stats: bool = False
    logged_missing_player_stats_warning: bool = False


_FETCH_CTX: FetchContext | None = None

# CUMULATIVE_STATS vive en sofascore_metric_registry (módulo ligero, importado arriba).

# ── LOGGING ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── DRIVER ────────────────────────────────────────────────────────────────────
def _resolve_chrome_binary() -> str | None:
    """CHROME_BINARY (preferido) o CHROME_BIN (compatibilidad)."""
    for key in ("CHROME_BINARY", "CHROME_BIN"):
        value = (os.environ.get(key) or "").strip()
        if value:
            return value
    return None


def _resolve_chromedriver_path() -> str | None:
    value = (os.environ.get("CHROMEDRIVER_PATH") or "").strip()
    return value or None


def _require_executable(path: str, *, label: str) -> None:
    if not os.path.exists(path):
        raise FileNotFoundError(f"{label} no encontrado en {path}")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"{label} no es un fichero ejecutable: {path}")
    if not os.access(path, os.X_OK):
        raise PermissionError(f"{label} no es ejecutable: {path}")


def build_driver(headless: bool = True) -> webdriver.Chrome:
    """
    Crea Chrome/Chromium para scraping.

    Si CHROME_BINARY / CHROMEDRIVER_PATH están definidos, se usan de forma
    explícita (sin Selenium Manager). Si no hay rutas, Selenium Manager actúa
    como fallback.
    """
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    chrome_binary = _resolve_chrome_binary()
    if chrome_binary:
        _require_executable(chrome_binary, label="Chromium")
        opts.binary_location = chrome_binary
        log.info("Chrome binary: %s", chrome_binary)

    chromedriver_path = _resolve_chromedriver_path()
    if chromedriver_path:
        _require_executable(chromedriver_path, label="ChromeDriver")
        log.info("ChromeDriver: %s", chromedriver_path)
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=opts)
    else:
        # Fallback: Selenium Manager resuelve el driver.
        log.warning(
            "CHROMEDRIVER_PATH no configurado; Selenium Manager elegirá el driver."
        )
        driver = webdriver.Chrome(options=opts)

    driver.execute_script(
        "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
    )
    return driver


# ── FETCH / DEBUG ─────────────────────────────────────────────────────────────
def debug_dir() -> Path:
    path = Path(__file__).resolve().parent / DEBUG_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def init_fetch_context(
    *,
    debug_fetch: bool = False,
    driver: webdriver.Chrome | None = None,
) -> FetchContext:
    global _FETCH_CTX
    _FETCH_CTX = FetchContext(debug_fetch=debug_fetch, driver=driver)
    if debug_fetch:
        log.setLevel(logging.DEBUG)
        log.debug("Debug fetch enabled → %s", debug_dir())
    return _FETCH_CTX


def get_fetch_context() -> FetchContext:
    if _FETCH_CTX is None:
        return init_fetch_context()
    return _FETCH_CTX


def _http_headers() -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": SOFASCORE_HOME,
        "Origin": "https://www.sofascore.com",
    }


def _is_json_text(raw: str) -> bool:
    stripped = (raw or "").lstrip()
    return stripped.startswith("{") or stripped.startswith("[")


def is_expected_missing_player_stats(
    url: str,
    status_code: int | None,
    payload: dict | list | None = None,
) -> bool:
    """
    404 (o error API 404) en /event/.../player/.../statistics: sin stats individuales.
    No es transitorio; no debe reintentarse.
    """
    u = (url or "").lower()
    if not all(part in u for part in ("event", "player", "statistics")):
        return False
    if status_code == 404:
        return True
    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, dict) and err.get("code") == 404:
            return True
    return False


def _parse_json_payload(raw: str) -> dict | list | None:
    if not _is_json_text(raw):
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _note_expected_missing_player_stats(ctx: FetchContext, url: str) -> None:
    ctx.last_fetch_expected_missing_stats = True
    if not ctx.logged_missing_player_stats_warning:
        log.warning(
            "Individual player statistics not found; skipping fallback"
        )
        ctx.logged_missing_player_stats_warning = True
    else:
        log.debug("Expected missing player stats (404): %s", url)


def _api_error_message(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None
    err = data.get("error")
    if isinstance(err, dict):
        code = err.get("code")
        reason = err.get("reason", "")
        return f"API error {code}: {reason}".strip()
    if err:
        return f"API error: {err}"
    return None


def _save_debug_response(
    url: str,
    raw: str,
    *,
    backend: str,
    content_type: str | None = None,
    current_url: str | None = None,
    page_title: str | None = None,
) -> None:
    ddir = debug_dir()
    txt_path = ddir / "last_response.txt"
    html_path = ddir / "last_response.html"
    meta_path = ddir / "last_response_meta.json"

    body = raw or ""
    txt_path.write_text(body, encoding="utf-8", errors="replace")
    if body.lstrip().startswith("<"):
        html_path.write_text(body, encoding="utf-8", errors="replace")
    else:
        html_path.write_text(
            f"<!-- not HTML; backend={backend} url={url} -->\n<pre>{body}</pre>",
            encoding="utf-8",
            errors="replace",
        )

    meta = {
        "url": url,
        "backend": backend,
        "current_url": current_url,
        "page_title": page_title,
        "content_type": content_type,
        "size": len(body.encode("utf-8", errors="replace")),
        "is_json": _is_json_text(body),
        "preview": body[:500],
    }
    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.debug("Saved debug response → %s", ddir)


def _log_fetch_diagnostics(
    url: str,
    raw: str,
    *,
    backend: str,
    content_type: str | None = None,
    current_url: str | None = None,
    page_title: str | None = None,
    status_code: int | None = None,
) -> None:
    preview = (raw or "")[:500]
    log.warning(
        "Fetch diagnostics [%s] status=%s content-type=%s size=%s url=%s current_url=%s title=%s",
        backend,
        status_code,
        content_type,
        len(raw or ""),
        url,
        current_url,
        page_title,
    )
    log.warning("Response preview (500 chars): %s", preview)
    if not _is_json_text(raw or ""):
        log.warning("Response is not JSON (does not start with { or [)")
    _save_debug_response(
        url,
        raw or "",
        backend=backend,
        content_type=content_type,
        current_url=current_url,
        page_title=page_title,
    )


def _parse_json_raw(
    raw: str,
    url: str,
    *,
    backend: str,
    content_type: str | None = None,
    current_url: str | None = None,
    page_title: str | None = None,
    status_code: int | None = None,
) -> dict | list | None:
    if not raw or not str(raw).strip():
        log.error("Empty response [%s] %s", backend, url)
        _log_fetch_diagnostics(
            url,
            raw or "",
            backend=backend,
            content_type=content_type,
            current_url=current_url,
            page_title=page_title,
            status_code=status_code,
        )
        return None

    if not _is_json_text(raw):
        log.warning("Response is not JSON [%s] %s", backend, url)
        _log_fetch_diagnostics(
            url,
            raw,
            backend=backend,
            content_type=content_type,
            current_url=current_url,
            page_title=page_title,
            status_code=status_code,
        )
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        log.error("json.loads failed [%s] %s: %s", backend, url, exc)
        _log_fetch_diagnostics(
            url,
            raw,
            backend=backend,
            content_type=content_type,
            current_url=current_url,
            page_title=page_title,
            status_code=status_code,
        )
        return None

    api_err = _api_error_message(data)
    if api_err:
        log.error("%s — %s", api_err, url)
        _log_fetch_diagnostics(
            url,
            raw,
            backend=backend,
            content_type=content_type,
            current_url=current_url,
            page_title=page_title,
            status_code=status_code,
        )
        return None

    return data


def _make_http_session(ctx: FetchContext) -> tuple[Any, str]:
    if curl_requests is not None:
        session = curl_requests.Session(impersonate="chrome131")
        ctx._http_backend = "curl_cffi"
        return session, "curl_cffi"
    session = std_requests.Session()
    session.headers.update(_http_headers())
    ctx._http_backend = "requests"
    return session, "requests"


def _http_warmup(session: Any, backend: str) -> None:
    try:
        session.get(SOFASCORE_HOME, timeout=20)
        log.debug("HTTP warmup OK (%s)", backend)
    except Exception as exc:
        log.debug("HTTP warmup failed (%s): %s", backend, exc)


def fetch_json_requests(
    url: str,
    delay: float = 0.0,
    *,
    ctx: FetchContext | None = None,
) -> tuple[dict | list | None, dict[str, Any]]:
    """HTTP fetch (curl_cffi preferido, requests como respaldo)."""
    ctx = ctx or get_fetch_context()
    meta: dict[str, Any] = {
        "backend": None,
        "status_code": None,
        "content_type": None,
        "api_error": None,
    }
    if delay > 0:
        time.sleep(delay)

    session, backend = _make_http_session(ctx)
    meta["backend"] = backend
    _http_warmup(session, backend)

    urls_to_try = [url]
    if BASE_URL in url and BASE_URL_ALT not in urls_to_try:
        urls_to_try.append(url.replace(BASE_URL, BASE_URL_ALT, 1))
    elif BASE_URL_ALT in url:
        urls_to_try.append(url.replace(BASE_URL_ALT, BASE_URL, 1))

    last_raw = ""
    for attempt_url in urls_to_try:
        try:
            resp = session.get(
                attempt_url,
                headers=_http_headers(),
                timeout=25,
            )
            meta["status_code"] = getattr(resp, "status_code", None)
            meta["content_type"] = (resp.headers.get("Content-Type") or "").split(";")[0]
            last_raw = resp.text or ""
            log.debug(
                "HTTP %s %s → %s %s bytes",
                backend,
                attempt_url,
                meta["status_code"],
                len(last_raw),
            )
            status_int = (
                int(meta["status_code"]) if meta["status_code"] is not None else None
            )
            if status_int is not None and status_int >= 400:
                payload = _parse_json_payload(last_raw)
                if is_expected_missing_player_stats(
                    attempt_url, status_int, payload
                ):
                    meta["expected_missing_player_stats"] = True
                    return None, meta
                _log_fetch_diagnostics(
                    attempt_url,
                    last_raw,
                    backend=backend,
                    content_type=meta["content_type"],
                    status_code=meta["status_code"],
                )
                continue
            data = _parse_json_raw(
                last_raw,
                attempt_url,
                backend=backend,
                content_type=meta["content_type"],
                status_code=meta["status_code"],
            )
            if data is not None:
                return data, meta
            probe = _parse_json_payload(last_raw)
            if is_expected_missing_player_stats(attempt_url, status_int, probe):
                meta["expected_missing_player_stats"] = True
                return None, meta
            if _is_json_text(last_raw):
                try:
                    meta["api_error"] = _api_error_message(json.loads(last_raw))
                except json.JSONDecodeError:
                    pass
        except Exception as exc:
            log.warning("HTTP fetch failed (%s) %s: %s", backend, attempt_url, exc)

    return None, meta


def _warmup_browser(driver: webdriver.Chrome, ctx: FetchContext) -> None:
    if ctx.browser_warmed:
        return
    log.info("Warming up browser session → %s", SOFASCORE_HOME)
    driver.get(SOFASCORE_HOME)
    time.sleep(3 if ctx.debug_fetch else 2)
    log.info("Browser title: %s", driver.title)
    snippet = (driver.page_source or "")[:500]
    log.debug("page_source[:500]: %s", snippet)
    if ctx.debug_fetch:
        _save_debug_response(
            SOFASCORE_HOME,
            driver.page_source or "",
            backend="selenium_home",
            current_url=driver.current_url,
            page_title=driver.title,
        )
        try:
            driver.save_screenshot(str(debug_dir() / "screenshot.png"))
            log.debug("Screenshot → %s", debug_dir() / "screenshot.png")
        except Exception as exc:
            log.debug("Screenshot failed: %s", exc)
    ctx.browser_warmed = True


def _fetch_json_selenium_xhr(
    driver: webdriver.Chrome,
    url: str,
    *,
    ctx: FetchContext,
) -> tuple[str | None, int | None]:
    _warmup_browser(driver, ctx)
    script = """
        const url = arguments[0];
        const done = arguments[arguments.length - 1];
        fetch(url, {
            credentials: 'include',
            headers: {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7',
            },
        })
        .then(r => r.text().then(body => ({
            status: r.status,
            contentType: r.headers.get('content-type'),
            body,
        })))
        .then(done)
        .catch(e => done({status: 0, contentType: '', body: '', error: String(e)}));
    """
    try:
        result = driver.execute_async_script(script, url)
    except Exception as exc:
        log.warning("Selenium XHR failed %s: %s", url, exc)
        return None, None
    if not isinstance(result, dict):
        return None, None
    status = result.get("status")
    status_int = int(status) if status is not None else None
    body = result.get("body") or ""
    log.debug("Selenium XHR %s → HTTP %s (%s bytes)", url, status, len(body))
    if ctx.debug_fetch:
        _log_fetch_diagnostics(
            url,
            body,
            backend="selenium_xhr",
            content_type=result.get("contentType"),
            current_url=driver.current_url,
            page_title=driver.title,
            status_code=status,
        )
        try:
            driver.save_screenshot(str(debug_dir() / "screenshot.png"))
        except Exception:
            pass
    if status_int is not None and status_int >= 400:
        return None, status_int
    return body, status_int


def _fetch_json_selenium_get(
    driver: webdriver.Chrome,
    url: str,
    delay: float,
    *,
    ctx: FetchContext,
) -> str | None:
    _warmup_browser(driver, ctx)
    driver.get(url)
    time.sleep(delay)
    log.info("Selenium GET title: %s", driver.title)
    log.debug("current_url: %s", driver.current_url)
    log.debug("page_source[:500]: %s", (driver.page_source or "")[:500])
    try:
        raw = driver.find_element("tag name", "pre").text
    except NoSuchElementException:
        raw = driver.find_element("tag name", "body").text
    if ctx.debug_fetch:
        _log_fetch_diagnostics(
            url,
            raw,
            backend="selenium_get",
            current_url=driver.current_url,
            page_title=driver.title,
        )
        try:
            driver.save_screenshot(str(debug_dir() / "screenshot.png"))
        except Exception:
            pass
    return raw


def fetch_json(
    url: str,
    delay: float = DEFAULT_DELAY_LINEUP,
    *,
    driver: webdriver.Chrome | None = None,
    ctx: FetchContext | None = None,
) -> dict | list | None:
    """
    Obtiene JSON de la API Sofascore.
    Orden: HTTP (curl_cffi/requests) → Selenium XHR → Selenium GET <pre>.
    Reintentos con backoff 2s / 5s / 10s.
    """
    if os.environ.get("SOFASCORE_FETCH_MODE") == "http":
        if delay > 0:
            time.sleep(delay)
        response = std_requests.get(url, timeout=25)
        if response.status_code == 404 and is_expected_missing_player_stats(url, 404, None):
            _note_expected_missing_player_stats(ctx or get_fetch_context(), url)
            return None
        if response.status_code != 200:
            raise RuntimeError(f"Sofascore HTTP {response.status_code}: {url}")
        return response.json()

    ctx = ctx or get_fetch_context()
    if driver is not None:
        ctx.driver = driver
    active_driver = ctx.driver
    ctx.last_fetch_expected_missing_stats = False

    for attempt in range(1 + len(RETRY_DELAYS)):
        if attempt > 0:
            wait = RETRY_DELAYS[attempt - 1]
            log.info("Retry %s/%s after %ss — %s", attempt, len(RETRY_DELAYS), wait, url)
            time.sleep(wait)

        data, _meta = fetch_json_requests(
            url,
            delay=delay if attempt == 0 else 0.0,
            ctx=ctx,
        )
        if _meta.get("expected_missing_player_stats"):
            _note_expected_missing_player_stats(ctx, url)
            return None
        if data is not None:
            return data

        if active_driver is None:
            continue

        raw, xhr_status = _fetch_json_selenium_xhr(active_driver, url, ctx=ctx)
        if xhr_status == 404 and is_expected_missing_player_stats(url, 404, None):
            _note_expected_missing_player_stats(ctx, url)
            return None
        if raw:
            data = _parse_json_raw(
                raw,
                url,
                backend="selenium_xhr",
                current_url=active_driver.current_url,
                page_title=active_driver.title,
                status_code=xhr_status,
            )
            if data is not None:
                return data
            payload = _parse_json_payload(raw)
            if is_expected_missing_player_stats(url, xhr_status, payload):
                _note_expected_missing_player_stats(ctx, url)
                return None

        raw = _fetch_json_selenium_get(active_driver, url, delay, ctx=ctx)
        if raw:
            data = _parse_json_raw(
                raw,
                url,
                backend="selenium_get",
                current_url=active_driver.current_url,
                page_title=active_driver.title,
            )
            if data is not None:
                return data

    if not ctx.last_fetch_expected_missing_stats:
        log.error(
            "fetch_json exhausted retries for %s — inspect %s (o ejecuta con --debug-fetch)",
            url,
            debug_dir(),
        )
    return None


def probe_http_endpoint(url: str) -> dict[str, Any]:
    """Prueba rápida HTTP sin reintentos (modo diagnóstico)."""
    ctx = FetchContext()
    session, backend = _make_http_session(ctx)
    _http_warmup(session, backend)
    try:
        resp = session.get(url, headers=_http_headers(), timeout=25)
        raw = resp.text or ""
        status = getattr(resp, "status_code", None)
        ct = (resp.headers.get("Content-Type") or "").split(";")[0]
    except Exception as exc:
        return {
            "url": url,
            "backend": backend,
            "status_code": None,
            "content_type": None,
            "size": 0,
            "is_json": False,
            "api_error": str(exc),
            "preview": "",
        }

    api_error = None
    if _is_json_text(raw):
        try:
            parsed = json.loads(raw)
            api_error = _api_error_message(parsed)
        except json.JSONDecodeError:
            api_error = "invalid JSON"
    return {
        "url": url,
        "backend": backend,
        "status_code": status,
        "content_type": ct,
        "size": len(raw.encode("utf-8", errors="replace")),
        "is_json": _is_json_text(raw),
        "api_error": api_error,
        "preview": raw[:300],
    }


def ts_to_date(ts) -> str | None:
    if ts:
        return datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d")
    return None


# ── STEP 1: TEAMS ─────────────────────────────────────────────────────────────
def get_teams(driver, tournament_id: int, season_id: int, *, delay_events: float) -> dict:
    url = (
        f"{BASE_URL}/unique-tournament/{tournament_id}"
        f"/season/{season_id}/standings/total"
    )
    log.info(f"Fetching standings → {url}")
    data = fetch_json(url, delay=delay_events, driver=driver)
    teams = {}
    if data and "standings" in data:
        for standing in data["standings"]:
            for row in standing.get("rows", []):
                t = row.get("team", {})
                teams[t["id"]] = {
                    "id":       t["id"],
                    "name":     t.get("name", ""),
                    "slug":     t.get("slug", ""),
                    "nameCode": t.get("nameCode", ""),
                }
    log.info(f"  → {len(teams)} teams")
    if not teams:
        log.warning(
            "0 teams — posible bloqueo WAF/challenge. Ejecuta con --debug-fetch y revisa %s",
            debug_dir(),
        )
    return teams


# ── STEP 2: EVENTS ────────────────────────────────────────────────────────────
def get_all_events(driver, tournament_id: int, season_id: int, *, delay_events: float) -> list:
    """Paginate last/0, last/1, … collecting only finished matches."""
    events = []
    page = 0
    while True:
        url = (
            f"{BASE_URL}/unique-tournament/{tournament_id}"
            f"/season/{season_id}/events/last/{page}"
        )
        log.info(f"Events page {page} → {url}")
        data = fetch_json(url, delay=delay_events, driver=driver)

        if not isinstance(data, dict) or not isinstance(data.get("events"), list):
            raise RuntimeError(f"Invalid or unavailable Sofascore calendar page {page}")
        if not data["events"] and data.get("hasNextPage"):
            raise RuntimeError(f"Empty Sofascore calendar page {page} with more pages announced")
        if not data["events"]:
            log.info("  → No more events.")
            break

        batch = data["events"]
        events.extend(batch)
        log.info(f"  → {len(batch)} events (total so far: {len(events)})")

        if not data.get("hasNextPage", False):
            break
        page += 1
        time.sleep(1)

    finished = [e for e in events if is_event_finished(e)]
    log.info(f"Finished matches: {len(finished)} / {len(events)}")
    return finished


def is_event_finished(event: dict) -> bool:
    return (event.get("status") or {}).get("type") == "finished"


def event_datetime_utc(event: dict) -> datetime | None:
    ts = event.get("startTimestamp")
    if not ts:
        return None
    return datetime.fromtimestamp(int(ts), tz=timezone.utc)


def compute_event_checksum(event: dict, *, incidents_count: int | None = None) -> str:
    """Hash estable para detectar cambios en un partido sin re-descargar lineups."""
    status = event.get("status") or {}
    payload: dict[str, Any] = {
        "event_id": event.get("id"),
        "status": status.get("type"),
        "homeScore": (event.get("homeScore") or {}).get("current"),
        "awayScore": (event.get("awayScore") or {}).get("current"),
        "hasLineups": event.get("hasLineups"),
        "hasXg": event.get("hasXg"),
        "lastUpdate": event.get("lastUpdate"),
    }
    if incidents_count is not None:
        payload["incidents_count"] = incidents_count

    if payload.get("lastUpdate") is None and incidents_count is None:
        subset = {
            k: event.get(k)
            for k in (
                "id",
                "status",
                "homeScore",
                "awayScore",
                "hasLineups",
                "hasXg",
                "startTimestamp",
            )
        }
        normalized = json.dumps(subset, sort_keys=True, separators=(",", ":"), default=str)
    else:
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)

    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def merge_events_by_id(existing: list, fetched: list) -> list:
    by_id: dict[int, dict] = {}
    for event in existing:
        eid = event.get("id")
        if eid is not None:
            by_id[int(eid)] = event
    for event in fetched:
        eid = event.get("id")
        if eid is not None:
            by_id[int(eid)] = event
    return sorted(by_id.values(), key=lambda x: x.get("startTimestamp") or 0, reverse=True)


def load_checkpoint(path: Path) -> dict[int, list]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Unexpected checkpoint format: {path}")
    raw: dict[int, list] = {}
    for key, matches in data.items():
        if isinstance(matches, list):
            raw[int(key)] = matches
    return raw


def remove_event_from_checkpoint(raw_stats: dict[int, list], event_id: int) -> dict[int, list]:
    out: dict[int, list] = {}
    for pid, entries in raw_stats.items():
        kept = [e for e in entries if e.get("event_id") != event_id]
        if kept:
            out[pid] = kept
    return out


def append_entries_to_checkpoint(raw_stats: dict[int, list], entries: list[dict]) -> dict[int, list]:
    for entry in entries:
        player = entry.get("player") or {}
        pid = player.get("id")
        if not pid:
            continue
        raw_stats.setdefault(int(pid), []).append(entry)
    return raw_stats


def process_finished_event(
    driver,
    event: dict,
    *,
    delay_lineup: float,
    delay_fallback: float,
    delay_incidents: float,
) -> tuple[list[dict], IncidentsScrapeDiagnostics]:
    """Descarga lineup + incidents de un partido finalizado. Etiqueta entradas con event_id."""
    event_id = int(event["id"])
    diag = IncidentsScrapeDiagnostics()

    players = get_lineup_with_stats(
        driver,
        event_id,
        delay_lineup=delay_lineup,
        delay_fallback=delay_fallback,
        home_team=event.get("homeTeam"),
        away_team=event.get("awayTeam"),
    )
    if not players:
        return [], diag

    diag.incidents_requested += 1
    incidents = get_event_incidents(
        driver,
        event_id,
        delay_incidents=delay_incidents,
    )
    diag.incidents_success += 1
    cards_by_player, card_diag = extract_player_cards_from_incidents(incidents)
    diag.cards.merge(card_diag)
    apply_cards_to_lineup_entries(players, cards_by_player)

    for entry in players:
        entry["event_id"] = event_id

    return players, diag


# ── STEP 3: LINEUPS (with embedded stats) ─────────────────────────────────────
def normalize_team_dict(team: dict | None) -> dict:
    """Asegura id/name/nameCode aunque el lineup venga incompleto."""
    if not team or not isinstance(team, dict):
        return {}
    tid = team.get("id")
    name = team.get("name") or ""
    code = team.get("nameCode") or team.get("name_code") or ""
    return {
        "id": tid if tid is not None else "",
        "name": str(name).strip() if name else "",
        "nameCode": str(code).strip() if code else "",
    }


def get_lineup_with_stats(
    driver,
    event_id: int,
    *,
    delay_lineup: float,
    delay_fallback: float,
    home_team: dict | None = None,
    away_team: dict | None = None,
) -> list[dict]:
    """
    Returns list of dicts with player info + match statistics already embedded.
    Falls back to individual stats endpoint if statistics missing from lineup.
    """
    url = f"{BASE_URL}/event/{event_id}/lineups"
    data = fetch_json(url, delay=delay_lineup, driver=driver)
    players = []
    if not data:
        return players

    for side, fallback_team in (("home", home_team), ("away", away_team)):
        side_data = data.get(side, {})
        team = normalize_team_dict(side_data.get("team") or {})
        if not (team.get("name") or team.get("id")) and fallback_team:
            team = normalize_team_dict(fallback_team)

        for entry in side_data.get("players", []):
            p = entry.get("player", {})
            if not p or not p.get("id"):
                continue

            stats = entry.get("statistics")

            # Fallback solo si el lineup no trae statistics embebidas
            if not stats:
                ctx = get_fetch_context()
                ctx.fallback_stats_requested += 1
                log.debug(
                    "  Fetching individual stats: event=%s player=%s",
                    event_id,
                    p["id"],
                )
                fb = fetch_json(
                    f"{BASE_URL}/event/{event_id}/player/{p['id']}/statistics",
                    delay=delay_fallback,
                    driver=driver,
                )
                if fb:
                    stats = fb.get("statistics") or {}
                    if stats:
                        ctx.fallback_stats_success += 1
                elif ctx.last_fetch_expected_missing_stats:
                    ctx.fallback_stats_404 += 1
                    stats = {}
                else:
                    stats = {}

            players.append({
                "player":     p,
                "team":       team,
                "statistics": stats or {},
                "position":   entry.get("position", p.get("position", "")),
                "substitute": entry.get("substitute", False),
            })

    return players


def get_event_incidents(
    driver,
    event_id: int,
    *,
    delay_incidents: float = DEFAULT_DELAY_INCIDENTS,
) -> list[dict]:
    """
    Tarjetas y otros incidents del partido.
    Usa fetch_json (HTTP curl_cffi → Selenium). En 403/404 devuelve [] sin abortar el scrape.
    """
    url = f"{BASE_URL}/event/{event_id}/incidents"
    data = fetch_json(url, delay=delay_incidents, driver=driver)
    if not data or not isinstance(data, dict):
        log.warning(
            "Incidents no disponibles para event %s (403/bloqueo o vacío). "
            "Probar --no-headless si persiste.",
            event_id,
        )
        return []
    incidents = data.get("incidents")
    if not isinstance(incidents, list):
        return []
    return [x for x in incidents if isinstance(x, dict)]


def lineup_team_diagnostics(players: list[dict]) -> dict[str, int]:
    """Conteos para logs: jugadores con/sin equipo en un partido."""
    total = len(players)
    with_team = sum(
        1
        for e in players
        if (e.get("team") or {}).get("name") or (e.get("team") or {}).get("id")
    )
    return {
        "total": total,
        "with_team": with_team,
        "without_team": total - with_team,
    }


# ── STEP 4: PLAYER DETAILS ────────────────────────────────────────────────────
def get_player_details(driver, player_id: int, *, delay_details: float) -> dict:
    url = f"{BASE_URL}/player/{player_id}"
    data = fetch_json(url, delay=delay_details, driver=driver)
    if not data or "player" not in data:
        return {}
    p = data["player"]
    country = p.get("country") or {}
    mv_raw  = p.get("proposedMarketValueRaw") or {}
    return {
        "country":               country.get("name", ""),
        "country_alpha2":        country.get("alpha2", ""),
        "country_alpha3":        country.get("alpha3", ""),
        "date_of_birth":         ts_to_date(p.get("dateOfBirthTimestamp")),
        "height":                p.get("height"),
        "preferred_foot":        p.get("preferredFoot", ""),
        "shirt_number":          p.get("shirtNumber"),
        "market_value":          mv_raw.get("value"),
        "market_value_currency": p.get("marketValueCurrency", "EUR"),
        "name_ar":               (p.get("fieldTranslations") or {})
                                 .get("nameTranslation", {}).get("ar", ""),
    }


def _match_position_code(entry_position: Any, player_position: Any) -> str | None:
    """Código G/D/M/F del partido (entry position), no ficha global del jugador."""
    for raw in (entry_position, player_position):
        if raw is None:
            continue
        code = str(raw).strip().upper()
        if code in ("G", "D", "M", "F"):
            return code
    return None


# ── STEP 5: AGGREGATE ─────────────────────────────────────────────────────────
def aggregate(
    raw_stats: dict,         # player_id → [match_entry, …]
    player_details_cache: dict,
) -> list[dict]:
    """Agrega estadísticas por jugador; alias de aggregate_player_stats()."""

    results = []

    for player_id, matches in raw_stats.items():
        if not matches:
            continue

        agg: dict[str, float] = {}
        present_counts: dict[str, int] = {}
        source_keys_used: dict[str, set[str]] = {}
        rating_vals = []
        player_meta = {}
        team_meta   = {}
        position_minutes: dict[str, float] = {}
        position_match_counts: dict[str, int] = {}
        card_minutes_all: list[dict] = []
        avg_sums: dict[str, float] = {}
        avg_counts: dict[str, int] = {}
        max_vals: dict[str, float] = {}
        max_counts: dict[str, int] = {}

        for m in matches:
            stats  = m.get("statistics") or {}
            p_info = m.get("player")     or {}
            t_info = normalize_team_dict(m.get("team"))

            if not player_meta and p_info:
                player_meta = p_info
            if t_info.get("name") or t_info.get("id"):
                if not team_meta.get("name") and not team_meta.get("id"):
                    team_meta = t_info
                elif t_info.get("name"):
                    team_meta = t_info

            pos_code = _match_position_code(m.get("position"), p_info.get("position"))
            if pos_code:
                try:
                    match_mins = float(stats.get("minutesPlayed") or 0)
                except (TypeError, ValueError):
                    match_mins = 0.0
                position_minutes[pos_code] = position_minutes.get(pos_code, 0.0) + match_mins
                position_match_counts[pos_code] = position_match_counts.get(pos_code, 0) + 1

            for stat in CUMULATIVE_STATS:
                if stat in STATS_ABSENT_IN_LINEUPS:
                    continue
                val, raw_key = resolve_stat_from_match_statistics(stats, stat)
                if raw_key is None:
                    continue
                try:
                    num = float(val)
                except (TypeError, ValueError):
                    continue
                agg[stat] = agg.get(stat, 0.0) + num
                present_counts[stat] = present_counts.get(stat, 0) + 1
                source_keys_used.setdefault(stat, set()).add(raw_key)

            # Métricas promediadas (valor por modelo/acción, no acumulativas).
            for stat in AVERAGE_STATS:
                val = stats.get(stat)
                if val is None:
                    continue
                try:
                    num = float(val)
                except (TypeError, ValueError):
                    continue
                avg_sums[stat] = avg_sums.get(stat, 0.0) + num
                avg_counts[stat] = avg_counts.get(stat, 0) + 1

            # Métricas de máximo (mejor registro del jugador).
            for stat in MAX_STATS:
                val = stats.get(stat)
                if val is None:
                    continue
                try:
                    num = float(val)
                except (TypeError, ValueError):
                    continue
                max_counts[stat] = max_counts.get(stat, 0) + 1
                if stat not in max_vals or num > max_vals[stat]:
                    max_vals[stat] = num

            rv = stats.get("rating")
            if rv is not None:
                rating_vals.append(rv)

            cm = stats.get("cardMinutes")
            if isinstance(cm, list):
                card_minutes_all.extend(x for x in cm if isinstance(x, dict))

        details = player_details_cache.get(player_id, {})

        row = {
            # ── Identity ──────────────────────────────────────────────────
            "player_id":    player_id,
            "player_name":  player_meta.get("name", ""),
            "player_name_ar": details.get("name_ar", ""),
            "short_name":   player_meta.get("shortName", ""),
            # Ficha/perfil Sofascore (puede diferir del rol por partido).
            "position":     player_meta.get("position", ""),
            "jersey_number": player_meta.get("jerseyNumber", ""),
            "height":       details.get("height") or player_meta.get("height"),
            "date_of_birth": details.get("date_of_birth")
                             or ts_to_date(player_meta.get("dateOfBirthTimestamp")),
            "country":          details.get("country", ""),
            "country_alpha2":   details.get("country_alpha2", ""),
            "country_alpha3":   details.get("country_alpha3", ""),
            "preferred_foot":   details.get("preferred_foot", ""),
            "market_value":     details.get("market_value"),
            "market_value_currency": details.get("market_value_currency", "EUR"),
            # ── Team ──────────────────────────────────────────────────────
            "team_id":   team_meta.get("id", ""),
            "team_name": team_meta.get("name", ""),
            "team_code": team_meta.get("nameCode", ""),
            # ── Appearances ───────────────────────────────────────────────
            "matches_played": len(matches),
            "avg_rating":     round(sum(rating_vals) / len(rating_vals), 2)
                              if rating_vals else None,
        }

        # Solo métricas presentes al menos en un partido (evita ceros falsos por ausencia).
        for stat, total in agg.items():
            row[stat] = total
            row[f"{stat}_present_count"] = present_counts[stat]
            raw_keys = sorted(source_keys_used.get(stat, ()))
            if raw_keys:
                row[f"{stat}_source_keys"] = ",".join(raw_keys)

        if position_minutes:
            dom_code = max(position_minutes.items(), key=lambda kv: kv[1])[0]
            row["dominant_match_position"] = dom_code
            row["match_position_minutes_json"] = json.dumps(position_minutes)
            row["match_position_counts_json"] = json.dumps(position_match_counts)

        if card_minutes_all:
            row["card_minutes_json"] = json.dumps(card_minutes_all, ensure_ascii=False)

        # Métricas promediadas (avg_{stat}) y de máximo ({stat}_max).
        for stat, total in avg_sums.items():
            cnt = avg_counts.get(stat, 0)
            if cnt > 0:
                row[f"avg_{stat}"] = round(total / cnt, 4)
                row[f"avg_{stat}_present_count"] = cnt
        for stat, mx in max_vals.items():
            cnt = max_counts.get(stat, 0)
            if cnt > 0:
                row[f"{stat}_max"] = round(mx, 4)
                row[f"{stat}_max_present_count"] = cnt

        # ── Derived metrics ───────────────────────────────────────────────
        mp = float(row.get("minutesPlayed") or 0)
        if mp > 0:
            if "goals" in row:
                row["goals_per90"] = round(float(row["goals"]) / mp * 90, 2)
            if "goalAssist" in row:
                row["assists_per90"] = round(float(row["goalAssist"]) / mp * 90, 2)
            if "totalShots" in row:
                row["shots_per90"] = round(float(row["totalShots"]) / mp * 90, 2)
            for card_stat in ("yellowCard", "redCard", "yellowRedCard"):
                if card_stat in row and row.get(f"{card_stat}_present_count", 0) > 0:
                    row[f"{card_stat}_per90"] = round(float(row[card_stat]) / mp * 90, 2)
            apply_card_derived_to_row(row, mp)

        if "totalPass" in row and "accuratePass" in row:
            tp = float(row["totalPass"])
            row["pass_accuracy_pct"] = (
                round(float(row["accuratePass"]) / tp * 100, 1) if tp > 0 else None
            )

        if "totalLongBalls" in row and "accurateLongBalls" in row:
            tlb = float(row["totalLongBalls"])
            row["long_ball_accuracy_pct"] = (
                round(float(row["accurateLongBalls"]) / tlb * 100, 1) if tlb > 0 else None
            )

        if "totalDribbles" in row and "successfulDribble" in row:
            td = float(row["totalDribbles"])
            row["dribble_success_pct"] = (
                round(float(row["successfulDribble"]) / td * 100, 1) if td > 0 else None
            )

        if "duelWon" in row and "duelLost" in row:
            dw = float(row["duelWon"]) + float(row["duelLost"])
            row["duel_win_pct"] = (
                round(float(row["duelWon"]) / dw * 100, 1) if dw > 0 else None
            )

        if "totalCross" in row and "accurateCross" in row:
            tc = float(row["totalCross"])
            row["cross_accuracy_pct"] = (
                round(float(row["accurateCross"]) / tc * 100, 1) if tc > 0 else None
            )

        if "wonTackle" in row and "totalTackle" in row:
            tt = float(row["totalTackle"])
            row["tackle_success_pct"] = (
                round(float(row["wonTackle"]) / tt * 100, 1) if tt > 0 else None
            )

        if "accurateKeeperSweeper" in row and "totalKeeperSweeper" in row:
            tks = float(row["totalKeeperSweeper"])
            row["keeper_sweeper_accuracy_pct"] = (
                round(float(row["accurateKeeperSweeper"]) / tks * 100, 1) if tks > 0 else None
            )

        if "penaltySave" in row and "penaltyFaced" in row:
            pf = float(row["penaltyFaced"])
            row["penalty_save_pct"] = (
                round(float(row["penaltySave"]) / pf * 100, 1) if pf > 0 else None
            )

        results.append(row)

    results.sort(key=lambda x: x.get("minutesPlayed", 0), reverse=True)
    return results


def aggregate_player_stats(
    raw_stats: dict,
    player_details_cache: dict,
) -> list[dict]:
    """API preferida: agrega raw_stats → filas player_stats."""
    return aggregate(raw_stats, player_details_cache)


# ── CSV COLUMN ORDER ──────────────────────────────────────────────────────────
PRIORITY_COLS = [
    "player_id", "player_name", "player_name_ar", "short_name",
    "position", "jersey_number",
    "team_id", "team_name", "team_code",
    "date_of_birth", "height",
    "country", "country_alpha2", "country_alpha3",
    "preferred_foot", "market_value", "market_value_currency",
    "matches_played", "minutesPlayed", "avg_rating",
    "goals", "goalAssist", "goals_per90", "assists_per90",
    "totalShots", "onTargetScoringAttempt", "shots_per90",
    "totalPass", "accuratePass", "pass_accuracy_pct",
    "totalLongBalls", "accurateLongBalls", "long_ball_accuracy_pct",
    "keyPass", "totalChanceCreated", "bigChanceCreated",
    "totalTackle", "interceptionWon", "totalClearance",
    "duelWon", "duelLost", "duel_win_pct",
    "aerialWon", "aerialLost",
    "ballRecovery", "touches", "possessionLostCtrl",
    "totalDribbles", "successfulDribble", "dribble_success_pct",
    "foulsCommited", "wasFouled", "totalOffside",
    "yellowCard", "redCard", "yellowRedCard",
    "yellowCard_total", "redCard_total", "yellowRedCard_total",
    "minutes_per_yellow_card", "minutes_per_red_card", "minutes_per_yellow_red_card",
    # Expected goals / assists
    "expectedGoals", "expectedAssists", "expectedGoalsOnTarget",
    # Ataque / eventos
    "bigChanceMissed", "hitWoodwork", "penaltyWon", "penaltyMiss", "ownGoals",
    # Centros
    "totalCross", "accurateCross", "cross_accuracy_pct", "crossNotClaimed",
    # Defensa avanzada
    "wonTackle", "tackle_success_pct", "challengeLost", "outfielderBlock",
    "clearanceOffLine", "lastManTackle", "penaltyConceded",
    "errorLeadToAShot", "errorLeadToAGoal",
    # Control / pérdidas
    "dispossessed", "unsuccessfulTouch",
    # Portero
    "goodHighClaim", "savedShotsFromInsideTheBox",
    "savedShotsFromOutsideTheBox", "goalsPrevented", "saves",
    "penaltySave", "penaltyFaced", "penalty_save_pct",
    "totalKeeperSweeper", "accurateKeeperSweeper", "keeper_sweeper_accuracy_pct",
    # Conducción / progresión
    "totalBallCarriesDistance", "totalProgression",
    "totalProgressiveBallCarriesDistance", "bestBallCarryProgression_max",
    # Value models
    "passValueNormalized", "dribbleValueNormalized",
    "defensiveValueNormalized", "goalkeeperValueNormalized",
    "avg_shotValueNormalized",
]


# ── HELPERS ───────────────────────────────────────────────────────────────────
def save_json(data, path: Path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info(f"Saved → {path}")


def save_csv(rows: list[dict], path: Path):
    if not rows:
        return
    all_keys   = {k for row in rows for k in row}
    remaining  = sorted(all_keys - set(PRIORITY_COLS))
    fieldnames = PRIORITY_COLS + remaining

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    log.info(f"Saved → {path}  ({len(rows)} players, {len(fieldnames)} columns)")


def parse_args(argv: list[str] | None = None) -> ScraperConfig:
    parser = argparse.ArgumentParser(
        description="Scrape Sofascore player stats for a league season."
    )
    parser.add_argument(
        "--tournament-id",
        type=int,
        default=DEFAULT_TOURNAMENT_ID,
        help=f"Sofascore tournament ID (default: {DEFAULT_TOURNAMENT_ID})",
    )
    parser.add_argument(
        "--season-id",
        type=int,
        default=DEFAULT_SEASON_ID,
        help=f"Sofascore season ID (default: {DEFAULT_SEASON_ID})",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Show Chrome window (default: headless)",
    )
    parser.add_argument(
        "--delay-lineup",
        type=float,
        default=DEFAULT_DELAY_LINEUP,
        help="Delay after lineup requests (seconds)",
    )
    parser.add_argument(
        "--delay-events",
        type=float,
        default=DEFAULT_DELAY_EVENTS,
        help="Delay after events/standings requests (seconds)",
    )
    parser.add_argument(
        "--delay-details",
        type=float,
        default=DEFAULT_DELAY_DETAILS,
        help="Delay after player profile requests (seconds)",
    )
    parser.add_argument(
        "--delay-fallback",
        type=float,
        default=DEFAULT_DELAY_FALLBACK,
        help="Delay after per-player stats fallback (seconds)",
    )
    parser.add_argument(
        "--delay-incidents",
        type=float,
        default=DEFAULT_DELAY_INCIDENTS,
        help="Delay after incidents requests (seconds)",
    )
    parser.add_argument(
        "--debug-fetch",
        action="store_true",
        help="Logs DEBUG, guarda debug_sofascore/ y screenshot.png",
    )
    args = parser.parse_args(argv)
    return ScraperConfig(
        tournament_id=args.tournament_id,
        season_id=args.season_id,
        output_dir=Path(args.output_dir),
        headless=not args.no_headless,
        delay_lineup=args.delay_lineup,
        delay_fallback=args.delay_fallback,
        delay_details=args.delay_details,
        delay_events=args.delay_events,
        delay_incidents=args.delay_incidents,
        debug_fetch=args.debug_fetch,
    )


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main(config: ScraperConfig) -> None:
    out = config.output_dir
    out.mkdir(parents=True, exist_ok=True)
    log.info("=" * 60)
    log.info(
        f"Sofascore scraper — tournament {config.tournament_id}, "
        f"season {config.season_id}"
    )
    log.info(f"Output → {out.resolve()}")
    log.info("=" * 60)

    driver = build_driver(headless=config.headless)
    init_fetch_context(debug_fetch=config.debug_fetch, driver=driver)
    if config.debug_fetch:
        log.info("Debug fetch ON → artifacts in %s", debug_dir())

    try:
        teams = get_teams(
            driver,
            config.tournament_id,
            config.season_id,
            delay_events=config.delay_events,
        )
        save_json(teams, out / "teams.json")

        events = get_all_events(
            driver,
            config.tournament_id,
            config.season_id,
            delay_events=config.delay_events,
        )
        save_json(events, out / "events.json")

        if not events:
            log.error(
                "No finished events — scrape abortado. Diagnóstico: "
                "python3 sofascore_scraper.py --debug-fetch "
                f"--tournament-id {config.tournament_id} --season-id {config.season_id}"
            )
            raise SystemExit(1)

        raw_stats: dict[int, list] = {}
        details_cache: dict[int, dict] = {}
        total = len(events)
        lineup_diag = {
            "events": 0,
            "events_empty_lineup": 0,
            "player_entries": 0,
            "entries_with_team": 0,
            "events_no_team_in_lineup": 0,
        }
        incidents_diag = IncidentsScrapeDiagnostics()

        for idx, event in enumerate(events, 1):
            event_id = event["id"]
            home = event.get("homeTeam", {}).get("name", "?")
            away = event.get("awayTeam", {}).get("name", "?")
            mdate = ts_to_date(event.get("startTimestamp"))
            score_h = event.get("homeScore", {}).get("current", "")
            score_a = event.get("awayScore", {}).get("current", "")

            log.info(
                f"[{idx:>3}/{total}] #{event_id}  "
                f"{home} {score_h}-{score_a} {away}  ({mdate})"
            )

            players, ev_incidents = process_finished_event(
                driver,
                event,
                delay_lineup=config.delay_lineup,
                delay_fallback=config.delay_fallback,
                delay_incidents=config.delay_incidents,
            )
            incidents_diag.incidents_requested += ev_incidents.incidents_requested
            incidents_diag.incidents_success += ev_incidents.incidents_success
            incidents_diag.incidents_failed += ev_incidents.incidents_failed
            incidents_diag.cards.merge(ev_incidents.cards)
            if not players:
                log.warning("  No lineup data — skipping.")
                lineup_diag["events_empty_lineup"] += 1
                continue

            lineup_diag["events"] += 1
            ev_diag = lineup_team_diagnostics(players)
            lineup_diag["player_entries"] += ev_diag["total"]
            lineup_diag["entries_with_team"] += ev_diag["with_team"]
            if ev_diag["with_team"] == 0:
                lineup_diag["events_no_team_in_lineup"] += 1

            log.info(
                f"  {ev_diag['total']} players · "
                f"team ok {ev_diag['with_team']} / {ev_diag['total']}"
            )

            for entry in players:
                pid = entry["player"].get("id")
                if not pid:
                    continue
                entry["event_id"] = event_id
                raw_stats.setdefault(pid, []).append(entry)

                if pid not in details_cache:
                    details_cache[pid] = get_player_details(
                        driver, pid, delay_details=config.delay_details
                    )

            if idx % 5 == 0:
                save_json(raw_stats, out / "checkpoint_raw.json")

        log.info(f"Total unique players tracked: {len(raw_stats)}")
        fctx = get_fetch_context()
        log.info(
            "Fallback individual stats: requested=%s 404=%s success=%s",
            fctx.fallback_stats_requested,
            fctx.fallback_stats_404,
            fctx.fallback_stats_success,
        )
        if lineup_diag["player_entries"]:
            pct = 100.0 * lineup_diag["entries_with_team"] / lineup_diag["player_entries"]
            log.info(
                "Lineup team coverage: %s/%s entries (%.1f%%) · events sin equipo: %s / %s",
                lineup_diag["entries_with_team"],
                lineup_diag["player_entries"],
                pct,
                lineup_diag["events_no_team_in_lineup"],
                lineup_diag["events"],
            )

        c = incidents_diag.cards
        log.info(
            "Incidents: requested=%s success=%s failed=%s",
            incidents_diag.incidents_requested,
            incidents_diag.incidents_success,
            incidents_diag.incidents_failed,
        )
        log.info(
            "Cards: total=%s yellow=%s red=%s yellowRed=%s with_player=%s without_player=%s",
            c.cards_total,
            c.yellow_cards,
            c.red_cards,
            c.yellow_red_cards,
            c.cards_with_player,
            c.cards_without_player,
        )

        log.info("Aggregating…")
        aggregated = aggregate(raw_stats, details_cache)
        agg_with_team = sum(1 for r in aggregated if r.get("team_name") or r.get("team_id"))
        log.info(
            "Aggregated players with team_name/id: %s / %s",
            agg_with_team,
            len(aggregated),
        )

        save_json(aggregated, out / "player_stats.json")
        save_csv(aggregated, out / "player_stats.csv")

        log.info("All done.")

    finally:
        driver.quit()


if __name__ == "__main__":
    main(parse_args())
