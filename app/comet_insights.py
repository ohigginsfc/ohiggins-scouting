"""Pantallas COMET: indicadores, alertas, jugadores adelantados y seguimiento (solo administración)."""
from __future__ import annotations

from datetime import timedelta
from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from comet_context import Context, context, season_choices
from scouting.comet import adelantados, alerts as alert_rules, config_store, indicators, quality
from scouting.comet.dependencies import PIPELINE_DEPENDENCIES
from scouting.comet.digest import build_weekly_digest, previous_week
from scouting.comet.rules import ORIGIN_PABLO, RULE_DEFS, RULES_BY_KEY, parse
from scouting.portal.security import admin_only
from ui.comet_widgets import (FMT_1, FMT_2, FMT_INT, FMT_PCT, SERIES_COLORS, alert_tile, fmt, inject_styles, pill,
                              rule_note, show_static_table, show_table, status_pill, title)
from ui.theme import OHIGGINS_BLUE, apply_ohiggins_plotly_theme

THRESHOLD_RULES = {'yellow_cards': 'yellow_threshold', 'low_participation': 'participation_threshold',
                   'no_promotion': 'seasons_without_promotion'}
QUALITY_COLORS = {'Correcto': 'Verde', 'Aviso': 'Naranja', 'Error': 'Rojo', 'Información': 'Azul'}
CHOICE_LABELS = {'competicion': 'Por competición', 'temporada': 'Por temporada completa',
                 'registrada': 'Registrada (el minuto más largo jugado)', 'nominal': 'Nominal (duración reglamentaria)',
                 'primer_partido': 'Primer partido registrado', 'datefrom': 'Fecha «datefrom» de la ficha'}
WEEKDAYS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']


def _season_picker(ctx: Context, key: str) -> int:
    return st.selectbox('Temporada', season_choices(ctx), key=key)


def _label(value, fallback: str = 'Jugador sin ficha') -> str:
    return value if isinstance(value, str) and value else fallback


def _named(frame: pd.DataFrame, column: str = 'displayname') -> pd.DataFrame:
    return frame.assign(**{column: frame[column].map(_label)})


