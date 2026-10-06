"""Métricas por jugador, categoría y partido a partir de un `Dataset`."""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from .facts import (Dataset, RESULT_DRAW, RESULT_LOSS, RESULT_WIN, ROLE_SUB_IN, ROLE_SUB_OUT, ROLE_STARTER)

EMPTY_PERIODS = pd.DataFrame(columns=['personid', 'start', 'end', 'kind', 'active'])


def _sum(series: pd.Series):
    return series.sum(min_count=1)  # NaN si todo falta; no se disfraza de 0


def _strict_sum(series: pd.Series):
    """Suma que no se afirma si falta algún sumando: un total con un dato desconocido es desconocido."""
    return np.nan if series.isna().any() else series.sum(min_count=1)


MINUTES_COLUMNS = ('minutes', 'ahead_minutes', 'counted_minutes')


def blank_unknown_minutes(frame: pd.DataFrame) -> pd.DataFrame:
    """Deja sin dato los totales de minutos de quien tiene algún partido sin minutos conocidos.

    Una suma parcial (80 minutos de un jugador que jugó dos partidos) no es un total: se vería como si fuera
    exacto, bajaría su participación y podría disparar la alerta de baja participación. Los minutos
    *posibles* no dependen de este dato y se conservan.
    """
    if 'minutes_missing' not in frame:
        return frame
    gap = frame['minutes_missing'].fillna(0) > 0
    frame = frame.copy()
    for column in MINUTES_COLUMNS:
        if column in frame:
            frame.loc[gap, column] = np.nan
    return frame


def match_duration(ds: Dataset) -> pd.Series:
    """Duración de cada partido según la regla `duration_source`; sin el dato elegido, queda desconocida."""
    column = 'nominal_duration' if ds.rules.value('duration_source') == 'nominal' else 'duration'
    return ds.matches.set_index('matchid')[column]


def possible_grid(ds: Dataset, periods: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Un renglón por jugador y partido que **cuenta** como posible, con su duración.

    Es el único conjunto de partidos para el denominador (minutos posibles) y para el numerador
    (minutos jugados que se comparan): así la participación no puede superar el 100 % por usar
    conjuntos distintos. Regla supuesta (pendiente de Pablo): todos los partidos ya jugados de la
    competición donde el jugador fue citado alguna vez. Quedan fuera los partidos sin duración
    conocida, los de un estado excluido por regla y, si la regla está encendida, los que caen dentro
    de un período de selección **y el jugador no jugó** (si los jugó, el partido cuenta).
    """
    rules = ds.rules
    duration = match_duration(ds)
    known = ds.matches.assign(duration_used=ds.matches['matchid'].map(duration))
    known = known.loc[known['duration_used'].notna(), ['matchid', 'competition_id', 'matchdate', 'matchstatus', 'duration_used']]
    excluded = {s.lower() for s in rules.value('excluded_match_statuses')}
    if excluded:
        known = known[~known['matchstatus'].fillna('').str.lower().isin(excluded)]
    calls = ds.facts.groupby(['personid', 'competition_id'], as_index=False).agg(first_call=('matchdate', 'min'))
    grid = calls.merge(known.drop(columns='matchstatus'), on='competition_id', how='inner')
    if rules.value('possible_from_first_call'):
        grid = grid[grid['matchdate'].dt.normalize() >= grid['first_call'].dt.normalize()]
    if rules.value('exclude_selection_periods') and periods is not None and len(periods):
        active = periods[periods['active'].astype(bool)][['personid', 'start', 'end']]
        joined = grid.merge(active, on='personid', how='inner')
        day = joined['matchdate'].dt.normalize()
        hit = joined[(day >= joined['start']) & (day <= joined['end'])][['personid', 'matchid']].drop_duplicates()
        # Un partido jugado (o con planilla contradictoria: quizá jugado) no se descuenta.
        played = ds.facts.loc[ds.facts['participated'] | ds.facts['conflict'], ['personid', 'matchid']].drop_duplicates()
        hit = hit.merge(played.assign(_played=True), on=['personid', 'matchid'], how='left')
        hit = hit[hit['_played'].isna()][['personid', 'matchid']]
        grid = grid.merge(hit.assign(_excluded=True), on=['personid', 'matchid'], how='left')
        grid = grid[grid['_excluded'].isna()].drop(columns='_excluded')
    return grid


def possible_minutes(ds: Dataset, periods: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Minutos posibles y minutos jugados dentro de esos mismos partidos, por jugador y competición."""
    grid = possible_grid(ds, periods)
    keys = ['personid', 'competition_id']
    possible = grid.groupby(keys, as_index=False).agg(
        possible_minutes=('duration_used', 'sum'), possible_matches=('matchid', 'nunique'))
    inside = ds.facts.merge(grid[['personid', 'matchid']], on=['personid', 'matchid'], how='inner')
    counted = inside.groupby(keys, as_index=False).agg(counted_minutes=('minutes', _sum))
    return possible.merge(counted, on=keys, how='left')


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
        second_yellows=('second_yellows', _sum), own_goals=('own_goals', _sum),
        wins_with=('with_win', 'sum'), draws_with=('with_draw', 'sum'),
        losses_with=('with_loss', 'sum'), results_with=('with_result', 'sum'),
        ahead_minutes=('ahead_minutes', _sum), incomplete=('conflict', 'sum'), minutes_missing=('minutes_unknown', 'sum'),
        first_call=('matchdate', 'min'), last_call=('matchdate', 'max'))
    out = out.merge(possible_minutes(ds, periods), on=keys, how='left')
    return blank_unknown_minutes(out)


