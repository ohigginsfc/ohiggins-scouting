"""Estadísticas por año de temporada para las pantallas SQL de COMET (Desarrollo juvenil, Análisis de jugadores y
Rendimiento por categoría).

Esas pantallas sumaban todos los años juntos, así que los goles no se podían separar por temporada. Las consultas traen
ahora una fila por año; aquí se elige un año (o se suman todos) y se arma la tabla de goles por año.

El año de una temporada es el mismo que usa el resto de COMET (`facts.season_year_of`): el primer año de cuatro cifras
del nombre de la temporada («2026», «2025/2026» → 2025) y, si no tiene, el año del partido.

Un año en el que el jugador no tiene partidos queda como dato ausente («—»); el 0 es haber jugado ese año sin marcar.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from .facts import season_year_of

ALL_YEARS = 'Todos los años'

PLAYER_KEY = ['personid', 'displayname', 'age', 'nationality', 'level', 'category']
SUMMED = ('matches', 'minutes', 'starts', 'goals', 'yellow_cards', 'red_cards')
STATS_COLUMNS = PLAYER_KEY + list(SUMMED) + ['avg_minutes', 'goals_per90']
KEEPER_KEY = ['personid', 'displayname', 'age', 'category']
KEEPER_SUMMED = ('matches', 'minutes', 'goals_conceded', 'clean_sheets')
KEEPER_COLUMNS = KEEPER_KEY + list(KEEPER_SUMMED) + ['gc_per90', 'clean_sheet_pct']


def _total(values: pd.Series):
    return values.sum(min_count=1)   # igual que SUM() en SQL: ignora los NULL; si todo falta, queda sin dato


def with_season_year(frame: pd.DataFrame, season: str = 'season', fallback: str = 'match_year') -> pd.DataFrame:
    """Agrega `season_year`: el año de la temporada o, si el nombre no trae año, el de `fallback` (año del partido)."""
    if frame.empty:
        return frame.assign(season_year=pd.array([], dtype='Int64'))
    seasons = frame[season] if season in frame else pd.Series(None, index=frame.index, dtype=object)
    backups = frame[fallback] if fallback in frame else pd.Series(None, index=frame.index, dtype=object)
    years = [season_year_of(s, None if pd.isna(b) else int(b)) for s, b in zip(seasons, backups)]
    return frame.assign(season_year=pd.array(years, dtype='Int64'))


def years_available(frame: pd.DataFrame, column: str = 'season_year') -> list[int]:
    """Años con datos, el más reciente primero."""
    if frame.empty or column not in frame:
        return []
    return sorted({int(y) for y in frame[column].dropna()}, reverse=True)


def in_year(frame: pd.DataFrame, year: Optional[int], column: str = 'season_year') -> pd.DataFrame:
    """Las filas de un año; con `year=None`, todas."""
    return frame if year is None else frame[frame[column] == year]


def label(year: Optional[int]) -> str:
    return ALL_YEARS if year is None else str(year)


def stats_for_year(by_year: pd.DataFrame, year: Optional[int] = None) -> pd.DataFrame:
    """Una fila por jugador y categoría: partidos, minutos, titularidades, goles y tarjetas del año elegido (o de todos).

    Quedan solo quienes suman más de 0 minutos en ese período (igual que la antigua consulta por categoría), con el
    promedio de minutos y los goles por 90 minutos recalculados sobre lo que se suma.
    """
    scope = in_year(by_year, year)
    if scope.empty:
        return pd.DataFrame(columns=STATS_COLUMNS)
    out = scope.groupby(PLAYER_KEY, as_index=False, dropna=False).agg(**{c: (c, _total) for c in SUMMED})
    out = out[out['minutes'] > 0].copy()
    out['avg_minutes'] = (out['minutes'] / out['matches'].where(out['matches'] > 0)).round(0)
    out['goals_per90'] = (out['goals'] * 90 / out['minutes']).round(2)
    return out.sort_values('minutes', ascending=False).reset_index(drop=True)


def keeper_stats_for_year(by_year: pd.DataFrame, year: Optional[int] = None) -> pd.DataFrame:
    """Lo mismo para arqueros: partidos, minutos, goles recibidos, vallas invictas y sus tasas del año elegido (o de todos)."""
    scope = in_year(by_year, year)
    if scope.empty:
        return pd.DataFrame(columns=KEEPER_COLUMNS)
    out = scope.groupby(KEEPER_KEY, as_index=False, dropna=False).agg(**{c: (c, _total) for c in KEEPER_SUMMED})
    out = out[out['minutes'] > 0].copy()
    out['gc_per90'] = (out['goals_conceded'] * 90 / out['minutes']).round(2)
    out['clean_sheet_pct'] = (out['clean_sheets'] * 100 / out['matches'].where(out['matches'] > 0)).round(1)
    return out.sort_values('minutes', ascending=False).reset_index(drop=True)


def goals_by_year(by_year: pd.DataFrame, players: pd.DataFrame) -> pd.DataFrame:
    """Goles de los jugadores de `players` (en su orden): una columna por año, más el total.

    Cada fila es un jugador en una categoría. Una celda vacía es un año sin partidos suyos en esa categoría.
    El total también incluye los goles cuyo año de temporada falta, sin atribuirlos a ningún año.
    """
    shown = players[['personid', 'displayname', 'category']].drop_duplicates(['personid', 'category'])
    keys = shown[['personid', 'category']]
    scope = by_year.merge(keys, on=['personid', 'category'], how='inner')
    if scope.empty:
        return shown.assign(Total=pd.Series(dtype=float))
    wide = scope.groupby(['personid', 'category', 'season_year'])['goals'].agg(_total).unstack('season_year')
    wide = wide[sorted(wide.columns)]
    wide.columns = [str(int(y)) for y in wide.columns]
    totals = scope.groupby(['personid', 'category'], dropna=False)['goals'].agg(_total).rename('Total')
    return shown.merge(wide.join(totals, how='outer').reset_index(), on=['personid', 'category'], how='left')


def year_columns(table: pd.DataFrame) -> list[str]:
    """Columnas de año de la tabla de `goals_by_year`, en orden."""
    return [c for c in table.columns if c.isdigit()]
