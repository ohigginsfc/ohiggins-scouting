"""Categorías del fútbol formativo: orden, tope de edad y categoría por edad."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Optional

import pandas as pd

SENIOR_LABEL = 'Primer Equipo'
SENIOR_RANK = 1000
# Secciones del club (reunión con Pablo, 13-10-2026): sub-20, sub-18, sub-16, sub-15, sub-14, sub-13, sub-12 «y así».
# Cada sección reúne a quienes tienen hasta ese tope de edad y más que la sección menor siguiente.
DEFAULT_LADDER_CAPS = (20, 18, 16, 15, 14, 13, 12, 11)
_YOUTH = re.compile(r'^\s*(?:u|sub)\s*[-_ ]?\s*(\d{1,2})\s*$', re.IGNORECASE)
_SENIOR = {'primer equipo', 'primera', 'adulto', 'adultos'}


@dataclass(frozen=True)
class Category:
    label: str
    rank: Optional[int]  # orden comparable; None si la categoría no se reconoce
    cap: Optional[int]   # edad máxima de una categoría U-N; None si no es U-N


def parse_category(label) -> Category:
    """'U-15' -> tope 15; 'Primer Equipo' -> la más alta; otro texto -> sin clasificar."""
    text = '' if label is None or (not isinstance(label, str) and pd.isna(label)) else str(label).strip()
    if text.lower() in _SENIOR:
        return Category(SENIOR_LABEL, SENIOR_RANK, None)
    match = _YOUTH.match(text)
    if match:
        cap = int(match.group(1))
        return Category(f'U-{cap}', cap, cap)
    return Category(text, None, None)


def category_rank(label) -> Optional[int]:
    return parse_category(label).rank


def order_categories(labels: Iterable, *, descending: bool = True) -> list[str]:
    """Categorías reconocidas ordenadas (Primer Equipo, U-19, U-16...); sin duplicados."""
    seen = {}
    for label in labels:
        cat = parse_category(label)
        if cat.rank is not None:
            seen[cat.label] = cat.rank
    return sorted(seen, key=seen.get, reverse=descending)


def build_ladder(caps: Iterable[int], data_categories: Iterable = ()) -> list[str]:
    """Escalera de categorías, de mayor a menor: las secciones oficiales más las que haya en los datos.

    Una categoría que COMET trae y no está en la lista oficial se agrega (no se descarta ni se inventa su tope);
    una sección oficial sin partidos sigue contando para saber qué categoría le corresponde a un jugador por edad.
    """
    labels = {SENIOR_LABEL: SENIOR_RANK}
    for cap in caps:
        labels[f'U-{int(cap)}'] = int(cap)
    for label in data_categories:
        parsed = parse_category(label)
        if parsed.rank is not None:
            labels[parsed.label] = parsed.rank
    return sorted(labels, key=labels.get, reverse=True)


def parse_ladder(text) -> tuple[int, ...]:
    """'20,18,16' -> (20, 18, 16); ValueError si no es una lista de edades entre 5 y 25 sin repetir."""
    try:
        caps = [int(part) for part in str(text).replace(';', ',').split(',') if part.strip()]
    except ValueError:
        raise ValueError('usa edades separadas por coma, por ejemplo 20,18,16,15,14,13,12') from None
    if not caps or len(set(caps)) != len(caps) or any(cap < 5 or cap > 25 for cap in caps):
        raise ValueError('usa edades distintas entre 5 y 25, por ejemplo 20,18,16,15,14,13,12')
    return tuple(sorted(caps, reverse=True))


def age_category_case_sql(age_expr: str, caps: Iterable[int] = DEFAULT_LADDER_CAPS) -> str:
    """CASE de SQL con la misma regla que `category_for_age` (la U-N más pequeña cuyo tope alcanza para la edad).

    Es la única definición para las pantallas antiguas de COMET (que consultan la edad en SQL) y para el cálculo nuevo.
    """
    ordered = sorted({int(cap) for cap in caps})
    lines = [f'WHEN {age_expr} IS NULL THEN NULL',  # sin fecha de nacimiento no hay categoría por edad (no se supone una)
             f"WHEN {age_expr} > {ordered[-1]} THEN '{SENIOR_LABEL}'"]
    for upper, lower in zip(reversed(ordered), reversed(ordered[:-1])):
        lines.append(f"WHEN {age_expr} > {lower} THEN 'U-{upper}'")
    lines.append(f"ELSE 'U-{ordered[0]}'")
    return 'CASE ' + ' '.join(lines) + ' END'


def age_on(birth, ref: date) -> Optional[int]:
    """Años cumplidos de `birth` en la fecha `ref`; None si no hay fecha de nacimiento."""
    if birth is None or pd.isna(birth):
        return None
    birth = pd.Timestamp(birth)
    return ref.year - birth.year - ((ref.month, ref.day) < (birth.month, birth.day))


def _add_years(day: pd.Timestamp, years: int) -> pd.Timestamp:
    try:
        return day.replace(year=day.year + years)
    except ValueError:  # 29 de febrero en un año no bisiesto: el aniversario es el 1 de marzo
        return pd.Timestamp(year=day.year + years, month=3, day=1)


def elapsed_years(start, end) -> Optional[float]:
    """Años transcurridos entre dos fechas: años completos por aniversario más la fracción del año en curso.

    No usa 365,25: dos personas nacidas el mismo día tienen exactamente la misma edad cumplida.
    """
    if start is None or end is None or pd.isna(start) or pd.isna(end):
        return None
    start, end = pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize()
    if end < start:
        return None
    years = end.year - start.year - ((end.month, end.day) < (start.month, start.day))
    last, following = _add_years(start, years), _add_years(start, years + 1)
    return years + (end - last).days / (following - last).days


def season_reference_date(season_year: int, month: int = 12, day: int = 31) -> date:
    """Fecha en que se mide la edad de una temporada (por defecto 31 de diciembre)."""
    return date(int(season_year), int(month), int(day))


def category_for_age(age, available: Iterable) -> Optional[str]:
    """Categoría por edad: la U-N más pequeña cuyo tope alcanza; sobre el tope, Primer Equipo.

    Regla supuesta hasta que el club confirme cómo se asigna la categoría por edad.
    """
    if age is None or pd.isna(age):
        return None
    caps = sorted({c.cap: c.label for c in map(parse_category, available) if c.cap is not None}.items())
    if not caps:
        return None
    if age > caps[-1][0]:
        return SENIOR_LABEL
    for cap, label in caps:
        if age <= cap:
            return label
    return None


def steps_ahead(played, by_age, available: Iterable) -> Optional[int]:
    """Categorías de diferencia entre donde juega y donde le corresponde por edad.

    Positivo = juega en una categoría superior. Cuenta pasos entre categorías
    existentes (no años): con U-16 y U-19 sin U-17/U-18, U-16 -> U-19 es 1 paso.
    """
    top, base = parse_category(played), parse_category(by_age)
    if top.rank is None or base.rank is None:
        return None
    ladder = sorted({c.rank for c in map(parse_category, available) if c.rank is not None} | {top.rank, base.rank})
    return ladder.index(top.rank) - ladder.index(base.rank)


def years_younger(age, category) -> Optional[int]:
    """Años que un jugador es menor que el tope de la categoría (U-15 y 13 años -> 2)."""
    cat = parse_category(category)
    if cat.cap is None or age is None or pd.isna(age):
        return None
    return cat.cap - int(age)
