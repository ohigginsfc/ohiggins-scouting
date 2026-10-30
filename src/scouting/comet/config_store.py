"""Persistencia en Supabase (esquema privado `portal`) de reglas, alertas, marcas, períodos y bajas de jugadores.

Solo administración lee o escribe: cada función llama a `require_admin()` antes de abrir
una conexión. COMET se lee con `comet_reader` (solo lectura) y no guarda nada; por eso esta
configuración vive en `portal`, con la conexión `portal_runtime` que ya usan las cuentas.
Requiere aplicar `db/portal/003_comet_followup.sql` (y `005_comet_player_bajas.sql` para las bajas); si no está
aplicada, lanza `StoreUnavailable` y la interfaz sigue con los valores por defecto, en solo lectura.
"""
from __future__ import annotations

import re
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
import psycopg
from psycopg.types.json import Jsonb

from scouting.portal import accounts
from scouting.portal.security import require_admin
from scouting.portal.readonly_pilot import writable_only

from .alerts import ALERT_COLORS, ALERTS_BY_KEY
from .roster import BAJA_COLUMNS, BAJA_REASONS, EMPTY_BAJAS
from .rules import RULES_BY_KEY, parse

MARKS = {'proyectado': 'Jugador proyectado', 'seleccion': 'Jugador de selección'}
PERIOD_KINDS = {'microciclo': 'Microciclo de selección', 'sudamericano': 'Sudamericano', 'mundial': 'Mundial'}
ALERT_CONFIG_KEY = 'alert_config'
FOLLOWUP_MIGRATION = '003_comet_followup.sql'
BAJAS_MIGRATION = '005_comet_player_bajas.sql'
MAX_BAJAS_AT_ONCE = 200
_ID = re.compile(r'^[0-9A-Za-z_-]{1,40}$')


class StoreUnavailable(RuntimeError):
    """La base de configuración no está disponible o falta aplicar una migración (003 o 005)."""


@contextmanager
def _db(migration: str = FOLLOWUP_MIGRATION):
    try:
        with accounts.connect() as db:
            yield db
    except psycopg.errors.UndefinedTable:
        raise StoreUnavailable(f'Falta aplicar db/portal/{migration} en Supabase.') from None
    except (RuntimeError, psycopg.OperationalError):
        raise StoreUnavailable('No se pudo conectar con la configuración de Supabase.') from None


# --- Validación (pura: la comparten el almacén real y la demostración) -------------------------------

def clean_person(personid) -> str:
    text = str(personid).strip()
    if not _ID.match(text):
        raise ValueError('Identificador de jugador no válido.')
    return text


def clean_note(note) -> str:
    text = (note or '').strip()
    if len(text) > 500:
        raise ValueError('La nota admite hasta 500 caracteres.')
    return text


def clean_mark(mark: str) -> str:
    if mark not in MARKS:
        raise ValueError('Marca desconocida.')
    return mark


def clean_period(personid, kind: str, starts_on: date, ends_on: date, note: str = '') -> tuple:
    if kind not in PERIOD_KINDS:
        raise ValueError('Tipo de período desconocido.')
    if ends_on < starts_on:
        raise ValueError('La fecha de término no puede ser anterior a la de inicio.')
    return clean_person(personid), kind, starts_on, ends_on, clean_note(note)


def clean_baja(personid, reason: str, effective_on, note: str = '', *, today: date | None = None) -> tuple:
    """Valida una baja: jugador, motivo de la lista, fecha razonable (hasta mañana, por la diferencia de huso) y nota."""
    if reason not in BAJA_REASONS:
        raise ValueError('Motivo de baja desconocido.')
    if isinstance(effective_on, datetime):
        effective_on = effective_on.date()
    if not isinstance(effective_on, date):
        raise ValueError('La fecha de la baja no es válida.')
    if effective_on < date(2000, 1, 1) or effective_on > (today or date.today()) + timedelta(days=1):
        raise ValueError('La fecha de la baja no puede ser futura ni anterior al año 2000.')
    return clean_person(personid), reason, effective_on, clean_note(note)


