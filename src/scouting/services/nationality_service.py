"""Chilenos y extranjeros para los campogramas del Dashboard (pedido de Pablo, 13-10-2026).

La nacionalidad llega como texto libre: Sofascore trae el nombre del país («Chile») y el alta manual de informes la
escribe a mano («Chilena», «chileno», «Chile / Argentina»). Se agrupa así:

* **Chileno**: alguna de las nacionalidades que figuran es chilena (también la doble nacionalidad: no cuenta como extranjero).
* **Extranjero**: tiene nacionalidad y ninguna es chilena.
* **Sin dato**: no hay nacionalidad. No se supone ninguna: ese jugador no aparece en ninguno de los dos campogramas.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable

CHILEAN = "chilean"
FOREIGN = "foreign"

GROUP_LABELS = {CHILEAN: "Jugadores chilenos", FOREIGN: "Jugadores extranjeros"}

_CHILEAN_WORDS = frozenset({"chile", "chilena", "chileno", "chilenas", "chilenos", "chilean", "chl"})
_SEPARATORS = re.compile(r"[/,;&+\-]|\s+y\s+|\s+e\s+|\s+and\s+")


def _plain(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text)
    return "".join(c for c in folded if not unicodedata.combining(c)).casefold().strip(" .")


def nationality_group(value: Any) -> str | None:
    """'chilean', 'foreign' o None si no hay nacionalidad."""
    if value is None or (not isinstance(value, str) and value != value):  # None o NaN
        return None
    text = _plain(str(value))
    if not text or text in {"-", "—", "sin dato", "desconocida", "desconocido", "n/a", "na"}:
        return None
    parts = [part.strip(" .") for part in _SEPARATORS.split(text) if part.strip(" .")]
    if not parts:
        return None
    return CHILEAN if any(part in _CHILEAN_WORDS for part in parts) else FOREIGN


def split_position_counts(rows: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Agrupa filas (posición, nacionalidad, jugadores, informes) en chilenos, extranjeros y sin dato, sumando por posición.

    Un jugador tiene una sola posición y una sola nacionalidad, así que los jugadores y los informes se suman sin duplicar.
    """
    totals: dict[str, dict[str, dict[str, int]]] = {CHILEAN: {}, FOREIGN: {}, "unknown": {}}
    for row in rows:
        position = row.get("position")
        if not position:
            continue
        group = nationality_group(row.get("nationality")) or "unknown"
        bucket = totals[group].setdefault(str(position), {"players_count": 0, "reports_count": 0})
        bucket["players_count"] += int(row.get("players_count") or 0)
        bucket["reports_count"] += int(row.get("reports_count") or 0)
    return {group: [{"position": position, **counts} for position, counts in sorted(by_position.items())]
            for group, by_position in totals.items()}
