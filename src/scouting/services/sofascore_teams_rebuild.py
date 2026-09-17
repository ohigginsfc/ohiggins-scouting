"""Reconstrucción de teams.json Sofascore desde events / checkpoint / player_stats.

El scraper completo genera teams.json vía get_teams() (standings API).
El pipeline incremental solo descarga eventos y no llama a get_teams, por lo que
teams.json puede faltar aunque exista checkpoint válido.

Esta utilidad reconstruye el mismo esquema que get_teams() sin Selenium.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def team_entry_from_payload(team: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(team, dict):
        return None
    tid = team.get("id")
    if tid is None:
        return None
    try:
        tid_int = int(tid)
    except (TypeError, ValueError):
        return None
    return {
        "id": tid_int,
        "name": str(team.get("name") or "").strip(),
        "slug": str(team.get("slug") or "").strip(),
        "nameCode": str(team.get("nameCode") or team.get("name_code") or "").strip(),
    }


def merge_team(teams: dict[int, dict[str, Any]], entry: dict[str, Any] | None) -> None:
    if not entry:
        return
    tid = int(entry["id"])
    prev = teams.get(tid)
    if prev is None:
        teams[tid] = {
            "id": tid,
            "name": entry.get("name") or "",
            "slug": entry.get("slug") or "",
            "nameCode": entry.get("nameCode") or "",
        }
        return
    # Completar campos vacíos sin pisar datos mejores
    for key in ("name", "slug", "nameCode"):
        if not prev.get(key) and entry.get(key):
            prev[key] = entry[key]


def teams_from_events(events: list[Any]) -> dict[int, dict[str, Any]]:
    teams: dict[int, dict[str, Any]] = {}
    if not isinstance(events, list):
        return teams
    for event in events:
        if not isinstance(event, dict):
            continue
        merge_team(teams, team_entry_from_payload(event.get("homeTeam")))
        merge_team(teams, team_entry_from_payload(event.get("awayTeam")))
    return teams


def teams_from_checkpoint(checkpoint: Any) -> dict[int, dict[str, Any]]:
    """checkpoint_raw: dict player_id → list[entries] o lista de entradas."""
    teams: dict[int, dict[str, Any]] = {}
    entries: list[Any] = []
    if isinstance(checkpoint, dict):
        for value in checkpoint.values():
            if isinstance(value, list):
                entries.extend(value)
            elif isinstance(value, dict):
                entries.append(value)
    elif isinstance(checkpoint, list):
        entries = checkpoint

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        # Formatos habituales del scraper
        for key in ("team", "teamInfo"):
            merge_team(teams, team_entry_from_payload(entry.get(key)))
        event = entry.get("event")
        if isinstance(event, dict):
            merge_team(teams, team_entry_from_payload(event.get("homeTeam")))
            merge_team(teams, team_entry_from_payload(event.get("awayTeam")))
        # A veces team_id / team_name planos
        tid = entry.get("team_id") or entry.get("teamId")
        name = entry.get("team_name") or entry.get("teamName")
        if tid is not None:
            try:
                merge_team(
                    teams,
                    {
                        "id": int(tid),
                        "name": str(name or ""),
                        "slug": str(entry.get("team_slug") or ""),
                        "nameCode": str(entry.get("team_code") or entry.get("teamCode") or ""),
                    },
                )
            except (TypeError, ValueError):
                pass
    return teams


def teams_from_player_stats(player_stats: Any) -> dict[int, dict[str, Any]]:
    teams: dict[int, dict[str, Any]] = {}
    rows: list[Any]
    if isinstance(player_stats, list):
        rows = player_stats
    elif isinstance(player_stats, dict):
        rows = list(player_stats.values()) if player_stats else []
        if rows and not isinstance(rows[0], dict):
            rows = [player_stats]
    else:
        return teams

    for row in rows:
        if not isinstance(row, dict):
            continue
        tid = row.get("team_id") or row.get("teamId")
        if tid is None and isinstance(row.get("team"), dict):
            merge_team(teams, team_entry_from_payload(row.get("team")))
            continue
        if tid is None:
            continue
        try:
            merge_team(
                teams,
                {
                    "id": int(tid),
                    "name": str(row.get("team_name") or row.get("teamName") or ""),
                    "slug": str(row.get("team_slug") or ""),
                    "nameCode": str(row.get("team_code") or row.get("teamCode") or ""),
                },
            )
        except (TypeError, ValueError):
            continue
    return teams


def _load_json(path: Path) -> Any | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def rebuild_teams_dict_from_league_dir(league_dir: Path) -> dict[int, dict[str, Any]]:
    teams: dict[int, dict[str, Any]] = {}
    events = _load_json(league_dir / "events.json")
    if events is not None:
        for tid, entry in teams_from_events(events).items():
            merge_team(teams, entry)

    checkpoint = _load_json(league_dir / "checkpoint_raw.json")
    if checkpoint is not None:
        for tid, entry in teams_from_checkpoint(checkpoint).items():
            merge_team(teams, entry)

    player_stats = _load_json(league_dir / "player_stats.json")
    if player_stats is not None:
        for tid, entry in teams_from_player_stats(player_stats).items():
            merge_team(teams, entry)

    return teams


def ensure_teams_json(
    league_dir: Path,
    *,
    overwrite: bool = False,
) -> tuple[bool, str, int]:
    """
    Asegura teams.json en league_dir.

    Returns (ok, reason, team_count).
    """
    league_dir = Path(league_dir)
    teams_path = league_dir / "teams.json"
    if teams_path.is_file() and not overwrite:
        existing = _load_json(teams_path)
        if isinstance(existing, dict) and existing:
            return True, "teams.json already present", len(existing)
        # vacío o inválido → regenerar

    teams = rebuild_teams_dict_from_league_dir(league_dir)
    if not teams:
        return (
            False,
            "No se pudo reconstruir teams.json: sin equipos en events.json, "
            "checkpoint_raw.json ni player_stats.json",
            0,
        )

    # JSON object keyed by stringified id (json.dump convierte int keys a str)
    payload = {str(tid): meta for tid, meta in sorted(teams.items(), key=lambda x: x[0])}
    teams_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return True, f"teams.json written ({len(payload)} teams)", len(payload)
