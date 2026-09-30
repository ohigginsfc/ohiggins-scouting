"""Consultas de solo lectura a las tablas COMET (esquema `public`).

Se piden únicamente las filas de O'Higgins y los jugadores que figuran en sus planillas
(minimización de datos de menores). Las tablas se leen con el rol `comet_reader`.

Las columnas del dashboard antiguo son obligatorias. Otras columnas que COMET tiene en algunas
instalaciones (`matchlength`, `matchstatus`, `secondyellow`, `owngoals`, `datefrom`, estatura y
peso) son opcionales: antes de consultar se mira `information_schema` y solo se piden las que
existen; si falta una, llega como dato ausente y no se rompe la pantalla.
"""
from __future__ import annotations

import re
from typing import Callable, Optional

import pandas as pd

OHIGGINS_CLUB_ID = 40010  # mismo identificador que app/comet_dashboard.py (lo verifica un test)

TABLES = ('actuaciones_jugadores', 'actuaciones_arqueros', 'competiciones', 'jugadores', 'partidos')

# Metadatos: nombres de columnas visibles para el lector. No devuelve datos de jugadores.
COLUMNS_SQL = """
    SELECT table_name, column_name
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name IN ('actuaciones_jugadores', 'actuaciones_arqueros', 'competiciones', 'jugadores', 'partidos')
"""

_SHEET = """
    SELECT a.matchid, a.id AS competition_id, a.personid, a.played, a.startinglineup,
           a.minutesplayed, a.goals,
           a.singleyellow::int AS yellow_cards, a.redcards::int AS red_cards, a.goalkeeper{extras}
    FROM actuaciones_jugadores a
    WHERE a.clubid = %(club)s
"""

GOALKEEPERS_SQL = """
    SELECT a.matchid, a.id AS competition_id, a.personid, a.played, a.minutesplayed, a.goalsconceded
    FROM actuaciones_arqueros a
    WHERE a.clubid = %(club)s
"""

# Misma definición de resultado que get_match_results_by_category: el marcador final es el de la
# fase 'Segundo tiempo'. Sin marcador el resultado queda NULL (no se cuenta como derrota ni empate).
_MATCHES = """
    WITH scores AS (
        SELECT pf.matchid,
               MAX(CASE WHEN pf.phase = 'Segundo tiempo' THEN pf.homeresult END) AS final_home,
               MAX(CASE WHEN pf.phase = 'Segundo tiempo' THEN pf.awayresult END) AS final_away
        FROM partidos_fases pf
        GROUP BY pf.matchid
    )
    SELECT p.matchid, p.id AS competition_id, p.matchdate, c.category, c.name AS competition, c.season,
           CASE WHEN p.hometeam = %(club)s THEN 'Local' ELSE 'Visita' END AS venue,
           e_home.club AS home_team, e_away.club AS away_team,
           CASE WHEN p.hometeam = %(club)s THEN s.final_home ELSE s.final_away END AS goals_for,
           CASE WHEN p.hometeam = %(club)s THEN s.final_away ELSE s.final_home END AS goals_against,
           CASE
               WHEN s.final_home IS NULL OR s.final_away IS NULL THEN NULL
               WHEN p.hometeam = %(club)s AND s.final_home > s.final_away THEN 'Victoria'
               WHEN p.awayteam = %(club)s AND s.final_away > s.final_home THEN 'Victoria'
               WHEN s.final_home = s.final_away THEN 'Empate'
               ELSE 'Derrota'
           END AS result{extras}
    FROM partidos p
    JOIN competiciones c ON p.id = c.id
    LEFT JOIN equipos e_home ON p.hometeam = e_home.clubid
    LEFT JOIN equipos e_away ON p.awayteam = e_away.clubid
    LEFT JOIN scores s ON p.matchid = s.matchid
    WHERE (p.hometeam = %(club)s OR p.awayteam = %(club)s)
      AND p.matchdate IS NOT NULL
      AND p.matchdate < NOW()
"""

_PLAYERS = """
    SELECT j.personid, j.displayname, j.dateofbirth, j.nationality, j.level, j.status, j.orgname{extras}
    FROM jugadores j
    WHERE j.personid IN (SELECT a.personid FROM actuaciones_jugadores a WHERE a.clubid = %(club)s)
"""

# Consultas base (solo columnas del dashboard antiguo); las pruebas de seguridad las revisan.
SHEET_SQL = _SHEET.format(extras='')
MATCHES_SQL = _MATCHES.format(extras='')
PLAYERS_SQL = _PLAYERS.format(extras='')

# Nombre en COMET de estatura y peso: puede variar; se toma el primero que exista de cada lista.
HEIGHT_CANDIDATES = ('height', 'heightcm', 'estatura', 'altura')
WEIGHT_CANDIDATES = ('weight', 'weightkg', 'peso')
_IDENTIFIER = re.compile(r'^[a-z_][a-z0-9_]*$')

Loader = Callable[[str, Optional[dict]], pd.DataFrame]


def available_columns(load: Loader) -> set:
    """{(tabla, columna)} que el lector puede ver. Si no se puede consultar, se usan solo las base."""
    try:
        frame = load(COLUMNS_SQL, None)
        return {(str(t).lower(), str(c).lower()) for t, c in zip(frame['table_name'], frame['column_name'])}
    except Exception:  # sin permiso, sin conexión o respuesta inesperada: no bloquea la carga
        return set()


def _first(columns: set, table: str, candidates) -> Optional[str]:
    return next((name for name in candidates if (table, name) in columns), None)


def _extras(parts: list) -> str:
    return ''.join(f',\n           {part}' for part in parts)


def sheet_sql(columns: set) -> str:
    has = lambda name: ('actuaciones_jugadores', name) in columns  # noqa: E731
    return _SHEET.format(extras=_extras([
        'a.secondyellow::int AS second_yellows' if has('secondyellow') else 'NULL::int AS second_yellows',
        'a.owngoals::int AS own_goals' if has('owngoals') else 'NULL::int AS own_goals']))


def matches_sql(columns: set) -> str:
    return _MATCHES.format(extras=_extras([
        'c.matchlength AS nominal_duration' if ('competiciones', 'matchlength') in columns else 'NULL AS nominal_duration',
        'p.matchstatus AS matchstatus' if ('partidos', 'matchstatus') in columns else 'NULL AS matchstatus']))


def players_sql(columns: set) -> str:
    height = _first(columns, 'jugadores', HEIGHT_CANDIDATES)
    weight = _first(columns, 'jugadores', WEIGHT_CANDIDATES)
    parts = ['j.datefrom AS datefrom' if ('jugadores', 'datefrom') in columns else 'NULL AS datefrom',
             f'j.{height} AS height' if height else 'NULL AS height',
             f'j.{weight} AS weight' if weight else 'NULL AS weight']
    assert all(_IDENTIFIER.match(name or 'x') for name in (height, weight)), 'nombre de columna no válido'
    return _PLAYERS.format(extras=_extras(parts))


def fetch_raw(load: Loader) -> dict:
    """Ejecuta las consultas con `load(sql, params)` y devuelve los datos sin procesar."""
    params = {'club': OHIGGINS_CLUB_ID}
    columns = available_columns(load)
    return dict(sheet=load(sheet_sql(columns), params), matches=load(matches_sql(columns), params),
                players=load(players_sql(columns), params), goalkeepers=load(GOALKEEPERS_SQL, params))
