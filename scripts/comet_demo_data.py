"""Datos COMET FICTICIOS para pruebas y demostraciones. No contienen personas ni resultados reales.

Genera, con semilla fija, las mismas tablas que lee el portal (planillas, partidos, jugadores y
arqueros) para tres temporadas de un club imaginario. Los nombres se componen de listas cortas
y apellidos inventados; cualquier parecido con una persona real es casual.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from datetime import timedelta

TODAY = pd.Timestamp('2026-09-30')

# categoría -> (tope de edad, duración del partido, partidos por temporada)
CATEGORIES = {
    'Primer Equipo': (None, 90, 30), 'U-19': (19, 90, 30), 'U-16': (16, 80, 30),
    'U-15': (15, 80, 30), 'U-14': (14, 70, 30), 'U-13': (13, 70, 30), 'U-12': (12, 60, 26),
}
FIRST = ['Matías', 'Benjamín', 'Vicente', 'Martín', 'Joaquín', 'Tomás', 'Agustín', 'Maximiliano', 'Cristóbal',
         'Sebastián', 'Nicolás', 'Felipe', 'Lucas', 'Diego', 'Gaspar', 'Emilio', 'Bastián', 'Santiago',
         'Ignacio', 'Renato', 'Alonso', 'Facundo', 'Amaru', 'Dante']
LAST = ['Aravena', 'Quilodrán', 'Valdomar', 'Reyeros', 'Tapiaga', 'Morandé', 'Cuadrat', 'Elgueta', 'Lizamar',
        'Ponchet', 'Barrenil', 'Solmayor', 'Cantuel', 'Ibarrola', 'Norambel', 'Velasten', 'Orrego', 'Zambrán',
        'Pedrales', 'Cañuman', 'Ferretti', 'Huenulaf', 'Bascuñán', 'Trelles']
RIVALS = ['Club Ficticio Norte', 'Deportivo Ejemplo', 'Unión Muestra', 'Atlético Simulado', 'Racing Prueba',
          'Sporting Demostración', 'Liga Imaginaria', 'Independiente Modelo']
OWN_CLUB = 'Club Demo O\'H'


def _caps():
    return sorted((cap, name) for name, (cap, _, _) in CATEGORIES.items() if cap)


def _age_category(age: int) -> str:
    for cap, name in _caps():
        if age <= cap:
            return name
    return 'Primer Equipo'


def build_raw(seed: int = 2026, today: pd.Timestamp = TODAY) -> dict:
    """Devuelve dict con `sheet`, `matches`, `players`, `goalkeepers` (formato de las consultas)."""
    rng = np.random.default_rng(seed)
    names = [f'{f} {l}' for f in FIRST for l in LAST]
    rng.shuffle(names)
    n_players = 264
    players = pd.DataFrame({
        'personid': np.arange(9001, 9001 + n_players),
        'displayname': names[:n_players],
        'dateofbirth': [pd.Timestamp(year=int(y), month=int(m), day=int(d)) for y, m, d in zip(
            rng.integers(2004, 2015, n_players), rng.integers(1, 13, n_players), rng.integers(1, 29, n_players))],
        'nationality': rng.choice(['Chile', 'Chile', 'Chile', 'Chile', 'Argentina', 'Venezuela'], n_players),
        'status': 'ACTIVO', 'orgname': "O'Higgins",
    })
    players['level'] = np.where(players['dateofbirth'].dt.year <= 2006, 'Profesional', 'Formativo')
    players['is_keeper'] = rng.random(n_players) < 0.10
    ability = dict(zip(players['personid'], rng.random(n_players)))

    matches, sheet_rows, keeper_rows = [], [], []
    match_id, comp_id = 500000, {}
    ladder = [n for _, n in _caps()] + ['Primer Equipo']
    # Algunos jugadores se quedan las tres temporadas en la misma categoría (caso de la alerta).
    stalled = set(players.loc[players['dateofbirth'].dt.year.isin([2011, 2012]), 'personid'].head(5))
    assigned_prev = {}
    for season in (2024, 2025, 2026):
        assigned = {}
        for p in players.itertuples():
            age = season - p.dateofbirth.year
            if age < 11 or age > 21:
                continue
            base = _age_category(age)
            roll = rng.random()
            if p.personid in stalled and p.personid in assigned_prev:
                base = assigned_prev[p.personid]                # sin promoción
            elif roll < 0.14 and ladder.index(base) + 1 < len(ladder):
                base = ladder[ladder.index(base) + 1]           # juega en una categoría superior
            elif roll < 0.20 and p.personid in assigned_prev:
                base = assigned_prev[p.personid]                # se queda un año más
            assigned[p.personid] = base
        assigned_prev = assigned
        squads = {}
        for pid, cat in assigned.items():
            squads.setdefault(cat, []).append(pid)

        for cat, (_, duration, n_matches) in CATEGORIES.items():
            squad = squads.get(cat, [])
            keepers = [p for p in squad if players.loc[players.personid == p, 'is_keeper'].iloc[0]]
            if not keepers and len(squad) >= 14:
                keepers = squad[:1]  # toda serie necesita al menos un arquero en la demostración
            field = [p for p in squad if p not in keepers]
            if not keepers or len(field) < 12:
                continue
            comp_id.setdefault((cat, season), 7000 + len(comp_id))
            first_saturday = pd.Timestamp(f'{season}-03-07')
            for k in range(n_matches):
                date = first_saturday + timedelta(days=7 * k + int(rng.integers(0, 2)))
                date = date + timedelta(hours=int(rng.choice([10, 12, 15])))
                if date > today:
                    continue
                match_id += 1
                home = bool(rng.random() < 0.5)
                gf, ga = int(rng.poisson(1.5)), int(rng.poisson(1.1))
                matches.append(dict(
                    matchid=match_id, competition_id=comp_id[(cat, season)], matchdate=date, category=cat,
                    competition=f'Campeonato {cat} {season}', season=str(season),
                    venue='Local' if home else 'Visita',
                    home_team=OWN_CLUB if home else str(rng.choice(RIVALS)),
                    away_team=str(rng.choice(RIVALS)) if home else OWN_CLUB,
                    goals_for=gf, goals_against=ga,
                    result='Victoria' if gf > ga else 'Empate' if gf == ga else 'Derrota'))
                called = list(rng.choice(field, size=min(17, len(field)), replace=False,
                                         p=_weights(field, ability)))
                keeper = int(rng.choice(keepers))
                starters = called[:10] + [keeper]
                bench = called[10:] + ([int(rng.choice([x for x in keepers if x != keeper]))]
                                       if len(keepers) > 1 else [])
                minutes = {p: duration for p in starters}
                entered = {}
                for p in bench[:int(rng.integers(0, 4))]:
                    if p in keepers:
                        continue
                    on = int(rng.integers(35, duration - 4))
                    entered[p] = duration - on
                    out = rng.choice([s for s in starters if s != keeper])
                    minutes[out] = min(minutes[out], on)
                minutes.update(entered)
                scorers = rng.choice([p for p in minutes if p != keeper], size=gf) if gf else []
                goals = {p: int((np.array(scorers) == p).sum()) for p in set(scorers)}
                for pid in starters + bench:
                    played = pid in minutes
                    sheet_rows.append(dict(
                        matchid=match_id, competition_id=comp_id[(cat, season)], personid=pid,
                        played=played, startinglineup=pid in starters,
                        minutesplayed=minutes.get(pid, 0), goals=goals.get(pid, 0),
                        yellow_cards=int(rng.random() < 0.05 + 0.10 * (1 - ability[pid])),
                        red_cards=int(rng.random() < 0.006),
                        goalkeeper=pid in keepers))
                keeper_rows.append(dict(matchid=match_id, competition_id=comp_id[(cat, season)], personid=keeper,
                                        played=True, minutesplayed=minutes[keeper], goalsconceded=ga))
    players = players.drop(columns='is_keeper')
    return dict(sheet=pd.DataFrame(sheet_rows), matches=pd.DataFrame(matches), players=players,
                goalkeepers=pd.DataFrame(keeper_rows))


def _weights(pool, ability):
    w = np.array([0.35 + ability[p] for p in pool])
    return w / w.sum()

