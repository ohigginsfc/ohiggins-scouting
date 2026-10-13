"""Lectura REST paginada y estable de public; nunca escribe en la BD."""
from __future__ import annotations
import os
import re
from types import SimpleNamespace
import requests
from scouting.comet_ingest.publisher import Publisher, TABLES
from scouting.comet_ingest.db_pipeline.specs import SPECS


class ReportSource:
    def __init__(self, url, key):
        self.transport = Publisher(url, key)
        self.cache = {}

    @classmethod
    def from_env(cls):
        return cls(os.environ.get('COMET_SUPABASE_URL', ''),
                   os.environ.get('COMET_SUPABASE_SERVICE_ROLE_KEY', ''))

    def table(self, name):
        if name not in TABLES:
            raise ValueError('Tabla fuera del ámbito COMET')
        return ReadQuery(self, name)

    def rows(self, name):
        if name in self.cache:
            return self.cache[name]
        rows, offset, expected_total = [], 0, None
        order = ','.join(f'{key.lower()}.asc' for key in SPECS[name].pk)
        if not order:
            raise ValueError('La lectura paginada requiere una clave estable')
        # Finish a complete table before caching it: a failure is never an empty result.
        while True:
            for attempt in range(self.transport.max_retries + 1):
                response = None
                try:
                    response = requests.get(f'{self.transport.url}/rest/v1/{name}',
                        params={'select': '*', 'order': order, 'limit': 1000, 'offset': offset},
                        headers={'apikey': self.transport.key, 'Authorization': f'Bearer {self.transport.key}',
                                 'Accept-Profile': 'public', 'Prefer': 'count=exact'}, timeout=(10, 60))
                except (requests.Timeout, requests.ConnectionError):
                    if attempt == self.transport.max_retries:
                        raise RuntimeError(f'Lectura COMET {name}: conexión agotada') from None
                except requests.RequestException:
                    raise RuntimeError(f'Lectura COMET {name}: conexión rechazada') from None
                if response is not None:
                    if response.status_code == 200:
                        break
                    if response.status_code not in (429, 500, 502, 503, 504) or attempt == self.transport.max_retries:
                        raise RuntimeError(f'Lectura COMET {name}: HTTP {response.status_code}')
                import time
                time.sleep(self.transport._wait(response, attempt))
            try:
                batch = response.json()
            except ValueError:
                raise RuntimeError('Supabase devolvió una respuesta de lectura inválida') from None
            if not isinstance(batch, list) or any(not isinstance(row, dict) for row in batch):
                raise RuntimeError('Supabase devolvió un contrato de lectura inválido')
            content_range = response.headers.get('Content-Range', '')
            match = re.fullmatch(r'(?:\d+-\d+|\*)/(\d+)', content_range)
            if not match:
                raise RuntimeError('Supabase no confirmó el total de filas; lectura incompleta')
            total = int(match[1])
            if expected_total is not None and total != expected_total:
                raise RuntimeError('El origen cambió durante la lectura; reintentar antes de publicar')
            expected_total = total
            rows.extend(batch)
            if len(rows) == total:
                break
            if not batch or len(rows) > total:
                raise RuntimeError('Supabase devolvió una página incompleta o inconsistente')
            offset += len(batch)
        self.cache[name] = rows
        return rows


class ReadQuery:
    """Adaptador mínimo para conservar los cálculos del reporte anterior, sin SDK global."""
    def __init__(self, source, name):
        self.source, self.name = source, name
        self.columns, self.start, self.end = [], 0, 999

    def select(self, columns):
        allowed = {column.lower() for column in SPECS[self.name].cols}
        self.columns = columns.split(',')
        if set(self.columns) - allowed:
            raise ValueError('Columnas fuera del contrato COMET')
        return self

    def range(self, start, end):
        self.start, self.end = start, end
        return self

    def execute(self):
        rows = self.source.rows(self.name)[self.start:self.end + 1]
        if any(set(self.columns) - set(row) for row in rows):
            raise RuntimeError('Faltan columnas necesarias para los reportes COMET')
        return SimpleNamespace(data=[{column: row[column] for column in self.columns} for row in rows])