def _percentages(frame: pd.DataFrame) -> pd.DataFrame:
    """Porcentajes SIN redondear: se comparan con los umbrales tal cual; solo la pantalla redondea."""
    frame = frame.copy()
    possible = frame['possible_minutes'].where(frame['possible_minutes'] > 0)
    frame['participation_pct'] = frame['counted_minutes'] / possible * 100
    results = frame['results_with'].where(frame['results_with'] > 0)
    frame['win_pct_with'] = frame['wins_with'] / results * 100
    return frame


def add_percentages(comp_summary: pd.DataFrame) -> pd.DataFrame:
    return _percentages(comp_summary)


_SUM_COLUMNS = ['cited', 'started', 'sub_in', 'only_called', 'played', 'wins_with', 'draws_with',
                'losses_with', 'results_with', 'possible_matches', 'incomplete', 'minutes_missing']
_NAN_SUM_COLUMNS = ['minutes', 'goals', 'yellow_cards', 'red_cards', 'second_yellows', 'own_goals',
                    'ahead_minutes', 'possible_minutes', 'counted_minutes']


def category_summary(comp_summary: pd.DataFrame) -> pd.DataFrame:
    """Suma las competiciones de una misma categoría y temporada (una fila por jugador)."""
    keys = ['personid', 'season_year', 'category']
    agg = {c: (c, 'sum') for c in _SUM_COLUMNS}
    agg.update({c: (c, _sum) for c in _NAN_SUM_COLUMNS})
    agg.update(displayname=('displayname', 'first'), category_rank=('category_rank', 'first'),
               age=('age', 'first'), age_category=('age_category', 'first'),
               first_call=('first_call', 'min'), last_call=('last_call', 'max'))
    # Una competición con minutos desconocidos deja sin dato el total de la categoría: no se suma el resto.
    return _percentages(blank_unknown_minutes(comp_summary.groupby(keys, as_index=False).agg(**agg)))


def principal_categories(cat_summary: pd.DataFrame) -> pd.DataFrame:
    """Categoría de cada jugador en cada temporada: donde sumó más minutos (luego citaciones y rango)."""
    confirmed = cat_summary
    if 'minutes_missing' in confirmed:
        # No elegir otra categoría solo porque sus minutos sí se conocen. La temporada
        # desconocida queda fuera del historial y corta cualquier racha de promoción.
        gaps = confirmed.groupby(['personid', 'season_year'])['minutes_missing'].transform('sum').fillna(0) > 0
        confirmed = confirmed[~gaps]
    ordered = confirmed.assign(_minutes=confirmed['minutes'].fillna(-1)).sort_values(
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


def incomplete_players(cat_summary: pd.DataFrame, *, category: str, season_year: int) -> pd.DataFrame:
    """Jugadores de una categoría y temporada con planillas contradictorias (cifras incompletas)."""
    scope = cat_summary[(cat_summary['category'] == category) & (cat_summary['season_year'] == season_year)]
    return scope[scope['incomplete'] > 0][['personid', 'displayname', 'incomplete']]


def minutes_gap_players(cat_summary: pd.DataFrame, *, category: str, season_year: int) -> pd.DataFrame:
    """Jugadores de una categoría y temporada con partidos sin minutos conocidos.

    No entran en el ranking de minutos (no se ordena por una suma parcial); en goles y tarjetas sí figuran.
    """
    scope = cat_summary[(cat_summary['category'] == category) & (cat_summary['season_year'] == season_year)]
    return scope[scope['minutes_missing'] > 0][['personid', 'displayname', 'minutes_missing']]


def ranking(cat_summary: pd.DataFrame, metric: str, *, category: str, season_year: int,
            top: Optional[int] = None, include_incomplete: bool = False) -> pd.DataFrame:
    """Ranking de una categoría y temporada. Empates comparten posición; sin datos o en 0 no entran.

    Los jugadores con planillas contradictorias no entran: sus cifras están incompletas y ordenarlos
    sería engañoso (`incomplete_players` los lista para avisarlo en pantalla).
    """
    column = RANKING_METRICS[metric]
    scope = cat_summary[(cat_summary['category'] == category) & (cat_summary['season_year'] == season_year)]
    if not include_incomplete:
        scope = scope[scope['incomplete'] == 0]
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
    # Un mes con un partido sin minutos conocidos no se dibuja como una suma parcial.
    played = mine.groupby(['periodo', 'category'], as_index=False).agg(
        minutes=('minutes', _strict_sum), played=('participated', 'sum'))
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
    # Una fila contradictoria se muestra (con «—»): el arquero sí figura en el partido.
    g = g[((g['played'] == True).fillna(False) | (g['minutesplayed'] > 0) | g['conflict']).astype(bool)]  # noqa: E712
    names = ds.players.set_index('personid')['displayname']
    return g.assign(displayname=g['personid'].map(names))[
        ['matchid', 'competition_id', 'personid', 'displayname', 'minutesplayed', 'goalsconceded']]
