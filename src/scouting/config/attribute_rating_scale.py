"""Escala subjetiva de atributos: 1.0–4.0 en pasos de 0.25."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

RATING_MIN = 1.0
RATING_MAX = 4.0
RATING_STEP = 0.25
RATING_DEFAULT = 2.5
LEGACY_MAX_RATING = 5.0

_QUARTER = Decimal("0.25")

RATING_QUARTER_OPTIONS: tuple[float, ...] = tuple(
    round(RATING_MIN + i * RATING_STEP, 2) for i in range(int((RATING_MAX - RATING_MIN) / RATING_STEP) + 1)
)


def _quantize_rating(value: float | Decimal | int) -> Decimal:
    d = Decimal(str(float(value)))
    units = (d / _QUARTER).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    q = (units * _QUARTER).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return max(Decimal(str(RATING_MIN)), min(Decimal(str(RATING_MAX)), q))


def snap_rating_to_quarters(
    value: float | Decimal | int,
    *,
    min_value: float = RATING_MIN,
    max_value: float = RATING_MAX,
) -> float:
    opts = [x for x in RATING_QUARTER_OPTIONS if min_value - 1e-9 <= x <= max_value + 1e-9]
    if not opts:
        return float(max_value)
    return min(opts, key=lambda x: abs(x - float(value)))


def validate_rating(value: float | Decimal | int, max_rating: float | Decimal | int = RATING_MAX) -> None:
    mx = float(max_rating)
    r = float(value)
    if mx <= 0:
        raise ValueError("max_rating must be > 0")
    if r < RATING_MIN or r > mx:
        raise ValueError(f"rating must be between {RATING_MIN} and {max_rating}")
    snapped = snap_rating_to_quarters(r, min_value=RATING_MIN, max_value=min(mx, RATING_MAX))
    if abs(snapped - r) > 1e-6:
        raise ValueError(f"rating must be a multiple of {RATING_STEP}")


def rating_star_fill_percent(rating: float, max_rating: float = RATING_MAX) -> float:
    """
    Porcentaje de ancho para rellenar N estrellas (escala 1–4: valor 2 → 50% de 4 estrellas).
    """
    m = float(max_rating) if float(max_rating) > 0 else RATING_MAX
    r = max(RATING_MIN, min(float(rating), m))
    return max(0.0, min(100.0, (r / m) * 100.0))


def convert_rating_5_to_4(old_rating: float | Decimal | int) -> float:
    """
    Migra escala 0–5 → 1–4:
    nuevo = 1 + (valor_antiguo / 5) * 3, redondeado a 0.25.
    """
    old = float(old_rating)
    if old <= 0:
        return RATING_MIN
    if old >= LEGACY_MAX_RATING:
        return RATING_MAX
    raw = RATING_MIN + (old / LEGACY_MAX_RATING) * (RATING_MAX - RATING_MIN)
    return snap_rating_to_quarters(raw)
