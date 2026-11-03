"""Plantel vigente: quién cuenta hoy como jugador del club y quién ya no.

COMET no borra a un jugador que deja el club (la sincronización solo hace upserts) y, por lo que se ve en las pantallas, lo
sigue mostrando como «ACTIVO»: el Primer Equipo llegaba a sumar cientos de jugadores. Aquí se decide, con datos que sí
existen y sin borrar nada, quién sigue en el plantel (en este orden):

  1. Baja registrada por un administrador (reversible): queda fuera.
  2. Figuró en la planilla de un partido de O'Higgins dentro de los últimos N días (regla `squad_activity_days`).
  3. O su ficha trae una fecha `datefrom` dentro de esos N días (alta reciente que todavía no tiene partidos).
  4. Todo lo demás: «sin actividad reciente». No se asume que se fue: queda a la vista en la revisión del plantel.

No se usa ninguna fecha de salida o de fin de contrato: no está confirmado que COMET la entregue ni qué significaría
(pregunta para Pablo).
Este módulo no abre conexiones: recibe el plantel ya leído.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Iterable, Optional

import pandas as pd

from .categories import SENIOR_LABEL
from .facts import _local_datetime, civil_date, norm_id

STATE_CURRENT = 'Vigente'
STATE_INACTIVE = 'Sin actividad reciente'
STATE_BAJA = 'Baja registrada'
STATES = (STATE_CURRENT, STATE_INACTIVE, STATE_BAJA)

DEFAULT_WINDOWS = (90, 180, 365, 730, 1095)   # ventanas que se comparan para elegir la regla

BAJA_COLUMNS = ['personid', 'active', 'reason', 'effective_on', 'note', 'updated_at']
EMPTY_BAJAS = pd.DataFrame(columns=BAJA_COLUMNS)
# Motivos de baja: lista corta provisional (no la fijó Pablo); la nota libre cubre el resto.
BAJA_REASONS = {'dejo_club': 'Dejó el club', 'cedido': 'Cedido a otro club', 'transferido': 'Transferido',
                'otro': 'Otro motivo (ver la nota)'}


def active_baja_ids(bajas: Optional[pd.DataFrame]) -> frozenset:
    """Identificadores (como texto estable) de los jugadores con una baja vigente."""
    if bajas is None or bajas.empty:
        return frozenset()
    active = bajas[bajas['active'].astype(bool)]
    return frozenset(filter(None, active['personid'].map(norm_id)))


def _days_text(days: int) -> str:
    return 'hoy' if days <= 0 else ('hace 1 día' if days == 1 else f'hace {days} días')


def classify(squad: pd.DataFrame, today, activity_days: int, bajas: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Una fila por jugador registrado, con `state`, `reason`, `last_sheet` (día) y `days_since`.

    `squad` trae `personid` y, si existen, `last_match` (último partido de O'Higgins en que figuró) y `datefrom`.
    Un dato que falta no se completa: sin planilla ni `datefrom` reciente el jugador queda «sin actividad reciente».
    """
    out = squad.copy()
    out['personid'] = out['personid'].map(norm_id)
    today_day = pd.Timestamp(today).normalize()
    limit = today_day - timedelta(days=int(activity_days))

    if 'last_match' in out:
        last = _local_datetime(out['last_match']).dt.normalize()
    else:
        last = pd.Series(pd.NaT, index=out.index, dtype='datetime64[ns]')
    if 'datefrom' in out:
        since = civil_date(out['datefrom'])
    else:
        since = pd.Series(pd.NaT, index=out.index, dtype='datetime64[ns]')
    days_since = (today_day - last).dt.days
    out['last_sheet'] = last
    out['days_since'] = days_since

    baja_info = {}
    if bajas is not None and not bajas.empty:
        for row in bajas[bajas['active'].astype(bool)].itertuples():
            baja_info[norm_id(row.personid)] = row
    recent_match = last >= limit
    recent_since = (since >= limit) & (since <= today_day)

    states, reasons = [], []
    for pid, is_match, is_since, day, days, start in zip(out['personid'], recent_match, recent_since, last, days_since, since):
        if pid in baja_info:
            row = baja_info[pid]
            when = pd.Timestamp(row.effective_on).strftime('%d-%m-%Y') if pd.notna(row.effective_on) else 'fecha sin registrar'
            states.append(STATE_BAJA)
            text = f'{BAJA_REASONS.get(row.reason, row.reason)} · desde {when}'
            if pd.notna(row.effective_on) and pd.notna(day) and day > pd.Timestamp(row.effective_on):
                # La baja manda, pero si el jugador volvió a una planilla el administrador debe saberlo para decidir.
                text += f' · atención: figura en una planilla posterior ({day:%d-%m-%Y})'
            reasons.append(text)
        elif is_match:
            states.append(STATE_CURRENT)
            reasons.append(f'Última planilla: {day:%d-%m-%Y} ({_days_text(int(days))})')
        elif is_since:
            states.append(STATE_CURRENT)
            reasons.append(f'Alta reciente: datefrom {start:%d-%m-%Y}, todavía sin planilla')
        else:
            states.append(STATE_INACTIVE)
            reasons.append('Nunca figuró en una planilla de O’Higgins' if pd.isna(day) else
                           f'Última planilla: {day:%d-%m-%Y} ({_days_text(int(days))}, fuera de los {int(activity_days)} días)')
    out['state'] = states
    out['reason'] = reasons
    return out


def current(classified: pd.DataFrame) -> pd.DataFrame:
    """Solo los jugadores vigentes (mismas columnas que el plantel leído)."""
    return classified[classified['state'] == STATE_CURRENT]


def summary_by_category(classified: pd.DataFrame, order: Iterable[str]) -> pd.DataFrame:
    """Cuántos registros hay por categoría y estado: lo que cuenta, lo que no y el total registrado en COMET."""
    table = pd.crosstab(classified['age_category'], classified['state']).reindex(columns=list(STATES), fill_value=0)
    table = table.reindex([c for c in order if c in table.index]).fillna(0).astype(int)
    table['Registrados en COMET'] = table.sum(axis=1)
    return table.reset_index().rename(columns={'age_category': 'Categoría', STATE_CURRENT: 'Vigentes'})


def calibration(squad: pd.DataFrame, today, bajas: Optional[pd.DataFrame] = None,
                windows: Iterable[int] = DEFAULT_WINDOWS) -> pd.DataFrame:
    """Cuántos jugadores quedarían vigentes con cada ventana: sirve para elegir el valor de la regla con datos a la vista."""
    rows = []
    for days in windows:
        done = classify(squad, today, days, bajas)
        vigente = current(done)
        category = vigente['age_category']
        rows.append({'Días sin planilla': int(days), 'Vigentes': len(vigente),
                     SENIOR_LABEL: int((category == SENIOR_LABEL).sum()),
                     'Categorías menores': int((category.notna() & (category != SENIOR_LABEL)).sum())})
    return pd.DataFrame(rows)
