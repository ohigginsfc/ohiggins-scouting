"""Pantallas COMET: partido semanal, rankings por categoría y ficha individual (solo administración)."""
from __future__ import annotations

from datetime import timedelta
from html import escape

import pandas as pd
import plotly.express as px
import streamlit as st

from comet_context import Context, context, season_choices
from scouting.comet import config_store, metrics
from scouting.comet.categories import age_on
from scouting.comet.facts import ROLE_STARTER, ROLE_SUB_IN, ROLE_SUB_OUT, ROLE_UNKNOWN
from scouting.comet.digest import MONTHS, spanish_date
from scouting.portal.security import admin_only
from ui.comet_widgets import (FMT_INT, FMT_PCT, RESULT_STYLE as RESULT_COLORS, SERIES_COLORS, fmt, inject_styles,
                              pill, rule_note, show_table, title)
from ui.theme import OHIGGINS_BLUE, apply_ohiggins_plotly_theme


def _label(value, fallback: str = 'Jugador sin ficha') -> str:
    return value if isinstance(value, str) and value else fallback


def _person_label(row) -> str:
    return _label(getattr(row, 'displayname', None), f'Jugador {row.personid}')


def week_label(start: pd.Timestamp, count: int) -> str:
    end = start + timedelta(days=6)
    same_month = start.month == end.month
    span = (f'{start.day} al {end.day} de {MONTHS[end.month - 1]} de {end.year}' if same_month
            else f'{spanish_date(start.date(), False)} al {spanish_date(end.date())}')
    return f'{span} · {count} {"partido" if count == 1 else "partidos"}'


def _score(m) -> str:
    if pd.isna(m.goals_for) or pd.isna(m.goals_against):
        return 'sin marcador'
    return f'{int(m.goals_for)}-{int(m.goals_against)}'


def _result_text(m) -> str:
    return m.result if isinstance(m.result, str) else 'sin resultado'


def _match_title(m) -> str:
    return (f'{m.matchdate:%d-%m-%Y} · {m.category} · {_label(m.rival, "rival sin nombre")} '
            f'({m.venue}) · {_score(m)} {_result_text(m)}')


def _sheet_table(ctx: Context, rows: pd.DataFrame, match) -> None:
    """Tabla de jugadores de un rol, con su resultado del partido si jugaron lo suficiente."""
    threshold = ctx.rules.value('min_minutes_on_pitch')
    played = rows['participated'] & (rows['minutes'] >= threshold)
    text = f'{_result_text(match)} {_score(match)}' if match.result and isinstance(match.result, str) else 'sin resultado'
    rows = rows.assign(resultado_en_cancha=[text if p else None for p in played],
                       displayname=rows['displayname'].map(_label))
    show_table(rows, {
        'displayname': ('Jugador', None), 'age': ('Edad', FMT_INT), 'minutes': ('Minutos', FMT_INT),
        'goals': ('Goles', FMT_INT), 'own_goals': ('Autogoles', FMT_INT), 'yellow_cards': ('Amarillas', FMT_INT),
        'second_yellows': ('2.ª amarilla', FMT_INT), 'red_cards': ('Rojas', FMT_INT),
        'resultado_en_cancha': ('Resultado con el jugador en cancha', None)})


