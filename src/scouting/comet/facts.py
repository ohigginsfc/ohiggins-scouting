"""Preparación de los datos de COMET: tipos, rol en la planilla y unión de tablas.

Regla general: un dato que falta queda como NaN/NA, nunca como 0. Un 0 solo aparece
cuando es cierto (por ejemplo, minutos de un suplente que no ingresó).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .categories import category_for_age, order_categories, parse_category, steps_ahead, years_younger
from .rules import Rules

LOCAL_TZ = 'America/Santiago'

ROLE_STARTER = 'Titular'
ROLE_SUB_IN = 'Suplente que ingresó'
ROLE_SUB_OUT = 'Suplente que no ingresó'
ROLE_UNKNOWN = 'Sin dato'

RESULT_WIN, RESULT_DRAW, RESULT_LOSS = 'Victoria', 'Empate', 'Derrota'

SHEET_COLUMNS = ['matchid', 'competition_id', 'personid', 'played', 'startinglineup',
                 'minutesplayed', 'goals', 'yellow_cards', 'red_cards', 'goalkeeper']
MATCH_COLUMNS = ['matchid', 'competition_id', 'matchdate', 'category', 'competition', 'season',
                 'venue', 'home_team', 'away_team', 'goals_for', 'goals_against', 'result']
PLAYER_COLUMNS = ['personid', 'displayname', 'dateofbirth', 'nationality', 'level', 'status', 'orgname']
GOALKEEPER_COLUMNS = ['matchid', 'competition_id', 'personid', 'played', 'minutesplayed', 'goalsconceded']

# Columnas que COMET tiene en algunas instalaciones. Si no llegan, quedan como dato ausente.
SHEET_OPTIONAL = ['second_yellows', 'own_goals']
MATCH_OPTIONAL = ['nominal_duration', 'matchstatus']
PLAYER_OPTIONAL = ['datefrom', 'height', 'weight']

# Valores de una fila de planilla que deben coincidir para considerar idénticas dos filas repetidas.
SHEET_VALUES = ['played', 'startinglineup', 'minutesplayed', 'goals', 'yellow_cards', 'red_cards',
                'goalkeeper', 'second_yellows', 'own_goals']
KEEPER_VALUES = ['played', 'minutesplayed', 'goalsconceded']

_TRUE = {'t', 'true', '1', 'si', 'sí', 'yes', 'y'}
_FALSE = {'f', 'false', '0', 'no', 'n'}


def norm_id(value):
    """Identificador como texto estable (12 y 12.0 son el mismo jugador); None si falta."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        return str(int(value))
    return str(value).strip()


def to_bool(series: pd.Series) -> pd.Series:
    """Booleano con NA (dato ausente), tolerante a 't'/'f', 0/1 y texto."""
    def convert(value):
        if value is None or (not isinstance(value, str) and pd.isna(value)):
            return pd.NA
        if isinstance(value, str):
            text = value.strip().lower()
            return True if text in _TRUE else False if text in _FALSE else pd.NA
        return bool(value)
    return pd.Series([convert(v) for v in series], index=series.index, dtype='boolean')


def _missing_columns(frame: pd.DataFrame, columns) -> list:
    return [c for c in columns if c not in frame.columns]


def _require(frame: pd.DataFrame, columns, name: str) -> None:
    missing = _missing_columns(frame, columns)
    if missing:
        raise ValueError(f'A los datos de {name} les faltan columnas: {", ".join(missing)}')


def _local_datetime(series: pd.Series) -> pd.Series:
    """Fecha y hora en Santiago, sin zona horaria, para agrupar por día y semana locales."""
    if isinstance(series.dtype, pd.DatetimeTZDtype):
        return series.dt.tz_convert(LOCAL_TZ).dt.tz_localize(None)
    if pd.api.types.is_datetime64_dtype(series):
        return series  # sin zona: se asume hora local
    aware = any(getattr(v, 'tzinfo', None) is not None for v in series.head(50))
    parsed = pd.to_datetime(series, errors='coerce', utc=aware)
    return parsed.dt.tz_convert(LOCAL_TZ).dt.tz_localize(None) if aware else parsed


def civil_date(series: pd.Series) -> pd.Series:
    """Fecha civil (sin hora ni zona) de una columna de fechas, sea `date`, `timestamp` o `timestamptz`.

    Un nacimiento guardado como 2011-06-10 00:00 UTC es el 10 de junio: no se convierte a la hora de
    Santiago (retrocedería un día). Se toma el día en UTC, que coincide tanto con «medianoche UTC» como
    con «medianoche de Chile» (03:00 o 04:00 UTC del mismo día).
    """
    parsed = pd.to_datetime(series, errors='coerce', utc=True)
    return parsed.dt.tz_localize(None).dt.normalize()