@admin_only
def page_indicators() -> None:
    inject_styles()
    title('Indicadores por categoría', 'Participación, victorias, edad, antigüedad y minutos de jugadores más chicos.')
    ctx = context()
    ds, cat = ctx.ds, ctx.computed.cat
    if ds.facts.empty:
        st.info('COMET no tiene planillas de O’Higgins.')
        return
    rule_note(ctx.rules, ['age_cutoff', 'possible_from_first_call', 'min_minutes_on_pitch', 'seniority_rule'])
    season = _season_picker(ctx, 'ci_season')
    ind = indicators.category_indicators(ds, cat, season, ctx.today)
    if ind.empty:
        st.info('No hay partidos de esa temporada.')
        return
    tabs = st.tabs(['Por categoría', 'Edad y categoría', 'Minutos de jugadores más chicos', 'Partidos por jugador',
                    'Disciplina y goles', 'Participación y victorias'])
    seniority_from_profile = ctx.rules.value('seniority_rule') == 'datefrom'

    with tabs[0]:
        show_table(ind, {
            'category': ('Categoría', None), 'partidos': ('Partidos', FMT_INT), 'pct_victorias': ('% victorias de la serie', FMT_PCT),
            'jugadores_citados': ('Jugadores citados', FMT_INT), 'jugadores_con_minutos': ('Jugadores con minutos', FMT_INT),
            'edad_promedio': ('Edad promedio', FMT_1),
            'antiguedad_promedio': ('Antigüedad promedio (años, datefrom)' if seniority_from_profile
                                   else 'Antigüedad promedio (años, mínimo)', FMT_1),
            'participacion_pct': ('Participación (% de minutos posibles)', FMT_PCT), 'minutos_totales': ('Minutos totales de la serie', FMT_INT),
            'filas_contradictorias': ('Filas contradictorias', FMT_INT)})
        if int(ind['filas_contradictorias'].sum()):
            st.caption('Las filas contradictorias (repetidas con valores distintos) no se suman: los totales de esas series '
                       'están incompletos. Detalle en Seguimiento y configuración → Calidad de datos.')
        horizon = quality.history_horizon(ds)
        if seniority_from_profile:
            st.caption('La antigüedad usa la fecha «datefrom» de la ficha de COMET; si falta, queda sin dato. '
                       'La edad se mide en la fecha de corte de la temporada.')
        elif horizon['first'] is not None:
            st.caption(f'La antigüedad cuenta desde el primer partido registrado en COMET ({horizon["first"]:%d-%m-%Y}); '
                       'es un mínimo, no la fecha real de ingreso al club. La edad se mide en la fecha de corte de la temporada.')

    with tabs[1]:
        matrix = indicators.age_category_matrix(ds, season)
        if matrix.empty:
            st.info('Sin jugadores con minutos en esa temporada.')
        else:
            fig = px.imshow(matrix, text_auto=True, aspect='auto', color_continuous_scale=['#F4F8FC', OHIGGINS_BLUE],
                            labels=dict(x='Categoría en que juegan', y='Categoría que les corresponde por edad', color='Jugadores'))
            apply_ohiggins_plotly_theme(fig, height=380)
            st.plotly_chart(fig, use_container_width=True)
            st.caption('Cada celda cuenta jugadores con minutos. La diagonal son quienes juegan en la categoría que les '
                       'corresponde por edad; a la derecha de la diagonal, quienes juegan en una superior (adelantados).')
        relation = indicators.age_vs_category(ds, season)
        if not relation.empty:
            box = px.box(relation.assign(displayname=relation['displayname'].map(_label)), x='category', y='age',
                         points='all', hover_name='displayname', labels={'category': 'Categoría en que juega', 'age': 'Edad al corte'},
                         category_orders={'category': list(reversed(ds.categories))})
            box.update_traces(marker_color=OHIGGINS_BLUE)
            apply_ohiggins_plotly_theme(box, height=340)
            st.plotly_chart(box, use_container_width=True)

    with tabs[2]:
        younger = ind[['category', 'minutos_totales', 'min_tope_o_mayor', 'min_menor_1', 'min_menor_2', 'min_menor_3',
                       'min_menor_4_o_mas', 'pct_menores']]
        show_table(younger, {
            'category': ('Categoría', None), 'minutos_totales': ('Minutos totales de la serie', FMT_INT),
            'min_tope_o_mayor': ('Edad tope o mayor', FMT_INT), 'min_menor_1': ('1 año menor', FMT_INT),
            'min_menor_2': ('2 años menores', FMT_INT), 'min_menor_3': ('3 años menores', FMT_INT),
            'min_menor_4_o_mas': ('4 o más años menores', FMT_INT), 'pct_menores': ('% de minutos de menores', FMT_PCT)})
        melted = younger.melt(id_vars='category', value_vars=['min_tope_o_mayor', 'min_menor_1', 'min_menor_2', 'min_menor_3',
                                                             'min_menor_4_o_mas'], var_name='grupo', value_name='minutos')
        names = {'min_tope_o_mayor': 'Edad tope o mayor', 'min_menor_1': '1 año menor', 'min_menor_2': '2 años menores',
                 'min_menor_3': '3 años menores', 'min_menor_4_o_mas': '4 o más años menores'}
        melted = melted.assign(grupo=melted['grupo'].map(names)).dropna(subset=['minutos'])
        fig = px.bar(melted, x='category', y='minutos', color='grupo', barmode='stack',
                     color_discrete_sequence=SERIES_COLORS,
                     category_orders={'grupo': list(names.values())}, labels={'category': '', 'minutos': 'Minutos', 'grupo': ''})
        apply_ohiggins_plotly_theme(fig, height=360)
        st.plotly_chart(fig, use_container_width=True)
        st.caption('Los años menores se miden contra el tope de edad de la categoría (U-15: 14 años es 1 año menor). '
                   'Primer Equipo no tiene tope y no se descompone.')

    with tabs[3]:
        category = st.selectbox('Categoría', list(ind['category']), key='ci_roles_category')
        roles = cat[(cat['season_year'] == season) & (cat['category'] == category)].sort_values(
            ['played', 'cited'], ascending=False)
        show_table(_named(roles), {'displayname': ('Jugador', None), 'cited': ('Partidos citado', FMT_INT),
                                   'started': ('Titular', FMT_INT), 'sub_in': ('Suplente que ingresó', FMT_INT),
                                   'only_called': ('Solo citación', FMT_INT), 'played': ('Jugó', FMT_INT)})

    with tabs[4]:
        show_table(ind, {'category': ('Categoría', None), 'goles': ('Goles marcados', FMT_INT),
                         'goles_recibidos_arqueros': ('Goles recibidos por arqueros', FMT_INT),
                         'amarillas': ('Amarillas', FMT_INT), 'rojas': ('Rojas', FMT_INT)})
        keepers = ds.goalkeepers.merge(ds.matches[['matchid', 'season_year', 'category']], on='matchid')
        keepers = keepers[(keepers['season_year'] == season) & ((keepers['played'] == True).fillna(False)  # noqa: E712
                                                                | (keepers['minutesplayed'] > 0)).astype(bool)]
        if len(keepers):
            table = keepers.groupby(['personid', 'category'], as_index=False).agg(
                partidos=('matchid', 'nunique'), minutos=('minutesplayed', lambda s: s.sum(min_count=1)),
                recibidos=('goalsconceded', lambda s: s.sum(min_count=1)),
                invictas=('goalsconceded', lambda s: int((s == 0).sum())))
            table['por_90'] = (table['recibidos'] * 90 / table['minutos'].where(table['minutos'] > 0)).round(2)
            table['displayname'] = table['personid'].map(ds.players.set_index('personid')['displayname']).map(_label)
            st.markdown('**Arqueros: goles recibidos**')
            show_table(table.sort_values('minutos', ascending=False), {
                'displayname': ('Arquero', None), 'category': ('Categoría', None), 'partidos': ('Partidos', FMT_INT),
                'minutos': ('Minutos', FMT_INT), 'recibidos': ('Goles recibidos', FMT_INT), 'por_90': ('Recibidos por 90', FMT_2),
                'invictas': ('Vallas invictas', FMT_INT)})
        category = st.selectbox('Categoría para ver a los jugadores', list(ind['category']), key='ci_discipline_category')
        players = cat[(cat['season_year'] == season) & (cat['category'] == category)]
        players = players[(players['yellow_cards'].fillna(0) > 0) | (players['red_cards'].fillna(0) > 0) | (players['goals'].fillna(0) > 0)]
        show_table(_named(players.sort_values(['yellow_cards', 'goals'], ascending=False)), {
            'displayname': ('Jugador', None), 'goals': ('Goles', FMT_INT), 'yellow_cards': ('Amarillas', FMT_INT),
            'red_cards': ('Rojas', FMT_INT), 'minutes': ('Minutos', FMT_INT)})

    with tabs[5]:
        category = st.selectbox('Categoría', list(ind['category']), key='ci_part_category')
        players = cat[(cat['season_year'] == season) & (cat['category'] == category)].sort_values('participation_pct')
        show_table(_named(players), {'displayname': ('Jugador', None), 'played': ('Partidos jugados', FMT_INT),
                                     'minutes': ('Minutos', FMT_INT), 'possible_minutes': ('Minutos posibles', FMT_INT),
                                     'participation_pct': ('Participación', FMT_PCT),
                                     'wins_with': ('Ganados con el jugador', FMT_INT), 'results_with': ('Con resultado', FMT_INT),
                                     'win_pct_with': ('% victorias con el jugador', FMT_PCT)})
        if players['participation_pct'].notna().any():
            fig = px.histogram(players.dropna(subset=['participation_pct']), x='participation_pct', nbins=10,
                               labels={'participation_pct': 'Participación (% de minutos posibles)'})
            fig.update_traces(marker_color=OHIGGINS_BLUE)
            apply_ohiggins_plotly_theme(fig, height=280)
            st.plotly_chart(fig, use_container_width=True)


