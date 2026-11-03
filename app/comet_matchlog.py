"""Historial de partidos de un jugador con sus subidas de categoría marcadas (Ficha del jugador y Jugadores adelantados).

Muestra todos los partidos del jugador en las planillas de COMET, de todas las temporadas y categorías, sin recortar nada:
el historial completo de quien sube de categoría. Las subidas se detectan con los partidos que COMET tiene registrados.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from comet_context import Context
from scouting.comet import adelantados, events
from scouting.portal.security import admin_only
from ui.comet_widgets import FMT_INT, RESULT_STYLE, fmt, show_table

ALL_MATCHES = 'Todos sus partidos'
ONLY_ABOVE_AGE = 'Solo los jugados por encima de su edad'
ONLY_ASCENTS = 'Solo los partidos en que subió de categoría'
NEWEST_FIRST = 'Del más reciente al más antiguo'
CHRONOLOGICAL = 'Del primero al último'


def _rival(value) -> str:
    return value if isinstance(value, str) and value else 'rival sin nombre'


def _above_age(steps) -> str | None:
    if pd.isna(steps):
        return None
    return f'Sí, +{int(steps)}' if steps > 0 else 'No'


def player_log(ctx: Context, personid: str) -> pd.DataFrame:
    """Los partidos del jugador, cronológicos, con el resultado real en cancha y el texto de cada marca."""
    log = adelantados.player_timeline(ctx.ds, personid)
    log = log.assign(
        fecha=log['matchdate'].dt.strftime('%d-%m-%Y'),
        rival=log['rival'].map(_rival),
        marcador=[None if pd.isna(a) or pd.isna(b) else f'{int(a)}-{int(b)}' for a, b in zip(log['goals_for'], log['goals_against'])],
        sobre_su_edad=[_above_age(steps) if played else None for steps, played in zip(log['steps_ahead'], log['participated'])],
        ascenso=[f'Subió de {before} a {now}' if up else None
                 for up, before, now in zip(log['ascended'], log['highest_before'], log['category'])])
    return events.attach_results(log, ctx.computed.onpitch)


def _summary(log: pd.DataFrame) -> None:
    played = log[log['participated']]
    above = played[played['ahead']]
    k = st.columns(4)
    k[0].metric('Partidos en su historial', len(log))
    k[1].metric('Partidos jugados', len(played))
    k[2].metric('Subidas de categoría', int(log['ascended'].sum()))
    k[3].metric('Jugados por encima de su edad', len(above))
    if len(above):
        minutes = above['minutes'].sum(min_count=1)
        st.caption(f'Minutos jugados por encima de su edad: {fmt(minutes)}'
                   f'{"" if above["minutes"].notna().all() else " (hay partidos sin minutos conocidos: el total no los incluye)"}.')
    for row in log[log['ascended']].itertuples():
        day = f'{row.matchdate:%d-%m-%Y}' if pd.notna(row.matchdate) else 'fecha sin dato'
        season = f', temporada {int(row.season_year)}' if pd.notna(row.season_year) else ''
        st.caption(f'Subió de {row.highest_before} a {row.category} en su partido del {day}{season}.')


@admin_only
def render_match_log(ctx: Context, personid: str, key: str, oldest_first: bool = False) -> None:
    """Resumen del historial y tabla de todos los partidos del jugador, con filtros que no ocultan nada por defecto."""
    log = player_log(ctx, personid)
    if log.empty:
        st.info('Este jugador no tiene partidos en las planillas de COMET.')
        return
    _summary(log)
    c1, c2 = st.columns(2)
    with c1:
        shown = st.radio('Mostrar', [ALL_MATCHES, ONLY_ABOVE_AGE, ONLY_ASCENTS], horizontal=True, key=f'{key}_filter')
    with c2:
        order = st.radio('Orden', [NEWEST_FIRST, CHRONOLOGICAL], index=1 if oldest_first else 0, horizontal=True,
                         key=f'{key}_order')
    if shown == ONLY_ABOVE_AGE:
        log = log[log['participated'] & log['ahead']]
    elif shown == ONLY_ASCENTS:
        log = log[log['ascended']]
    if order == NEWEST_FIRST:
        log = log.iloc[::-1]
    show_table(log, {
        'fecha': ('Fecha', None), 'season_year': ('Temporada', '{:.0f}'), 'category': ('Categoría', None),
        'age_category': ('Le corresponde por edad', None), 'sobre_su_edad': ('Por encima de su edad', None),
        'ascenso': ('Subida de categoría', None), 'rival': ('Rival', None), 'venue': ('Local / Visita', None),
        'marcador': ('Marcador final', None), 'result': ('Resultado final', None), 'role': ('Rol', None),
        'minutes': ('Minutos', FMT_INT), 'goals': ('Goles', FMT_INT), 'yellow_cards': ('Amarillas', FMT_INT),
        'red_cards': ('Rojas', FMT_INT),
        'onpitch_entry': ('Entró', None), 'onpitch_exit': ('Salió', None),
        'onpitch_score_entry': ('Marcador al entrar', None), 'onpitch_state_entry': ('Al entrar', None),
        'onpitch_score_exit': ('Marcador al salir', None), 'onpitch_state_exit': ('Al salir', None),
        'onpitch_changed': ('¿Cambió el resultado?', None),
        'onpitch_for': ('Goles a favor en cancha', FMT_INT), 'onpitch_against': ('Goles en contra en cancha', FMT_INT),
        'onpitch_status': ('Cronología', None)}, colors=('result', RESULT_STYLE))
    st.caption('Gol y cambio en el mismo minuto: se cuenta el gol con el jugador dentro. Las subidas de categoría se detectan '
               'comparando con los partidos que COMET tiene registrados: antes de ese historial no se sabe en qué categoría jugó.')
