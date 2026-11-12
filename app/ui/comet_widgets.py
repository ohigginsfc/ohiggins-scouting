"""Componentes visuales de las pantallas de seguimiento COMET.

Todo texto que viene de datos (nombres, notas, rivales) se escapa antes de mostrarse como HTML.
Un dato ausente se muestra como "—", nunca como 0.
"""
from __future__ import annotations

import logging
from html import escape
from typing import Callable, Mapping, Optional

import pandas as pd
import streamlit as st
from streamlit.errors import DuplicateWidgetID

from scouting.comet import excel_export, yearly
from scouting.comet.alerts import ALERT_COLORS
from scouting.comet.rules import RULES_BY_KEY, STATUS_CONFIRMED, STATUS_PENDING, STATUS_REQUESTED
from ui.portal_brand import PORTAL_VERSION

logger = logging.getLogger(__name__)

MISSING = '—'
EXCEL_LABEL = 'Descargar Excel'
EXCEL_HELP = 'Descarga esta tabla en un archivo de Excel (.xlsx), con las mismas columnas y filas que se ven.'
_NOTES_KEY = '_cm_provisional_notes'  # criterios provisionales de la pantalla abierta, para repetirlos en el Excel
_MAX_BUTTONS_PER_TABLE = 200

STATUS_STYLE = {STATUS_REQUESTED: 'Azul', STATUS_CONFIRMED: 'Verde', STATUS_PENDING: 'Naranja'}
RESULT_STYLE = {'Victoria': 'Verde', 'Empate': 'Amarillo', 'Derrota': 'Rojo'}

SERIES_COLORS = ['#1B537B', '#75B9E5', '#49A942', '#F59E0B', '#64748B', '#8AD184']  # sin rojo: no implica "malo"

FMT_INT = '{:.0f}'
FMT_1 = '{:.1f}'
FMT_2 = '{:.2f}'
FMT_PCT = '{:.1f} %'


def inject_styles() -> None:
    st.markdown('''<style>
    .cm-pill {display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:700;
        border:1px solid;line-height:1.5;white-space:nowrap;}
    .cm-note {border-left:4px solid #b54708;background:#fff7ed;color:#5c3106;padding:10px 14px;
        border-radius:8px;margin:6px 0 16px;font-size:13px;line-height:1.55;}
    .cm-note strong {color:#3f2304;}
    .cm-title {font-size:22px;font-weight:800;color:#102e46;margin:6px 0 2px;letter-spacing:-.01em;}
    .cm-sub {color:#496477;font-size:14px;margin:0 0 14px;}
    .cm-match {display:flex;flex-wrap:wrap;gap:10px;align-items:center;background:white;border:1px solid #dce7ee;
        border-left:5px solid #75b9e5;border-radius:12px;padding:12px 16px;margin:8px 0 12px;}
    .cm-match .score {font-size:22px;font-weight:800;color:#102e46;}
    .cm-match .meta {color:#496477;font-size:13px;}
    .cm-alert {border-left:5px solid;border-radius:10px;padding:10px 14px;margin:0 0 8px;}
    .cm-alert .n {font-size:26px;font-weight:800;line-height:1.1;}
    .cm-alert .t {font-size:13px;font-weight:650;}
    </style>''', unsafe_allow_html=True)


def pill(text: str, color: str = 'Gris') -> str:
    ink, paper = ALERT_COLORS.get(color, ALERT_COLORS['Gris'])
    return f'<span class="cm-pill" style="color:{ink};background:{paper};border-color:{ink}">{escape(str(text))}</span>'


def status_pill(status: str) -> str:
    return pill(status, STATUS_STYLE.get(status, 'Gris'))


def title(text: str, subtitle: Optional[str] = None) -> None:
    st.markdown(f'<div class="cm-title">{escape(text)}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="cm-sub">{escape(subtitle)}</div>', unsafe_allow_html=True)


