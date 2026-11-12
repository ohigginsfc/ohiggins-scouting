"""Plantel vigente en las pantallas COMET (solo administración): quién cuenta, quién no y las bajas.

COMET no borra a quien deja el club y lo sigue mostrando como «ACTIVO», así que contar todos esos registros infla el Primer Equipo. Estas
funciones toman el plantel que ya leía `comet_dashboard` y le aplican la regla de vigencia y las bajas guardadas
(`scouting.comet.roster`). Nada se borra ni se escribe en COMET: las bajas viven en `portal.comet_player_bajas`.

No importa `comet_dashboard` ni `comet_context` al cargarse (ellos importan este módulo dentro de sus pantallas).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd
import streamlit as st

from scouting.comet import config_store, roster
from scouting.comet.facts import norm_id
from scouting.comet.rules import Rules
from scouting.portal import readonly_pilot
from scouting.portal.security import admin_only
from ui.comet_widgets import FMT_INT, inject_styles, rule_note, show_table

FLASH = 'comet_squad_flash'
DATE = lambda value: f'{value:%d-%m-%Y}'  # noqa: E731


def now() -> pd.Timestamp:
    """Hora de Santiago; es la de `comet_context` para que demostraciones y pruebas la fijen en un solo lugar."""
    import comet_context
    return comet_context.now()


@dataclass(frozen=True)
class Roster:
    classified: pd.DataFrame   # todos los registrados como activos, con `state` y `reason`
    current: pd.DataFrame      # solo los vigentes: lo que cuentan las pantallas
    bajas: pd.DataFrame
    rules: Rules
    today: pd.Timestamp
    store_error: Optional[str]  # por qué no se pudieron leer las reglas o las bajas guardadas (None si todo bien)

    @property
    def activity_days(self) -> int:
        return self.rules.value('squad_activity_days')

    @property
    def excluded(self) -> int:
        return len(self.classified) - len(self.current)

    @property
    def can_write(self) -> bool:
        return self.store_error is None and not readonly_pilot.enabled()


@admin_only
def load_roster(squad: pd.DataFrame) -> Roster:
    """Clasifica el plantel leído de COMET. Si no se pueden leer las bajas, usa solo la regla automática y lo avisa."""
    try:
        stored, bajas, error = config_store.load_roster_config()
    except config_store.StoreUnavailable as exc:
        stored, bajas, error = {}, roster.EMPTY_BAJAS, str(exc)
    rules = Rules({k: v for k, v in stored.items() if k != config_store.ALERT_CONFIG_KEY})
    today = now()
    classified = roster.classify(squad, today, rules.value('squad_activity_days'), bajas)
    return Roster(classified, roster.current(classified), bajas, rules, today, error)


@admin_only
def render_notice(r: Roster) -> None:
    """Cuántos registros quedan fuera de las cifras y por qué (bajo las cifras de cada pantalla)."""
    if r.classified.empty:
        return
    inject_styles()
    rule_note(r.rules, ['squad_activity_days'])
    st.caption(f'Plantel vigente: {len(r.current)} de {len(r.classified)} jugadores que COMET mantiene como activos. '
               f'{r.excluded} no cuentan: sin planilla de O’Higgins en los últimos {r.activity_days} días o con baja registrada. '
               'Nada se borra; el detalle y la reincorporación están en Estructura del plantel.')
    if r.store_error:
        st.caption(f'No se pudieron leer las bajas guardadas ({r.store_error}); se usa solo la regla automática.')


@admin_only
def exclude_former(stats: pd.DataFrame, r: Roster, key: str) -> pd.DataFrame:
    """Quita de una lista de estadísticas a quienes ya no están en el plantel, salvo que se pida ver el histórico."""
    if r.classified.empty or stats.empty:
        return stats
    if st.checkbox('Incluir jugadores que ya no están en el club (histórico)', value=False, key=key):
        return stats
    return stats[stats['personid'].map(norm_id).isin(set(r.current['personid']))]


def _flash() -> None:
    """Aviso que sobrevive al `st.rerun()` que actualiza las listas después de guardar: (nivel, texto)."""
    shown = st.session_state.pop(FLASH, None)
    if shown:
        level, message = shown
        getattr(st, level)(message)


def _availability(r: Roster) -> bool:
    """Muestra por qué no se puede escribir (si es el caso) y devuelve si los controles deben quedar deshabilitados."""
    if r.store_error:
        st.warning(f'No se pueden registrar bajas: {r.store_error}')
    elif readonly_pilot.enabled():
        st.info('Modo solo lectura: las bajas no se pueden modificar desde aquí.')
    return not r.can_write


def _people(frame: pd.DataFrame) -> dict:
    """{personid: etiqueta} con nombre y edad; sin nombre o edad se escribe «Jugador sin ficha» o «—»."""
    labels = {}
    for row in frame.sort_values('displayname', na_position='last').itertuples():
        name = row.displayname if isinstance(row.displayname, str) and row.displayname else 'Jugador sin ficha'
        age = '—' if pd.isna(row.age) else f'{int(row.age)} años'
        labels[row.personid] = f'{name} · {age}'
    return labels


def _reinstate_form(r: Roster, rows: pd.DataFrame, key: str, disabled: bool) -> None:
    labels = _people(rows)
    with st.form(f'comet_reinstate_{key}', clear_on_submit=True):
        back = st.multiselect('Reincorporar al plantel', list(labels), format_func=labels.get, disabled=disabled,
                              key=f'reinstate_pick_{key}')
        submitted = st.form_submit_button('Reincorporar', disabled=disabled)
    if not submitted:
        return
    if not back:
        st.warning('Elige al menos un jugador.')
        return
    try:
        count = config_store.reinstate_bajas(back)
    except (ValueError, PermissionError, config_store.StoreUnavailable) as exc:
        st.error(str(exc))
        return
    st.session_state[FLASH] = (('success', f'Se reincorporó a {count} jugador(es). Vuelven a contar en el plantel si les '
                                           'corresponde por la regla automática.') if count else
                               ('info', 'Esos jugadores ya no tenían una baja vigente (otra persona pudo reincorporarlos antes). '
                                        'La lista se actualizó.'))
    st.rerun()


@admin_only
def render_baja_panel(r: Roster, category: str) -> None:
    """Desarrollo juvenil: dar de baja a jugadores de la categoría (por ejemplo, quienes dejan el club) y reincorporarlos."""
    _flash()
    pool = r.current[r.current['age_category'] == category]
    baja = r.classified[(r.classified['state'] == roster.STATE_BAJA) & (r.classified['age_category'] == category)]
    with st.expander(f'Bajas de {category}: sacar a un jugador del plantel o reincorporarlo'):
        st.caption('Una baja saca al jugador de las cifras y listas del plantel; no borra nada en COMET y se puede revertir. '
                   'Su historial de partidos, goles y minutos se conserva.')
        disabled = _availability(r)
        labels = _people(pool)
        with st.form(f'comet_baja_{category}', clear_on_submit=True):
            picked = st.multiselect('Jugadores que causan baja', list(labels), format_func=labels.get, disabled=disabled,
                                    key=f'baja_pick_{category}')
            c1, c2 = st.columns(2)
            reason = c1.selectbox('Motivo', list(roster.BAJA_REASONS), format_func=roster.BAJA_REASONS.get,
                                  disabled=disabled, key=f'baja_reason_{category}')
            day = c2.date_input('Fecha de la baja', value=r.today.date(), max_value=r.today.date(), disabled=disabled,
                                key=f'baja_day_{category}')
            note = st.text_input('Nota (opcional)', max_chars=500, disabled=disabled, key=f'baja_note_{category}')
            confirm = st.checkbox('Confirmo que estos jugadores dejan de contar en el plantel (se puede revertir)',
                                  disabled=disabled, key=f'baja_confirm_{category}')
            submitted = st.form_submit_button('Dar de baja', disabled=disabled)
        if submitted:
            if not picked:
                st.warning('Elige al menos un jugador.')
            elif not confirm:
                st.warning('Marca la confirmación para registrar la baja.')
            else:
                try:
                    count = config_store.set_bajas(picked, reason, day, note)
                except (ValueError, PermissionError, config_store.StoreUnavailable) as exc:
                    st.error(str(exc))
                else:
                    st.session_state[FLASH] = ('success', f'Se registró la baja de {count} jugador(es). Ya no cuentan en el '
                                                          'plantel; se pueden reincorporar en este mismo panel.')
                    st.rerun()
        if len(baja):
            st.markdown(f'**Bajas registradas en {category}**')
            show_table(baja, {'displayname': ('Jugador', None), 'age': ('Edad', FMT_INT), 'reason': ('Baja', None)},
                       name=f'Bajas registradas · {category}')
            _reinstate_form(r, baja, f'{category}', disabled)


@admin_only
def render_audit(r: Roster, order: list[str]) -> None:
    """Estructura del plantel: qué registros cuentan y cuáles no, con la comparación de plazos y la reincorporación."""
    _flash()
    if r.classified.empty:
        return
    st.markdown('---')
    st.subheader('🧹 Revisión del plantel: quién cuenta y quién no')
    st.caption(f'COMET mantiene como activos a {len(r.classified)} jugadores registrados en O’Higgins, pero solo '
               f'{len(r.current)} figuran en una planilla de los últimos {r.activity_days} días, tienen un alta reciente o no '
               'tienen baja. El resto no se borra: aquí se revisa y, si hace falta, se reincorpora.')
    show_table(roster.summary_by_category(r.classified, order), {
        'Categoría': ('Categoría', None), 'Vigentes': ('Vigentes (cuentan)', FMT_INT),
        roster.STATE_INACTIVE: (roster.STATE_INACTIVE, FMT_INT), roster.STATE_BAJA: (roster.STATE_BAJA, FMT_INT),
        'Registrados en COMET': ('Registrados en COMET', FMT_INT)}, name='Plantel · resumen por categoría')
    with st.expander('¿Qué plazo conviene? Cuántos jugadores quedarían vigentes con cada uno'):
        st.caption('Cada fila repite la regla automática con otro plazo, para elegirlo con los datos a la vista. '
                   'El plazo vigente se cambia en Seguimiento y configuración → Reglas.')
        show_table(roster.calibration(r.classified, r.today, r.bajas), {
            'Días sin planilla': ('Días sin planilla', FMT_INT), 'Vigentes': ('Vigentes', FMT_INT),
            'Primer Equipo': ('Primer Equipo', FMT_INT), 'Categorías menores': ('Categorías menores', FMT_INT)},
            name='Plantel · plazo de actividad')
    views = {'Sin actividad reciente (no cuentan)': roster.STATE_INACTIVE, 'Con baja registrada': roster.STATE_BAJA,
             'Vigentes (cuentan)': roster.STATE_CURRENT}
    chosen = st.selectbox('Ver los jugadores', list(views), key='squad_audit_view')
    rows = r.classified[r.classified['state'] == views[chosen]].sort_values(['age_category', 'displayname'])
    show_table(rows, {'displayname': ('Jugador', None), 'age': ('Edad', FMT_INT), 'age_category': ('Categoría', None),
                      'nationality': ('Nacionalidad', None), 'last_sheet': ('Última planilla', DATE),
                      'reason': ('Detalle', None)}, name=f'Plantel · {chosen}')
    bajas = r.classified[r.classified['state'] == roster.STATE_BAJA]
    if len(bajas):
        _reinstate_form(r, bajas, 'audit', not r.can_write)