def marked_players(ctx: Context) -> dict:
    """personid -> texto con sus marcas activas (Proyectado / Selección)."""
    active = ctx.marks[ctx.marks['active'].astype(bool)] if len(ctx.marks) else ctx.marks
    grouped = active.groupby('personid')['mark'].agg(lambda s: ', '.join(config_store.MARKS[m] for m in s))
    return grouped.to_dict()


@admin_only
def page_alerts() -> None:
    inject_styles()
    title('Alertas automáticas', 'Jugadores que requieren atención deportiva. Los umbrales y colores se configuran en Seguimiento.')
    ctx = context()
    ds = ctx.ds
    if ds.facts.empty:
        st.info('COMET no tiene planillas de O’Higgins.')
        return
    rule_note(ctx.rules, ['card_cycle', 'possible_from_first_call', 'exclude_selection_periods', 'age_cutoff', 'promotion_rule'])
    season = _season_picker(ctx, 'ca_season')
    found = alert_rules.evaluate_alerts(ds, ctx.computed.cat, season, ctx.alert_config)
    tiles = st.columns(len(alert_rules.ALERT_DEFS))
    for tile, definition in zip(tiles, alert_rules.ALERT_DEFS):
        config = ctx.alert_config[definition.key]
        count = int((found['alert_key'] == definition.key).sum()) if len(found) else 0
        label = alert_rules.alert_label(definition.key, ctx.rules) + ('' if config['enabled'] else ' (desactivada)')
        tile.markdown(alert_tile(count, label, config['color']), unsafe_allow_html=True)
    first_year = ds.seasons[0] if ds.seasons else None
    st.caption(f'El historial de COMET empieza en {first_year}: las temporadas sin promoción no pueden superar lo que ese '
               'historial permite ver.' if first_year else '')
    blocked = ds.blocked_players(season)
    if len(blocked):
        with st.expander(f'{len(blocked)} jugador(es) no se evalúan por planillas contradictorias', expanded=False):
            st.write('COMET trae filas repetidas con valores distintos para estos jugadores y partidos; no se elige ninguna. '
                     'Sus cifras están incompletas, así que ninguna alerta los considera hasta que se aclare el dato.')
            show_table(_named(blocked), {'displayname': ('Jugador', None), 'partidos': ('Partidos afectados', FMT_INT)})
    if found.empty:
        st.success('No hay alertas activas con la configuración actual.')
        return
    c1, c2 = st.columns(2)
    with c1:
        kinds = st.multiselect('Tipo de alerta', [d.key for d in alert_rules.ALERT_DEFS],
                               default=[d.key for d in alert_rules.ALERT_DEFS],
                               format_func=lambda k: alert_rules.alert_label(k, ctx.rules), key='ca_kinds')
    with c2:
        cats = st.multiselect('Categoría', list(ds.categories), default=list(ds.categories), key='ca_cats')
    view = found[found['alert_key'].isin(kinds) & found['category'].isin(cats)]
    marks = marked_players(ctx)
    view = _named(view).assign(marca=view['personid'].map(marks))
    show_table(view, {'alert': ('Alerta', None), 'displayname': ('Jugador', None), 'category': ('Categoría', None),
                      'detail': ('Detalle', None), 'marca': ('Marca del club', None)}, colors=('alert', {
                          alert_rules.alert_label(d.key, ctx.rules): ctx.alert_config[d.key]['color'] for d in alert_rules.ALERT_DEFS}))
    st.caption('El color de cada alerta se acompaña siempre de su nombre. Se configura en Seguimiento y configuración.')


