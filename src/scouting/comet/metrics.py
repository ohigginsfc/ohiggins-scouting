"""Métricas por jugador, categoría y partido a partir de un `Dataset`."""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from .facts import (Dataset, RESULT_DRAW, RESULT_LOSS, RESULT_WIN, ROLE_SUB_IN, ROLE_SUB_OUT, ROLE_STARTER)

EMPTY_PERIODS = pd.DataFrame(columns=['personid', 'start', 'end', 'kind', 'active'])


def _sum(series: pd.Series):
    return series.sum(min_count=1)  # NaN si todo falta; no se disfraza de 0


def possible_minutes(ds: Dataset, periods: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Minutos posibles por jugador y competición.

    Regla supuesta (pendiente de Pablo): todos los partidos ya jugados de la competición donde el
    jugador fue citado alguna vez, con la duración registrada en cada partido. Los partidos sin
    minutos registrados no se cuentan porque su duración se desconoce.
    """
    rules = ds.rules
    known = ds.matches.loc[ds.matches['duration'].notna(), ['matchid', 'competition_id', 'matchdate', 'duration']]
    calls = ds.facts.groupby(['personid', 'competition_id'], as_index=False).agg(first_call=('matchdate', 'min'))
    grid = calls.merge(known, on='competition_id', how='inner')
    if rules.value('possible_from_first_call'):
        grid = grid[grid['matchdate'].dt.normalize() >= grid['first_call'].dt.normalize()]
    if rules.value('exclude_selection_periods') and periods is not None and len(periods):
        active = periods[periods['active'].astype(bool)][['personid', 'start', 'end']]
        joined = grid.merge(active, on='personid', how='inner')
        day = joined['matchdate'].dt.normalize()
        hit = joined[(day >= joined['start']) & (day <= joined['end'])][['personid', 'matchid']].drop_duplicates()
        grid = grid.merge(hit.assign(_excluded=True), on=['personid', 'matchid'], how='left')
        grid = grid[grid['_excluded'].isna()].drop(columns='_excluded')
    return grid.groupby(['personid', 'competition_id'], as_index=False).agg(
        possible_minutes=('duration', 'sum'), possible_matches=('matchid', 'nunique'))


def player_competition_summary(ds: Dataset, periods: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Una fila por jugador y competición: partidos, roles, minutos, goles, tarjetas y resultados."""
    f = ds.facts
    min_minutes = ds.rules.value('min_minutes_on_pitch')
    on_pitch = f['participated'] & (f['minutes'] >= min_minutes)
    known = on_pitch & f['result'].notna()
    work = f.assign(
        is_starter=f['role'].eq(ROLE_STARTER), is_sub_in=f['role'].eq(ROLE_SUB_IN),
        is_only_called=f['role'].eq(ROLE_SUB_OUT), played_flag=f['participated'],
        with_win=on_pitch & f['result'].eq(RESULT_WIN), with_draw=on_pitch & f['result'].eq(RESULT_DRAW),
        with_loss=on_pitch & f['result'].eq(RESULT_LOSS), with_result=known)
    keys = ['personid', 'competition_id']
    out = work.groupby(keys, as_index=False).agg(
        displayname=('displayname', 'first'), competition=('competition', 'first'),
        category=('category', 'first'), category_rank=('category_rank', 'first'),
        season_year=('season_year', 'first'), age=('age', 'first'), age_category=('age_category', 'first'),
        cited=('matchid', 'nunique'), started=('is_starter', 'sum'), sub_in=('is_sub_in', 'sum'),
        only_called=('is_only_called', 'sum'), played=('played_flag', 'sum'),
        minutes=('minutes', _sum), goals=('goals', _sum),
        yellow_cards=('yellow_cards', _sum), red_cards=('red_cards', _sum),
        wins_with=('with_win', 'sum'), draws_with=('with_draw', 'sum'),
        losses_with=('with_loss', 'sum'), results_with=('with_result', 'sum'),
        ahead_minutes=('ahead_minutes', _sum),
        first_call=('matchdate', 'min'), last_call=('matchdate', 'max'))
    out = out.merge(possible_minutes(ds, periods), on=keys, how='left')
    return out


def _percentages(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    possible = frame['possible_minutes'].where(frame['possible_minutes'] > 0)
    frame['participation_pct'] = (frame['minutes'] / possible * 100).round(1)
    results = frame['results_with'].where(frame['results_with'] > 0)
    frame['win_pct_with'] = (frame['wins_with'] / results * 100).round(1)
    return frame


def add_percentages(comp_summary: pd.DataFrame) -> pd.DataFrame:
    return _percentages(comp_summary)


_SUM_COLUMNS = ['cited', 'started', 'sub_in', 'only_called', 'played', 'wins_with', 'draws_with',
                'losses_with', 'results_with', 'possible_matches']
_NAN_SUM_COLUMNS = ['minutes', 'goals', 'yellow_cards', 'red_cards', 'ahead_minutes', 'possible_minutes']


def category_summary(comp_summary: pd.DataFrame) -> pd.DataFrame:
    """Suma las competiciones de una misma categoría y temporada (una fila por jugador)."""
    keys = ['personid', 'season_year', 'category']
    agg = {c: (c, 'sum') for c in _SUM_COLUMNS}
    agg.update({c: (c, _sum) for c in _NAN_SUM_COLUMNS})
    agg.update(displayname=('displayname', 'first'), category_rank=('category_rank', 'first'),
               age=('age', 'first'), age_category=('age_category', 'first'),
               first_call=('first_call', 'min'), last_call=('last_call', 'max'))
    return _percentages(comp_summary.groupby(keys, as_index=False).agg(**agg))


def principal_categories(cat_summary: pd.DataFrame) -> pd.DataFrame:
    """Categoría de cada jugador en cada temporada: donde sumó más minutos (luego citaciones y rango)."""
    ordered = cat_summary.assign(_minutes=cat_summary['minutes'].fillna(-1)).sort_values(
        ['_minutes', 'cited', 'category_rank'], ascending=False)
    return ordered.groupby(['personid', 'season_year'], as_index=False).head(1).drop(columns='_minutes')


def seasons_without_promotion(principal: pd.DataFrame, season_year: int) -> pd.DataFrame:
    """Temporadas seguidas en la misma categoría, contadas hacia atrás desde `season_year`.

    Una promoción es una categoría mayor que la de la temporada anterior. Un hueco de temporadas
    corta el conteo: no se afirma nada sobre años sin datos.
    """
    rows = []
    history_start = int(principal['season_year'].min()) if len(principal) else None
    for pid, grp in principal.groupby('personid'):
        by_season = grp.sort_values('season_year').set_index('season_year')
        if season_year not in by_season.index:
            continue
        streak, year = 1, season_year
        while year - 1 in by_season.index and (
                by_season.loc[year, 'category_rank'] <= by_season.loc[year - 1, 'category_rank']):
            streak, year = streak + 1, year - 1
        row = by_season.loc[season_year]
        rows.append(dict(personid=pid, displayname=row['displayname'], category=row['category'],
                         category_rank=row['category_rank'], seasons_in_category=streak,
                         since_season=year, history_start=history_start))
    return pd.DataFrame(rows, columns=['personid', 'displayname', 'category', 'category_rank',
                                       'seasons_in_category', 'since_season', 'history_start'])


RANKING_METRICS = {
    'Minutos jugados': 'minutes',
    'Goles': 'goals',
    'Tarjetas amarillas': 'yellow_cards',
    'Tarjetas rojas': 'red_cards',
    'Partidos ganados con el jugador en cancha': 'wins_with',
}


def ranking(cat_summary: pd.DataFrame, metric: str, *, category: str, season_year: int,
            top: Optional[int] = None) -> pd.DataFrame:
    """Ranking de una categoría y temporada. Empates comparten posición; sin datos o en 0 no entran."""
    column = RANKING_METRICS[metric]
    scope = cat_summary[(cat_summary['category'] == category) & (cat_summary['season_year'] == season_year)]
    scope = scope[scope[column].fillna(0) > 0]
    tie_break = ['minutes'] if column != 'minutes' else ['cited']
    scope = scope.sort_values([column] + tie_break + ['displayname'], ascending=[False, False, True],
                              na_position='last')
    scope = scope.assign(position=scope[column].rank(method='min', ascending=False).astype(int))
    return scope.head(top) if top else scope


def minutes_timeline(ds: Dataset, personid: str, freq: str = 'Mes') -> pd.DataFrame:
    """Minutos del jugador por mes o semestre.

    Solo aparecen los períodos en que O'Higgins jugó en alguna categoría donde el jugador fue citado
    esa temporada: 0 minutos allí es un 0 real; un mes sin partidos no se dibuja como 0.
    """
    f = ds.facts[ds.facts['personid'] == personid]
    if f.empty:
        return pd.DataFrame(columns=['periodo', 'category', 'minutes', 'matches'])
    cited = f[['season_year', 'category']].drop_duplicates()
    calendar = ds.matches.merge(cited, on=['season_year', 'category'], how='inner')
    calendar = calendar[calendar['matchdate'].notna()]

    def label(dates: pd.Series) -> pd.Series:
        if freq == 'Semestre':
            return dates.dt.year.astype(str) + ' · S' + np.where(dates.dt.month <= 6, '1', '2')
        return dates.dt.strftime('%Y-%m')

    calendar = calendar.assign(periodo=label(calendar['matchdate']))
    mine = f.assign(periodo=label(f['matchdate']))
    played = mine.groupby(['periodo', 'category'], as_index=False).agg(
        minutes=('minutes', _sum), played=('participated', 'sum'))
    base = calendar.groupby(['periodo', 'category'], as_index=False).agg(matches=('matchid', 'nunique'))
    out = base.merge(played, on=['periodo', 'category'], how='left')
    out['minutes'] = out['minutes'].where(out['played'].notna(), 0.0)  # sin filas propias: no jugó
    return out.drop(columns='played').sort_values(['periodo', 'category']).reset_index(drop=True)


def match_sheet(ds: Dataset, matchid: str) -> pd.DataFrame:
    """Planilla de un partido: una fila por jugador con su rol, minutos, goles y tarjetas."""
    sheet = ds.facts[ds.facts['matchid'] == matchid]
    order = {ROLE_STARTER: 0, ROLE_SUB_IN: 1, ROLE_SUB_OUT: 2}
    sheet = sheet.assign(_order=sheet['role'].map(order).fillna(3))
    return sheet.sort_values(['_order', 'minutes', 'displayname'], ascending=[True, False, True],
                             na_position='last').drop(columns='_order').reset_index(drop=True)


def not_called_reference(ds: Dataset, matchid: str) -> pd.DataFrame:
    """Referencial: figuran en otra planilla de la misma competición pero no en ésta.

    Es un sustituto mientras COMET no entregue el plantel de cada serie (pregunta abierta para Pablo).
    """
    match = ds.matches[ds.matches['matchid'] == matchid]
    if match.empty:
        return pd.DataFrame(columns=['personid', 'displayname'])
    competition = match['competition_id'].iloc[0]
    in_competition = ds.facts[ds.facts['competition_id'] == competition]
    called = set(ds.facts.loc[ds.facts['matchid'] == matchid, 'personid'])
    others = in_competition[~in_competition['personid'].isin(called)]
    return (others.groupby('personid', as_index=False)
            .agg(displayname=('displayname', 'first'), citaciones=('matchid', 'nunique'))
            .sort_values('displayname').reset_index(drop=True))


def goalkeeper_conceded(ds: Dataset, matchid: Optional[str] = None) -> pd.DataFrame:
    """Goles recibidos por arquero; se muestra "sin dato" si COMET no trae la fila del arquero."""
    g = ds.goalkeepers
    if matchid is not None:
        g = g[g['matchid'] == matchid]
    g = g[((g['played'] == True).fillna(False) | (g['minutesplayed'] > 0)).astype(bool)]  # noqa: E712
    names = ds.players.set_index('personid')['displayname']
    return g.assign(displayname=g['personid'].map(names))[
        ['matchid', 'competition_id', 'personid', 'displayname', 'minutesplayed', 'goalsconceded']]
