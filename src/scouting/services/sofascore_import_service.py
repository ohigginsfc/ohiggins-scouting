"""Sofascore CSV (wide) → objective_metrics (long) transformation.

Equipo en métricas: solo en raw_payload (team_name/team_id/team_code), nunca en
players.current_team. Ver docs/sofascore_objective_team_context.md.

TODO (futuro): tabla player_team_seasons (player_id, team_name, competition, season,
minutes_played, matches_played) y objective_metrics referenciando esa entidad.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd

from scouting.config.card_disciplinary_metrics import (
    CARD_DISCIPLINARY_DISPLAY_METRICS,
    CARD_STAT_SPECS,
    derive_card_metrics,
    is_card_minutes_per_metric,
)
from scouting.config.position_analysis import standardize_sofascore_position

SOURCE_NAME = "Sofascore"
PROVIDER = "sofascore"

# Columnas que nunca se importan como métrica
BLOCKLIST_COLUMNS = frozenset({
    "player_id",
    "player_name",
    "player_name_ar",
    "short_name",
    "team_id",
    "team_name",
    "team_code",
    "country",
    "country_alpha2",
    "country_alpha3",
    "date_of_birth",
    "preferred_foot",
    "position",
    "market_value_currency",
    "jersey_number",
    "dominant_match_position",
    "match_position_minutes_json",
    "match_position_counts_json",
    "card_minutes_json",
})

# Ya normalizadas o porcentajes: importar tal cual
ALREADY_NORMALIZED = frozenset({
    "avg_rating",
    "goals_per90",
    "assists_per90",
    "shots_per90",
    "pass_accuracy_pct",
    "long_ball_accuracy_pct",
    "dribble_success_pct",
    "duel_win_pct",
    "market_value",
    "yellowCard_total",
    "redCard_total",
    "yellowRedCard_total",
    "minutes_per_yellow_card",
    "minutes_per_red_card",
    "minutes_per_yellow_red_card",
    # Centros / defensa / portero (porcentajes derivados)
    "cross_accuracy_pct",
    "tackle_success_pct",
    "keeper_sweeper_accuracy_pct",
    "penalty_save_pct",
    # Value model (promedio) y máximo de conducción
    "avg_shotValueNormalized",
    "bestBallCarryProgression_max",
})

# Totales / metadatos de temporada: mantener absolutos
ABSOLUTE_KEEP = frozenset({
    "minutesPlayed",
    "matches_played",
})

# Acumuladas → convertir a per90 (nombre métrica: {col}_per90)
# Si el CSV ya trae la columna *_per90 del scraper, no recalcular desde el total.
PER90_SKIP_IF_COLUMN_PRESENT = {
    "goals": "goals_per90",
    "goalAssist": "assists_per90",
    "totalShots": "shots_per90",
}

# CSV del scraper usa nombres canónicos; aliases por si hay columnas legacy.
STAT_COLUMN_ALIASES: dict[str, str] = {
    "foulsCommitted": "foulsCommited",
    "fouls": "foulsCommited",
    "bigChanceCreated": "totalChanceCreated",
    "totalContest": "totalDribbles",
    "wonContest": "successfulDribble",
}

PER90_CONVERT = frozenset({
    "goals",
    "goalAssist",
    "totalShots",
    "totalPass",
    "accuratePass",
    "totalLongBalls",
    "accurateLongBalls",
    "keyPass",
    "totalChanceCreated",
    "totalTackle",
    "interceptionWon",
    "totalClearance",
    "duelWon",
    "duelLost",
    "aerialWon",
    "aerialLost",
    "ballRecovery",
    "touches",
    "possessionLostCtrl",
    "totalDribbles",
    "successfulDribble",
    "foulsCommited",
    "wasFouled",
    "totalOffside",
    "yellowCard",
    "redCard",
    "yellowRedCard",
    "saves",
    "goodHighClaim",
    "savedShotsFromInsideTheBox",
    "savedShotsFromOutsideTheBox",
    "goalsPrevented",
    "totalBallCarriesDistance",
    "totalProgression",
    "passValueNormalized",
    "dribbleValueNormalized",
    "defensiveValueNormalized",
    "goalkeeperValueNormalized",
    # Expected goals / assists
    "expectedGoals",
    "expectedAssists",
    "expectedGoalsOnTarget",
    # Ataque / eventos
    "bigChanceMissed",
    "hitWoodwork",
    "penaltyWon",
    "penaltyMiss",
    "ownGoals",
    # Centros / bandas
    "totalCross",
    "accurateCross",
    "crossNotClaimed",
    # Defensa avanzada
    "wonTackle",
    "challengeLost",
    "outfielderBlock",
    "clearanceOffLine",
    "lastManTackle",
    "penaltyConceded",
    "errorLeadToAShot",
    "errorLeadToAGoal",
    # Control / pérdidas
    "dispossessed",
    "unsuccessfulTouch",
    # Portero / penaltis
    "penaltySave",
    "penaltyFaced",
    "totalKeeperSweeper",
    "accurateKeeperSweeper",
    # Conducción progresiva
    "totalProgressiveBallCarriesDistance",
})

FOOT_MAP = {
    "left": "Izquierdo",
    "right": "Derecho",
    "both": "Ambos",
}


def sofascore_raw_position(position: Any) -> str | None:
    """Código crudo G/D/M/F tal como viene del CSV (sin mapeo táctico)."""
    if position is None or (isinstance(position, float) and pd.isna(position)):
        return None
    key = str(position).strip().upper()
    if key in ("G", "D", "M", "F"):
        return key
    return None


def map_sofascore_foot(preferred_foot: Any) -> str | None:
    if preferred_foot is None or (isinstance(preferred_foot, float) and pd.isna(preferred_foot)):
        return "Desconocido"
    key = str(preferred_foot).strip().lower()
    if not key:
        return "Desconocido"
    return FOOT_MAP.get(key, "Desconocido")


def infer_metric_unit(metric_name: str) -> str:
    if metric_name == "avg_rating":
        return "rating"
    if metric_name == "market_value":
        return "eur"
    if is_card_minutes_per_metric(metric_name):
        return "minutes"
    if metric_name.endswith("_per90"):
        return "per90"
    if metric_name.endswith("_pct"):
        return "pct"
    if metric_name.endswith("_total"):
        return "count"
    if "per90" in metric_name:
        return "per90"
    return "count"


def normalize_stat_column(column_name: str) -> str:
    return STAT_COLUMN_ALIASES.get(column_name, column_name)


def should_import_metric(column_name: str) -> bool:
    column_name = normalize_stat_column(column_name)
    if column_name.endswith("_present_count") or column_name.endswith("_source_keys"):
        return False
    if column_name in BLOCKLIST_COLUMNS:
        return False
    if column_name in ALREADY_NORMALIZED or column_name in ABSOLUTE_KEEP:
        return True
    if column_name in CARD_DISCIPLINARY_DISPLAY_METRICS:
        return True
    if column_name in PER90_CONVERT:
        return True
    return False


def should_convert_to_per90(column_name: str) -> bool:
    return normalize_stat_column(column_name) in PER90_CONVERT


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        if isinstance(value, str) and not value.strip():
            return None
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _parse_birth_date(value: Any) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def build_player_profile_updates(row: pd.Series) -> dict[str, Any]:
    """
    Campos para merge en players (solo rellenar vacíos) al importar Sofascore.

    No escribe posición scouting ni current_team: la ficha subjetiva y el club
    manual vienen de informes/loaders. El equipo del CSV va solo en raw_payload.
    """
    return {
        "full_name": str(row.get("player_name") or "").strip() or None,
        "birth_date": _parse_birth_date(row.get("date_of_birth")),
        "nationality": _cell_str(row.get("country")),
        "height_cm": _to_decimal(row.get("height")),
        "preferred_foot": map_sofascore_foot(row.get("preferred_foot")),
    }


def _cell_str(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    return s or None


def _snapshot_raw_row(row: pd.Series) -> dict[str, Any]:
    """Copia ligera de la fila CSV para resolver equipo/posición tras import."""
    keys = (
        "player_id",
        "player_name",
        "position",
        "team_id",
        "team_name",
        "team_code",
        "country",
        "minutesPlayed",
        "matches_played",
    )
    out: dict[str, Any] = {}
    for key in keys:
        val = row.get(key) if key in row.index else None
        if val is None or (isinstance(val, float) and pd.isna(val)):
            continue
        if key in ("player_id", "team_id"):
            try:
                out[key] = str(int(val)) if isinstance(val, (int, float)) else str(val).strip()
            except (TypeError, ValueError):
                out[key] = str(val).strip()
        else:
            out[key] = str(val).strip() if not isinstance(val, (int, float)) else val
    return out


def _resolve_team_fields(row: pd.Series, teams_lookup: dict[str, str] | None) -> dict[str, str | None]:
    team_id = _cell_str(row.get("team_id"))
    team_name = _cell_str(row.get("team_name"))
    team_code = _cell_str(row.get("team_code"))
    if (not team_name) and team_id and teams_lookup:
        team_name = teams_lookup.get(str(team_id)) or teams_lookup.get(team_id)
    return {
        "team_id": team_id,
        "team_name": team_name,
        "team_code": team_code,
    }


def load_teams_lookup(csv_path: Any) -> dict[str, str]:
    """team_id → name desde teams.json junto al CSV."""
    import json
    from pathlib import Path

    path = Path(csv_path)
    teams_file = path.parent / "teams.json"
    if not teams_file.is_file():
        return {}
    try:
        data = json.loads(teams_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[str, str] = {}
    if isinstance(data, dict):
        for tid, meta in data.items():
            if isinstance(meta, dict) and meta.get("name"):
                out[str(tid)] = str(meta["name"]).strip()
    return out


def _stat_diagnostic_fields(row: pd.Series, source_column: str) -> dict[str, Any]:
    """Present count y claves API usadas (scraper post-alias)."""
    extra: dict[str, Any] = {}
    pc_col = f"{source_column}_present_count"
    if pc_col in row.index:
        pc = row.get(pc_col)
        if pc is not None and not (isinstance(pc, float) and pd.isna(pc)):
            try:
                extra["source_present_count"] = int(pc)
            except (TypeError, ValueError):
                pass
    sk_col = f"{source_column}_source_keys"
    if sk_col in row.index:
        sk = row.get(sk_col)
        if sk is not None and not (isinstance(sk, float) and pd.isna(sk)):
            extra["source_raw_keys"] = str(sk).strip()
    return extra


def _match_position_payload_fields(row: pd.Series) -> dict[str, Any]:
    """Posición objetiva desde partidos agregados (no solo position de ficha)."""
    out: dict[str, Any] = {}
    dom = row.get("dominant_match_position")
    if dom is not None and not (isinstance(dom, float) and pd.isna(dom)):
        code = str(dom).strip().upper()
        if code in ("G", "D", "M", "F"):
            out["dominant_match_position"] = code
            out["sofascore_position"] = code
            group = standardize_sofascore_position(code)
            if group:
                out["objective_position_group"] = group
    for col, key in (
        ("match_position_minutes_json", "match_position_minutes"),
        ("match_position_counts_json", "match_position_counts"),
    ):
        if col not in row.index:
            continue
        raw = row.get(col)
        if raw is None or (isinstance(raw, float) and pd.isna(raw)):
            continue
        try:
            parsed = json.loads(str(raw))
            if isinstance(parsed, dict):
                out[key] = parsed
        except json.JSONDecodeError:
            continue
    return out


def _skip_stat_without_scraper_presence(row: pd.Series, source_column: str, diag: dict[str, Any]) -> bool:
    """
    CSV nuevo: omitir si el scraper marcó present_count=0 (campo ausente en API).
    CSV legacy sin columnas *_present_count: no filtrar aquí.
    """
    pc_col = f"{source_column}_present_count"
    if pc_col not in row.index:
        return False
    return int(diag.get("source_present_count") or 0) <= 0


def _base_raw_payload(
    row: pd.Series,
    source_column: str,
    *,
    season: str,
    competition: str,
    teams_lookup: dict[str, str] | None = None,
) -> dict[str, Any]:
    teams = _resolve_team_fields(row, teams_lookup)
    match_pos = _match_position_payload_fields(row)
    profile_pos = sofascore_raw_position(row.get("position")) or _cell_str(row.get("position"))
    raw_pos = match_pos.get("sofascore_position") or profile_pos
    obj_group = match_pos.get("objective_position_group") or standardize_sofascore_position(raw_pos)
    payload: dict[str, Any] = {
        "sofascore_player_id": _cell_str(row.get("player_id")),
        "original_position": raw_pos,
        "sofascore_position": raw_pos,
        "objective_position_group": obj_group,
        "profile_sofascore_position": profile_pos,
        "team_id": teams["team_id"],
        "team_name": teams["team_name"],
        "team_code": teams["team_code"],
        "season": season,
        "competition": competition,
        "source_column": source_column,
        "raw_row": _snapshot_raw_row(row),
    }
    name_ar = row.get("player_name_ar")
    if name_ar is not None and not (isinstance(name_ar, float) and pd.isna(name_ar)):
        payload["player_name_ar"] = str(name_ar)
    payload.update(match_pos)
    return payload


def convert_row_to_metrics(
    row: pd.Series,
    *,
    season: str,
    competition: str,
    teams_lookup: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Convierte una fila del CSV ancho en filas objective_metrics."""
    minutes = _to_decimal(row.get("minutesPlayed"))
    minutes_f = float(minutes) if minutes is not None else 0.0
    out: list[dict[str, Any]] = []

    for col in row.index:
        col_name = normalize_stat_column(str(col))
        if not should_import_metric(col_name):
            continue

        raw_val = row[col]
        if raw_val is None or (isinstance(raw_val, float) and pd.isna(raw_val)):
            continue

        base_payload = _base_raw_payload(
            row,
            col_name,
            season=season,
            competition=competition,
            teams_lookup=teams_lookup,
        )

        if should_convert_to_per90(col_name):
            diag = _stat_diagnostic_fields(row, col_name)
            if _skip_stat_without_scraper_presence(row, col_name, diag):
                continue
            skip_col = PER90_SKIP_IF_COLUMN_PRESENT.get(col_name)
            if skip_col and skip_col in row.index:
                existing = row.get(skip_col)
                if existing is not None and not (
                    isinstance(existing, float) and pd.isna(existing)
                ):
                    continue
            total = _to_decimal(raw_val)
            if total is None:
                continue
            if minutes_f <= 0:
                continue
            per90 = (float(total) / minutes_f) * 90.0
            metric_name = f"{col_name}_per90"
            out.append({
                "source_name": SOURCE_NAME,
                "season": season,
                "competition": competition,
                "metric_name": metric_name,
                "metric_value": round(per90, 4),
                "metric_unit": "per90",
                "raw_payload": {
                    **base_payload,
                    **diag,
                    "absolute_total": float(total),
                    "minutes_played": minutes_f,
                },
            })
            continue

        if col_name in ALREADY_NORMALIZED or col_name in ABSOLUTE_KEEP:
            diag = _stat_diagnostic_fields(row, col_name)
            if _skip_stat_without_scraper_presence(row, col_name, diag):
                continue
            val = _to_decimal(raw_val)
            if val is None and col_name not in ("avg_rating",):
                continue
            if col_name == "avg_rating":
                val = _to_decimal(raw_val)
                if val is None:
                    continue
            normalized_payload = {**base_payload, **diag}
            if minutes_f > 0:
                normalized_payload["minutes_played"] = minutes_f
            if val is not None:
                try:
                    normalized_payload["absolute_total"] = float(val)
                except (TypeError, ValueError):
                    pass
            out.append({
                "source_name": SOURCE_NAME,
                "season": season,
                "competition": competition,
                "metric_name": col_name,
                "metric_value": val,
                "metric_unit": infer_metric_unit(col_name),
                "raw_payload": normalized_payload,
            })

    out.extend(
        _card_disciplinary_metrics_from_row(
            row,
            minutes_f=minutes_f,
            season=season,
            competition=competition,
            teams_lookup=teams_lookup,
            existing_names={str(m["metric_name"]) for m in out},
        )
    )

    return out


