"""Consultas de solo lectura a las tablas COMET (esquema `public`).

Solo se usan columnas que ya consultan las pantallas actuales de `app/comet_dashboard.py`.
Se piden únicamente las filas de O'Higgins y los jugadores que figuran en sus planillas
(minimización de datos de menores). Las tablas se leen con el rol `comet_reader`.
"""
from __future__ import annotations

from typing import Callable

import pandas as pd

OHIGGINS_CLUB_ID = 40010  # mismo identificador que app/comet_dashboard.py (lo verifica un test)

SHEET_SQL = """
    SELECT a.matchid, a.id AS competition_id, a.personid, a.played, a.startinglineup,
           a.minutesplayed, a.goals,
           a.singleyellow::int AS yellow_cards, a.redcards::int AS red_cards, a.goalkeeper
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
MATCHES_SQL = """
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
           END AS result
    FROM partidos p
    JOIN competiciones c ON p.id = c.id
    LEFT JOIN equipos e_home ON p.hometeam = e_home.clubid
    LEFT JOIN equipos e_away ON p.awayteam = e_away.clubid
    LEFT JOIN scores s ON p.matchid = s.matchid
    WHERE (p.hometeam = %(club)s OR p.awayteam = %(club)s)
      AND p.matchdate IS NOT NULL
      AND p.matchdate < NOW()
"""

PLAYERS_SQL = """
    SELECT j.personid, j.displayname, j.dateofbirth, j.nationality, j.level, j.status, j.orgname
    FROM jugadores j
    WHERE j.personid IN (SELECT a.personid FROM actuaciones_jugadores a WHERE a.clubid = %(club)s)
"""

Loader = Callable[[str, dict], pd.DataFrame]


def fetch_raw(load: Loader) -> dict:
    """Ejecuta las cuatro consultas con `load(sql, params)` y devuelve los datos sin procesar."""
    params = {'club': OHIGGINS_CLUB_ID}
    return dict(sheet=load(SHEET_SQL, params), matches=load(MATCHES_SQL, params),
                players=load(PLAYERS_SQL, params), goalkeepers=load(GOALKEEPERS_SQL, params))
