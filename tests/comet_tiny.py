"""Mini-torneo ficticio con resultados calculables a mano. Lo usan las pruebas de cálculo.

Categorías: U-14, U-15 y Primer Equipo. Temporada 2026, corte de edad 31-12 (por defecto).

    P1 nació 2011-06-10 (15 años)  -> le corresponde U-15
    P2 nació 2012-03-01 (14 años)  -> le corresponde U-14, juega en U-15: adelantado
    P3 arquero, 2011-01-20 (15)
    P4 nació 2011-09-09 (15), solo aparece como suplente que no ingresa
    P5 nació 2012-05-05 (14), juega en U-14 (su categoría)

Competición 100 = U-15 2026 (3 partidos de 80 min, todos ya jugados):
    M1 sáb 07-03 Local  2-1 Victoria   M2 sáb 14-03 Visita 0-0 Empate   M3 sáb 21-03 Local 0-3 Derrota
Competición 200 = U-14 2026 (1 partido de 70 min):  M4 dom 08-03 Local 1-0 Victoria; juegan P2 y P5.
"""
import pandas as pd

TODAY = pd.Timestamp('2026-09-30')


def sheet_row(matchid, personid, played, starting, minutes, goals=0, yellow=0, red=0, keeper=False, comp=100):
    return dict(matchid=matchid, competition_id=comp, personid=personid, played=played, startinglineup=starting,
                minutesplayed=minutes, goals=goals, yellow_cards=yellow, red_cards=red, goalkeeper=keeper)


def build(extra_sheet=(), extra_matches=(), extra_players=()):
    matches = pd.DataFrame([
        dict(matchid=1, competition_id=100, matchdate=pd.Timestamp('2026-03-07 15:00'), category='U-15',
             competition='Campeonato U-15 2026', season='2026', venue='Local', home_team='O\'Higgins',
             away_team='Rival A', goals_for=2, goals_against=1, result='Victoria'),
        dict(matchid=2, competition_id=100, matchdate=pd.Timestamp('2026-03-14 15:00'), category='U-15',
             competition='Campeonato U-15 2026', season='2026', venue='Visita', home_team='Rival B',
             away_team='O\'Higgins', goals_for=0, goals_against=0, result='Empate'),
        dict(matchid=3, competition_id=100, matchdate=pd.Timestamp('2026-03-21 15:00'), category='U-15',
             competition='Campeonato U-15 2026', season='2026', venue='Local', home_team='O\'Higgins',
             away_team='Rival C', goals_for=0, goals_against=3, result='Derrota'),
        dict(matchid=4, competition_id=200, matchdate=pd.Timestamp('2026-03-08 11:00'), category='U-14',
             competition='Campeonato U-14 2026', season='2026', venue='Local', home_team='O\'Higgins',
             away_team='Rival D', goals_for=1, goals_against=0, result='Victoria'),
    ] + list(extra_matches))
    players = pd.DataFrame([
        dict(personid=1, displayname='Jugador Uno', dateofbirth='2011-06-10', nationality='Chile', level='Formativo',
             status='ACTIVO', orgname='O\'Higgins'),
        dict(personid=2, displayname='Jugador Dos', dateofbirth='2012-03-01', nationality='Chile', level='Formativo',
             status='ACTIVO', orgname='O\'Higgins'),
        dict(personid=3, displayname='Arquero Tres', dateofbirth='2011-01-20', nationality='Chile', level='Formativo',
             status='ACTIVO', orgname='O\'Higgins'),
        dict(personid=4, displayname='Jugador Cuatro', dateofbirth='2011-09-09', nationality='Chile', level='Formativo',
             status='ACTIVO', orgname='O\'Higgins'),
        dict(personid=5, displayname='Jugador Cinco', dateofbirth='2012-05-05', nationality='Chile', level='Formativo',
             status='ACTIVO', orgname='O\'Higgins'),
    ] + list(extra_players))
    sheet = pd.DataFrame([
        sheet_row(1, 1, True, True, 80, goals=1, yellow=1), sheet_row(1, 2, True, False, 30),
        sheet_row(1, 3, True, True, 80, keeper=True), sheet_row(1, 4, False, False, 0),
        sheet_row(2, 1, True, True, 60, yellow=1), sheet_row(2, 2, True, True, 80),
        sheet_row(2, 3, False, False, 0, keeper=True), sheet_row(2, 4, False, False, 0),
        sheet_row(3, 1, False, False, 0), sheet_row(3, 2, True, True, 80, goals=1, yellow=1),
        sheet_row(3, 3, True, True, 80, keeper=True), sheet_row(3, 4, False, False, 0),
        sheet_row(4, 2, True, True, 70, comp=200), sheet_row(4, 5, True, True, 70, comp=200),
    ] + list(extra_sheet))
    keepers = pd.DataFrame([
        dict(matchid=1, competition_id=100, personid=3, played=True, minutesplayed=80, goalsconceded=1),
        dict(matchid=3, competition_id=100, personid=3, played=True, minutesplayed=80, goalsconceded=3),
    ])
    return dict(sheet=sheet, matches=matches, players=players, goalkeepers=keepers)
