"""Persistencia en Supabase (esquema privado `portal`) de reglas, alertas, marcas y períodos.

Solo administración lee o escribe: cada función llama a `require_admin()` antes de abrir
una conexión. COMET se lee con `comet_reader` (solo lectura) y no guarda nada; por eso esta
configuración vive en `portal`, con la conexión `portal_runtime` que ya usan las cuentas.
Requiere aplicar `db/portal/003_comet_followup.sql`; si no está aplicada, lanza
`StoreUnavailable` y la interfaz sigue con los valores por defecto, en solo lectura.
"""
from __future__ import annotations

import re
from contextlib import contextmanager
from datetime import date
from typing import Any

import pandas as pd
import psycopg
from psycopg.types.json import Jsonb

from scouting.portal import accounts
from scouting.portal.security import require_admin

from .alerts import ALERT_COLORS, ALERTS_BY_KEY
from .rules import RULES_BY_KEY, parse

MARKS = {'proyectado': 'Jugador proyectado', 'seleccion': 'Jugador de selección'}
PERIOD_KINDS = {'microciclo': 'Microciclo de selección', 'sudamericano': 'Sudamericano', 'mundial': 'Mundial'}
ALERT_CONFIG_KEY = 'alert_config'
_ID = re.compile(r'^[0-9A-Za-z_-]{1,40}$')


class StoreUnavailable(RuntimeError):
    """La base de configuración no está disponible o falta aplicar la migración 003."""


@contextmanager
def _db():
    try:
        with accounts.connect() as db:
            yield db
    except psycopg.errors.UndefinedTable:
        raise StoreUnavailable('Falta aplicar db/portal/003_comet_followup.sql en Supabase.') from None
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


def set_mark(personid, mark: str, active: bool, note: str = '') -> None:
    """Marca o desmarca a un jugador como proyectado o de selección (no borra: desactiva)."""
    actor = require_admin()
    values = (clean_person(personid), clean_mark(mark), bool(active), clean_note(note), actor['id'])
    with _db() as db:
        db.execute(
            'INSERT INTO portal.comet_player_marks(personid, mark, active, note, updated_by) VALUES (%s, %s, %s, %s, %s) '
            'ON CONFLICT (personid, mark) DO UPDATE SET active = EXCLUDED.active, note = EXCLUDED.note, '
            'updated_by = EXCLUDED.updated_by, updated_at = now()', values)


def add_period(personid, kind: str, starts_on: date, ends_on: date, note: str = '') -> None:
    actor = require_admin()
    values = clean_period(personid, kind, starts_on, ends_on, note) + (actor['id'],)
    with _db() as db:
        db.execute(
            'INSERT INTO portal.comet_selection_periods(personid, kind, starts_on, ends_on, note, created_by) '
            'VALUES (%s, %s, %s, %s, %s, %s)', values)


def retire_period(period_id: int) -> None:
    """Retira un período (queda inactivo, con quién y cuándo lo retiró; no se borra)."""
    actor = require_admin()
    with _db() as db:
        db.execute('UPDATE portal.comet_selection_periods SET active = false, retired_by = %s, retired_at = now() '
                   'WHERE id = %s AND active', (actor['id'], int(period_id)))
