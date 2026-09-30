"""Indicadores por categoría: edad, antigüedad, minutos de jugadores más chicos, resultados."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .categories import elapsed_years
from .facts import Dataset, RESULT_DRAW, RESULT_LOSS, RESULT_WIN

YOUNGER_BUCKETS = ['min_tope_o_mayor', 'min_menor_1', 'min_menor_2', 'min_menor_3', 'min_menor_4_o_mas']


def _sum(series: pd.Series):
    return series.sum(min_count=1)


def first_seen(ds: Dataset) -> pd.Series:
    """Fecha del primer partido de O'Higgins registrado por jugador (base de la antigüedad mínima)."""
    return ds.facts.groupby('personid')['matchdate'].min()


def seniority_years(ds: Dataset, today) -> pd.Series:
    """Antigüedad en años según la regla `seniority_rule` (por jugador, indexada por personid).

    `primer_partido`: desde el primer partido registrado (un mínimo: no llega más atrás que el historial).
    `datefrom`: desde la fecha `datefrom` de la ficha; sin esa fecha la antigüedad queda sin dato, no se
    sustituye por la otra fuente. Años por aniversario, no por división entre 365,25.
    """
    if ds.rules.value('seniority_rule') == 'datefrom':
        start = ds.players.set_index('personid')['datefrom']
    else:
        start = first_seen(ds)
    years = start.map(lambda day: elapsed_years(day, today))
    return pd.to_numeric(years, errors='coerce').round(2)


def _bucket(years_younger: pd.Series) -> pd.Series:
    labels = np.select(
        [years_younger.isna(), years_younger <= 0, years_younger == 1, years_younger == 2, years_younger == 3],
        ['sin_dato', 'min_tope_o_mayor', 'min_menor_1', 'min_menor_2', 'min_menor_3'], default='min_menor_4_o_mas')
    return pd.Series(labels, index=years_younger.index)


def minutes_by_years_younger(ds: Dataset, season_year: int) -> pd.DataFrame:
    """Minutos de cada categoría según cuántos años menor es el jugador que el tope de la categoría.

    `min_tope_o_mayor` = jugadores de la edad tope de la serie (o mayores); `min_menor_N` = N años menores.
    Primer Equipo no tiene tope de edad, por eso no se descompone.
    """
    f = ds.facts[(ds.facts['season_year'] == season_year) & ds.facts['participated']]
    f = f.assign(bucket=_bucket(f['years_younger']))
    f = f[f['category_rank'] < 1000]
    pivot = f.pivot_table(index='category', columns='bucket', values='minutes', aggfunc=_sum)
    for col in YOUNGER_BUCKETS + ['sin_dato']:
        if col not in pivot.columns:
            pivot[col] = np.nan
    pivot = pivot[YOUNGER_BUCKETS + ['sin_dato']]
    pivot['total_minutes'] = pivot.sum(axis=1, min_count=1)
    younger = pivot[['min_menor_1', 'min_menor_2', 'min_menor_3', 'min_menor_4_o_mas']].sum(axis=1, min_count=1)
    pivot['pct_menores'] = (younger.fillna(0) / pivot['total_minutes'].where(pivot['total_minutes'] > 0) * 100).round(1)
    return pivot.reset_index()


def category_indicators(ds: Dataset, cat_summary: pd.DataFrame, season_year: int, today) -> pd.DataFrame:
    """Una fila por categoría con los indicadores de la temporada."""
    f = ds.facts[ds.facts['season_year'] == season_year]
    seniority = seniority_years(ds, today)
    rows = []
    for category in ds.categories:
        cat_rows = f[f['category'] == category]
        if cat_rows.empty:
            continue
        people = cat_rows.drop_duplicates('personid')
        summary = cat_summary[(cat_summary['season_year'] == season_year) & (cat_summary['category'] == category)]
        possible = summary['possible_minutes'].sum(min_count=1)
        counted = summary['counted_minutes'].sum(min_count=1)
        played = cat_rows[cat_rows['participated']]
        series = ds.matches[(ds.matches['season_year'] == season_year) & (ds.matches['category'] == category)
                            & ds.matches['matchid'].isin(cat_rows['matchid'])]
        known = series[series['result'].notna()]
        keepers = ds.goalkeepers.merge(series[['matchid']], on='matchid')
        conceded = keepers['goalsconceded'].sum(min_count=1) if len(keepers) else np.nan
        rows.append(dict(
            category=category,
            partidos=len(series), victorias=int((known['result'] == RESULT_WIN).sum()),
            empates=int((known['result'] == RESULT_DRAW).sum()), derrotas=int((known['result'] == RESULT_LOSS).sum()),
            pct_victorias=round((known['result'] == RESULT_WIN).mean() * 100, 1) if len(known) else np.nan,
            jugadores_citados=len(people), jugadores_con_minutos=played['personid'].nunique(),
            edad_promedio=round(people['age'].mean(), 1) if people['age'].notna().any() else np.nan,
            antiguedad_promedio=round(people['personid'].map(seniority).mean(), 1),
            minutos_totales=played['minutes'].sum(min_count=1),
            participacion_pct=counted / possible * 100 if pd.notna(counted) and pd.notna(possible) and possible > 0 else np.nan,
            filas_contradictorias=int(cat_rows['conflict'].sum()),
            goles=played['goals'].sum(min_count=1),
            amarillas=cat_rows['yellow_cards'].sum(min_count=1), rojas=cat_rows['red_cards'].sum(min_count=1),
            goles_recibidos_arqueros=conceded))
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.merge(minutes_by_years_younger(ds, season_year)[['category'] + YOUNGER_BUCKETS + ['pct_menores']],
                     on='category', how='left')


def age_category_matrix(ds: Dataset, season_year: int) -> pd.DataFrame:
    """Jugadores por categoría que les corresponde por edad (filas) y categoría donde juegan (columnas)."""
    f = ds.facts[(ds.facts['season_year'] == season_year) & ds.facts['participated']]
    people = f.drop_duplicates(['personid', 'category'])
    matrix = pd.crosstab(people['age_category'].fillna('Sin fecha de nacimiento'), people['category'])
    ascending = list(reversed(ds.categories))  # U-12 ... U-19, Primer Equipo; así la diagonal es "juega en la suya"
    rows = [c for c in ascending if c in matrix.index] + [c for c in matrix.index if c not in ascending]
    return matrix.reindex(index=rows, columns=[c for c in ascending if c in matrix.columns])


def age_vs_category(ds: Dataset, season_year: int) -> pd.DataFrame:
    """Relación edad-categoría de cada jugador que participó: edad, categoría por edad, donde juega."""
    f = ds.facts[(ds.facts['season_year'] == season_year) & ds.facts['participated']]
    return (f.groupby(['personid', 'category'], as_index=False)
            .agg(displayname=('displayname', 'first'), age=('age', 'first'),
                 age_category=('age_category', 'first'), steps_ahead=('steps_ahead', 'max'),
                 minutes=('minutes', _sum)))