def clean_setting(key: str, value: Any) -> Any:
    """Valida una regla o la configuración de alertas y devuelve el valor a guardar."""
    if key == ALERT_CONFIG_KEY:
        if not isinstance(value, dict) or set(value) - set(ALERTS_BY_KEY):
            raise ValueError('Configuración de alertas no válida.')
        for entry in value.values():
            if not isinstance(entry, dict) or not isinstance(entry.get('enabled'), bool) \
                    or entry.get('color') not in ALERT_COLORS:
                raise ValueError('Cada alerta necesita activación y un color válido.')
        return {k: {'enabled': v['enabled'], 'color': v['color']} for k, v in value.items()}
    if key in RULES_BY_KEY and RULES_BY_KEY[key].editable:
        return parse(RULES_BY_KEY[key], value)
    if key in RULES_BY_KEY:
        return RULES_BY_KEY[key].default  # regla informativa: solo se registra su confirmación
    raise ValueError('Configuración desconocida.')


# --- Lectura y escritura ---------------------------------------------------------------------------

def load_all() -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    """Reglas guardadas, marcas y períodos con una sola conexión (una lectura por recarga de pantalla)."""
    require_admin()
    return _read_all()


def load_all_for_job() -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    """Igual que `load_all` para el script operativo del resumen semanal, que no tiene sesión de usuario.

    Solo lee. La protección es la propia credencial privada `PORTAL_AUTH_DATABASE_URL`, que únicamente tiene
    quien opera el servidor. Las pantallas del portal no deben usarla (lo verifica un test).
    """
    return _read_all()


def _read_all() -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    with _db() as db:
        settings = db.execute('SELECT key, value, confirmed FROM portal.comet_settings').fetchall()
        marks = db.execute('SELECT personid, mark, active, note, updated_at FROM portal.comet_player_marks '
                           'ORDER BY updated_at DESC').fetchall()
        periods = db.execute('SELECT id, personid, kind, starts_on, ends_on, note, active '
                             'FROM portal.comet_selection_periods ORDER BY starts_on DESC').fetchall()
    frame = pd.DataFrame(periods, columns=['id', 'personid', 'kind', 'starts_on', 'ends_on', 'note', 'active'])
    frame = frame.assign(start=pd.to_datetime(frame['starts_on']), end=pd.to_datetime(frame['ends_on']))
    return ({r['key']: {'value': r['value'], 'confirmed': r['confirmed']} for r in settings},
            pd.DataFrame(marks, columns=['personid', 'mark', 'active', 'note', 'updated_at']), frame)


@writable_only
def save_setting(key: str, value: Any, *, confirmed: bool = False) -> None:
    """Guarda una regla o la configuración de alertas. `confirmed` = aprobado por el club."""
    actor = require_admin()
    clean = clean_setting(key, value)
    with _db() as db:
        db.execute(
            'INSERT INTO portal.comet_settings(key, value, confirmed, updated_by) VALUES (%s, %s, %s, %s) '
            'ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, confirmed = EXCLUDED.confirmed, '
            'updated_by = EXCLUDED.updated_by, updated_at = now()',
            (key, Jsonb(clean), bool(confirmed), actor['id']))


DELIVERY_MAX_ATTEMPTS = 3


def clean_recipient(recipient) -> str:
    text = str(recipient).strip().lower()
    if len(text) > 254 or '@' not in text[1:] or ' ' in text:
        raise ValueError('Destinatario no válido.')
    return text


# --- Registro de entregas del resumen semanal (solo el script operativo; sin sesión de usuario) -----------
# Igual que `load_all_for_job`: la protección es la credencial privada. Las pantallas del portal no las
# usan (lo verifica un test).