@admin_only
def page_adelantados() -> None:
    inject_styles()
    title('Jugadores adelantados', 'Quienes juegan en una categoría superior a la que les corresponde por su edad.')
    ctx = context()
    ds = ctx.ds
    if ds.facts.empty:
        st.info('COMET no tiene planillas de O’Higgins.')
        return
    rule_note(ctx.rules, ['age_cutoff', 'possible_from_first_call', 'min_minutes_on_pitch'])
    season = _season_picker(ctx, 'cd_season')
    blocked = ds.blocked_players(season)
    if len(blocked):
        st.warning(f'{len(blocked)} jugador(es) quedan fuera de los indicadores de adelantados, permanencia y '
                   'comparación por planillas contradictorias en esta temporada. Sus actuaciones válidas siguen '
                   'disponibles en la ficha y los partidos. Ver Seguimiento y configuración → Calidad de datos.')
    players = adelantados.ahead_players(ds, season)
    share = adelantados.ahead_share_by_category(ds, season)
    total_minutes = share['minutos'].sum(min_count=1)
    ahead_minutes = players['ahead_minutes'].sum(min_count=1) if len(players) else 0
    k = st.columns(4)
    k[0].metric('Jugadores adelantados', len(players))
    k[1].metric('Minutos en categoría superior', fmt(ahead_minutes))
    k[2].metric('% de los minutos de todas las series', fmt(ahead_minutes / total_minutes * 100 if pd.notna(total_minutes) and total_minutes else None, 1, ' %'))
    k[3].metric('Categorías con adelantados', int((share['adelantados'] > 0).sum()))
    tabs = st.tabs(['Jugadores', 'Por categoría', 'Permanencia en el año', 'Comparación con su grupo de edad'])

    with tabs[0]:
        if players.empty:
            st.info('Nadie juega por encima de su edad en esa temporada.')
        else:
            show_table(_named(players), {
                'displayname': ('Jugador', None), 'age': ('Edad al corte', FMT_INT), 'age_category': ('Le corresponde', None),
                'plays_in': ('Juega en', None), 'steps': ('Categorías por encima', FMT_INT),
                'ahead_minutes': ('Minutos en la superior', FMT_INT), 'total_minutes': ('Minutos totales', FMT_INT),
                'ahead_share_pct': ('% de sus minutos arriba', FMT_PCT), 'ahead_matches': ('Partidos arriba', FMT_INT)})
    with tabs[1]:
        show_table(share, {'category': ('Categoría en que juegan', None), 'jugadores': ('Jugadores con minutos', FMT_INT),
                           'adelantados': ('Adelantados', FMT_INT), 'pct_adelantados': ('% de adelantados', FMT_PCT),
                           'minutos': ('Minutos de la categoría', FMT_INT), 'minutos_adelantados': ('Minutos de adelantados', FMT_INT)})
        fig = px.bar(share, x='category', y='pct_adelantados', text='pct_adelantados',
                     labels={'category': '', 'pct_adelantados': '% de adelantados'})
        fig.update_traces(marker_color=OHIGGINS_BLUE, texttemplate='%{text:.1f} %', textposition='outside')
        apply_ohiggins_plotly_theme(fig, height=320)
        st.plotly_chart(fig, use_container_width=True)
    with tabs[2]:
        monthly = adelantados.ahead_permanence(ds, season)
        if monthly.empty:
            st.info('Sin adelantados con minutos en esa temporada.')
        else:
            matrix = monthly.assign(displayname=monthly['displayname'].map(_label)).pivot_table(
                index='displayname', columns='mes', values='minutes', aggfunc='sum')
            fig = go.Figure(go.Heatmap(z=matrix.values, x=list(matrix.columns), y=list(matrix.index), colorscale=[[0, '#F4F8FC'], [1, OHIGGINS_BLUE]],
                                       hoverongaps=False, colorbar=dict(title='Minutos')))
            apply_ohiggins_plotly_theme(fig, height=max(260, 24 * len(matrix) + 120))
            fig.update_xaxes(type='category')
            st.plotly_chart(fig, use_container_width=True)
            st.caption('Cada celda son los minutos del mes en la categoría superior; un espacio en blanco es un mes sin minutos arriba.')
            summary = adelantados.ahead_permanence_summary(ds, season)
            show_table(_named(summary.assign(first_date=summary['first_date'].dt.strftime('%d-%m-%Y'))), {
                'displayname': ('Jugador', None), 'plays_in': ('Juega en', None), 'months_active': ('Meses con minutos arriba', FMT_INT),
                'first_date': ('Primera participación arriba', None), 'matches_in_series': ('Partidos de la serie desde entonces', FMT_INT),
                'called': ('Citado', FMT_INT), 'called_pct': ('% citado', FMT_PCT), 'played': ('Jugó', FMT_INT), 'played_pct': ('% jugó', FMT_PCT)})
    with tabs[3]:
        compare = adelantados.ahead_vs_peers(ds, ctx.computed.cat, season)
        if compare.empty:
            st.info('No hay datos para comparar.')
        else:
            show_table(compare, {'age_category': ('Categoría por edad', None), 'group': ('Grupo', None),
                                 'jugadores': ('Jugadores', FMT_INT), 'partidos_jugados': ('Partidos jugados', FMT_INT),
                                 'minutos_por_partido': ('Minutos por partido', FMT_1), 'goles_por_90': ('Goles por 90', FMT_2),
                                 'amarillas_por_90': ('Amarillas por 90', FMT_2), 'participacion_pct': ('Participación', FMT_PCT),
                                 'victorias_pct': ('% victorias con el jugador', FMT_PCT)})
            st.caption('“Adelantados” son los jugadores de esa edad con minutos en una categoría superior (sus cifras allí); '
                       '“Grupo de edad” son los que juegan en la categoría que les corresponde. Con pocos jugadores la '
                       'comparación es solo orientativa: mira la columna Jugadores.')