def season_year_of(season, fallback_year=None):
    """Año de la temporada: '2026' o '2025/2026' -> primer año de 4 cifras."""
    match = re.search(r'(19|20)\d{2}', '' if season is None else str(season))
    return int(match.group(0)) if match else fallback_year


def _with_optional(frame: pd.DataFrame, columns) -> pd.DataFrame:
    for col in columns:
        if col not in frame.columns:
            frame[col] = np.nan
    return frame


def prepare_matches(raw: pd.DataFrame) -> pd.DataFrame:
    _require(raw, MATCH_COLUMNS, 'partidos')
    m = _with_optional(raw[[c for c in MATCH_COLUMNS + MATCH_OPTIONAL if c in raw.columns]].copy(), MATCH_OPTIONAL)
    m['matchid'] = m['matchid'].map(norm_id)
    m['competition_id'] = m['competition_id'].map(norm_id)
    m['matchdate'] = _local_datetime(m['matchdate'])
    parsed = m['category'].map(parse_category)
    m['category'] = [p.label if p.rank is not None else raw_label for p, raw_label in zip(parsed, m['category'])]
    m['category_rank'] = [p.rank for p in parsed]
    m['season_year'] = [season_year_of(s, d.year if pd.notna(d) else None)
                        for s, d in zip(m['season'], m['matchdate'])]
    m['week_start'] = m['matchdate'].dt.normalize() - pd.to_timedelta(m['matchdate'].dt.weekday, unit='D')
    m['rival'] = np.where(m['venue'].eq('Local'), m['away_team'], m['home_team'])
    for col in ('goals_for', 'goals_against', 'nominal_duration'):
        m[col] = pd.to_numeric(m[col], errors='coerce')
    m['matchstatus'] = m['matchstatus'].map(lambda v: None if v is None or (not isinstance(v, str) and pd.isna(v))
                                            else str(v).strip())
    return m.drop_duplicates('matchid').reset_index(drop=True)


def prepare_players(raw: pd.DataFrame) -> pd.DataFrame:
    _require(raw, PLAYER_COLUMNS, 'jugadores')
    p = _with_optional(raw[[c for c in PLAYER_COLUMNS + PLAYER_OPTIONAL if c in raw.columns]].copy(), PLAYER_OPTIONAL)
    p['personid'] = p['personid'].map(norm_id)
    p['dateofbirth'] = civil_date(p['dateofbirth'])
    p['datefrom'] = civil_date(p['datefrom'])
    for col in ('height', 'weight'):
        p[col] = pd.to_numeric(p[col], errors='coerce')
    return p.drop_duplicates('personid').reset_index(drop=True)


def prepare_sheet(raw: pd.DataFrame) -> pd.DataFrame:
    _require(raw, SHEET_COLUMNS, 'planillas')
    s = _with_optional(raw[[c for c in SHEET_COLUMNS + SHEET_OPTIONAL if c in raw.columns]].copy(), SHEET_OPTIONAL)
    for col in ('matchid', 'competition_id', 'personid'):
        s[col] = s[col].map(norm_id)
    for col in ('played', 'startinglineup', 'goalkeeper'):
        s[col] = to_bool(s[col])
    for col in ('minutesplayed', 'goals', 'yellow_cards', 'red_cards', 'second_yellows', 'own_goals'):
        s[col] = pd.to_numeric(s[col], errors='coerce')
    return s


def prepare_goalkeepers(raw: pd.DataFrame) -> pd.DataFrame:
    _require(raw, GOALKEEPER_COLUMNS, 'arqueros')
    g = raw[GOALKEEPER_COLUMNS].copy()
    for col in ('matchid', 'competition_id', 'personid'):
        g[col] = g[col].map(norm_id)
    g['played'] = to_bool(g['played'])
    for col in ('minutesplayed', 'goalsconceded'):
        g[col] = pd.to_numeric(g[col], errors='coerce')
    return g


DUPLICATE_COLUMNS = ['tabla', 'matchid', 'personid', 'filas', 'versiones', 'resolucion']
RESOLVED_IDENTICAL = 'idénticas: se cuenta una sola'
RESOLVED_CONFLICT = 'contradictorias: sin resolver'