def render_match(ctx: Context, matchid: str) -> None:
    ds = ctx.ds
    match = next(ds.matches[ds.matches['matchid'] == matchid].itertuples())
    color = RESULT_COLORS.get(match.result, 'Gris')
    st.markdown(
        f'<div class="cm-match"><span class="score">{escape(_score(match))}</span>{pill(_result_text(match), color)}'
        f'<span class="meta"><strong>{escape(match.category)}</strong> · {escape(_label(match.competition, "competición"))}'
        f' · {match.matchdate:%d-%m-%Y %H:%M} · {escape(match.venue)} vs {escape(_label(match.rival, "rival sin nombre"))}'
        f'</span></div>', unsafe_allow_html=True)
    sheet = metrics.match_sheet(ds, matchid)
    if sheet.empty:
        st.info('COMET no trae la planilla de este partido.')
        return
    if sheet['conflict'].any():
        st.warning(f'{int(sheet["conflict"].sum())} jugador(es) tienen filas repetidas con valores distintos en este partido: '
                   'no se elige ninguna y sus datos se muestran como «—» (rol «Sin dato»).')
    left, right = st.columns(2, gap='large')
    with left:
        st.markdown(f'**Titulares** ({int((sheet["role"] == ROLE_STARTER).sum())})')
        _sheet_table(ctx, sheet[sheet['role'] == ROLE_STARTER], match)
        st.markdown(f'**Suplentes que ingresaron** ({int((sheet["role"] == ROLE_SUB_IN).sum())})')
        _sheet_table(ctx, sheet[sheet['role'] == ROLE_SUB_IN], match)
    with right:
        outs = sheet[sheet['role'] == ROLE_SUB_OUT]
        st.markdown(f'**Suplentes que no ingresaron** ({len(outs)})')
        if outs.empty:
            st.caption('Sin suplentes sin ingresar en la planilla (o COMET no los incluye).')
        else:
            show_table(outs.assign(displayname=outs['displayname'].map(_label)),
                       {'displayname': ('Jugador', None), 'age': ('Edad', FMT_INT),
                        'yellow_cards': ('Amarillas', FMT_INT), 'red_cards': ('Rojas', FMT_INT)})
        unknown = sheet[sheet['role'] == ROLE_UNKNOWN]
        if len(unknown):
            st.markdown(f'**Sin dato de titular o suplente** ({len(unknown)})')
            show_table(unknown.assign(displayname=unknown['displayname'].map(_label)),
                       {'displayname': ('Jugador', None), 'minutes': ('Minutos', FMT_INT)})
        absent = metrics.not_called_reference(ds, matchid)
        st.markdown(f'**No citados que no participaron** ({len(absent)}) · referencial')
        if absent.empty:
            st.caption('Nadie más figura en las planillas de esta competición.')
        else:
            show_table(absent.assign(displayname=absent['displayname'].map(_label)),
                       {'displayname': ('Jugador', None), 'citaciones': ('Citaciones en la competición', FMT_INT)})
        keepers = metrics.goalkeeper_conceded(ds, matchid)
        st.markdown('**Goles recibidos por arquero**')
        if keepers.empty:
            st.caption('COMET no trae el registro del arquero en este partido.')
        else:
            show_table(keepers.assign(displayname=keepers['displayname'].map(_label)),
                       {'displayname': ('Arquero', None), 'minutesplayed': ('Minutos', FMT_INT),
                        'goalsconceded': ('Goles recibidos', FMT_INT)})


@admin_only
def page_weekly_match() -> None:
    inject_styles()
    title('Partido semanal', 'Información completa de la planilla de cada partido de O’Higgins.')
    ctx = context()
    ds = ctx.ds
    matches = ds.matches[ds.matches['matchdate'].notna()]
    if matches.empty:
        st.info('COMET no tiene partidos ya jugados de O’Higgins.')
        return
    rule_note(ctx.rules, ['min_minutes_on_pitch', 'roster_rule'])
    counts = matches.groupby('week_start').size()
    weeks = sorted(counts.index, reverse=True)
    c1, c2 = st.columns([2, 3])
    with c1:
        week = st.selectbox('Semana (lunes a domingo)', weeks, key='cw_week',
                            format_func=lambda w: week_label(pd.Timestamp(w), int(counts[w])))
    with c2:
        wanted = st.multiselect('Categorías', list(ds.categories), default=list(ds.categories), key='cw_categories')
    scope = matches[(matches['week_start'] == week) & matches['category'].isin(wanted)].sort_values(
        ['category_rank', 'matchdate'], ascending=[False, True])
    if scope.empty:
        st.info('No hay partidos de esas categorías en la semana elegida.')
        return
    known = scope[scope['result'].notna()]
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric('Partidos', len(scope))
    k2.metric('Victorias', int((known['result'] == 'Victoria').sum()))
    k3.metric('Empates', int((known['result'] == 'Empate').sum()))
    k4.metric('Derrotas', int((known['result'] == 'Derrota').sum()))
    k5.metric('Goles a favor / en contra', f'{fmt(known["goals_for"].sum(min_count=1))} / '
                                          f'{fmt(known["goals_against"].sum(min_count=1))}')
    summary = scope.assign(marcador=[_score(m) for m in scope.itertuples()],
                           resultado=[_result_text(m) for m in scope.itertuples()],
                           fecha=scope['matchdate'].dt.strftime('%d-%m-%Y %H:%M'),
                           rival=scope['rival'].map(lambda r: _label(r, 'rival sin nombre')))
    show_table(summary, {'fecha': ('Fecha', None), 'category': ('Categoría', None), 'competition': ('Competición', None),
                         'rival': ('Rival', None), 'venue': ('Local / Visita', None), 'marcador': ('Marcador', None),
                         'resultado': ('Resultado', None)}, colors=('resultado', RESULT_COLORS))
    st.markdown('---')
    ids = scope['matchid'].tolist()
    by_id = {m.matchid: m for m in scope.itertuples()}
    chosen = st.selectbox('Partido para ver la planilla completa', ids, key='cw_match',
                          format_func=lambda i: _match_title(by_id[i]))
    render_match(ctx, chosen)
    if st.checkbox('Mostrar también la planilla de los demás partidos de la semana', key='cw_all'):
        for other in ids:
            if other != chosen:
                st.markdown('---')
                render_match(ctx, other)


