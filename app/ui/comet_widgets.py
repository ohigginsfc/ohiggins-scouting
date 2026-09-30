"""Componentes visuales de las pantallas de seguimiento COMET.

Todo texto que viene de datos (nombres, notas, rivales) se escapa antes de mostrarse como HTML.
Un dato ausente se muestra como "—", nunca como 0.
"""
from __future__ import annotations

from html import escape
from typing import Callable, Mapping, Optional

import pandas as pd
import streamlit as st

from scouting.comet.alerts import ALERT_COLORS
from scouting.comet.rules import RULES_BY_KEY, STATUS_CONFIRMED, STATUS_PENDING, STATUS_REQUESTED

MISSING = '—'

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


def rule_note(rules, keys: list[str]) -> None:
    """Aviso con el estado de las reglas que usa la pantalla; solo aparece si alguna es un supuesto."""
    lines = []
    for key in keys:
        status = rules.status(key)
        if status == STATUS_PENDING:
            rule = RULES_BY_KEY[key]
            lines.append(f'{status_pill(status)} <strong>{escape(rule.label)}.</strong> {escape(rule.applied)}')
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


def show_table(frame: pd.DataFrame, columns: Mapping[str, tuple], *, key: Optional[str] = None,
               colors: Optional[tuple] = None, height: Optional[int] = None) -> None:
    """Muestra `frame` con las columnas indicadas: {columna: (título, formato o None)}."""
    if frame.empty:
        st.caption('Sin registros.')
        return
    if height is None:  # alto justo para todas las filas (hasta 640 px); no se cortan filas a la vista
        height = min(35 * (len(frame) + 1) + 3, 640)
    present = {c: v for c, v in columns.items() if c in frame.columns}
    view = frame[list(present)].rename(columns={c: v[0] for c, v in present.items()})
    formats = {v[0]: v[1] for v in present.values() if v[1]}
    for column in view.columns:
        if view[column].isna().any():
            # Streamlit dibuja las celdas vacías como "None"; con texto, un dato ausente se ve como "—".
            view[column] = [MISSING if pd.isna(v) else _render(v, formats.get(column)) for v in view[column]]
            formats.pop(column, None)
    styler = styled(view, formats)
    if colors:
        column, mapping = colors
        styler = color_column(styler, present[column][0] if column in present else column, mapping)
    st.dataframe(styler, hide_index=True, use_container_width=True, key=key, height=height)


def show_static_table(frame: pd.DataFrame, columns: Mapping[str, tuple], *, colors: Optional[tuple] = None) -> None:
    """Tabla que ajusta el texto largo (las tablas interactivas lo cortan). La primera columna hace de índice."""
    if frame.empty:
        st.caption('Sin registros.')
        return
    present = {c: v for c, v in columns.items() if c in frame.columns}
    view = frame[list(present)].rename(columns={c: v[0] for c, v in present.items()})
    view = view.set_index(view.columns[0])
    styler = view.style.format(na_rep=MISSING)
    if colors:
        column, mapping = colors
        styler = color_column(styler, present[column][0], mapping)
    st.table(styler)


def alert_tile(count: int, label: str, color: str) -> str:
    ink, paper = ALERT_COLORS[color]
    return (f'<div class="cm-alert" style="background:{paper};border-color:{ink};color:{ink}">'
            f'<div class="n">{count}</div><div class="t">{escape(label)}</div>'
            f'<div class="t" style="font-weight:500">{escape(color)}</div></div>')