def _rule_widget(ctx: Context, rule, disabled: bool):
    """Widget de edición de una regla; devuelve el valor ingresado."""
    current = ctx.rules.value(rule.key)
    key = f'rule_{rule.key}'
    hidden = 'collapsed'  # el título ya se muestra sobre el campo
    if rule.key == 'digest_weekday':
        return st.selectbox(rule.label, list(range(7)), index=int(current), format_func=WEEKDAYS.__getitem__,
                            key=key, disabled=disabled, label_visibility=hidden)
    if rule.kind == 'int':
        return st.number_input(rule.label, min_value=rule.minimum, max_value=rule.maximum, value=int(current), step=1,
                               key=key, disabled=disabled, label_visibility=hidden)
    if rule.kind == 'bool':
        return st.checkbox(rule.label, value=bool(current), key=key, disabled=disabled)
    if rule.kind == 'choice':
        return st.selectbox(rule.label, list(rule.choices), index=list(rule.choices).index(current),
                            format_func=lambda v: CHOICE_LABELS.get(v, v), key=key, disabled=disabled,
                            label_visibility=hidden)
    if rule.kind in ('list', 'words'):
        placeholder = 'Un correo por línea' if rule.kind == 'list' else 'Un estado por línea (según matchstatus)'
        return [line.strip() for line in st.text_area(rule.label, value='\n'.join(current), height=90, key=key,
                                                      placeholder=placeholder, disabled=disabled,
                                                      label_visibility=hidden).splitlines() if line.strip()]
    if rule.editable:
        return st.text_input(rule.label, value=str(current), key=key, disabled=disabled, label_visibility=hidden)
    return current