def _bar(frame: pd.DataFrame, value: str, label: str, name: str = 'displayname'):
    frame = frame.head(10).assign(**{name: frame.head(10)[name].map(_label)}).iloc[::-1]
    fig = px.bar(frame, x=value, y=name, orientation='h', text=value, labels={value: label, name: ''})
    fig.update_traces(marker_color=OHIGGINS_BLUE, textposition='outside', cliponaxis=False)
    apply_ohiggins_plotly_theme(fig, height=max(240, 34 * len(frame) + 80), margin=dict(l=10, r=40, t=10, b=30))
    st.plotly_chart(fig, use_container_width=True)


@admin_only
def page_rankings() -> None:
    inject_styles()
    title('Rankings por categoría', 'Minutos, goles, tarjetas y partidos ganados con el jugador en cancha.')
    ctx = context()
    ds, cat = ctx.ds, ctx.computed.cat
    if cat.empty:
        st.info('COMET no tiene planillas de O’Higgins.')
        return
    rule_note(ctx.rules, ['min_minutes_on_pitch'])
    c1, c2, c3 = st.columns(3)
    with c1:
        season = st.selectbox('Temporada', season_choices(ctx), key='cr_season')
    in_season = [c for c in ds.categories if ((cat['season_year'] == season) & (cat['category'] == c)).any()]
    with c2:
        category = st.selectbox('Categoría', in_season, key='cr_category',
                                index=in_season.index('U-15') if 'U-15' in in_season else 0)
    with c3:
        top = st.select_slider('Mostrar', options=[10, 20, 50, 'Todos'], value=20, key='cr_top')
    limit = None if top == 'Todos' else int(top)
    excluded = metrics.incomplete_players(cat, category=category, season_year=season)
    if len(excluded):
        names = ', '.join(_label(n) for n in excluded['displayname'].head(8))
        st.warning(f'{len(excluded)} jugador(es) no entran en los rankings porque COMET trae filas repetidas con valores '
                   f'distintos en su planilla y no se elige ninguna: {names}{"…" if len(excluded) > 8 else ""}. '
                   'Ver Seguimiento y configuración → Calidad de datos.')
    no_minutes = metrics.minutes_gap_players(cat, category=category, season_year=season)
    tabs = st.tabs(['Minutos jugados', 'Goles', 'Tarjetas', 'Partidos ganados con el jugador en cancha'])

    def board(metric: str, value: str, label: str, extra: dict, chart: bool = True) -> None:
        ranked = metrics.ranking(ctx.computed.cat, metric, category=category, season_year=season, top=limit)
        if ranked.empty:
            st.info('Nadie tiene datos para este ranking en la categoría y temporada elegidas.')
            return
        ranked = ranked.assign(displayname=ranked['displayname'].map(_label))
        columns = {'position': ('Pos.', FMT_INT), 'displayname': ('Jugador', None), 'age': ('Edad', FMT_INT),
                   'played': ('Partidos jugados', FMT_INT), value: (label, FMT_INT)}
        columns.update(extra)
        show_table(ranked, columns)
        if chart:
            _bar(ranked, value, label)

    with tabs[0]:
        if len(no_minutes):
            names = ', '.join(_label(n) for n in no_minutes['displayname'].head(8))
            st.warning(f'{len(no_minutes)} jugador(es) no entran en el ranking de minutos porque COMET no trae los minutos de '
                       f'algún partido en que jugaron: {names}{"…" if len(no_minutes) > 8 else ""}. Sus minutos se ven como «—»: '
                       'no se ordena a nadie por una suma parcial. Sus goles y tarjetas sí cuentan en los otros rankings. '
                       'Ver Seguimiento y configuración → Calidad de datos.')
        board('Minutos jugados', 'minutes', 'Minutos',
              {'started': ('Titular', FMT_INT), 'sub_in': ('Ingresó', FMT_INT), 'participation_pct': ('Participación', FMT_PCT)})
    with tabs[1]:
        board('Goles', 'goals', 'Goles', {'minutes': ('Minutos', FMT_INT)})
    with tabs[2]:
        left, right = st.columns(2, gap='large')
        with left:
            st.markdown('**Tarjetas amarillas**')
            board('Tarjetas amarillas', 'yellow_cards', 'Amarillas', {'red_cards': ('Rojas', FMT_INT)}, chart=False)
        with right:
            st.markdown('**Tarjetas rojas**')
            board('Tarjetas rojas', 'red_cards', 'Rojas', {'yellow_cards': ('Amarillas', FMT_INT)}, chart=False)
    with tabs[3]:
        board('Partidos ganados con el jugador en cancha', 'wins_with', 'Partidos ganados',
              {'results_with': ('Partidos con resultado', FMT_INT), 'win_pct_with': ('% victorias', FMT_PCT)})


