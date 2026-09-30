"""Control de calidad de los datos de COMET: qué supuestos se cumplen y cuáles fallan.

No corrige nada. Enumera lo que el pipeline de COMET debería aportar o revisar, para que
ningún dato ausente se transforme en un cero silencioso en las pantallas.
"""
from __future__ import annotations

import pandas as pd

from .categories import parse_category
from .facts import Dataset, prepare_sheet, season_year_of

ERROR, WARNING, INFO = 'Error', 'Aviso', 'Información'


def _check(rows: list, name: str, count: int, level_if_any: str, detail: str, impact: str) -> None:
    rows.append(dict(control=name, nivel=level_if_any if count else 'Correcto', cantidad=int(count),
                     detalle=detail, efecto=impact))


def data_quality(ds: Dataset, sheet_raw: pd.DataFrame, matches_raw: pd.DataFrame) -> pd.DataFrame:
    """Devuelve una fila por control con su nivel (Correcto / Aviso / Error)."""
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
    _check(rows, 'Jugador repetido en un partido', int(sheet.duplicated(['matchid', 'personid']).sum()), ERROR,
           'Más de una fila para el mismo jugador y partido.', 'Minutos, goles y tarjetas podrían contarse dos veces.')
    _check(rows, 'Jugadores sin ficha', int((~f['personid'].isin(ds.players['personid'])).sum()), WARNING,
           'Filas de planilla cuyo jugador no está en la tabla de jugadores.', 'Se muestran sin nombre ni edad.')
    _check(rows, 'Jugadores sin fecha de nacimiento', int(f.loc[f['dateofbirth'].isna(), 'personid'].nunique()), WARNING,
           'Jugadores con planilla pero sin fecha de nacimiento.', 'No se calcula su edad ni si están adelantados.')
    _check(rows, 'Jugó y sin minutos', int((played_yes & minutes.isna()).sum()), ERROR,
           'Marcados como que jugaron, pero sin minutos.', 'Sus minutos aparecen como "sin dato", no como 0.')
    _check(rows, 'Minutos sin marca de jugó', int((played_no & (minutes > 0)).sum()), ERROR,
           'Tienen minutos, pero la fila dice que no jugaron.', 'Se ignoran esos minutos.')
    _check(rows, 'Titular que no jugó', int((started_yes & played_no).sum()), WARNING,
           'Titulares marcados como que no jugaron.', 'Se cuentan como titulares con 0 minutos.')
    _check(rows, 'Sin dato de titular o de jugó', int((sheet['startinglineup'].isna() | sheet['played'].isna()).sum()),
           WARNING, 'Falta la marca de titular o de jugó.', 'Su rol aparece como "Sin dato".')
    _check(rows, 'Minutos fuera de rango', int(((minutes < 0) | (minutes > 130)).sum()),
           ERROR, 'Minutos negativos o mayores de 130.', 'Distorsionan minutos y duración del partido.')

    with_sheet = set(f['matchid'])
    _check(rows, 'Partidos jugados sin planilla', int((~m['matchid'].isin(with_sheet)).sum()), WARNING,
           'Partidos ya jugados sin ninguna fila de planilla.', 'No entran en minutos posibles ni en rankings.')
    _check(rows, 'Partidos sin resultado', int(m['result'].isna().sum()), WARNING,
           'Partidos sin marcador final (fase "Segundo tiempo").', 'No cuentan para victorias ni para el resultado con el jugador.')
    _check(rows, 'Partidos sin duración conocida', int((m['matchid'].isin(with_sheet) & m['duration'].isna()).sum()), WARNING,
           'Partidos con planilla pero sin minutos registrados.', 'No entran en los minutos posibles.')

    per_match = f.groupby('matchid')['participated'].agg(['size', 'sum'])
    all_only_players = len(per_match) > 0 and bool((per_match['size'] == per_match['sum']).all())
    _check(rows, 'Planillas que solo traen a quienes jugaron', len(per_match) if all_only_players else 0,
           ERROR, 'Ningún partido incluye suplentes que no ingresaron: COMET no parece entregar la citación completa.',
           '"Suplente que no ingresó" y "solo citación" no se pueden calcular. Dependencia del pipeline de COMET.')
    goals = f.groupby('matchid')['goals'].sum(min_count=1)
    compare = m.set_index('matchid')['goals_for'].reindex(goals.index)
    _check(rows, 'Goles de jugadores distintos del marcador', int(((goals != compare) & goals.notna() & compare.notna()).sum()),
           INFO, 'Suma de goles de la planilla distinta del marcador (autogoles o goles sin autor).',
           'Los goles por jugador pueden no sumar el marcador.')
    keeper_matches = set(ds.goalkeepers['matchid'])
    _check(rows, 'Partidos sin arquero registrado', int((~pd.Series(list(with_sheet), dtype=object).isin(keeper_matches)).sum()),
           WARNING, 'Partidos con planilla pero sin fila en actuaciones de arqueros.', 'Sus goles recibidos quedan "sin dato".')
    _check(rows, 'Categorías no reconocidas',
           int(matches_raw['category'].map(lambda c: parse_category(c).rank is None).sum()), WARNING,
           'Categorías que no son "U-N" ni "Primer Equipo".', 'No se comparan con la edad ni entran en adelantados.')
    _check(rows, 'Temporadas sin año reconocible',
           int(matches_raw['season'].map(lambda s: season_year_of(s) is None).sum()), WARNING,
           'La temporada no contiene un año de 4 cifras.', 'Se usa el año de la fecha del partido.')
    return pd.DataFrame(rows)


def history_horizon(ds: Dataset) -> dict:
    """Desde cuándo hay datos: límite real de antigüedad y de conteo de temporadas sin promoción."""
    dates = ds.facts['matchdate'].dropna()
    return dict(first=dates.min() if len(dates) else None, last=dates.max() if len(dates) else None,
                seasons=ds.seasons)
