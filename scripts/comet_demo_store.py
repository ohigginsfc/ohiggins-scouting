"""Almacén EN MEMORIA que sustituye a Supabase en la demostración con datos ficticios.

No abre conexiones ni escribe en disco: todo desaparece al cerrar el proceso. Usa las mismas
validaciones que `scouting.comet.config_store`, así que se comporta igual que el almacén real.
"""
from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from scouting.comet import config_store
from scouting.portal.security import require_admin

_settings: dict = {}
_marks: dict = {}
_periods: list = []


def _frames():
    marks = pd.DataFrame(
        [dict(personid=p, mark=m, **v) for (p, m), v in _marks.items()],
        columns=['personid', 'mark', 'active', 'note', 'updated_at'])
    periods = pd.DataFrame(_periods, columns=['id', 'personid', 'kind', 'starts_on', 'ends_on', 'note', 'active'])
    return marks, periods.assign(start=pd.to_datetime(periods['starts_on']), end=pd.to_datetime(periods['ends_on']))


def load_all():
    require_admin()
    marks, periods = _frames()
    return dict(_settings), marks, periods


def save_setting(key, value, *, confirmed=False):
    require_admin()
    _settings[key] = {'value': config_store.clean_setting(key, value), 'confirmed': bool(confirmed)}


def set_mark(personid, mark, active, note=''):
    require_admin()
    key = (config_store.clean_person(personid), config_store.clean_mark(mark))
    _marks[key] = dict(active=bool(active), note=config_store.clean_note(note), updated_at=datetime.now())


def add_period(personid, kind, starts_on: date, ends_on: date, note=''):
    require_admin()
    person, kind, start, end, note = config_store.clean_period(personid, kind, starts_on, ends_on, note)
    _periods.append(dict(id=len(_periods) + 1, personid=person, kind=kind, starts_on=start, ends_on=end,
                         note=note, active=True))


def retire_period(period_id):
    require_admin()
    for period in _periods:
        if period['id'] == int(period_id):
            period['active'] = False


def install() -> None:
    """Reemplaza las funciones de lectura y escritura de `config_store` por las de memoria."""
    for name in ('load_all', 'save_setting', 'set_mark', 'add_period', 'retire_period'):
        setattr(config_store, name, globals()[name])
