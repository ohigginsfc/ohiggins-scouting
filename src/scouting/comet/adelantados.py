"""Indicadores de jugadores adelantados: los que juegan en una categoría superior a la de su edad."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .categories import steps_ahead
from .facts import Dataset


def _sum(series: pd.Series):
    return series.sum(min_count=1)


def left_out_players(ds: Dataset, season_year: int) -> set:
    """Quienes no entran en los indicadores de la temporada: una contradicción o un partido sin minutos conocidos
    en cualquier categoría invalida las tasas comparativas (minutos arriba, permanencia, goles por 90...)."""
    return set(ds.blocked_players(season_year)['personid']) | set(ds.minutes_gap_players(season_year)['personid'])


def _complete_facts(ds: Dataset, season_year: int) -> pd.DataFrame:
    return ds.facts[(ds.facts['season_year'] == season_year) & ~ds.facts['personid'].isin(left_out_players(ds, season_year))]


def ahead_players(ds: Dataset, season_year: int) -> pd.DataFrame:
    """Jugadores con minutos en una categoría superior a la que les corresponde por edad."""
    f = _complete_facts(ds, season_year)
    f = f[f['participated']]
    total = f.groupby('personid')['minutes'].agg(_sum)
    up = f[f['steps_ahead'] > 0]
    if up.empty:
        return pd.DataFrame(columns=['personid', 'displayname', 'age', 'age_category', 'plays_in', 'steps',
                                     'ahead_minutes', 'total_minutes', 'ahead_share_pct', 'ahead_matches',
                                     'first_date', 'last_date'])
    by_cat = up.groupby(['personid', 'category'], as_index=False).agg(
        displayname=('displayname', 'first'), age=('age', 'first'), age_category=('age_category', 'first'),
        steps=('steps_ahead', 'max'), ahead_minutes=('minutes', _sum), ahead_matches=('matchid', 'nunique'),
        first_date=('matchdate', 'min'), last_date=('matchdate', 'max'))
    out = by_cat.sort_values('ahead_minutes', ascending=False).groupby('personid', as_index=False).agg(
        displayname=('displayname', 'first'), age=('age', 'first'), age_category=('age_category', 'first'),
        plays_in=('category', lambda s: ', '.join(s)), steps=('steps', 'max'),
        ahead_minutes=('ahead_minutes', _sum), ahead_matches=('ahead_matches', 'sum'),
        first_date=('first_date', 'min'), last_date=('last_date', 'max'))
    out['total_minutes'] = out['personid'].map(total)
    out['ahead_share_pct'] = (out['ahead_minutes'] / out['total_minutes'].where(out['total_minutes'] > 0) * 100).round(1)
    return out.sort_values('ahead_minutes', ascending=False).reset_index(drop=True)


def ahead_share_by_category(ds: Dataset, season_year: int) -> pd.DataFrame:
    """Porcentaje de los jugadores de cada categoría que están adelantados (juegan por encima de su edad)."""
    f = _complete_facts(ds, season_year)
    f = f[f['participated']]
    rows = []
    for category, grp in f.groupby('category'):
        players = grp.drop_duplicates('personid')
        n_ahead = int((players['steps_ahead'] > 0).sum())
        minutes = grp['minutes'].sum(min_count=1)
        ahead_minutes = grp.loc[grp['steps_ahead'] > 0, 'minutes'].sum(min_count=1)
        rows.append(dict(category=category, jugadores=len(players), adelantados=n_ahead,
                         pct_adelantados=round(n_ahead / len(players) * 100, 1),
                         minutos=minutes, minutos_adelantados=ahead_minutes if n_ahead else 0.0))
    out = pd.DataFrame(rows, columns=['category', 'jugadores', 'adelantados', 'pct_adelantados',
                                      'minutos', 'minutos_adelantados'])
    order = {c: i for i, c in enumerate(ds.categories)}
    return out.sort_values('category', key=lambda s: s.map(order)).reset_index(drop=True)


def ahead_permanence(ds: Dataset, season_year: int) -> pd.DataFrame:
    """Minutos en la categoría superior por jugador y mes: cuánto se sostiene su permanencia en el año."""
    f = _complete_facts(ds, season_year)
    f = f[(f['steps_ahead'] > 0) & f['participated']]
    if f.empty:
        return pd.DataFrame(columns=['personid', 'displayname', 'mes', 'minutes'])
    f = f.assign(mes=f['matchdate'].dt.strftime('%Y-%m'))
    return (f.groupby(['personid', 'mes'], as_index=False)
            .agg(displayname=('displayname', 'first'), minutes=('minutes', _sum)))


def ahead_permanence_summary(ds: Dataset, season_year: int) -> pd.DataFrame:
    """Por adelantado: meses activos y qué parte de los partidos de la categoría superior jugó.

    "Desde su primera participación arriba" evita penalizarlo por partidos anteriores a su llegada.
    """
    f = _complete_facts(ds, season_year)
    up = f[(f['steps_ahead'] > 0) & f['participated']]
    rows = []
    for pid, grp in up.groupby('personid'):
        category = grp.groupby('category')['minutes'].sum(min_count=1).idxmax()
        first = grp.loc[grp['category'] == category, 'matchdate'].min()
        series = ds.matches[(ds.matches['season_year'] == season_year) & (ds.matches['category'] == category)
                            & (ds.matches['matchdate'] >= first)]
        mine = f[(f['personid'] == pid) & (f['category'] == category) & (f['matchdate'] >= first)]
        rows.append(dict(
            personid=pid, displayname=grp['displayname'].iloc[0], plays_in=category,
            months_active=grp['matchdate'].dt.strftime('%Y-%m').nunique(),
            first_date=first, matches_in_series=len(series), called=mine['matchid'].nunique(),
            played=int(mine['participated'].sum())))
    out = pd.DataFrame(rows, columns=['personid', 'displayname', 'plays_in', 'months_active', 'first_date',
                                      'matches_in_series', 'called', 'played'])
    total = out['matches_in_series'].where(out['matches_in_series'] > 0)
    out['called_pct'] = (out['called'] / total * 100).round(1)
    out['played_pct'] = (out['played'] / total * 100).round(1)
    return out.sort_values('played_pct', ascending=False).reset_index(drop=True)


def ahead_vs_peers(ds: Dataset, cat_summary: pd.DataFrame, season_year: int) -> pd.DataFrame:
    """Rendimiento de los adelantados frente a los jugadores de su misma edad que juegan en su categoría.

    Para cada categoría por edad X: `Adelantados` = jugadores de esa edad con minutos en una categoría
    superior (sus cifras allí); `Grupo de edad` = jugadores de esa edad que juegan en X.
    Con pocos jugadores la comparación es solo orientativa: la columna `jugadores` lo muestra.
    """
    cs = cat_summary[(cat_summary['season_year'] == season_year) & (cat_summary['played'] > 0)
                     & ~cat_summary['personid'].isin(left_out_players(ds, season_year))].copy()
    cs['steps'] = [steps_ahead(c, a, ds.categories) for c, a in zip(cs['category'], cs['age_category'])]
    cs['steps'] = pd.to_numeric(cs['steps'], errors='coerce')
    cs['group'] = np.select([cs['steps'] > 0, cs['steps'] == 0], ['Adelantados', 'Grupo de edad'], default='')
    cs = cs[cs['group'] != '']
    rows = []
    for (age_category, group), grp in cs.groupby(['age_category', 'group']):
        minutes = grp['minutes'].sum(min_count=1)
        results = grp['results_with'].sum()
        rows.append(dict(
            age_category=age_category, group=group, jugadores=grp['personid'].nunique(),
            partidos_jugados=int(grp['played'].sum()),
            minutos_por_partido=round(minutes / grp['played'].sum(), 1) if pd.notna(minutes) else np.nan,
            goles_por_90=round(grp['goals'].sum(min_count=1) * 90 / minutes, 2) if pd.notna(minutes) and minutes > 0 else np.nan,
            amarillas_por_90=round(grp['yellow_cards'].sum(min_count=1) * 90 / minutes, 2) if pd.notna(minutes) and minutes > 0 else np.nan,
            participacion_pct=round(grp['participation_pct'].mean(), 1) if grp['participation_pct'].notna().any() else np.nan,
            victorias_pct=round(grp['wins_with'].sum() / results * 100, 1) if results else np.nan))
    out = pd.DataFrame(rows, columns=['age_category', 'group', 'jugadores', 'partidos_jugados', 'minutos_por_partido',
                                      'goles_por_90', 'amarillas_por_90', 'participacion_pct', 'victorias_pct'])
    order = {c: i for i, c in enumerate(ds.categories)}
    return out.sort_values(['age_category', 'group'], key=lambda s: s.map(order) if s.name == 'age_category' else s
                           ).reset_index(drop=True)