def _save_rules(ctx: Context, keys: list[str], values: dict, confirms: dict) -> None:
    saved = 0
    for key in keys:
        rule = RULES_BY_KEY[key]
        new_value = parse(rule, values[key]) if rule.editable else rule.default
        confirmed = confirms.get(key, ctx.rules.confirmed(key))
        if new_value != ctx.rules.value(key) or confirmed != ctx.rules.confirmed(key):
            config_store.save_setting(key, new_value, confirmed=confirmed)
            saved += 1
    if saved:
        st.cache_data.clear()  # los indicadores dependen de las reglas
        st.success(f'Se guardaron {saved} cambios.')
        st.rerun()
    st.info('No hay cambios para guardar.')


def _tab_rules(ctx: Context) -> None:
    disabled = not ctx.store_available
    if disabled:
        st.warning(f'No se pueden guardar cambios: {ctx.store_error}. Se muestran los valores por defecto.')
    pending = ctx.rules.pending()
    st.markdown(f'**{len(pending)} reglas son supuestos pendientes de confirmar con Pablo.** '
                'Mientras no se confirmen, cada pantalla lo indica junto a las cifras que dependen de ellas.')
    with st.expander('Preguntas para Pablo, todas juntas'):
        for number, rule in enumerate([r for r in pending if r.question], start=1):
            st.markdown(f'**{number}. {escape(rule.label)}**  \n{escape(rule.question)}')
    threshold_keys = set(THRESHOLD_RULES.values())
    shown = [r for r in RULE_DEFS if r.key not in threshold_keys]
    values, confirms = {}, {}
    with st.form('comet_rules'):
        for rule in shown:
            st.markdown(f'{status_pill(ctx.rules.status(rule.key))} **{escape(rule.label)}**', unsafe_allow_html=True)
            st.caption(rule.applied)
            values[rule.key] = _rule_widget(ctx, rule, disabled)
            if rule.origin != ORIGIN_PABLO:
                confirms[rule.key] = st.checkbox('Confirmada por Pablo / el club', value=ctx.rules.confirmed(rule.key),
                                                 key=f'confirm_{rule.key}', disabled=disabled)
            if rule.question:
                with st.expander('Pregunta para Pablo'):
                    st.write(rule.question)
            st.markdown('---')
        submitted = st.form_submit_button('Guardar reglas', disabled=disabled)
    if submitted:
        try:
            _save_rules(ctx, [r.key for r in shown], values, confirms)
        except (ValueError, config_store.StoreUnavailable) as exc:
            st.error(str(exc))