def _player_options(ctx: Context, season, category) -> pd.DataFrame:
    f = ctx.ds.facts
    if season != 'Todas':
        f = f[f['season_year'] == season]
    if category != 'Todas':
        f = f[f['category'] == category]
    latest = f.sort_values('matchdate').groupby('personid', as_index=False).tail(1)
    return latest.assign(label=[f'{_label(r.displayname, "Jugador " + r.personid)} · {r.category}'
                                for r in latest.itertuples()]).sort_values('label')


def _marks_panel(ctx: Context, personid: str) -> None:
    active = ctx.marks[(ctx.marks['personid'] == personid) & ctx.marks['active'].astype(bool)]
    current = {row.mark: row.note for row in active.itertuples()}
    periods = ctx.periods[(ctx.periods['personid'] == personid) & ctx.periods['active'].astype(bool)] \
        if len(ctx.periods) else ctx.periods
    st.markdown('**Seguimiento del club**')
    if not ctx.store_available:
        st.warning(f'La configuración no está disponible ({ctx.store_error}). Las marcas y los períodos se '
                   'podrán guardar cuando se aplique la migración en Supabase.')
    with st.form(f'marks_{personid}'):
        c1, c2 = st.columns(2)
        proj = c1.checkbox('Jugador proyectado', value='proyectado' in current, disabled=not ctx.store_available)
        sel = c2.checkbox('Jugador de selección', value='seleccion' in current, disabled=not ctx.store_available)
        note = st.text_input('Nota sobre las marcas (opcional, hasta 500 caracteres)',
                             value=current.get('seleccion') or current.get('proyectado') or '',
                             max_chars=500, disabled=not ctx.store_available)
        if st.form_submit_button('Guardar marcas', disabled=not ctx.store_available):
            try:
                for mark, wanted in (('proyectado', proj), ('seleccion', sel)):
                    if wanted or mark in current:  # no crea filas para marcas que nunca se usaron
                        config_store.set_mark(personid, mark, wanted, note)
                st.rerun()
            except (ValueError, config_store.StoreUnavailable) as exc:
                st.error(str(exc))
    if len(periods):
        show_table(periods.assign(kind=periods['kind'].map(config_store.PERIOD_KINDS)),
                   {'kind': ('Período', None), 'starts_on': ('Desde', None), 'ends_on': ('Hasta', None), 'note': ('Nota', None)})
        retire = st.selectbox('Retirar un período', [None] + periods['id'].astype(int).tolist(), key=f'retire_{personid}',
                              format_func=lambda i: 'Elegir…' if i is None else
                              f'{config_store.PERIOD_KINDS[periods.loc[periods.id == i, "kind"].iloc[0]]} · '
                              f'{periods.loc[periods.id == i, "starts_on"].iloc[0]}')
        if retire is not None and st.button('Retirar período', key=f'retire_btn_{personid}', disabled=not ctx.store_available):
            config_store.retire_period(retire)
            st.rerun()
    with st.form(f'period_{personid}'):
        st.caption('Marcar un microciclo de selección, Sudamericano o Mundial.')
        c1, c2, c3 = st.columns(3)
        kind = c1.selectbox('Tipo', list(config_store.PERIOD_KINDS), format_func=config_store.PERIOD_KINDS.get,
                            disabled=not ctx.store_available)
        start = c2.date_input('Desde', value=ctx.today.date(), disabled=not ctx.store_available)
        end = c3.date_input('Hasta', value=ctx.today.date(), disabled=not ctx.store_available)
        period_note = st.text_input('Nota del período (opcional)', max_chars=500, disabled=not ctx.store_available)
        if st.form_submit_button('Agregar período', disabled=not ctx.store_available):
            try:
                config_store.add_period(personid, kind, start, end, period_note)
                st.rerun()
            except (ValueError, config_store.StoreUnavailable) as exc:
                st.error(str(exc))


