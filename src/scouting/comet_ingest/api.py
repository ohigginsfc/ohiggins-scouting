from __future__ import annotations

import re
import math
import time
import unicodedata
from email.utils import parsedate_to_datetime
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd
import requests
from pandas import json_normalize

import os, json
import base64
# =========================
# Config por defecto
# =========================
URL_API_BASE = "https://latam.analyticom.de/data-backend/api/public/areports/run"

DEFAULT_PAGE_SIZE = 1000
DEFAULT_MAX_PAGES = 999
DEFAULT_TIMEOUT = 60
DEFAULT_SLEEP_BETWEEN_PAGES = 3.0  # segundos entre solicitudes, incluso entre informes


# =========================
# Utilidades
# =========================
def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_slug(name: str) -> str:
    """Convierte un nombre cualquiera en un slug apto para ser usado como clave/archivo."""
    name = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip()).strip("_")
    return slug.lower() or "dataset"


def extract_api_key(link: str) -> Optional[str]:
    """Extrae API_KEY=... de una URL con querystring."""
    if not isinstance(link, str):
        return None
    m = re.search(r"(?:\?|&)API_KEY=([^&]+)", link)
    return m.group(1) if m else None


@dataclass(frozen=True)
class Endpoint:
    name: str
    api_key: str = field(repr=False)
    number: Optional[str] = None

    @property
    def slug(self) -> str:
        return safe_slug(self.name)