def _tab_alerts(ctx: Context) -> None:
    disabled = not ctx.store_available
    if disabled:
        st.warning(f'No se pueden guardar cambios: {ctx.store_error}.')
    colors = list(alert_rules.ALERT_COLORS)
    enabled, chosen, thresholds = {}, {}, {}
    with st.form('comet_alert_config'):
        for definition in alert_rules.ALERT_DEFS:
            config = ctx.alert_config[definition.key]
            c1, c2, c3, c4 = st.columns([3, 1, 2, 1])
            c1.markdown(f'**{escape(alert_rules.alert_label(definition.key, ctx.rules))}**')
            enabled[definition.key] = c2.checkbox('Activa', value=config['enabled'], key=f'alert_on_{definition.key}', disabled=disabled)
            chosen[definition.key] = c3.selectbox('Color', colors, index=colors.index(config['color']),
                                                  key=f'alert_color_{definition.key}', disabled=disabled)
            c4.markdown(pill(chosen[definition.key], chosen[definition.key]), unsafe_allow_html=True)
            rule_key = THRESHOLD_RULES.get(definition.key)
            if rule_key:
                rule = RULES_BY_KEY[rule_key]
                thresholds[rule_key] = st.number_input(rule.label, min_value=rule.minimum, max_value=rule.maximum,
                                                       value=int(ctx.rules.value(rule_key)), step=1,
                                                       key=f'alert_thr_{rule_key}', disabled=disabled)
                st.caption(rule.applied)
            st.markdown('---')
        submitted = st.form_submit_button('Guardar alertas', disabled=disabled)
    if submitted:
        try:
            config_store.save_setting(config_store.ALERT_CONFIG_KEY, {
                k: {'enabled': enabled[k], 'color': chosen[k]} for k in enabled})
            for key, value in thresholds.items():
                if value != ctx.rules.value(key):
                    config_store.save_setting(key, value, confirmed=ctx.rules.confirmed(key))
            st.cache_data.clear()
            st.rerun()
        except (ValueError, config_store.StoreUnavailable) as exc:
            st.error(str(exc))


def _tab_marks(ctx: Context) -> None:
    names = ctx.ds.players.set_index('personid')['displayname']
    marks = ctx.marks[ctx.marks['active'].astype(bool)] if len(ctx.marks) else ctx.marks
    st.markdown('**Jugadores marcados**')
    if marks.empty:
        st.caption('Aún no hay jugadores proyectados ni de selección. Se marcan desde la Ficha del jugador.')
    else:
        view = marks.assign(displayname=marks['personid'].map(names).map(_label), mark=marks['mark'].map(config_store.MARKS))
        show_table(view, {'displayname': ('Jugador', None), 'mark': ('Marca', None), 'note': ('Nota', None), 'updated_at': ('Actualizada', None)})
    periods = ctx.periods[ctx.periods['active'].astype(bool)] if len(ctx.periods) else ctx.periods
    st.markdown('**Períodos de selección**')
    if periods.empty:
        st.caption('Aún no hay períodos de microciclo, Sudamericano o Mundial. Se registran desde la Ficha del jugador.')
    else:
        view = periods.assign(displayname=periods['personid'].map(names).map(_label), kind=periods['kind'].map(config_store.PERIOD_KINDS))
        show_table(view, {'displayname': ('Jugador', None), 'kind': ('Período', None), 'starts_on': ('Desde', None),
                          'ends_on': ('Hasta', None), 'note': ('Nota', None)})
    st.caption('Los períodos solo se muestran, salvo que la regla “excluir períodos de selección” esté activada: '
               'entonces esos partidos se descuentan de los minutos posibles del jugador.')


