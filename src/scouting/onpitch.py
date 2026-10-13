"""Resultado con el jugador en la cancha: marcador cuando entró, cuando salió y si el resultado cambió.

Pablo lo pidió para COMET y para Scouting (reunión del 13-10-2026): no basta el resultado final del partido en que jugó;
hay que mostrar cuál era el marcador cuando entró y cuando salió, y si el resultado se modificó mientras estuvo en la cancha.

El cálculo no sabe de dónde salen los datos. Recibe los goles del partido con su minuto y los minutos de entrada y salida
del jugador; cada fuente (la tabla de eventos de COMET, los incidentes de Sofascore) debe entregarlos. Si faltan, o si los
goles no suman el marcador final, el resultado queda **sin dato** (`None`): no se inventa ni se reemplaza por el resultado final.
"""
from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral
from typing import Iterable, Optional, Sequence

LEADING, TIED, TRAILING = 'Ganando', 'Empatando', 'Perdiendo'
WIN, DRAW, LOSS = 'Victoria', 'Empate', 'Derrota'

FOR, AGAINST = 'for', 'against'

# Un gol en el mismo minuto que la entrada o la salida: ¿ocurrió con el jugador dentro? Pablo no lo ha definido (supuesto).
DURING, OUTSIDE = 'durante', 'fuera'
SAME_MINUTE_RULES = (DURING, OUTSIDE)

Clock = tuple[int, int]  # (minuto, minutos de descuento): 45+2 es (45, 2); el orden de las tuplas es el orden del partido


@dataclass(frozen=True)
class Goal:
    """Un gol del partido. `side` es el equipo al que suma en el marcador (un autogol del rival suma a favor)."""
    minute: int
    side: str
    added: int = 0

    def __post_init__(self):
        if self.side not in (FOR, AGAINST):
            raise ValueError("side debe ser 'for' o 'against'")
        _check_clock((self.minute, self.added))

    @property
    def clock(self) -> Clock:
        return (self.minute, self.added)


@dataclass(frozen=True)
class OnPitch:
    """Lo que pasó con el marcador mientras el jugador estuvo en la cancha."""
    entered: Optional[Clock]            # None: titular, desde el inicio
    left: Optional[Clock]               # None: siguió hasta el final del partido
    score_at_entry: tuple[int, int]     # (a favor, en contra) cuando entró
    score_at_exit: tuple[int, int]      # (a favor, en contra) cuando salió (o el final)
    final_score: tuple[int, int]
    goals_for_while_on: int
    goals_against_while_on: int

    @property
    def state_at_entry(self) -> str:
        return live_state(self.score_at_entry)

    @property
    def state_at_exit(self) -> str:
        return live_state(self.score_at_exit)

    @property
    def result_changed(self) -> bool:
        """El resultado (ganando, empatando o perdiendo) era otro cuando salió que cuando entró."""
        return self.state_at_entry != self.state_at_exit

    @property
    def final_result(self) -> str:
        return final_result(self.final_score)


def live_state(score: tuple[int, int]) -> str:
    return LEADING if score[0] > score[1] else TRAILING if score[0] < score[1] else TIED


def final_result(score: tuple[int, int]) -> str:
    return WIN if score[0] > score[1] else LOSS if score[0] < score[1] else DRAW


def _check_pair(values, label: str) -> None:
    try:
        valid = len(values) == 2 and all(isinstance(value, Integral) and not isinstance(value, bool) and value >= 0
                                       for value in values)
    except TypeError:
        valid = False
    if not valid:
        raise ValueError(f'{label}: se requieren dos enteros no negativos')


def _check_clock(clock: Clock) -> None:
    _check_pair(clock, 'minuto y descuento')


def _score(goals: Iterable[Goal], keep) -> tuple[int, int]:
    mine = [g for g in goals if keep(g)]
    return sum(g.side == FOR for g in mine), sum(g.side == AGAINST for g in mine)


def on_pitch_result(goals: Sequence[Goal], final: Optional[tuple[int, int]], *, entered: Optional[Clock] = None,
                    left: Optional[Clock] = None, same_minute: str = DURING) -> Optional[OnPitch]:
    """Marcador con el jugador en la cancha, o `None` si no se puede afirmar.

    * `goals`: todos los goles del partido con su minuto.
    * `final`: marcador final (a favor, en contra). Los goles deben sumarlo exactamente: si no, la cronología está
      incompleta o es contradictoria y no se afirma nada.
    * `entered`: minuto de entrada; `None` si fue titular. `left`: minuto de salida; `None` si siguió hasta el final.
    * `same_minute`: `'durante'` (por defecto, supuesto) cuenta con el jugador dentro un gol del mismo minuto que su
      entrada o su salida; `'fuera'` lo cuenta fuera.
    """
    if same_minute not in SAME_MINUTE_RULES:
        raise ValueError(f'same_minute debe ser uno de {SAME_MINUTE_RULES}')
    for clock in (entered, left):
        if clock is not None:
            _check_clock(clock)
    if entered is not None and left is not None and left < entered:
        raise ValueError('el jugador no puede salir antes de entrar')
    if final is None:
        return None
    _check_pair(final, 'marcador final')
    goals = list(goals)
    if _score(goals, lambda g: True) != tuple(final):
        return None
    inclusive = same_minute == DURING
    at_entry = (0, 0) if entered is None else _score(
        goals, (lambda g: g.clock < entered) if inclusive else (lambda g: g.clock <= entered))
    at_exit = tuple(final) if left is None else _score(
        goals, (lambda g: g.clock <= left) if inclusive else (lambda g: g.clock < left))
    # Con entrada y salida en el mismo instante y goles fuera, el intervalo está
    # vacío. Ambos marcadores deben coincidir; no puede restarse un gol ya contado.
    if not inclusive and entered is not None and entered == left:
        at_exit = at_entry
    return OnPitch(entered=entered, left=left, score_at_entry=at_entry, score_at_exit=at_exit, final_score=tuple(final),
                   goals_for_while_on=at_exit[0] - at_entry[0], goals_against_while_on=at_exit[1] - at_entry[1])


def _minute_text(clock: Optional[Clock], fallback: str) -> str:
    if clock is None:
        return fallback
    return f"{clock[0]}+{clock[1]}'" if clock[1] else f"{clock[0]}'"


def describe(result: Optional[OnPitch]) -> str:
    """Frase para la pantalla; «sin dato» si no se pudo calcular."""
    if result is None:
        return 'Sin dato: la cronología del partido no está completa'
    start = 'Fue titular' if result.entered is None else f'Entró a los {_minute_text(result.entered, "")}'
    entry = f'{start} con {result.score_at_entry[0]}-{result.score_at_entry[1]} ({result.state_at_entry.lower()})'
    leaving = 'terminó el partido' if result.left is None else f'salió a los {_minute_text(result.left, "")}'
    exit_ = f'{leaving} con {result.score_at_exit[0]}-{result.score_at_exit[1]} ({result.state_at_exit.lower()})'
    changed = 'el resultado cambió mientras estuvo en la cancha' if result.result_changed else 'el resultado no cambió'
    return f'{entry}; {exit_}: {changed}'