# =========================
# Cliente principal
# =========================
class CometAPI:
    """
    Cliente profesional para descarga y gestión de datasets de COMET.
    - Guarda los datos en memoria como DataFrames (self.datasets)
    - Permite exportar a CSV/ZIP
    """

    def __init__(
        self,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_pages: int = DEFAULT_MAX_PAGES,
        timeout: int = DEFAULT_TIMEOUT,
        sleep_between_pages: float = DEFAULT_SLEEP_BETWEEN_PAGES,
        base_url: str = URL_API_BASE,
        verbose: bool = True,
        max_retries: int = 6,
        max_retry_wait: float = 120,
    ) -> None:
        self.page_size = int(page_size)
        self.max_pages = int(max_pages)
        self.timeout = int(timeout)
        self.sleep_between_pages = float(sleep_between_pages)
        self.base_url = str(base_url).rstrip("/")
        self.verbose = bool(verbose)
        self.max_retries = int(max_retries)
        self.max_retry_wait = float(max_retry_wait)
        self._requested = False
        if min(self.page_size, self.max_pages, self.timeout) <= 0:
            raise ValueError("page_size, max_pages y timeout deben ser positivos")
        if min(self.sleep_between_pages, self.max_retries, self.max_retry_wait) < 0:
            raise ValueError("Las esperas y reintentos no pueden ser negativos")

        # Donde se guardan los DataFrames (en memoria)
        self.datasets: Dict[str, pd.DataFrame] = {}
        # Catálogo de endpoints
        self.endpoints: List[Endpoint] = []

    # ------------- Logging interno -------------
    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[{now_str()}] {msg}")

    # ------------- Carga de endpoints -------------
    def load_endpoints_from_env(self, var_name: str = "ENCODED_JSON_DATA") -> List[Endpoint]:

        raw = os.getenv(var_name, "").strip()
        if not raw:
            raise ValueError(f"Falta {var_name}")
        try:
            if not raw.startswith(("[", "{")):
                raw = base64.b64decode(raw, validate=True).decode("utf-8")
            payload = json.loads(raw)
            rows = payload.get("endpoints") if isinstance(payload, dict) else payload
            if not isinstance(rows, list) or not rows:
                raise ValueError()
            endpoints = []
            for row in rows:
                name = row.get("name") or row.get("NOMBRE") or row.get("title")
                key = row.get("api_key") or extract_api_key(row.get("link") or row.get("LINK"))
                if not isinstance(name, str) or not name.strip() or not isinstance(key, str) or not key.strip():
                    raise ValueError()
                endpoints.append(Endpoint(name.strip(), key.strip(), row.get("number")))
        except Exception:
            raise ValueError(f"{var_name}: se requiere JSON válido con nombres y claves, directo o Base64") from None
        self.validate_endpoints(endpoints)
        self.endpoints = endpoints
        self._log(f"Cargados {len(endpoints)} endpoints desde {var_name}")
        return endpoints

    @staticmethod
    def validate_endpoints(endpoints, required=()):
        slugs = [ep.slug for ep in endpoints]
        if not slugs:
            raise ValueError("No hay endpoints configurados")
        if len(set(slugs)) != len(slugs):
            raise ValueError("Nombres de endpoints duplicados tras normalizar")
        missing = set(required) - set(slugs)
        if missing:
            raise ValueError(f"Faltan datasets requeridos: {sorted(missing)}")

    def load_configured_endpoints(self):
        """Fuente explícita; nunca cambia de fuente tras un error."""
        source = os.getenv("COMET_ENDPOINT_SOURCE", "sheets").strip().lower()
        if source == "env":
            return self.load_endpoints_from_env("COMET_ENDPOINTS")
        if source != "sheets":
            raise ValueError("COMET_ENDPOINT_SOURCE debe ser sheets o env")
        return self.load_endpoints_from_gsheet(
            sheet_id=os.getenv("COMET_SHEET_ID", "1OI1kt4NvR0ggKF_wU3zWTn_uUkEexjFENhF81L8A2c8"),
            worksheet_name=os.getenv("COMET_WORKSHEET", "ENDPOINTS"),
        )

    def load_endpoints_from_gsheet(
        self,
        sheet_id: str,
        worksheet_name: str | None = None,
        gsheets_client=None,  # tipo esperado: GoogleSheets
        col_name: str = "NOMBRE",
        col_link: str = "LINK",
        col_number: str = "NUMERO",
    ) -> List[Endpoint]:
        """
        Lee endpoints desde Google Sheets (columnas NUMERO, NOMBRE, LINK),
        extrae API_KEY del LINK y construye self.endpoints.
        """
        # Si no pasan cliente, lo creamos con tu clase
        if gsheets_client is None:
            from .sheets import GoogleSheets
            gsheets_client = GoogleSheets()

        # Descarga hoja como DataFrame
        df = gsheets_client.download_as_df(sheet_id=sheet_id, worksheet_name=worksheet_name)

        if df.empty:
            self._log(f"La hoja '{worksheet_name or 'sheet1'}' está vacía.")
            self.endpoints = []
            return []

        # Normaliza nombres de columnas (por si vienen con espacios)
        df.columns = [str(c).strip() for c in df.columns]

        missing = [c for c in (col_name, col_link) if c not in df.columns]
        if missing:
            raise ValueError(
                f"Faltan columnas requeridas en Google Sheets: {missing}. "
                f"Presentes: {list(df.columns)}"
            )

        # Limpia y extrae API_KEY desde LINK
        work = df.copy()
        work[col_name] = work[col_name].astype(str).str.strip()
        work[col_link] = work[col_link].astype(str).str.strip()
        work["API_KEY"] = work[col_link].apply(extract_api_key)

        # Ignore blank rows, but never silently discard a configured report.
        active = df[col_name].notna() & df[col_name].astype(str).str.strip().ne("")
        linked = df[col_link].notna() & df[col_link].astype(str).str.strip().ne("")
        invalid = (active | linked) & (~active | work["API_KEY"].isna() | work["API_KEY"].eq(""))
        if invalid.any():
            raise ValueError(f"Google Sheets: {int(invalid.sum())} endpoints sin nombre o API_KEY válidos")
        work = work[active & work["API_KEY"].notna()]
        work = work.reset_index(drop=True)

        endpoints: List[Endpoint] = []
        for _, row in work.iterrows():
            endpoints.append(
                Endpoint(
                    name=str(row[col_name]),
                    api_key=str(row["API_KEY"]),
                    number=(
                        str(row[col_number]).strip()
                        if col_number in work.columns and pd.notna(row[col_number]) and str(row[col_number]).strip() != ""
                        else None
                    ),
                )
            )

        self.endpoints = endpoints
        self._log(
            f"Cargados {len(endpoints)} endpoints desde Google Sheets "
            f"(worksheet='{worksheet_name or 'sheet1'}')"
        )
        return endpoints

    def load_endpoints_from_excel(
        self,
        excel_path: Path | str,
        col_name: str = "NOMBRE",
        col_link: str = "LINK",
        col_number: str = "NUMERO",
    ) -> List[Endpoint]:
        """
        Lee un Excel con columnas NOMBRE, LINK (y opcional NUMERO),
        extrae API_KEY y construye la lista de endpoints.
        """
        excel_path = Path(excel_path)
        if not excel_path.exists():
            raise FileNotFoundError(f"No existe el Excel: {excel_path}")

        df = pd.read_excel(excel_path)
        missing = [c for c in (col_name, col_link) if c not in df.columns]
        if missing:
            raise ValueError(
                f"Faltan columnas requeridas en el Excel: {missing}. Presentes: {list(df.columns)}"
            )

        df["API_KEY"] = df[col_link].apply(extract_api_key)
        df = df.dropna(subset=["API_KEY"]).reset_index(drop=True)

        endpoints: List[Endpoint] = []
        for _, row in df.iterrows():
            ep = Endpoint(
                name=str(row[col_name]),
                api_key=str(row["API_KEY"]),
                number=str(row[col_number]) if col_number in df.columns and pd.notna(row[col_number]) else None,
            )
            endpoints.append(ep)

        self.endpoints = endpoints
        self._log(f"Cargados {len(endpoints)} endpoints desde {excel_path}")
        return endpoints

    def _retry_delay(self, response, attempt):
        base = 30 if response is not None and response.status_code == 429 else 1
        delay = min(base * 2 ** attempt, self.max_retry_wait)
        value = response.headers.get("Retry-After") if response is not None else None
        if value:
            try:
                candidate = float(value)
                if math.isfinite(candidate) and candidate >= 0:
                    delay = candidate
            except ValueError:
                try:
                    date = parsedate_to_datetime(value)
                    delay = (date - datetime.now(timezone.utc)).total_seconds()
                except (TypeError, ValueError, OverflowError):
                    pass
        if delay > self.max_retry_wait:
            raise RuntimeError("COMET solicita una espera superior al límite; reintentar más tarde") from None
        return max(0, delay)

    def _fetch_page(self, api_key, page):
        for attempt in range(self.max_retries + 1):
            response = None
            # Share pacing across pages AND reports, including empty reports.
            if self._requested and self.sleep_between_pages:
                time.sleep(self.sleep_between_pages)
            self._requested = True
            try:
                response = requests.get(
                    f"{self.base_url}/{page}/{self.page_size}/",
                    params={"API_KEY": api_key}, timeout=self.timeout,
                )
            except (requests.Timeout, requests.ConnectionError):
                if attempt == self.max_retries:
                    raise RuntimeError(f"COMET página {page}: conexión agotada tras {attempt + 1} intentos") from None
            except requests.RequestException:
                raise RuntimeError(f"COMET página {page}: error de solicitud") from None
            else:
                status = response.status_code
                if status not in {429, 500, 502, 503, 504}:
                    if not 200 <= status < 300:
                        raise RuntimeError(f"COMET página {page}: HTTP {status}") from None
                    try:
                        return response.json()
                    except ValueError:
                        raise RuntimeError(f"COMET página {page}: JSON inválido") from None
                if attempt == self.max_retries:
                    raise RuntimeError(f"COMET página {page}: HTTP {status}, reintentos agotados") from None
            delay = self._retry_delay(response, attempt)
            self._log(f"COMET página {page}: reintento {attempt + 1}/{self.max_retries} en {delay:.1f}s")
            time.sleep(delay)

    def fetch_report(self, api_key: str) -> pd.DataFrame:
        """Solo devuelve descargas completas; no imprime URL, clave ni cuerpo remoto."""
        chunks = []
        for page in range(self.max_pages):
            payload = self._fetch_page(api_key, page)
            results = payload
            if isinstance(results, dict):
                if "results" in results:
                    results = results["results"]
                if isinstance(results, dict) and "items" in results:
                    results = results["items"]
            if not isinstance(results, list) or any(not isinstance(row, dict) or not row for row in results):
                raise RuntimeError(f"COMET página {page}: contrato JSON inesperado")
            if len(results) > self.page_size:
                raise RuntimeError(f"COMET página {page}: tamaño de página inesperado")
            if not results:
                break
            chunks.append(json_normalize(results))
            if len(results) < self.page_size:
                break
        else:
            raise RuntimeError("COMET: max_pages alcanzado; descarga posiblemente incompleta")
        if not chunks:
            return pd.DataFrame()
        out = pd.concat(chunks, ignore_index=True)
        # Keep the production data contract; native-null changes need separate validation.
        obj_cols = out.select_dtypes(include=["object"]).columns
        if len(obj_cols):
            out[obj_cols] = out[obj_cols].astype(str)
        return out

    # ------------- Descarga masiva -------------
    def fetch_all(
        self,
        endpoints: Optional[Iterable[Endpoint]] = None,
        store: bool = True,
    ) -> Dict[str, pd.DataFrame]:
        """
        Descarga todos los endpoints proporcionados (o los cargados en self.endpoints).
        Almacena en self.datasets con clave = slug del endpoint.
        """
        endpoints = list(endpoints) if endpoints is not None else self.endpoints
        if not endpoints:
            raise ValueError("No hay endpoints para descargar. Llama primero a load_endpoints_from_excel().")

        self.validate_endpoints(endpoints)
        if store:
            self.datasets = {}
        results: Dict[str, pd.DataFrame] = {}
        for ep in endpoints:
            self._log(f"Descargando: {ep.name} (slug: {ep.slug})")
            df = self.fetch_report(ep.api_key)
            self._log(f" -> Filas: {len(df)} | Columnas: {len(df.columns)}")
            results[ep.slug] = df

        if store:
            self.datasets = results
        self._log(f"Descargados {len(results)} datasets.")
        return results

    # ------------- Accesores y utilidades -------------
    def get(self, key: str) -> pd.DataFrame:
        """Obtiene un DataFrame por su clave (slug)."""
        slug = safe_slug(key)
        if slug not in self.datasets:
            raise KeyError(f"No existe dataset '{slug}' en memoria. Claves disponibles: {list(self.datasets.keys())}")
        return self.datasets[slug]

    def list_datasets(self) -> List[str]:
        """Lista las claves de datasets en memoria."""
        return list(self.datasets.keys())

    # ------------- Exportación opcional -------------
    def save_all_csv(self, output_dir: Path | str) -> List[Path]:
        """
        Exporta todos los DataFrames en memoria a CSV. Devuelve rutas creadas.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        written: List[Path] = []
        for slug, df in self.datasets.items():
            path = output_dir / f"{slug}.csv"
            df.to_csv(path, index=False)
            written.append(path)
        self._log(f"Guardados {len(written)} CSV en {output_dir}")
        return written

    def zip_folder(self, folder: Path | str, zip_name: str = "analyticom_exports.zip") -> Path:
        """
        Crea un ZIP a partir de una carpeta (no usa APIs de Colab).
        """
        folder = Path(folder)
        if not folder.is_dir():
            raise FileNotFoundError(f"La carpeta no existe: {folder}")

        zip_path = folder.parent / zip_name
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in folder.rglob("*"):
                if p.is_file():
                    zf.write(p, p.relative_to(folder))
        self._log(f"ZIP creado: {zip_path}")
        return zip_path