def delivery_status_for_job(week_start: date, recipient: str):
    """(estado, intentos) de una entrega, o None si nunca se reservó."""
    with _db() as db:
        row = db.execute('SELECT status, attempts FROM portal.comet_digest_deliveries WHERE week_start = %s AND recipient = %s',
                         (week_start, clean_recipient(recipient))).fetchone()
    return (row['status'], row['attempts']) if row else None


@writable_only
def reserve_delivery_for_job(week_start: date, recipient: str, max_attempts: int = DELIVERY_MAX_ATTEMPTS) -> bool:
    """Reserva atómica: True solo si ESTA ejecución debe enviar.

    Inserta la reserva; si ya existía, solo la retoma cuando quedó «fallido» y quedan intentos. Dos procesos
    a la vez no pueden reservar lo mismo (clave primaria + bloqueo de fila), y una reserva sin cerrar nunca se
    retoma sola: si el proceso murió después de enviar, reenviar duplicaría el correo.
    """
    with _db() as db:
        row = db.execute(
            'INSERT INTO portal.comet_digest_deliveries AS d (week_start, recipient, status) VALUES (%s, %s, \'reservado\') '
            'ON CONFLICT (week_start, recipient) DO UPDATE SET status = \'reservado\', attempts = d.attempts + 1, '
            'last_error = \'\', updated_at = now() WHERE d.status = \'fallido\' AND d.attempts < %s RETURNING attempts',
            (week_start, clean_recipient(recipient), int(max_attempts))).fetchone()
    return row is not None


@writable_only
def finish_delivery_for_job(week_start: date, recipient: str, *, sent: bool, error: str = '') -> None:
    """Cierra una reserva: `enviado` o `fallido` (con el motivo, sin datos sensibles)."""
    with _db() as db:
        db.execute(
            'UPDATE portal.comet_digest_deliveries SET status = %s, last_error = %s, updated_at = now(), '
            'sent_at = CASE WHEN %s THEN now() ELSE sent_at END WHERE week_start = %s AND recipient = %s AND status = \'reservado\'',
            ('enviado' if sent else 'fallido', (error or '')[:200], bool(sent), week_start, clean_recipient(recipient)))


@writable_only
def set_mark(personid, mark: str, active: bool, note: str = '') -> None:
    """Marca o desmarca a un jugador como proyectado o de selección (no borra: desactiva)."""
    actor = require_admin()
    values = (clean_person(personid), clean_mark(mark), bool(active), clean_note(note), actor['id'])
    with _db() as db:
        db.execute(
            'INSERT INTO portal.comet_player_marks(personid, mark, active, note, updated_by) VALUES (%s, %s, %s, %s, %s) '
            'ON CONFLICT (personid, mark) DO UPDATE SET active = EXCLUDED.active, note = EXCLUDED.note, '
            'updated_by = EXCLUDED.updated_by, updated_at = now()', values)


@writable_only
def add_period(personid, kind: str, starts_on: date, ends_on: date, note: str = '') -> None:
    actor = require_admin()
    values = clean_period(personid, kind, starts_on, ends_on, note) + (actor['id'],)
    with _db() as db:
        db.execute(
            'INSERT INTO portal.comet_selection_periods(personid, kind, starts_on, ends_on, note, created_by) '
            'VALUES (%s, %s, %s, %s, %s, %s)', values)


@writable_only
def retire_period(period_id: int) -> None:
    """Retira un período (queda inactivo, con quién y cuándo lo retiró; no se borra)."""
    actor = require_admin()
    with _db() as db:
        db.execute('UPDATE portal.comet_selection_periods SET active = false, retired_by = %s, retired_at = now() '
                   'WHERE id = %s AND active', (actor['id'], int(period_id)))


# --- Bajas de jugadores (migración 005) ---------------------------------------------------------------

_BAJAS_SELECT = ('SELECT personid, active, reason, effective_on, note, updated_at FROM portal.comet_player_bajas '
                 'ORDER BY updated_at DESC')