def _period_labels(periods: pd.DataFrame, freq: str) -> set:
    labels = set()
    for p in periods.itertuples():
        for day in pd.date_range(p.start, p.end, freq='D'):
            labels.add(f'{day.year} · S{1 if day.month <= 6 else 2}' if freq == 'Semestre' else day.strftime('%Y-%m'))
    return labels


@admin_only
def page_player() -> None:
    inject_styles()
    title('Ficha del jugador', 'Perfil, historial, categoría por edad y evolución de minutos.')
    ctx = context()
    ds = ctx.ds
    if ds.facts.empty:
        st.info('COMET no tiene planillas de O’Higgins.')
        return
    rule_note(ctx.rules, ['age_cutoff', 'possible_from_first_call', 'min_minutes_on_pitch'])
    c1, c2 = st.columns(2)
    with c1:
        season_pick = st.selectbox('Filtrar por temporada', ['Todas'] + season_choices(ctx), key='cp_season')
    with c2:
        category_pick = st.selectbox('Filtrar por categoría', ['Todas'] + list(ds.categories), key='cp_category')
    options = _player_options(ctx, season_pick, category_pick)
    if options.empty:
        st.info('No hay jugadores con ese filtro.')
        return
    labels = dict(zip(options['personid'], options['label']))
    personid = st.selectbox('Jugador (escribe para buscar)', list(labels), format_func=labels.get, key='cp_player')
    facts = ds.facts[ds.facts['personid'] == personid]
    profile = next(ds.players[ds.players['personid'] == personid].itertuples(), None)
    name = _label(getattr(profile, 'displayname', None), f'Jugador {personid}')

    marks_active = ctx.marks[(ctx.marks['personid'] == personid) & ctx.marks['active'].astype(bool)]
    tags = ''.join(pill(config_store.MARKS[m], 'Verde' if m == 'seleccion' else 'Azul') + ' ' for m in marks_active['mark'])
    born = getattr(profile, 'dateofbirth', pd.NaT)  # fecha civil (sin hora ni zona): ver facts.civil_date
    if pd.notna(born):
        birth = f'Nacimiento {born:%d-%m-%Y} · {age_on(born, ctx.today.date())} años'
    else:
        birth = 'Sin fecha de nacimiento'
    meta = ' · '.join([birth,
                       _label(getattr(profile, 'nationality', None), 'nacionalidad sin dato'),
                       'nivel ' + _label(getattr(profile, 'level', None), 'sin dato'),
                       'estado ' + _label(getattr(profile, 'status', None), 'sin dato')])
    st.markdown(f'<div class="cm-match"><span class="score">{escape(name)}</span>{tags}'
                f'<span class="meta">{escape(meta)}</span></div>', unsafe_allow_html=True)
    since, height, weight = (getattr(profile, column, None) for column in ('datefrom', 'height', 'weight'))
    st.caption('Ficha de COMET · ' + ' · '.join([
        f'datefrom: {since:%d-%m-%Y}' if pd.notna(since) else 'datefrom: —',
        f'estatura: {height:g}' if pd.notna(height) else 'estatura: —',
        f'peso: {weight:g}' if pd.notna(weight) else 'peso: —']) + ' (estatura y peso tal como los entrega COMET, sin conversión).')

    comp = ctx.computed.comp[ctx.computed.comp['personid'] == personid]
    total = ctx.computed.cat[ctx.computed.cat['personid'] == personid]
    if int(total['incomplete'].sum()):
        st.warning(f'Las cifras de este jugador están **incompletas**: en {int(total["incomplete"].sum())} partido(s) COMET '
                   'trae filas repetidas con valores distintos y no se elige ninguna. Esos valores aparecen como «—» y '
                   'el jugador no entra en rankings ni alertas. Ver Seguimiento y configuración → Calidad de datos.')
    no_minutes = int(total['minutes_missing'].sum())
    if no_minutes:
        st.warning(f'En {no_minutes} partido(s) COMET no trae los minutos de este jugador (o la marca de jugó los contradice): '
                   'sus minutos y su participación aparecen como «—» —no se muestra una suma parcial— y no entra en el ranking '
                   'de minutos ni en la alerta de baja participación. Sus goles y tarjetas sí cuentan. '
                   'Ver Seguimiento y configuración → Calidad de datos.')
    k = st.columns(6)
    k[0].metric('Partidos citado', int(total['cited'].sum()))
    k[1].metric('Partidos jugados', int(total['played'].sum()))
    k[2].metric('Minutos', fmt(total['minutes'].sum(skipna=False) if len(total) else None))
    k[3].metric('Goles', fmt(total['goals'].sum(min_count=1)))
    k[4].metric('Amarillas / rojas', f'{fmt(total["yellow_cards"].sum(min_count=1))} / {fmt(total["red_cards"].sum(min_count=1))}')
    results = total['results_with'].sum()
    k[5].metric('Victorias con el jugador', fmt(total['wins_with'].sum() / results * 100 if results else None, 0, ' %'))

    tabs = st.tabs(['Historial', 'Categoría vs edad', 'Evolución', 'Partidos', 'Arquero', 'Seguimiento'])
    with tabs[0]:
        history = comp.sort_values(['season_year', 'category_rank'], ascending=False)
        show_table(history, {
            'season_year': ('Temporada', '{:.0f}'), 'category': ('Categoría', None), 'competition': ('Competición', None),
            'cited': ('Citado', FMT_INT), 'started': ('Titular', FMT_INT), 'sub_in': ('Suplente que ingresó', FMT_INT),
            'only_called': ('Solo citación', FMT_INT), 'minutes': ('Minutos', FMT_INT), 'goals': ('Goles', FMT_INT),
            'yellow_cards': ('Amarillas', FMT_INT), 'second_yellows': ('2.ª amarilla', FMT_INT),
            'red_cards': ('Rojas', FMT_INT), 'own_goals': ('Autogoles', FMT_INT),
            'possible_minutes': ('Minutos posibles', FMT_INT), 'participation_pct': ('Participación', FMT_PCT),
            'wins_with': ('Ganados con él', FMT_INT), 'win_pct_with': ('% victorias', FMT_PCT),
            'incomplete': ('Partidos con datos contradictorios', FMT_INT)})
    with tabs[1]:
        by_season = facts.groupby('season_year', as_index=False).agg(
            age=('age', 'first'), age_category=('age_category', 'first'),
            ahead_minutes=('ahead_minutes', lambda s: s.sum(min_count=1)))
        principal = ctx.computed.principal[ctx.computed.principal['personid'] == personid][['season_year', 'category']]
        by_season = by_season.merge(principal, on='season_year', how='left').sort_values('season_year', ascending=False)
        steps = facts.groupby('season_year')['steps_ahead'].max()
        by_season['adelantado'] = by_season['season_year'].map(
            lambda y: 'Sí, +%d' % steps[y] if steps.get(y, 0) > 0 else ('No' if pd.notna(steps.get(y)) else None))
        show_table(by_season, {'season_year': ('Temporada', '{:.0f}'), 'age': ('Edad al corte', FMT_INT),
                               'age_category': ('Categoría por edad', None), 'category': ('Categoría en que juega', None),
                               'adelantado': ('Categorías por encima de su edad', None),
                               'ahead_minutes': ('Minutos en categoría superior', FMT_INT)})
        st.caption('La categoría en que juega es donde sumó más minutos esa temporada. La edad se mide en la fecha de '
                   'corte configurada (supuesto pendiente de confirmar).')
    with tabs[2]:
        freq = st.radio('Agrupar minutos por', ['Mes', 'Semestre'], horizontal=True, key='cp_freq')
        timeline = metrics.minutes_timeline(ds, personid, freq)
        if timeline.empty:
            st.info('Sin partidos para armar la evolución.')
        else:
            fig = px.bar(timeline, x='periodo', y='minutes', color='category', barmode='stack',
                         color_discrete_sequence=SERIES_COLORS,
                         labels={'periodo': '', 'minutes': 'Minutos jugados', 'category': 'Categoría'})
            apply_ohiggins_plotly_theme(fig, height=360)
            fig.update_xaxes(type='category')
            mine = ctx.periods[(ctx.periods['personid'] == personid) & ctx.periods['active'].astype(bool)] if len(ctx.periods) else ctx.periods
            if len(mine):
                top = float(timeline.groupby('periodo')['minutes'].sum().max() or 0) + 20
                for label in sorted(_period_labels(mine, freq) & set(timeline['periodo'])):
                    fig.add_annotation(x=label, y=top, text='Selección', showarrow=False,
                                       font=dict(color='#1B6B34', size=11), bgcolor='#DCFCE7')
            st.plotly_chart(fig, use_container_width=True)
            st.caption('Solo se muestran los períodos en que O’Higgins jugó en las categorías donde el jugador fue citado; '
                       'un mes sin partidos no se dibuja como cero, y un mes con minutos desconocidos no se dibuja como una suma parcial.')
    with tabs[3]:
        log = facts.sort_values('matchdate', ascending=False).assign(
            fecha=lambda d: d['matchdate'].dt.strftime('%d-%m-%Y'),
            rival=lambda d: d['rival'].map(lambda r: _label(r, 'rival sin nombre')),
            marcador=lambda d: [None if pd.isna(a) or pd.isna(b) else f'{int(a)}-{int(b)}'
                                for a, b in zip(d['goals_for'], d['goals_against'])])
        show_table(log, {'fecha': ('Fecha', None), 'category': ('Categoría', None), 'rival': ('Rival', None),
                         'venue': ('Local / Visita', None), 'marcador': ('Marcador', None), 'result': ('Resultado', None),
                         'role': ('Rol', None), 'minutes': ('Minutos', FMT_INT), 'goals': ('Goles', FMT_INT),
                         'yellow_cards': ('Amarillas', FMT_INT), 'red_cards': ('Rojas', FMT_INT)},
                   colors=('result', RESULT_COLORS))
    with tabs[4]:
        keeper = ds.goalkeepers[ds.goalkeepers['personid'] == personid]
        keeper = keeper[((keeper['played'] == True).fillna(False) | (keeper['minutesplayed'] > 0)).astype(bool)]  # noqa: E712
        if keeper.empty:
            st.info('Sin partidos como arquero.')
        else:
            minutes = keeper['minutesplayed'].sum(min_count=1)
            conceded = keeper['goalsconceded'].sum(min_count=1)
            a, b, c, d = st.columns(4)
            a.metric('Partidos como arquero', len(keeper))
            b.metric('Goles recibidos', fmt(conceded))
            c.metric('Goles recibidos por 90', fmt(conceded * 90 / minutes if pd.notna(minutes) and minutes > 0 else None, 2))
            d.metric('Vallas invictas', int((keeper['goalsconceded'] == 0).sum()))
    with tabs[5]:
        _marks_panel(ctx, personid)
