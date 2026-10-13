"""Descarga completa, normalización y publicación; sin correos ni informes en Sheets."""
from __future__ import annotations

import math
import os
import pandas as pd

from .api import CometAPI
from .db_pipeline import SPECS, clean_df
from .publisher import Publisher, TABLES

REPORTS = {
    'competiciones': 'competiciones', 'equipos': 'equipos_en_competencia',
    'competidores': 'equipos_en_competencia', 'jugadores': 'registro_de_personas',
    'partidos': 'listado_de_partidos_con_informacion_general', 'posiciones': 'tabla_de_posiciones',
    'partidos_fases': 'fases_de_partidos', 'eventos_partido': 'eventos_de_partido',
    'partidos_cambios_estado': 'cambios_de_estado_de_partidos',
    'partidos_cambios_estado_equipo': 'cambios_de_estado-equipo_de_partido',
    'actuaciones_jugadores': 'actuaciones_de_jugadores', 'actuaciones_arqueros': 'actuaciones_de_arqueros',
}


def configured_api():
    try:
        delay = float(os.environ.get('COMET_REQUEST_DELAY', '3'))
    except ValueError:
        raise ValueError('COMET_REQUEST_DELAY debe ser un número entre 3 y 60 segundos') from None
    if not math.isfinite(delay) or not 3 <= delay <= 60:
        raise ValueError('COMET_REQUEST_DELAY debe estar entre 3 y 60 segundos')
    return CometAPI(sleep_between_pages=delay, max_retries=6, max_retry_wait=120)


def prepare(api):
    api.load_configured_endpoints()
    api.validate_endpoints(api.endpoints, required=REPORTS.values())
    api.fetch_all()
    frames = {}
    for table in TABLES:
        raw = api.get(REPORTS[table])
        spec = SPECS[table]
        if raw.empty and not len(raw.columns):
            # A valid empty child report has no columns in the JSON API. Critical
            # catalogs remain mandatory so an empty/misconfigured source fails.
            if table in ('competiciones', 'equipos', 'competidores', 'partidos', 'jugadores'):
                raise ValueError(f'COMET {table}: catálogo vacío; publicación detenida')
            raw = pd.DataFrame(columns=spec.cols)
        frames[table] = clean_df(raw, spec)
        if table in ('competiciones', 'equipos', 'competidores', 'partidos', 'jugadores') and frames[table].empty:
            raise ValueError(f'COMET {table}: catálogo sin filas válidas; publicación detenida')
    return frames


def run_sync(*, dry_run=True, api=None, publisher_factory=Publisher.from_env, out=print):
    frames = prepare(api if api is not None else configured_api())
    summary = {'mode': 'dry-run' if dry_run else 'publish', 'complete': False,
               'rows_prepared': sum(len(frame) for frame in frames.values()), 'rows_published': 0,
               'tables': {table: {'prepared': len(frame), 'published': 0,
                                  'cleaning': frame.attrs.get('cleaning', {})} for table, frame in frames.items()}}
    if not dry_run:
        publisher = publisher_factory()
        for table in TABLES:
            written = publisher.upsert(table, frames[table])
            if written != len(frames[table]):
                raise RuntimeError(f'COMET {table}: publicación incompleta')
            summary['tables'][table]['published'] = written
            summary['rows_published'] += written
            out(f'COMET {table}: {written} filas publicadas')
    summary['complete'] = True
    out(f"COMET {summary['mode']}: {summary['rows_prepared']} filas preparadas; {summary['rows_published']} publicadas")
    return summary
