"""Resumen semanal de COMET: partidos de la semana y alertas vigentes, en texto y HTML."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from html import escape
from typing import Optional

import pandas as pd

from .alerts import ALERT_COLORS, ALERT_DEFS, alert_label
from .facts import Dataset

MONTHS = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre',
          'octubre', 'noviembre', 'diciembre']
MAX_PER_ALERT = 25


@dataclass(frozen=True)
class Digest:
    subject: str
    text: str
    html: str
    week_start: date
    week_end: date
    matches: int
    alerts: int


def spanish_date(day: date, with_year: bool = True) -> str:
    text = f'{day.day} de {MONTHS[day.month - 1]}'
    return f'{text} de {day.year}' if with_year else text


def week_span(start: date, end: date) -> str:
    """'21 al 27 de septiembre de 2026'; si cruza de mes, '28 de septiembre al 4 de octubre de 2026'."""
    if (start.year, start.month) == (end.year, end.month):
        return f'{start.day} al {spanish_date(end)}'
    if start.year == end.year:
        return f'{spanish_date(start, False)} al {spanish_date(end)}'
    return f'{spanish_date(start)} al {spanish_date(end)}'


def previous_week(today) -> tuple[date, date]:
    """Última semana completa (lunes a domingo) anterior a la fecha de hoy."""
    today = pd.Timestamp(today).date()
    monday = today - timedelta(days=today.weekday()) - timedelta(days=7)
    return monday, monday + timedelta(days=6)


def _name(value) -> str:
    return value if isinstance(value, str) and value else 'Jugador sin ficha'


def _names(rows: pd.DataFrame, column: str) -> str:
    """'Nombre (2), Otro' para los jugadores con cantidad > 0."""
    picked = rows[rows[column].fillna(0) > 0]
    return ', '.join(_name(r.displayname) + (f' ({int(getattr(r, column))})' if getattr(r, column) > 1 else '')
                     for r in picked.itertuples())


def _match_line(m) -> str:
    score = None if pd.isna(m.goals_for) or pd.isna(m.goals_against) else f'{int(m.goals_for)}-{int(m.goals_against)}'
    result = m.result if isinstance(m.result, str) else 'sin resultado'
    rival = m.rival if isinstance(m.rival, str) else 'rival sin nombre'
    tail = f'{score} {result}' if score else result
    return f'{m.category} · {m.competition} · {m.venue} vs {rival} · {tail}'


def week_matches(ds: Dataset, week_start: date) -> pd.DataFrame:
    start = pd.Timestamp(week_start)
    m = ds.matches
    return m[(m['matchdate'] >= start) & (m['matchdate'] < start + timedelta(days=7))].sort_values(
        ['category_rank', 'matchdate'], ascending=[False, True])


def build_weekly_digest(ds: Dataset, alerts: pd.DataFrame, week_start: date, *, generated_on: date,
                        pending_rules: Optional[int] = None, blocked: int = 0, no_minutes: int = 0) -> Digest:
    week_end = week_start + timedelta(days=6)
    matches = week_matches(ds, week_start)
    title = f'Resumen semanal COMET · semana del {week_span(week_start, week_end)}'
    text_lines = [title, '']
    html_parts = [f'<h2 style="margin:0 0 4px;color:#102e46">{escape(title)}</h2>']

    text_lines.append(f'PARTIDOS DE LA SEMANA ({len(matches)})')
    html_parts.append(f'<h3 style="color:#1b537b">Partidos de la semana ({len(matches)})</h3>')
    if matches.empty:
        text_lines.append('  No hay partidos registrados en esta semana.')
        html_parts.append('<p>No hay partidos registrados en esta semana.</p>')
    for m in matches.itertuples():
        rows = ds.facts[ds.facts['matchid'] == m.matchid]
        details = [('Goles', _names(rows, 'goals')), ('Amarillas', _names(rows, 'yellow_cards')),
                   ('Rojas', _names(rows, 'red_cards'))]
        keeper = ds.goalkeepers[(ds.goalkeepers['matchid'] == m.matchid) & (ds.goalkeepers['minutesplayed'] > 0)]
        if len(keeper):
            names = ds.players.set_index('personid')['displayname']
            details.append(('Goles recibidos por arquero', ', '.join(
                f'{names.get(k.personid, "Arquero sin ficha")} ({"sin dato" if pd.isna(k.goalsconceded) else int(k.goalsconceded)})'
                for k in keeper.itertuples())))
        line = _match_line(m)
        text_lines.append(f'  {line}')
        html_parts.append(f'<p style="margin:10px 0 2px"><strong>{escape(line)}</strong></p><ul style="margin:0">')
        for label, value in details:
            if value:
                text_lines.append(f'      {label}: {value}')
                html_parts.append(f'<li>{escape(label)}: {escape(value)}</li>')
        html_parts.append('</ul>')

    text_lines += ['', f'ALERTAS VIGENTES ({len(alerts)})']
    html_parts.append(f'<h3 style="color:#1b537b">Alertas vigentes ({len(alerts)})</h3>')
    if alerts.empty:
        text_lines.append('  No hay alertas vigentes.')
        html_parts.append('<p>No hay alertas vigentes.</p>')
    for definition in ALERT_DEFS:
        group = alerts[alerts['alert_key'] == definition.key]
        if group.empty:
            continue
        label = alert_label(definition.key, ds.rules)
        ink, paper = ALERT_COLORS[group['color'].iloc[0]]
        text_lines.append(f'  {label} ({len(group)})')
        html_parts.append(f'<p style="margin:12px 0 2px;padding:4px 8px;background:{paper};color:{ink};'
                          f'border-left:4px solid {ink}"><strong>{escape(label)} ({len(group)})</strong></p><ul style="margin:0">')
        for r in group.head(MAX_PER_ALERT).itertuples():
            item = f'{_name(r.displayname)} · {r.detail}'
            text_lines.append(f'      - {item}')
            html_parts.append(f'<li>{escape(item)}</li>')
        if len(group) > MAX_PER_ALERT:
            extra = f'y {len(group) - MAX_PER_ALERT} más'
            text_lines.append(f'      {extra}')
            html_parts.append(f'<li>{escape(extra)}</li>')
        html_parts.append('</ul>')

    notes = ['Contiene datos de menores de edad: no reenviar fuera de las personas autorizadas por el club.']
    if blocked:
        notes.append(f'{blocked} jugador(es) no se evalúan en las alertas porque COMET trae filas repetidas con valores '
                     'distintos en sus planillas y no se elige ninguna.')
    if no_minutes:
        notes.append(f'{no_minutes} jugador(es) no se evalúan en la alerta de participación porque COMET no trae los minutos '
                     'de algún partido en que jugaron; no se calcula con una suma parcial.')
    if pending_rules:
        notes.append(f'{pending_rules} reglas de cálculo son supuestos pendientes de confirmar con Pablo; '
                     'las cifras pueden cambiar cuando se aprueben.')
    notes.append(f'Generado el {spanish_date(generated_on)} con datos de COMET.')
    text_lines += ['', 'NOTAS'] + [f'  - {n}' for n in notes]
    html_parts.append('<h3 style="color:#1b537b">Notas</h3><ul>' + ''.join(f'<li>{escape(n)}</li>' for n in notes) + '</ul>')

    html = ('<div style="font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#132e45;max-width:720px">'
            + ''.join(html_parts) + '</div>')
    return Digest(subject=title, text='\n'.join(text_lines), html=html, week_start=week_start,
                  week_end=week_end, matches=len(matches), alerts=len(alerts))
