"""Adaptación de la cronología COMET al cálculo de resultado en cancha.

El export registra al entrante en personid y al saliente en secondpersonid.
displayminute es el reloj absoluto (incluye categorías con tiempos de 35/40 minutos);
minute vuelve a cero en cada fase y nunca se interpreta como reloj de partido.
"""
from __future__ import annotations

import re
from numbers import Real

import pandas as pd

from scouting.onpitch import AGAINST, FOR, Goal, on_pitch_result
from .facts import norm_id

SCORING = {'Gol', 'Penal', 'Autogol'}
PERIODS = {'Primer tiempo', 'Segundo tiempo'}
FIELDS = ('onpitch_entry', 'onpitch_exit', 'onpitch_score_entry', 'onpitch_score_exit',
          'onpitch_state_entry', 'onpitch_state_exit', 'onpitch_changed',
          'onpitch_for', 'onpitch_against', 'onpitch_status')
_DISPLAY = re.compile(r"^\s*(\d+)\s*['′]?\s*(?:\+\s*(\d+)\s*['′]?)?\s*$")


def _integer(value):
    if isinstance(value, Real) and not isinstance(value, bool) and pd.notna(value) and value >= 0 and float(value).is_integer():
        return int(value)
    return None


def event_clock(event):
    """Reloj absoluto validado; no adivina la duración del primer tiempo."""
    if event.get('phase') not in PERIODS:
        return None
    match = _DISPLAY.fullmatch(str(event.get('displayminute', '')))
    if not match:
        return None
    minute, explicit_added = int(match[1]), match[2]
    raw_added = event.get('stoppagetime')
    added = _integer(raw_added) if pd.notna(raw_added) else 0
    if added is None or (explicit_added is not None and pd.notna(raw_added) and int(explicit_added) != added):
        return None
    # Un descuento explícito sin la columna opcional conserva su propio valor.
    if explicit_added is not None and pd.isna(raw_added):
        added = int(explicit_added)
    return minute, added


def _clock_text(clock, default):
    return default if clock is None else f"{clock[0]}{('+' + str(clock[1])) if clock[1] else ''}'"


def _score_text(score):
    return f'{score[0]}-{score[1]}'


def _true(value):
    return pd.notna(value) and value == True  # noqa: E712


def _deduplicate(frame):
    """UID estable: dos versiones diferentes se invalidan, no se elige la última."""
    frame = frame.drop_duplicates().copy()
    if 'uid' not in frame:
        return frame, set(frame['matchid'])
    bad = frame['uid'].isna() | frame['uid'].duplicated(keep=False)
    return frame, set(frame.loc[bad, 'matchid'])