def _card_disciplinary_metrics_from_row(
    row: pd.Series,
    *,
    minutes_f: float,
    season: str,
    competition: str,
    teams_lookup: dict[str, str] | None,
    existing_names: set[str],
) -> list[dict[str, Any]]:
    """Totales y minutos/tarjeta (métricas principales de disciplina)."""
    def _f(col: str) -> float | None:
        d = _to_decimal(row.get(col))
        return float(d) if d is not None else None

    derived = derive_card_metrics(
        yellow_card=_f("yellowCard"),
        red_card=_f("redCard"),
        yellow_red_card=_f("yellowRedCard"),
        minutes_played=minutes_f,
    )
    if not derived:
        return []

    out: list[dict[str, Any]] = []
    for base, total_name, mins_name in CARD_STAT_SPECS:
        if total_name not in derived:
            continue
        diag = _stat_diagnostic_fields(row, base)
        if _skip_stat_without_scraper_presence(row, base, diag):
            continue
        base_payload = _base_raw_payload(
            row,
            total_name,
            season=season,
            competition=competition,
            teams_lookup=teams_lookup,
        )
        total_val = derived[total_name]
        if total_name not in existing_names:
            out.append({
                "source_name": SOURCE_NAME,
                "season": season,
                "competition": competition,
                "metric_name": total_name,
                "metric_value": round(float(total_val), 4),
                "metric_unit": "count",
                "raw_payload": {
                    **base_payload,
                    **diag,
                    "absolute_total": float(total_val),
                    "minutes_played": minutes_f,
                    "source_column": base,
                },
            })
            existing_names.add(total_name)
        if mins_name in derived and minutes_f > 0 and mins_name not in existing_names:
            out.append({
                "source_name": SOURCE_NAME,
                "season": season,
                "competition": competition,
                "metric_name": mins_name,
                "metric_value": derived[mins_name],
                "metric_unit": "minutes",
                "raw_payload": {
                    **base_payload,
                    **diag,
                    "absolute_total": float(total_val),
                    "minutes_played": minutes_f,
                    "source_column": base,
                },
            })
            existing_names.add(mins_name)
    return out
