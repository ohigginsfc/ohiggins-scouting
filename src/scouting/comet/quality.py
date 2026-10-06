"""Control de calidad de los datos de COMET: qué supuestos se cumplen y cuáles fallan.

No corrige nada en silencio. Enumera lo que el pipeline de COMET debería aportar o revisar, para que
ningún dato ausente se transforme en un cero y ninguna contradicción se resuelva sin decirlo.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from .categories import parse_category
from .facts import Dataset, RESOLVED_CONFLICT, RESOLVED_IDENTICAL, prepare_sheet, season_year_of
from .metrics import possible_grid

ERROR, WARNING, INFO = 'Error', 'Aviso', 'Información'


def _check(rows: list, name: str, count: int, level_if_any: str, detail: str, impact: str) -> None:
    rows.append(dict(control=name, nivel=level_if_any if count else 'Correcto', cantidad=int(count),
                     detalle=detail, efecto=impact))


def _period_checks(rows: list, ds: Dataset, periods: Optional[pd.DataFrame]) -> None:
    active = periods[periods['active'].astype(bool)] if periods is not None and len(periods) else None
    if active is None or active.empty:
        _check(rows, 'Partidos jugados dentro de un período de selección', 0, WARNING,
               'Sin períodos de selección activos.', 'Ninguno.')
        _check(rows, 'Períodos de selección solapados', 0, WARNING, 'Sin períodos de selección activos.', 'Ninguno.')
        return
    joined = ds.facts.loc[ds.facts['participated'], ['personid', 'matchid', 'matchdate']].merge(
        active[['personid', 'start', 'end']], on='personid')
    day = joined['matchdate'].dt.normalize()
    played_inside = joined[(day >= joined['start']) & (day <= joined['end'])][['personid', 'matchid']].drop_duplicates()
    _check(rows, 'Partidos jugados dentro de un período de selección', len(played_inside), WARNING,
           'El jugador figura con minutos en un partido que cae dentro de un período de selección marcado.',
           'Con la regla «excluir períodos» encendida ese partido cuenta igual (jugó); revisa las fechas del período.')
    overlaps = 0
    for _, grp in active.sort_values('start').groupby('personid'):
        end_so_far = None
        for period in grp.itertuples():
            if end_so_far is not None and period.start <= end_so_far:
                overlaps += 1
            end_so_far = period.end if end_so_far is None else max(end_so_far, period.end)
    _check(rows, 'Períodos de selección solapados', overlaps, WARNING,
           'Dos períodos activos del mismo jugador se cruzan.', 'Se cuentan una sola vez, pero conviene unificarlos.')


def data_quality(ds: Dataset, sheet_raw: pd.DataFrame, matches_raw: pd.DataFrame,
                 periods: Optional[pd.DataFrame] = None, comp: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Devuelve una fila por control con su nivel (Correcto / Información / Aviso / Error)."""
    rows: list = []
    f, m = ds.facts, ds.matches
    sheet = prepare_sheet(sheet_raw)
    known_matches = set(m['matchid'])
    # El dato ausente no cuenta como True ni como False.
    played_yes = (sheet['played'] == True).fillna(False).astype(bool)  # noqa: E712
    played_no = (sheet['played'] == False).fillna(False).astype(bool)  # noqa: E712
    started_yes = (sheet['startinglineup'] == True).fillna(False).astype(bool)  # noqa: E712
    minutes = sheet['minutesplayed']

    _check(rows, 'Filas de planilla sin partido', int((~sheet['matchid'].isin(known_matches)).sum()), WARNING,
           'Filas de actuaciones cuyo partido no está entre los partidos ya jugados de O\'Higgins.',
           'Esas filas se ignoran (partidos futuros o sin registro del partido).')
    dups = ds.duplicates if ds.duplicates is not None else pd.DataFrame(columns=['resolucion'])
    _check(rows, 'Filas repetidas idénticas (jugador y partido)', int((dups['resolucion'] == RESOLVED_IDENTICAL).sum()),
           WARNING, 'Varias filas con exactamente los mismos valores para el mismo jugador y partido.',
           'Se cuenta una sola: sumarlas duplicaría minutos, goles y titularidades.')
    _check(rows, 'Filas repetidas contradictorias (jugador y partido)', int((dups['resolucion'] == RESOLVED_CONFLICT).sum()),
           ERROR, 'Varias filas con valores distintos para el mismo jugador y partido, sin versión ni fecha que diga '
                  'cuál vale.', 'No se elige ninguna: esos valores quedan sin dato, el jugador se marca con cifras '
                                'incompletas y sale de rankings y alertas hasta que COMET lo aclare.')
    match_comp = sheet.merge(m[['matchid', 'competition_id']].rename(columns={'competition_id': 'match_comp'}), on='matchid')
    _check(rows, 'Competición de la planilla distinta a la del partido',
           int((match_comp['competition_id'] != match_comp['match_comp']).sum()), WARNING,
           'La fila de actuaciones apunta a otra competición que su partido.', 'Se usa la competición del partido.')
    _check(rows, 'Jugadores sin ficha', int((~f['personid'].isin(ds.players['personid'])).sum()), WARNING,
           'Filas de planilla cuyo jugador no está en la tabla de jugadores.', 'Se muestran sin nombre ni edad.')
    _check(rows, 'Jugadores sin fecha de nacimiento', int(f.loc[f['dateofbirth'].isna(), 'personid'].nunique()), WARNING,
           'Jugadores con planilla pero sin fecha de nacimiento.', 'No se calcula su edad ni si están adelantados.')
    _check(rows, 'Jugó y sin minutos', int((played_yes & minutes.isna()).sum()), ERROR,
           'Marcados como que jugaron, pero sin minutos.',
           'Sus minutos y su participación aparecen como «—»: no se suma solo lo que sí figura.')
    _check(rows, 'Minutos sin marca de jugó', int((played_no & (minutes > 0)).sum()), ERROR,
           'Tienen minutos, pero la fila dice que no jugaron.',
           'La fuente se contradice: sus minutos quedan sin dato (no se usan ni se ignoran en silencio).')
    _check(rows, 'Titular que no jugó', int((started_yes & played_no).sum()), WARNING,
           'Titulares marcados como que no jugaron.', 'Se cuentan como titulares con 0 minutos.')
    _check(rows, 'Sin dato de titular o de jugó', int((sheet['startinglineup'].isna() | sheet['played'].isna()).sum()),
           WARNING, 'Falta la marca de titular o de jugó.',
           'Su rol aparece como "Sin dato"; si además faltan los minutos, no se supone que no jugó: quedan sin dato.')
    _check(rows, 'Jugadores con minutos desconocidos', len(ds.minutes_gap_players()), ERROR,
           'Jugadores con algún partido en que jugó (o no se sabe si jugó) y COMET no trae sus minutos, o en que la marca '
           'de jugó contradice los minutos.',
           'Sus minutos, su participación y sus minutos en categoría superior aparecen como «—» y no entran en el ranking '
           'de minutos, en la alerta de baja participación ni en los indicadores de adelantados. Sus goles y tarjetas sí cuentan.')
    _check(rows, 'Minutos fuera de rango', int(((minutes < 0) | (minutes > 130)).sum()),
           ERROR, 'Minutos negativos o mayores de 130.', 'Distorsionan minutos y duración del partido.')

    with_sheet = set(f['matchid'])
    _check(rows, 'Partidos jugados sin planilla', int((~m['matchid'].isin(with_sheet)).sum()), WARNING,
           'Partidos ya jugados sin ninguna fila de planilla.', 'No entran en minutos posibles ni en rankings.')
    _check(rows, 'Partidos sin resultado', int(m['result'].isna().sum()), WARNING,
           'Partidos sin marcador final (fase "Segundo tiempo").', 'No cuentan para victorias ni para el resultado con el jugador.')
    _check(rows, 'Partidos sin duración conocida', int((m['matchid'].isin(with_sheet) & m['duration'].isna()).sum()), WARNING,
           'Partidos con planilla pero sin minutos registrados.', 'Con la duración «registrada» no entran en los minutos posibles.')
    both = m['duration'].notna() & m['nominal_duration'].notna()
    _check(rows, 'Duración registrada distinta de la nominal',
           int((both & (m['duration'] != m['nominal_duration'])).sum()), INFO,
           'El minuto más largo jugado no coincide con la duración reglamentaria (matchlength) de la competición.',
           'Ninguna de las dos es «la correcta» por sí sola: la regla «duración de cada partido» elige cuál se usa.')
    _check(rows, 'Partidos con planilla sin duración nominal', int((m['matchid'].isin(with_sheet) & m['nominal_duration'].isna()).sum()),
           INFO, 'La competición no trae duración reglamentaria (matchlength).',
           'Con la duración «nominal» esos partidos no entran en los minutos posibles.')
    statuses = m['matchstatus'].dropna()
    listing = '; '.join(f'{k}: {v}' for k, v in statuses.value_counts().items())
    _check(rows, 'Partidos por estado (matchstatus)', int(statuses.nunique()), INFO,
           'Estados distintos que trae COMET: ' + (listing or 'ninguno'),
           'Sirve para decidir qué estados no cuentan como minutos posibles (regla «estados que no cuentan»).')

    per_match = f.groupby('matchid')['participated'].agg(['size', 'sum'])
    all_only_players = len(per_match) > 0 and bool((per_match['size'] == per_match['sum']).all())
    _check(rows, 'Planillas que solo traen a quienes jugaron', len(per_match) if all_only_players else 0,
           ERROR, 'Ningún partido incluye suplentes que no ingresaron: COMET no parece entregar la citación completa.',
           '"Suplente que no ingresó" y "solo citación" no se pueden calcular. Dependencia del pipeline de COMET.')
    goals = f.groupby('matchid')['goals'].sum(min_count=1)
    compare = m.set_index('matchid')['goals_for'].reindex(goals.index)
    own = f.groupby('matchid')['own_goals'].sum(min_count=1).reindex(goals.index).fillna(0)
    _check(rows, 'Goles de jugadores distintos del marcador', int(((goals != compare) & goals.notna() & compare.notna()).sum()),
           INFO, 'Suma de goles de la planilla distinta del marcador. Las filas son solo de O\'Higgins: los autogoles '
                 'del rival no figuran en ellas.', 'Los goles por jugador pueden no sumar el marcador.')
    _check(rows, 'Autogoles registrados', int(own.sum()), INFO,
           'Autogoles de jugadores de O\'Higgins (owngoals): se muestran aparte y no cuentan como goles a favor.',
           'Ninguno.')
    _check(rows, 'Segundas amarillas registradas', int(f['second_yellows'].fillna(0).sum()), INFO,
           'Tarjetas por doble amarilla (secondyellow): se muestran y se avisan en la alerta, pero no se suman a las amarillas.',
           'La regla del ciclo de tarjetas está pendiente de confirmar.')
    keeper_matches = set(ds.goalkeepers['matchid'])
    _check(rows, 'Partidos sin arquero registrado', int((~pd.Series(list(with_sheet), dtype=object).isin(keeper_matches)).sum()),
           WARNING, 'Partidos con planilla pero sin fila en actuaciones de arqueros.', 'Sus goles recibidos quedan "sin dato".')
    _check(rows, 'Categorías no reconocidas',
           int(matches_raw['category'].map(lambda c: parse_category(c).rank is None).sum()), WARNING,
           'Categorías que no son "U-N" ni "Primer Equipo".', 'No se comparan con la edad ni entran en adelantados.')
    _check(rows, 'Temporadas sin año reconocible',
           int(matches_raw['season'].map(lambda s: season_year_of(s) is None).sum()), WARNING,
           'La temporada no contiene un año de 4 cifras.', 'Se usa el año de la fecha del partido.')

    people = ds.players[ds.players['personid'].isin(f['personid'])]
    _check(rows, 'Jugadores sin datefrom', int(people['datefrom'].isna().sum()), INFO,
           'Fichas sin la fecha «datefrom», que podría ser la fecha de ingreso al club (por confirmar).',
           'Con la antigüedad por «datefrom» esos jugadores quedan sin dato.')
    _check(rows, 'Jugadores sin estatura o sin peso', int((people['height'].isna() | people['weight'].isna()).sum()), INFO,
           'Fichas sin estatura o sin peso.', 'La ficha del jugador muestra «—» en esos datos.')

    _period_checks(rows, ds, periods)
    if periods is not None:
        grid = possible_grid(ds, periods)
        played = f[f['participated'] & (f['minutes'] > 0)][['personid', 'matchid']]
        outside = played.merge(grid[['personid', 'matchid']].assign(_in=True), on=['personid', 'matchid'], how='left')
        _check(rows, 'Minutos jugados fuera de los partidos que cuentan como posibles', int(outside['_in'].isna().sum()), WARNING,
               'El jugador tiene minutos en partidos que la regla de minutos posibles deja fuera (sin duración, estado excluido).',
               'Esos minutos no entran en su participación: numerador y denominador usan los mismos partidos.')
    if comp is not None and len(comp):
        over = comp[(comp['possible_minutes'] > 0) & (comp['counted_minutes'] > comp['possible_minutes'])]
        _check(rows, 'Participación superior al 100 %', len(over), ERROR,
               'Minutos jugados mayores que los minutos posibles del mismo conjunto de partidos.',
               'No se recorta a 100 %: indica minutos mayores que la duración del partido; hay que revisar el dato.')
    return pd.DataFrame(rows)


def history_horizon(ds: Dataset) -> dict:
    """Desde cuándo hay datos: límite real de antigüedad y de conteo de temporadas sin promoción."""
    dates = ds.facts['matchdate'].dropna()
    return dict(first=dates.min() if len(dates) else None, last=dates.max() if len(dates) else None,
                seasons=ds.seasons)
