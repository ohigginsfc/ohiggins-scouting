"""Upsert idempotente REST, limitado a las tablas del importador en public."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from email.utils import parsedate_to_datetime
import math
import os
import time
from urllib.parse import urlsplit

import numpy as np
import pandas as pd
import requests

from .db_pipeline.specs import SPECS


def sanitize(value):
    if isinstance(value, dict):
        return {key: sanitize(v) for key, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize(v) for v in value]
    if value is None or pd.isna(value):
        return None
    if isinstance(value, np.generic):
        return sanitize(value.item())
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value) if value.is_finite() else None
    if isinstance(value, float):
        return None if not math.isfinite(value) else int(value) if value.is_integer() else value
    return value


def records(frame, spec):
    frame = frame.copy()
    # Keep the production serializer: text such as '005.0' never becomes an int.
    for column in set(frame.columns) & set(spec.int_cols):
        frame[column] = pd.to_numeric(frame[column], errors='coerce').astype('Int64')
    frame.columns = [str(c).lower() for c in frame.columns]
    result = [sanitize(row) for row in frame.to_dict('records')]
    return result


def validate_destination(url, key):
    try:
        parsed = urlsplit(url)
        valid = (parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password
                 and not parsed.query and not parsed.fragment and parsed.path in ('', '/') and parsed.port in (None, 443))
    except ValueError:
        valid = False
    if not valid or not key:
        raise ValueError('Falta COMET_SUPABASE_URL HTTPS válida o COMET_SUPABASE_SERVICE_ROLE_KEY')


@dataclass
class Publisher:
    url: str
    key: str = field(repr=False)
    max_retries: int = 3
    max_wait: float = 120

    def __post_init__(self):
        validate_destination(self.url, self.key)
        self.url = self.url.rstrip('/')

    @classmethod
    def from_env(cls):
        # No fallback to portal/scouting credentials, or a postgres password.
        return cls(os.environ.get('COMET_SUPABASE_URL', ''), os.environ.get('COMET_SUPABASE_SERVICE_ROLE_KEY', ''))

    def _wait(self, response, attempt):
        wait = min((30 if response is not None and response.status_code == 429 else 1) * 2 ** attempt, self.max_wait)
        header = response.headers.get('Retry-After') if response is not None else None
        if header:
            try:
                candidate = float(header)
            except ValueError:
                try:
                    candidate = (parsedate_to_datetime(header) - datetime.now(timezone.utc)).total_seconds()
                except (ValueError, TypeError, OverflowError):
                    candidate = wait
            if math.isfinite(candidate) and candidate >= 0:
                wait = candidate
        if wait > self.max_wait:
            raise RuntimeError('Supabase solicita una espera superior al límite; reintentar más tarde')
        return wait

    def upsert(self, table, frame, *, chunk_size=1000):
        if table not in TABLES:
            raise ValueError('Tabla fuera del ámbito del importador COMET')
        if chunk_size <= 0:
            raise ValueError('chunk_size debe ser positivo')
        spec = SPECS[table]
        payload = records(frame, spec)
        allowed = {col.lower() for col in spec.cols}
        if any(set(row) - allowed for row in payload):
            raise ValueError('Columnas fuera del contrato COMET')
        total = 0
        for offset in range(0, len(payload), chunk_size):
            batch = payload[offset:offset + chunk_size]
            for attempt in range(self.max_retries + 1):
                response = None
                try:
                    response = requests.post(f'{self.url}/rest/v1/{table}',
                        params={'on_conflict': ','.join(col.lower() for col in spec.pk)}, json=batch,
                        headers={'apikey': self.key, 'Authorization': f'Bearer {self.key}',
                                 'Content-Profile': 'public', 'Accept-Profile': 'public',
                                 'Prefer': 'resolution=merge-duplicates,return=minimal'}, timeout=(10, 60))
                except (requests.Timeout, requests.ConnectionError):
                    if attempt == self.max_retries:
                        raise RuntimeError(f'Publicación COMET {table}: conexión agotada') from None
                except requests.RequestException:
                    raise RuntimeError(f'Publicación COMET {table}: solicitud fallida') from None
                else:
                    if 200 <= response.status_code < 300:
                        break
                    if response.status_code not in (429, 500, 502, 503, 504) or attempt == self.max_retries:
                        # Remote bodies may contain identifiers, data, URLs or tokens.
                        raise RuntimeError(f'Publicación COMET {table}: HTTP {response.status_code}, lote {offset // chunk_size + 1}') from None
                time.sleep(self._wait(response, attempt))
            total += len(batch)
        return total


# Publication order: parents precede their dependent facts. No portal/scouting tables.
TABLES = ('competiciones', 'equipos', 'competidores', 'partidos', 'jugadores', 'posiciones',
          'partidos_fases', 'eventos_partido', 'partidos_cambios_estado',
          'partidos_cambios_estado_equipo', 'actuaciones_jugadores', 'actuaciones_arqueros')