def result_rows(ds, raw_events=None):
    """Una fila por jugador/partido, con motivos explícitos para los datos ausentes.

    No modifica los indicadores históricos basados en el resultado final. Los goles
    deben reconstruir ambos marcadores. Una reentrada o cambio incompleto no se reduce
    a un único intervalo inventado. Un no participante tampoco recibe un 0-0.
    """
    source = raw_events if raw_events is not None else pd.DataFrame()
    required = {'matchid', 'personid', 'secondpersonid', 'matcheventtype', 'phase', 'displayminute', 'side'}
    usable = required <= set(source.columns)
    groups, conflicts = {}, set()
    if usable:
        source = source.copy()
        for col in ('matchid', 'personid', 'secondpersonid'):
            source[col] = source[col].map(norm_id)
        source, conflicts = _deduplicate(source)
        groups = {key: frame.to_dict('records') for key, frame in source.groupby('matchid')}
    matches = ds.matches.set_index('matchid').to_dict('index')
    prepared = {}
    for matchid, match in matches.items():
        events = groups.get(matchid, [])
        reason = None if usable else 'Eventos no disponibles'
        if usable and not events:
            reason = 'Sin eventos del partido'
        if matchid in conflicts:
            reason = 'Eventos contradictorios'
        final = tuple(_integer(match.get(col)) for col in ('goals_for', 'goals_against'))
        if None in final:
            reason = reason or 'Sin marcador final'
        goals = []
        for event in events:
            if event['matcheventtype'] not in SCORING:
                continue
            clock, side = event_clock(event), event['side']
            if clock is None or pd.isna(side) or side not in (FOR, AGAINST):
                reason = reason or 'Gol sin minuto o equipo válido'
                continue
            if event['matcheventtype'] == 'Autogol':
                side = AGAINST if side == FOR else FOR
            goals.append(Goal(clock[0], side, clock[1]))
        if not reason and on_pitch_result(goals, final) is None:
            reason = 'Cronología de goles incompleta'
        prepared[matchid] = (events, goals, final, reason)

    rows = []
    for fact in ds.facts.to_dict('records'):
        matchid, personid = fact['matchid'], fact['personid']
        row = dict(matchid=matchid, personid=personid, **{field: None for field in FIELDS})
        events, goals, final, reason = prepared[matchid]
        if fact['conflict']:
            reason = 'Planilla contradictoria'
        elif not fact['participated']:
            reason = 'No participó' if not fact['minutes_unknown'] else 'Participación desconocida'
        elif pd.isna(fact['startinglineup']):
            reason = 'Titularidad desconocida'
        if not reason:
            incoming = [e for e in events if e['matcheventtype'] == 'Sustitución' and e['personid'] == personid]
            outgoing = [e for e in events if e['matcheventtype'] == 'Sustitución' and e['secondpersonid'] == personid]
            starter = _true(fact['startinglineup'])
            if len(incoming) != (0 if starter else 1) or len(outgoing) > 1:
                reason = 'Entrada o reentrada sin intervalo único'
            else:
                entered = None if starter else event_clock(incoming[0])
                left = event_clock(outgoing[0]) if outgoing else None
                if (not starter and entered is None) or (outgoing and left is None):
                    reason = 'Cambio sin minuto válido'
                # Las tarjetas de suplentes o de quien ya salió no son salidas del campo.
                dismissals = []
                for event in events:
                    if event['personid'] != personid or event['matcheventtype'] not in {'Tarjeta roja', 'Expulsión', 'Tarjeta amarilla'}:
                        continue
                    if event['matcheventtype'] == 'Tarjeta amarilla' and not _true(event.get('secondyellowcard')):
                        continue
                    clock = event_clock(event)
                    if clock is None:
                        reason = reason or 'Expulsión sin minuto válido'
                    elif (entered is None or clock >= entered) and (left is None or clock < left):
                        dismissals.append(clock)
                if dismissals:
                    left = min(dismissals)
                if not reason and entered is not None and left is not None and left < entered:
                    reason = 'Salida anterior a la entrada'
                if not reason and left is not None and pd.notna(fact['minutes']):
                    added_by_phase = {phase: max([event_clock(e)[1] for e in events
                                                 if e['phase'] == phase and event_clock(e) is not None] or [0])
                                      for phase in PERIODS}
                    expected = left[0] - (entered[0] if entered else 0)
                    if abs(fact['minutes'] - expected) > sum(added_by_phase.values()) + 1:
                        reason = 'Minutos incompatibles con los cambios'
                if not reason and left is None:
                    match = matches[matchid]
                    durations = [v for v in (match.get('nominal_duration'), match.get('duration')) if pd.notna(v) and v > 0]
                    duration = max(durations) if durations else None
                    minutes = fact['minutes']
                    # COMET puede omitir un cambio: no asumir que terminó si faltan minutos.
                    expected = duration - (entered[0] if entered else 0) if duration is not None else None
                    if pd.isna(minutes) or expected is None or minutes + 1 < expected:
                        reason = 'Salida no confirmada por la planilla'
                if not reason:
                    result = on_pitch_result(goals, final, entered=entered, left=left)
                    row.update(onpitch_entry=_clock_text(entered, 'Inicio'), onpitch_exit=_clock_text(left, 'Final'),
                               onpitch_score_entry=_score_text(result.score_at_entry),
                               onpitch_score_exit=_score_text(result.score_at_exit),
                               onpitch_state_entry=result.state_at_entry, onpitch_state_exit=result.state_at_exit,
                               onpitch_changed='Sí' if result.result_changed else 'No',
                               onpitch_for=result.goals_for_while_on, onpitch_against=result.goals_against_while_on)
        row['onpitch_status'] = reason or 'Calculado'
        rows.append(row)
    return pd.DataFrame(rows, columns=['matchid', 'personid', *FIELDS])


def attach_results(rows, results):
    """Combina solo las claves jugador/partido, sin expandir la planilla."""
    return rows.merge(results, on=['matchid', 'personid'], how='left', validate='one_to_one')