def _fetch_bajas(db) -> pd.DataFrame:
    return pd.DataFrame(db.execute(_BAJAS_SELECT).fetchall(), columns=BAJA_COLUMNS)


def load_bajas() -> pd.DataFrame:
    """Bajas registradas (vigentes y reincorporadas). `StoreUnavailable` si falta aplicar la migración 005."""
    require_admin()
    with _db(BAJAS_MIGRATION) as db:
        return _fetch_bajas(db)


def load_bajas_for_job() -> pd.DataFrame:
    """Igual que `load_bajas` para el script operativo del resumen semanal (sin sesión; solo lee). Ver `load_all_for_job`."""
    with _db(BAJAS_MIGRATION) as db:
        return _fetch_bajas(db)


def load_roster_config() -> tuple[dict, pd.DataFrame, str | None]:
    """Reglas guardadas y bajas con una sola conexión, para las pantallas del plantel.

    Si falta la migración 005 devuelve las reglas con una lista de bajas vacía y el motivo (la regla automática sigue
    funcionando); si falta la 003 o no hay conexión, lanza `StoreUnavailable`.
    """
    require_admin()
    with _db() as db:
        settings = db.execute('SELECT key, value, confirmed FROM portal.comet_settings').fetchall()
        present = db.execute("SELECT to_regclass('portal.comet_player_bajas') IS NOT NULL AS present").fetchone()['present']
        bajas = _fetch_bajas(db) if present else None
    stored = {r['key']: {'value': r['value'], 'confirmed': r['confirmed']} for r in settings}
    if bajas is None:
        return stored, EMPTY_BAJAS, f'Falta aplicar db/portal/{BAJAS_MIGRATION} en Supabase.'
    return stored, bajas, None


@writable_only
def set_bajas(personids, reason: str, effective_on, note: str = '') -> int:
    """Da de baja a uno o varios jugadores con el mismo motivo, fecha y nota (una sola transacción). No borra nada:
    una baja anterior del mismo jugador se actualiza y vuelve a quedar vigente. Devuelve cuántos se registraron."""
    actor = require_admin()
    ids = sorted({clean_person(p) for p in personids})
    if not ids:
        raise ValueError('Elige al menos un jugador.')
    if len(ids) > MAX_BAJAS_AT_ONCE:
        raise ValueError(f'Registra hasta {MAX_BAJAS_AT_ONCE} bajas a la vez.')
    _, reason, day, note = clean_baja(ids[0], reason, effective_on, note)
    with _db(BAJAS_MIGRATION) as db:
        for pid in ids:
            db.execute(
                'INSERT INTO portal.comet_player_bajas(personid, active, reason, effective_on, note, created_by, updated_by) '
                'VALUES (%s, true, %s, %s, %s, %s, %s) '
                'ON CONFLICT (personid) DO UPDATE SET active = true, reason = EXCLUDED.reason, '
                'effective_on = EXCLUDED.effective_on, note = EXCLUDED.note, '
                'updated_by = EXCLUDED.updated_by, updated_at = now()',
                (pid, reason, day, note, actor['id'], actor['id']))
    return len(ids)


@writable_only
def reinstate_bajas(personids) -> int:
    """Reincorpora a jugadores: la baja queda inactiva (con quién y cuándo), no se borra.

    Devuelve a cuántos se reincorporó de verdad: quien ya no tenía una baja vigente (otra persona lo reincorporó antes) no cuenta.
    """
    actor = require_admin()
    ids = sorted({clean_person(p) for p in personids})
    if not ids:
        raise ValueError('Elige al menos un jugador.')
    changed = 0
    with _db(BAJAS_MIGRATION) as db:
        for pid in ids:
            changed += db.execute('UPDATE portal.comet_player_bajas SET active = false, updated_by = %s, updated_at = now() '
                                  'WHERE personid = %s AND active', (actor['id'], pid)).rowcount
    return changed