def _tab_digest(ctx: Context) -> None:
    ds = ctx.ds
    recipients = ctx.rules.value('digest_recipients')
    default_start = pd.Timestamp(previous_week(ctx.today)[0])
    weeks = sorted(set(ds.matches['week_start'].dropna()) | {default_start}, reverse=True)
    week = st.selectbox('Semana a resumir', weeks, index=weeks.index(default_start), key='cs_week',
                        format_func=lambda w: f'{w:%d-%m-%Y} al {w + timedelta(days=6):%d-%m-%Y}')
    season = ds.current_season(week + timedelta(days=6)) or (ds.seasons[-1] if ds.seasons else None)
    found = alert_rules.evaluate_alerts(ds, ctx.computed.cat, season, ctx.alert_config) if season else pd.DataFrame(
        columns=['alert_key'])
    digest = build_weekly_digest(ds, found, week.date(), generated_on=ctx.today.date(), pending_rules=len(ctx.rules.pending()),
                                 blocked=len(ds.blocked_players(season)) if season else 0)
    a, b, c = st.columns(3)
    a.metric('Partidos en la semana', digest.matches)
    b.metric('Alertas vigentes', digest.alerts)
    c.metric('Destinatarios definidos', len(recipients))
    st.warning('Envío automático: no activado. Faltan los destinatarios y el servicio de correo confirmados por el club. '
               'Esta vista previa no envía nada.' if not recipients else
               'Hay destinatarios definidos, pero el envío solo se realiza con el script operativo y un servicio de correo '
               'configurado; esta pantalla no envía nada.')
    components.html(digest.html, height=640, scrolling=True)
    with st.expander('Versión en texto'):
        st.code(digest.text, language=None)
    d1, d2 = st.columns(2)
    d1.download_button('Descargar HTML', digest.html, file_name=f'resumen_comet_{digest.week_start}.html', mime='text/html')
    d2.download_button('Descargar texto', digest.text, file_name=f'resumen_comet_{digest.week_start}.txt', mime='text/plain')


def _tab_quality(ctx: Context) -> None:
    table = ctx.computed.quality
    show_static_table(table, {'control': ('Control', None), 'nivel': ('Estado', None), 'cantidad': ('Cantidad', None),
                              'detalle': ('Qué revisa', None), 'efecto': ('Efecto en las cifras', None)},
                      colors=('nivel', QUALITY_COLORS))
    horizon = quality.history_horizon(ctx.ds)
    if horizon['first'] is not None:
        st.caption(f'Datos disponibles desde {horizon["first"]:%d-%m-%Y} hasta {horizon["last"]:%d-%m-%Y} '
                   f'(temporadas {", ".join(str(s) for s in horizon["seasons"])}).')
    dups = ctx.ds.duplicates
    if dups is not None and len(dups):
        st.markdown('**Filas repetidas por jugador y partido**')
        st.caption('Idénticas: se cuenta una sola. Contradictorias: no se elige ninguna; el jugador queda con cifras incompletas '
                   'hasta que COMET indique cuál fila vale (identificadores tal como están en COMET).')
        show_table(dups.sort_values(['resolucion', 'tabla']).head(200), {
            'tabla': ('Tabla', None), 'matchid': ('Partido', None), 'personid': ('Jugador (id)', None),
            'filas': ('Filas', FMT_INT), 'versiones': ('Versiones distintas', FMT_INT), 'resolucion': ('Resolución', None)})
    st.markdown('**Datos de COMET: qué se usa, qué hay que confirmar y qué falta**')
    st.caption('No se modifica dataProject ni se conceden permisos desde este repositorio. «Existe» significa que la columna '
               'o tabla se comprobó en la lectura de COMET; un dato sin acceso no es un dato ausente.')
    show_static_table(pd.DataFrame(PIPELINE_DEPENDENCIES), {
        'dato': ('Dato', None), 'estado': ('Estado', None), 'para': ('Para qué se necesita', None),
        'hoy': ('Qué se hace hoy', None)})


@admin_only
def page_tracking() -> None:
    inject_styles()
    title('Seguimiento y configuración', 'Reglas, alertas con color, marcas, períodos de selección y resumen semanal.')
    ctx = context()
    tabs = st.tabs(['Reglas y pendientes', 'Alertas y colores', 'Marcas y períodos', 'Resumen semanal',
                    'Calidad de datos y dependencias'])
    with tabs[0]:
        _tab_rules(ctx)
    with tabs[1]:
        _tab_alerts(ctx)
    with tabs[2]:
        _tab_marks(ctx)
    with tabs[3]:
        _tab_digest(ctx)
    with tabs[4]:
        _tab_quality(ctx)