def fmt(value, decimals: int = 0, suffix: str = '') -> str:
    """Número para mostrar; '—' si falta el dato."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return MISSING
    return f'{value:.{decimals}f}{suffix}'


def year_filter(years: list[int], key: str, label: str = 'Año') -> Optional[int]:
    """Selector del año de la temporada: «Todos los años» (None) o uno de los años con datos, el más reciente primero."""
    return st.selectbox(label, [None] + list(years), format_func=yearly.label, key=key)


def _remember_notes(plain: list[str]) -> None:
    """Guarda los criterios provisionales de la pantalla abierta: el Excel de sus tablas los repite en la hoja «Información»."""
    st.session_state[_NOTES_KEY] = (st.session_state.get('comet_section'), tuple(plain))


def _provisional_notes() -> tuple:
    saved = st.session_state.get(_NOTES_KEY)
    return saved[1] if saved and saved[0] == st.session_state.get('comet_section') else ()


def rule_note(rules, keys: list[str]) -> None:
    """Aviso con el estado de las reglas que usa la pantalla; solo aparece si alguna es un supuesto."""
    lines, plain = [], []
    for key in keys:
        status = rules.status(key)
        if status == STATUS_PENDING:
            rule = RULES_BY_KEY[key]
            lines.append(f'{status_pill(status)} <strong>{escape(rule.label)}.</strong> {escape(rule.applied)}')
            plain.append(f'{status} · {rule.label}. {rule.applied}')
    _remember_notes(plain)
    if lines:
        st.markdown('<div class="cm-note"><strong>Criterios provisionales.</strong> Estas cifras dependen de reglas que '
                    'el club aún no ha confirmado:<br>' + '<br>'.join(lines) + '</div>', unsafe_allow_html=True)


def styled(frame: pd.DataFrame, formats: Optional[Mapping[str, str | Callable]] = None):
    """Tabla con formato por columna y '—' para datos ausentes (los números siguen ordenables)."""
    styler = frame.style.format(precision=1, na_rep=MISSING)
    for column, formatter in (formats or {}).items():
        if column in frame.columns:
            styler = styler.format(formatter, subset=[column], na_rep=MISSING)
    return styler


def _render(value, formatter) -> str:
    if formatter is None:
        return str(value)
    return formatter(value) if callable(formatter) else formatter.format(value)


def color_column(styler, column: str, colors: Mapping[str, str]):
    """Colorea las celdas de `column` según `colors[valor]` (nombre de color); el texto sigue visible."""
    def paint(value):
        name = colors.get(value)
        if name not in ALERT_COLORS:
            return ''
        ink, paper = ALERT_COLORS[name]
        return f'background-color:{paper};color:{ink};font-weight:650'
    return styler.map(paint, subset=[column])


def _fills(title: str, mapping: Mapping[str, str]) -> dict:
    """Colores de una columna para el Excel: {título: {valor: (texto, fondo)}}, los mismos que se ven en pantalla."""
    return {title: {value: ALERT_COLORS[name] for value, name in mapping.items() if name in ALERT_COLORS}}


def download_excel(frame: pd.DataFrame, name: str, *, formats: Optional[Mapping] = None,
                   fills: Optional[Mapping] = None) -> None:
    """Botón «Descargar Excel» para una tabla: baja los mismos datos y columnas que se ven, con los ausentes en blanco.

    `frame` lleva los títulos de columna tal como se muestran y los valores reales (no el texto «—»). `name` describe la
    tabla («Ranking de goles · U-15 2026»): da el nombre del archivo y de la hoja. Si el Excel no se puede preparar, la
    tabla igual se ve; solo falta el botón.
    """
    try:
        data = excel_export.build_workbook(frame, name, number_formats=formats, fills=fills, notes=_provisional_notes(),
                                           portal_version=PORTAL_VERSION)
    except Exception:
        logger.exception('No se pudo preparar el Excel de «%s»', name)
        st.caption('No se pudo preparar la descarga en Excel de esta tabla.')
        return
    base = f'cm_xlsx_{excel_export.slug(name)}'
    for attempt in range(1, _MAX_BUTTONS_PER_TABLE + 1):  # dos tablas con el mismo nombre no deben repetir la clave
        try:
            # Sin ícono Material: el tema del portal fuerza su tipografía en todos los span y el ícono se vería como texto.
            st.download_button(EXCEL_LABEL, data, file_name=excel_export.export_filename(name),
                               mime=excel_export.XLSX_MIME, key=base if attempt == 1 else f'{base}_{attempt}',
                               help=EXCEL_HELP)
            return
        except DuplicateWidgetID:
            continue
    logger.error('Demasiadas tablas con el mismo nombre «%s»: sin botón de Excel', name)


def show_table(frame: pd.DataFrame, columns: Mapping[str, tuple], *, key: Optional[str] = None,
               colors: Optional[tuple] = None, height: Optional[int] = None, name: Optional[str] = None) -> None:
    """Muestra `frame` con las columnas indicadas: {columna: (título, formato o None)}.

    Con `name`, agrega bajo la tabla el botón «Descargar Excel» (ver `download_excel`).
    """
    if frame.empty:
        st.caption('Sin registros.')
        return
    if height is None:  # alto justo para todas las filas (hasta 640 px); no se cortan filas a la vista
        height = min(35 * (len(frame) + 1) + 3, 640)
    present = {c: v for c, v in columns.items() if c in frame.columns}
    values = frame[list(present)].rename(columns={c: v[0] for c, v in present.items()})
    formats = {v[0]: v[1] for v in present.values() if v[1]}
    excel_formats = dict(formats)
    view = values.copy()
    for column in view.columns:
        if view[column].isna().any():
            # Streamlit dibuja las celdas vacías como "None"; con texto, un dato ausente se ve como "—".
            view[column] = [MISSING if pd.isna(v) else _render(v, formats.get(column)) for v in view[column]]
            formats.pop(column, None)
    styler = styled(view, formats)
    fills = None
    if colors:
        column, mapping = colors
        color_title = present[column][0] if column in present else column
        styler = color_column(styler, color_title, mapping)
        fills = _fills(color_title, mapping)
    st.dataframe(styler, hide_index=True, use_container_width=True, key=key, height=height)
    if name and len(values.columns):
        download_excel(values, name, formats=excel_formats, fills=fills)


def show_static_table(frame: pd.DataFrame, columns: Mapping[str, tuple], *, colors: Optional[tuple] = None,
                      name: Optional[str] = None) -> None:
    """Tabla que ajusta el texto largo (las tablas interactivas lo cortan). La primera columna hace de índice.

    Con `name`, agrega bajo la tabla el botón «Descargar Excel» (ver `download_excel`).
    """
    if frame.empty:
        st.caption('Sin registros.')
        return
    present = {c: v for c, v in columns.items() if c in frame.columns}
    values = frame[list(present)].rename(columns={c: v[0] for c, v in present.items()})
    view = values.set_index(values.columns[0])
    styler = view.style.format(na_rep=MISSING)
    fills = None
    if colors:
        column, mapping = colors
        styler = color_column(styler, present[column][0], mapping)
        fills = _fills(present[column][0], mapping)
    st.table(styler)
    if name:
        download_excel(values, name, fills=fills)


def alert_tile(count: int, label: str, color: str) -> str:
    ink, paper = ALERT_COLORS[color]
    return (f'<div class="cm-alert" style="background:{paper};border-color:{ink};color:{ink}">'
            f'<div class="n">{count}</div><div class="t">{escape(label)}</div>'
            f'<div class="t" style="font-weight:500">{escape(color)}</div></div>')
