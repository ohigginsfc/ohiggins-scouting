"""Reglas deportivas de COMET y su estado de aprobación.

Cada regla dice de dónde sale: `pablo` (figura en su solicitud) o `supuesto`
(criterio provisional que el club aún no ha confirmado). La interfaz muestra ese
estado junto a cada resultado; ninguna regla supuesta se presenta como aprobada.
Los valores pueden sobrescribirse desde Supabase (`portal.comet_settings`).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping, Optional

ORIGIN_PABLO = 'pablo'
ORIGIN_ASSUMED = 'supuesto'

STATUS_REQUESTED = 'Solicitada por Pablo'
STATUS_CONFIRMED = 'Confirmada por el club'
STATUS_PENDING = 'Supuesto: pendiente de confirmar'


@dataclass(frozen=True)
class RuleDef:
    key: str
    label: str
    default: Any
    origin: str
    kind: str            # int | bool | choice | text | list
    applied: str         # qué hace hoy la aplicación con esta regla
    question: Optional[str] = None  # pregunta para Pablo, en lenguaje sencillo
    choices: tuple = ()
    minimum: Optional[int] = None
    maximum: Optional[int] = None
    editable: bool = True


RULE_DEFS: tuple[RuleDef, ...] = (
    RuleDef(
        'yellow_threshold', 'Tarjetas amarillas para alertar', 4, ORIGIN_PABLO, 'int',
        'Alerta cuando el jugador llega a 4 amarillas o más (con 4 ya avisa; no espera a la quinta).',
        minimum=1, maximum=20),
    RuleDef(
        'participation_threshold', 'Participación mínima (% de minutos posibles)', 20, ORIGIN_PABLO, 'int',
        'Alerta cuando el jugador ha jugado menos del 20 % de los minutos posibles.',
        minimum=1, maximum=100),
    RuleDef(
        'seasons_without_promotion', 'Temporadas sin promoción para alertar', 2, ORIGIN_PABLO, 'int',
        'Alerta cuando lleva más de 2 temporadas seguidas en la misma categoría (3 o más).',
        minimum=1, maximum=10),
    RuleDef(
        'age_cutoff', 'Fecha de corte de edad (mes-día)', '12-31', ORIGIN_ASSUMED, 'text',
        'La edad se mide el 31 de diciembre del año de la temporada. Cada categoría U-N reúne hasta N años; '
        'la categoría por edad es la más pequeña que alcanza para su edad.',
        '¿A qué fecha se mide la edad para decir en qué categoría le corresponde jugar a un jugador '
        '(por ejemplo, el 31 de diciembre del año de la temporada)? ¿Un jugador de 14 años que está en U-15 '
        'se considera adelantado?'),
    RuleDef(
        'min_minutes_on_pitch', 'Minutos mínimos para contar el resultado del partido', 1, ORIGIN_ASSUMED, 'int',
        'El "resultado con el jugador en cancha" es el resultado final de los partidos en que el jugador '
        'sumó al menos este número de minutos.',
        '¿«Resultado con el jugador en cancha» es el resultado final del partido en que jugó (aunque haya entrado '
        'a los 85 minutos) o el marcador mientras estuvo dentro de la cancha? Lo segundo necesita el minuto de '
        'cada gol y de cada cambio, que COMET hoy no entrega.',
        minimum=1, maximum=90),
    RuleDef(
        'possible_from_first_call', 'Minutos posibles: contar desde la primera citación', False, ORIGIN_ASSUMED, 'bool',
        'Apagado: los minutos posibles son los de todos los partidos ya jugados de la categoría y competición '
        'donde el jugador fue citado alguna vez. Encendido: solo desde su primera citación.',
        '¿Qué partidos cuentan como minutos posibles? ¿Todos los de la serie, o solo desde que el jugador '
        'llegó a la serie? ¿Entran amistosos y copas? ¿Cuánto dura un partido en cada categoría?'),
    RuleDef(
        'exclude_selection_periods', 'Minutos posibles: excluir períodos de selección', False, ORIGIN_ASSUMED, 'bool',
        'Apagado: los períodos de selección solo se muestran. Encendido: los partidos que caen dentro de un '
        'período marcado se quitan de los minutos posibles de ese jugador.',
        '¿Los partidos que el jugador se pierde por estar en un microciclo de selección, Sudamericano o Mundial '
        'deben descontarse de sus minutos posibles?'),
    RuleDef(
        'card_cycle', 'Ciclo de tarjetas amarillas', 'competicion', ORIGIN_ASSUMED, 'choice',
        'Las amarillas se acumulan dentro de cada competición. Solo se cuenta la amarilla simple; la doble '
        'amarilla y las suspensiones cumplidas no se descuentan.',
        '¿Las amarillas se acumulan por campeonato o por temporada completa? ¿Se borran al cumplir una fecha '
        'de suspensión? ¿La roja por doble amarilla cuenta como amarilla?',
        choices=('competicion', 'temporada')),
    RuleDef(
        'roster_rule', '"No citado": cómo se conoce el plantel', 'planillas', ORIGIN_ASSUMED, 'text',
        'Es "no citado" quien figura en la planilla de otro partido de la misma competición, pero no en ésta. '
        'No se conoce a quien nunca ha sido citado.',
        '¿De dónde sale la lista oficial del plantel de cada serie para saber quién no fue citado? Hoy COMET solo '
        'entrega las planillas de los partidos, no el plantel completo.',
        editable=False),
    RuleDef(
        'seniority_rule', 'Antigüedad en el club', 'primer_partido', ORIGIN_ASSUMED, 'text',
        'Años desde el primer partido de O\'Higgins registrado en COMET para ese jugador. Es un mínimo: '
        'no llega más atrás que el historial disponible.',
        '¿La antigüedad se cuenta desde que el jugador entró al club? Necesitamos esa fecha de ingreso por '
        'jugador; hoy no está en los datos.',
        editable=False),
    RuleDef(
        'promotion_rule', 'Promoción de categoría', 'categoria_principal', ORIGIN_ASSUMED, 'text',
        'La categoría de una temporada es donde el jugador sumó más minutos. Hay promoción cuando esa '
        'categoría es mayor que la de la temporada anterior. Primer Equipo no se evalúa.',
        '¿Qué es una «promoción»: subir de serie de un año al siguiente, o también jugar partidos en la serie '
        'superior? ¿Los jugadores de U-19 y de Primer Equipo entran en esta alerta?',
        editable=False),
    RuleDef(
        'digest_recipients', 'Destinatarios del resumen semanal', [], ORIGIN_ASSUMED, 'list',
        'Sin destinatarios definidos no se envía nada. El resumen se puede ver en pantalla.',
        '¿Quiénes reciben el resumen y las alertas semanales (correos), qué día y a qué hora? Incluyen nombres '
        'de menores de edad: ¿está autorizado enviarlos por correo?'),
    RuleDef(
        'digest_weekday', 'Día de envío del resumen', 0, ORIGIN_ASSUMED, 'int',
        'Lunes (0) resume la semana anterior de lunes a domingo. No hay envío programado.',
        minimum=0, maximum=6),
)

RULES_BY_KEY = {rule.key: rule for rule in RULE_DEFS}


def parse(rule: RuleDef, raw: Any) -> Any:
    """Valida y normaliza el valor de una regla; ValueError si no es válido."""
    if rule.kind == 'int':
        if isinstance(raw, bool):
            raise ValueError(f'{rule.label}: debe ser un número entero.')
        try:
            value = int(raw)
        except (TypeError, ValueError):
            raise ValueError(f'{rule.label}: debe ser un número entero.') from None
        if (rule.minimum is not None and value < rule.minimum) or (rule.maximum is not None and value > rule.maximum):
            raise ValueError(f'{rule.label}: debe estar entre {rule.minimum} y {rule.maximum}.')
        return value
    if rule.kind == 'bool':
        if not isinstance(raw, bool):
            raise ValueError(f'{rule.label}: debe ser sí o no.')
        return raw
    if rule.kind == 'choice':
        if raw not in rule.choices:
            raise ValueError(f'{rule.label}: elige una de las opciones disponibles.')
        return raw
    if rule.kind == 'list':
        if not isinstance(raw, list):
            raise ValueError(f'{rule.label}: debe ser una lista.')
        items = [str(item).strip() for item in raw if str(item).strip()]
        if any('@' not in item or ' ' in item or len(item) > 254 for item in items):
            raise ValueError(f'{rule.label}: cada destinatario debe ser un correo válido.')
        return items
    if rule.key == 'age_cutoff':
        try:
            month, day = (int(part) for part in str(raw).split('-'))
            date(2001, month, day)  # 2001 no es bisiesto: evita aceptar 02-29
        except (TypeError, ValueError):
            raise ValueError(f'{rule.label}: usa el formato mes-día, por ejemplo 12-31.') from None
        return f'{month:02d}-{day:02d}'
    return str(raw)


def coerce(rule: RuleDef, raw: Any) -> Any:
    """Lee un valor guardado; si no es válido devuelve el valor por defecto."""
    try:
        return parse(rule, raw)
    except ValueError:
        return rule.default


class Rules:
    """Valores vigentes de las reglas: por defecto, o lo guardado en Supabase."""

    def __init__(self, stored: Optional[Mapping[str, Mapping[str, Any]]] = None):
        self._stored = dict(stored or {})

    def value(self, key: str) -> Any:
        rule = RULES_BY_KEY[key]
        entry = self._stored.get(key)
        return coerce(rule, entry.get('value')) if entry and 'value' in entry else rule.default

    def confirmed(self, key: str) -> bool:
        entry = self._stored.get(key) or {}
        return bool(entry.get('confirmed'))

    def status(self, key: str) -> str:
        rule = RULES_BY_KEY[key]
        if rule.origin == ORIGIN_PABLO:
            return STATUS_REQUESTED
        return STATUS_CONFIRMED if self.confirmed(key) else STATUS_PENDING

    def is_pending(self, key: str) -> bool:
        return self.status(key) == STATUS_PENDING

    def pending(self) -> list[RuleDef]:
        return [rule for rule in RULE_DEFS if self.is_pending(rule.key)]

    def cutoff(self) -> tuple[int, int]:
        month, day = (int(part) for part in self.value('age_cutoff').split('-'))
        return month, day
