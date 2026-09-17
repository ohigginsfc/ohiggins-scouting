"""
Tarjetas individuales desde /event/{event_id}/incidents (no están en lineups.statistics).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CardExtractDiagnostics:
    cards_total: int = 0
    cards_with_player: int = 0
    cards_without_player: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    yellow_red_cards: int = 0

    def merge(self, other: CardExtractDiagnostics) -> None:
        self.cards_total += other.cards_total
        self.cards_with_player += other.cards_with_player
        self.cards_without_player += other.cards_without_player
        self.yellow_cards += other.yellow_cards
        self.red_cards += other.red_cards
        self.yellow_red_cards += other.yellow_red_cards


@dataclass
class IncidentsScrapeDiagnostics:
    incidents_requested: int = 0
    incidents_success: int = 0
    incidents_failed: int = 0
    cards: CardExtractDiagnostics = field(default_factory=CardExtractDiagnostics)


def _player_id_from_incident(inc: dict) -> int | None:
    player = inc.get("player")
    if isinstance(player, dict) and player.get("id") is not None:
        try:
            return int(player["id"])
        except (TypeError, ValueError):
            return None
    raw = inc.get("playerId")
    if raw is not None:
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None
    return None


def _incident_minute(inc: dict) -> int | float | None:
    minute = inc.get("time")
    if minute is None:
        minute = inc.get("minute")
    if isinstance(minute, dict):
        minute = minute.get("minute")
    return minute


def extract_player_cards_from_incidents(
    incidents: list[dict],
) -> tuple[dict[int, dict[str, Any]], CardExtractDiagnostics]:
    """
    Agrega tarjetas de un partido por player_id.

    Valores por jugador:
      yellowCard, redCard, yellowRedCard (enteros)
      cardMinutes: [{"minute": ..., "type": "yellow"|"red"|"yellowRed"}, ...]
    """
    diag = CardExtractDiagnostics()
    by_player: dict[int, dict[str, Any]] = {}

    for inc in incidents:
        if not isinstance(inc, dict):
            continue
        if str(inc.get("incidentType") or "").lower() != "card":
            continue

        diag.cards_total += 1
        pid = _player_id_from_incident(inc)
        if pid is None:
            diag.cards_without_player += 1
            continue

        diag.cards_with_player += 1
        ic = str(inc.get("incidentClass") or "").strip()
        ic_lower = ic.lower()

        rec = by_player.setdefault(
            pid,
            {
                "yellowCard": 0,
                "redCard": 0,
                "yellowRedCard": 0,
                "cardMinutes": [],
            },
        )

        minute = _incident_minute(inc)
        card_type = ic or ic_lower or "?"

        if ic_lower == "yellow":
            rec["yellowCard"] += 1
            diag.yellow_cards += 1
        elif ic_lower == "red":
            rec["redCard"] += 1
            diag.red_cards += 1
        elif ic_lower in ("yellowred", "yellow_red", "secondyellow"):
            rec["yellowRedCard"] += 1
            rec["redCard"] += 1
            diag.yellow_red_cards += 1
            diag.red_cards += 1
            card_type = "yellowRed"
        else:
            # Clase desconocida: no inventar; registrar en cardMinutes solo
            card_type = ic or "unknown"

        rec["cardMinutes"].append({"minute": minute, "type": card_type})

    # Quitar cardMinutes vacíos y jugadores sin ningún conteo
    out: dict[int, dict[str, Any]] = {}
    for pid, rec in by_player.items():
        has_count = (
            rec["yellowCard"] > 0 or rec["redCard"] > 0 or rec["yellowRedCard"] > 0
        )
        if not has_count:
            continue
        if not rec["cardMinutes"]:
            del rec["cardMinutes"]
        out[pid] = rec

    return out, diag


def apply_cards_to_lineup_entries(
    players: list[dict],
    cards_by_player: dict[int, dict[str, Any]],
) -> int:
    """Fusiona tarjetas en statistics de cada entry. Devuelve jugadores actualizados."""
    updated = 0
    for entry in players:
        pid = (entry.get("player") or {}).get("id")
        if pid is None:
            continue
        try:
            pid_int = int(pid)
        except (TypeError, ValueError):
            continue
        card_data = cards_by_player.get(pid_int)
        if not card_data:
            continue
        stats = entry.setdefault("statistics", {})
        for key in ("yellowCard", "redCard", "yellowRedCard"):
            val = card_data.get(key)
            if val:
                stats[key] = val
        if card_data.get("cardMinutes"):
            stats["cardMinutes"] = card_data["cardMinutes"]
        updated += 1
    return updated