def reconcile_duplicates(frame: pd.DataFrame, values: list, table: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Deja una fila por jugador y partido.

    * Filas repetidas **idénticas** (mismos valores): se cuenta una sola, porque sumarlas duplicaría
      minutos, goles y titularidades.
    * Filas repetidas **contradictorias** (valores distintos): no se elige ninguna. La fuente no trae una
      versión ni una fecha de corrección que respalde preferir una, así que la fila queda con todos sus
      valores ausentes y marcada `conflict`. Las cifras del jugador se marcan incompletas.
    """
    key = ['matchid', 'personid']
    frame = frame.assign(conflict=False)
    repeated = frame.duplicated(key, keep=False)
    if not repeated.any():
        return frame, pd.DataFrame(columns=DUPLICATE_COLUMNS)
    dups = frame[repeated]
    versions = dups.drop_duplicates(key + values).groupby(key).size().rename('versiones')
    sizes = dups.groupby(key).size().rename('filas')
    summary = pd.concat([sizes, versions], axis=1).reset_index()
    summary['resolucion'] = np.where(summary['versiones'] > 1, RESOLVED_CONFLICT, RESOLVED_IDENTICAL)
    summary.insert(0, 'tabla', table)
    clean = pd.concat([frame[~repeated], dups.drop_duplicates(key, keep='first')], ignore_index=True)
    clashing = summary.loc[summary['versiones'] > 1, key]
    if len(clashing):
        marked = clean.merge(clashing.assign(_clash=True), on=key, how='left')['_clash'].eq(True).to_numpy()
        for col in values:
            clean.loc[marked, col] = pd.NA if str(clean[col].dtype) == 'boolean' else np.nan
        clean.loc[marked, 'conflict'] = True
    return clean, summary[DUPLICATE_COLUMNS]


@dataclass(frozen=True)
class Dataset:
    """Datos de COMET listos para calcular. `facts` tiene una fila por jugador y partido."""
    matches: pd.DataFrame
    players: pd.DataFrame
    facts: pd.DataFrame
    goalkeepers: pd.DataFrame
    categories: tuple  # categorías reconocidas, de mayor a menor
    rules: Rules
    duplicates: pd.DataFrame = None  # filas repetidas jugador/partido y cómo se resolvieron

    @property
    def seasons(self) -> list:
        return sorted(self.matches['season_year'].dropna().astype(int).unique().tolist())

    def current_season(self, today) -> int | None:
        """Temporada vigente: la más reciente con algún partido ya jugado."""
        played = self.matches[self.matches['matchdate'] <= pd.Timestamp(today)]
        years = played['season_year'].dropna()
        return int(years.max()) if len(years) else None

    def blocked_players(self, season_year: int | None = None) -> pd.DataFrame:
        """Jugadores con planillas contradictorias: sus cifras están incompletas y no se evalúan."""
        f = self.facts[self.facts['conflict']]
        if season_year is not None:
            f = f[f['season_year'] == season_year]
        return (f.groupby('personid', as_index=False)
                .agg(displayname=('displayname', 'first'), partidos=('matchid', 'nunique'))
                .sort_values('displayname').reset_index(drop=True))

    def minutes_gap_players(self, season_year: int | None = None) -> pd.DataFrame:
        """Jugadores con algún partido sin minutos conocidos: sus totales de minutos no se afirman."""
        f = self.facts[self.facts['minutes_unknown']]
        if season_year is not None:
            f = f[f['season_year'] == season_year]
        return (f.groupby('personid', as_index=False)
                .agg(displayname=('displayname', 'first'), partidos=('matchid', 'nunique'))
                .sort_values('displayname').reset_index(drop=True))


def _role(started: pd.Series, played: pd.Series) -> pd.Series:
    is_starter = (started == True).fillna(False).astype(bool)  # noqa: E712 (NA-aware comparison)
    on_bench = (started == False).fillna(False).astype(bool)  # noqa: E712
    did_play = (played == True).fillna(False).astype(bool)  # noqa: E712
    no_play = (played == False).fillna(False).astype(bool)  # noqa: E712
    return pd.Series(np.select(
        [is_starter, on_bench & did_play, on_bench & no_play],
        [ROLE_STARTER, ROLE_SUB_IN, ROLE_SUB_OUT], default=ROLE_UNKNOWN), index=started.index)


def _minutes_unknown(played: pd.Series, minutes: pd.Series, participated: pd.Series) -> pd.Series:
    """Filas en las que no se sabe cuántos minutos jugó el jugador.

    * Jugó y COMET no trae sus minutos.
    * No se sabe si jugó (sin marca de jugó) y tampoco hay minutos.
    * La marca dice que no jugó pero trae minutos: la fuente se contradice, no se elige una versión.
    """
    played_no = (played == False).fillna(False).astype(bool)  # noqa: E712
    no_minutes = minutes.isna()
    return (participated & no_minutes) | (played.isna() & no_minutes) | (played_no & (minutes > 0))


def build_dataset(sheet_raw, matches_raw, players_raw, goalkeepers_raw, rules: Rules | None = None) -> Dataset:
    rules = rules or Rules()
    matches = prepare_matches(matches_raw)
    players = prepare_players(players_raw)
    sheet, sheet_dups = reconcile_duplicates(prepare_sheet(sheet_raw), SHEET_VALUES, 'planilla')
    keepers, keeper_dups = reconcile_duplicates(prepare_goalkeepers(goalkeepers_raw), KEEPER_VALUES, 'arquero')
    categories = tuple(order_categories(matches['category']))

    # La competición de cada fila es la del partido: es única y evita que dos planillas discrepen.
    f = sheet.drop(columns='competition_id').merge(
        matches[['matchid', 'competition_id', 'competition', 'category', 'category_rank', 'season_year', 'matchdate',
                 'week_start', 'rival', 'venue', 'goals_for', 'goals_against', 'result']],
        on='matchid', how='inner')
    f = f.merge(players[['personid', 'displayname', 'dateofbirth', 'nationality', 'level', 'status']],
                on='personid', how='left')

    minutes = f['minutesplayed']
    f['participated'] = ((f['played'] == True) | (f['played'].isna() & (minutes > 0))).fillna(False).astype(bool)  # noqa: E712
    f['role'] = _role(f['startinglineup'], f['played'])
    f['conflict'] = f['conflict'].astype(bool)
    f['minutes_unknown'] = _minutes_unknown(f['played'], minutes, f['participated']) & ~f['conflict']
    # Quien no jugó tiene 0 minutos y 0 goles (es cierto). Si no se sabe cuántos minutos jugó (jugó sin minutos,
    # no se sabe si jugó, o la marca de jugó contradice los minutos) queda NaN: no es un 0 ni se ignora en silencio.
    # Una fila contradictoria tampoco es un 0: sus valores quedan ausentes.
    known_to_have_played = f['participated'] | f['conflict']
    f['minutes'] = minutes.where(known_to_have_played, 0.0).where(~f['minutes_unknown'])
    f['goals'] = f['goals'].where(known_to_have_played | f['minutes_unknown'], 0.0)
    f['goalkeeper'] = f['goalkeeper'].fillna(False).astype(bool)

    cutoff_month, cutoff_day = rules.cutoff()
    birth = f['dateofbirth']
    before_cutoff = (birth.dt.month * 100 + birth.dt.day) > (cutoff_month * 100 + cutoff_day)
    f['age'] = f['season_year'] - birth.dt.year - before_cutoff.astype(float)
    ages = {a: category_for_age(a, categories) for a in f['age'].dropna().unique()}
    f['age_category'] = f['age'].map(ages)
    pairs = f[['category', 'age_category']].drop_duplicates()
    ahead = {(a, b): steps_ahead(a, b, categories) for a, b in zip(pairs['category'], pairs['age_category'])}
    f['steps_ahead'] = [ahead.get((a, b)) for a, b in zip(f['category'], f['age_category'])]
    f['steps_ahead'] = pd.to_numeric(f['steps_ahead'], errors='coerce')
    f['years_younger'] = [years_younger(a, c) for a, c in zip(f['age'], f['category'])]
    f['years_younger'] = pd.to_numeric(f['years_younger'], errors='coerce')
    f['ahead_minutes'] = f['minutes'].where((f['steps_ahead'] > 0) & f['participated'], 0.0)

    # Duración registrada de cada partido = minuto más largo jugado por alguien de O'Higgins en él.
    # Si no hay minutos registrados queda desconocida (no se supone 90). La duración nominal
    # (`competiciones.matchlength`) se conserva aparte: la regla `duration_source` elige cuál se usa.
    duration = f[f['participated']].groupby('matchid')['minutes'].max()
    matches = matches.assign(duration=matches['matchid'].map(duration))

    duplicates = pd.concat([sheet_dups, keeper_dups], ignore_index=True)
    return Dataset(matches=matches, players=players, facts=f.reset_index(drop=True),
                   goalkeepers=keepers, categories=categories, rules=rules, duplicates=duplicates)
