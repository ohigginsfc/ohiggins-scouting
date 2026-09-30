"""Registro de entregas del resumen semanal: una entrega por semana y destinatario.

`PostgresLedger` es el real (tabla `portal.comet_digest_deliveries`, migración 003). `MemoryLedger` tiene la
misma semántica y sirve para pruebas y para probar sin base de datos. Semántica común:

* `reserve` es atómico y devuelve True solo a UN proceso: la primera vez, o cuando la entrega quedó `fallido`
  y aún hay intentos. Una reserva sin cerrar (`reservado`) no se retoma sola: si el proceso murió justo después
  de enviar, reenviar duplicaría el correo (política de a lo más una entrega por semana y destinatario).
* `finish` cierra la reserva como `enviado` o `fallido`.
"""
from __future__ import annotations

import threading
from datetime import date
from typing import Optional

DEFAULT_MAX_ATTEMPTS = 3


def _key(week_start: date, recipient: str) -> tuple:
    return week_start, str(recipient).strip().lower()


class MemoryLedger:
    def __init__(self):
        self._rows: dict = {}
        self._lock = threading.Lock()

    def status(self, week_start: date, recipient: str) -> Optional[tuple]:
        with self._lock:
            row = self._rows.get(_key(week_start, recipient))
            return (row['status'], row['attempts']) if row else None

    def reserve(self, week_start: date, recipient: str, max_attempts: int = DEFAULT_MAX_ATTEMPTS) -> bool:
        with self._lock:
            key = _key(week_start, recipient)
            row = self._rows.get(key)
            if row is None:
                self._rows[key] = dict(status='reservado', attempts=1, error='')
                return True
            if row['status'] == 'fallido' and row['attempts'] < max_attempts:
                row.update(status='reservado', attempts=row['attempts'] + 1, error='')
                return True
            return False

    def finish(self, week_start: date, recipient: str, *, sent: bool, error: str = '') -> None:
        with self._lock:
            row = self._rows.get(_key(week_start, recipient))
            if row and row['status'] == 'reservado':
                row.update(status='enviado' if sent else 'fallido', error=(error or '')[:200])


class PostgresLedger:
    """Entregas guardadas en Supabase con la conexión privada `PORTAL_AUTH_DATABASE_URL`."""

    def status(self, week_start: date, recipient: str) -> Optional[tuple]:
        from . import config_store
        return config_store.delivery_status_for_job(week_start, recipient)

    def reserve(self, week_start: date, recipient: str, max_attempts: int = DEFAULT_MAX_ATTEMPTS) -> bool:
        from . import config_store
        return config_store.reserve_delivery_for_job(week_start, recipient, max_attempts)

    def finish(self, week_start: date, recipient: str, *, sent: bool, error: str = '') -> None:
        from . import config_store
        config_store.finish_delivery_for_job(week_start, recipient, sent=sent, error=error)
