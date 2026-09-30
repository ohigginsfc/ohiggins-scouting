"""Categorías del fútbol formativo: orden, tope de edad y categoría por edad."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Optional

import pandas as pd

SENIOR_LABEL = 'Primer Equipo'
SENIOR_RANK = 1000
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


def age_on(birth, ref: date) -> Optional[int]:
    """Años cumplidos de `birth` en la fecha `ref`; None si no hay fecha de nacimiento."""
    if birth is None or pd.isna(birth):
        return None
    birth = pd.Timestamp(birth)
    return ref.year - birth.year - ((ref.month, ref.day) < (birth.month, birth.day))


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
