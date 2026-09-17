"""Objective metrics business operations."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd
from psycopg import Connection

from scouting.config import (
    metric_comparison_profiles,
    metric_direction,
    metric_labels,
    metric_profiles,
)
from scouting.config.sofascore_seasons import get_active_season
from scouting.config.position_analysis import (
    position_label_from_payload,
    standardize_position_for_analysis,
    standardize_sofascore_position,
)
from scouting.repositories import metrics_repository, players_repository
from scouting.services.players_service import calculate_age

# Metadatos de fila (no son métricas pivotables en análisis)
WIDE_INDEX_COLS = (
    "player_id",
    "player_name",
    "position",
    "position_standardized",
    "standard_position",
    "objective_team",
    "nationality",
    "preferred_foot",
    "birth_date",
    "age",
    "season",
    "season_label",
    "competition",
    "reports_count",
    "has_subjective_report",
    "source_name",
)

# Índice del pivot (sin birth_date: NaT en el índice colapsa el pivot a 0–1 filas en pandas)
PIVOT_INDEX_COLS: tuple[str, ...] = (
    "player_id",
    "player_name",
    "position",
    "position_standardized",
    "objective_team",
    "nationality",
    "preferred_foot",
    "season",
    "competition",
    "reports_count",
    "has_subjective_report",
)

PLAYER_TYPE_OPTIONS: dict[str, str] = {
    metrics_repository.PLAYER_TYPE_ALL: "Todos con datos objetivos",
    metrics_repository.PLAYER_TYPE_HYBRID: "Solo híbridos (informe + métricas)",
    metrics_repository.PLAYER_TYPE_OBJECTIVE_ONLY: "Solo sin informe",
    metrics_repository.PLAYER_TYPE_WITH_REPORT: "Solo con informe subjetivo",
}

# No ofrecer en selectores principales (IDs, texto, raw)
METRIC_SELECT_BLOCKLIST = frozenset({
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
})

METRIC_SELECT_BLOCKLIST_PATTERNS = (
    re.compile(r"^raw_", re.I),
    re.compile(r"_id$", re.I),
    re.compile(r"(name|code|date|country|currency|payload)$", re.I),
)

FALLBACK_RANKING_METRIC = metric_profiles.FALLBACK_RANKING_METRIC

COMPARE_BASE_METRICS: tuple[str, ...] = (
    "minutesPlayed",
    "matches_played",
    "avg_rating",
    "market_value",
)

NULL_RATIO_HIDE_THRESHOLD = 0.95


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        if isinstance(value, str) and not value.strip():
            return None
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def create_objective_metric_from_dict(conn: Connection, data: dict[str, Any]) -> tuple[int, bool]:
    """
    Resolve or create the player, insert an objective metric.

    Returns (metric_id, player_created).

    Expected keys include: player_name, source_name, metric_name (and optional season, competition, etc.).
    """
    player_name = data.get("player_name")
    if not player_name or not str(player_name).strip():
        raise ValueError("player_name is required")

    source_name = data.get("source_name")
    if not source_name or not str(source_name).strip():
        raise ValueError("source_name is required")

    metric_name = data.get("metric_name")
    if not metric_name or not str(metric_name).strip():
        raise ValueError("metric_name is required")

    player_id, player_created = players_repository.get_or_create_player(
        conn,
        full_name=str(player_name).strip(),
        nationality=data.get("nationality"),
        position=data.get("position"),
        current_team=data.get("current_team"),
    )

    metric_id = metrics_repository.create_metric(
        conn,
        player_id=player_id,
        source_name=str(source_name).strip(),
        season=data.get("season"),
        competition=data.get("competition"),
        metric_name=str(metric_name).strip(),
        metric_value=_to_decimal(data.get("metric_value")),
        metric_unit=data.get("metric_unit"),
        raw_payload=data.get("raw_payload"),
    )
    return metric_id, player_created


def count_metrics(
    conn: Connection,
    *,
    include_historical: bool = False,
    source_type: str | None = "sofascore",
) -> int:
    """
    Por defecto cuenta solo métricas Sofascore reales (no demo).

    Usa source_type=None para el total sin filtrar origen.
    """
    season = None if include_historical else get_active_season()
    return metrics_repository.count_metrics(conn, season=season, source_type=source_type)


def count_demo_metrics(conn: Connection, *, include_historical: bool = False) -> int:
    season = None if include_historical else get_active_season()
    return metrics_repository.count_metrics(conn, season=season, source_type="demo")


def count_metrics_by_player(
    conn: Connection,
    player_id: int,
    *,
    include_historical: bool = False,
) -> int:
    season = None if include_historical else get_active_season()
    return metrics_repository.count_metrics_by_player(conn, player_id, season=season)


def get_sources_by_player(conn: Connection, player_id: int) -> list[str]:
    return metrics_repository.get_sources_by_player(conn, player_id)


def get_metrics_summary_by_player(conn: Connection, player_id: int) -> list[dict[str, Any]]:
    return metrics_repository.get_metrics_summary_by_player(conn, player_id)


def get_metrics_by_player_grouped(
    conn: Connection,
    player_id: int,
    *,
    include_historical: bool = False,
) -> list[dict[str, Any]]:
    season = None if include_historical else get_active_season()
    return metrics_repository.get_metrics_by_player_grouped(conn, player_id, season=season)


def list_metrics_with_players(
    conn: Connection,
    *,
    source_name: str | None = None,
    season: str | None = None,
    competition: str | None = None,
    position: str | None = None,
    current_team: str | None = None,
    metric_name: str | None = None,
    player_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    return metrics_repository.get_all_metrics_with_players(
        conn,
        source_name=source_name,
        season=season,
        competition=competition,
        position=position,
        current_team=current_team,
        metric_name=metric_name,
        player_ids=player_ids,
    )


def get_metric_explorer_filters(conn: Connection) -> dict[str, list[Any]]:
    return metrics_repository.get_available_metric_filters(conn)


# --- Vista simple «Datos objetivos» (sin pivot / radar / ranking) ---

SOFASCORE_SOURCE = "Sofascore"

COMPARABLE_POSITION_METRICS: tuple[str, ...] = (
    "avg_rating",
    "goals_per90",
    "assists_per90",
    "goalAssist_per90",
    "shots_per90",
    "totalPass_per90",
    "keyPass_per90",
    "pass_accuracy_pct",
    "totalTackle_per90",
    "interceptionWon_per90",
    "duelWon_per90",
    "aerialWon_per90",
    "ballRecovery_per90",
    "successfulDribble_per90",
    "dribble_success_pct",
    "saves_per90",
)


def objective_source_name(source_name: str | None = None) -> str:
    if source_name is None or not str(source_name).strip():
        return SOFASCORE_SOURCE
    return str(source_name).strip()


def season_filter_labels(seasons_raw: list[str]) -> tuple[list[str], dict[str, str]]:
    """Etiquetas para UI y mapa etiqueta → season crudo en BD."""
    label_to_raw: dict[str, str] = {}
    for s in seasons_raw:
        label_to_raw[metric_labels.format_season_label(s)] = s
    return list(label_to_raw.keys()), label_to_raw


def get_objective_data_filter_options(
    conn: Connection,
    *,
    include_historical: bool = False,
) -> dict[str, list[Any]]:
    season = None if include_historical else get_active_season()
    return metrics_repository.get_objective_data_filter_options(
        conn, source_name=SOFASCORE_SOURCE, season=season
    )


def get_objective_players_summary(
    conn: Connection,
    *,
    source_name: str | None = None,
    season: str | None = None,
    competition: str | None = None,
    position: str | None = None,
    team: str | None = None,
    search_text: str | None = None,
    include_historical: bool = False,
    prefer_real: bool = True,
    source_type: str | None = None,
) -> list[dict[str, Any]]:
    if not include_historical and season is None:
        season = get_active_season()
    rows = metrics_repository.get_objective_players_summary(
        conn,
        source_name=objective_source_name(source_name),
        season=season,
        competition=competition,
        position=position,
        team=team,
        search_text=search_text,
        prefer_real=prefer_real,
        source_type=source_type,
    )
    for row in rows:
        code = row.get("sofascore_position_code")
        group = row.get("objective_position_group")
        if group and str(group).strip():
            row["objective_position_group"] = str(group).strip()
        else:
            row["objective_position_group"] = standardize_sofascore_position(
                str(code) if code else None
            )
        row["sofascore_position_code"] = (
            str(code).strip().upper() if code and str(code).strip() else None
        )
        row["sofascore_position_raw"] = row["sofascore_position_code"]
        row["position"] = row.get("scouting_position")
        team = row.get("objective_team")
        if team is None or not str(team).strip():
            row["objective_team"] = "—"
    return rows


def get_objective_metrics_for_player_block(
    conn: Connection,
    player_id: int,
    season: str | None,
    competition: str | None,
    *,
    source_name: str | None = None,
) -> list[dict[str, Any]]:
    return metrics_repository.get_objective_metrics_for_player_block(
        conn,
        player_id,
        season,
        competition,
        source_name=objective_source_name(source_name),
    )


def _metric_names_available_in_block(
    metrics_rows: list[dict[str, Any]],
) -> set[str]:
    return {
        str(r.get("metric_name") or "").strip()
        for r in metrics_rows
        if r.get("metric_name")
    }


def objective_comparison_metrics_for_player(
    metrics_rows: list[dict[str, Any]],
    *,
    position_group: str | None = None,
) -> list[str]:
    """Métricas comparables según grupo objetivo Sofascore (perfil por posición)."""
    if position_group is None:
        position_group, _ = resolve_objective_comparison_position(metrics_rows)
    return metric_comparison_profiles.get_objective_comparison_metrics_for_group(
        position_group,
        _metric_names_available_in_block(metrics_rows),
    )


def comparable_metrics_for_player(
    metrics_rows: list[dict[str, Any]],
    metric_names: list[str] | None = None,
    *,
    position_group: str | None = None,
) -> list[str]:
    """Métricas comparables presentes en el bloque del jugador."""
    if metric_names is None:
        return objective_comparison_metrics_for_player(
            metrics_rows,
            position_group=position_group,
        )
    available = _metric_names_available_in_block(metrics_rows)
    out: list[str] = []
    seen: set[str] = set()
    for name in metric_names:
        if name in available and name not in seen:
            out.append(name)
            seen.add(name)
        elif (
            name == "assists_per90"
            and "goalAssist_per90" in available
            and "goalAssist_per90" not in seen
        ):
            out.append("goalAssist_per90")
            seen.add("goalAssist_per90")
    return out


def resolve_objective_comparison_position_from_match_entries(
    metrics_rows: list[dict[str, Any]],
) -> tuple[str | None, str | None, dict[str, Any]]:
    """
    Grupo objetivo desde posición real por partido (raw_payload), no ficha global.
    Usa match_position_minutes / dominant_match_position del scraper.
    """
    meta: dict[str, Any] = {}
    for row in metrics_rows:
        payload = row.get("raw_payload")
        if not isinstance(payload, dict):
            continue
        mins = payload.get("match_position_minutes")
        counts = payload.get("match_position_counts")
        if isinstance(mins, dict) and mins:
            meta["match_position_minutes"] = {
                str(k): float(v) for k, v in mins.items()
            }
            if isinstance(counts, dict):
                meta["match_position_counts"] = {
                    str(k): int(v) for k, v in counts.items()
                }
            dom_code = max(
                mins.items(),
                key=lambda kv: float(kv[1] or 0),
            )[0]
            meta["dominant_match_position"] = str(dom_code)
            group = standardize_sofascore_position(dom_code)
            return group, str(dom_code), meta
        dom = payload.get("dominant_match_position")
        if dom is not None and str(dom).strip():
            code = str(dom).strip().upper()
            meta["dominant_match_position"] = code
            group = standardize_sofascore_position(code)
            return group, code, meta
    return None, None, meta


def resolve_objective_comparison_position(
    metrics_rows: list[dict[str, Any]],
    *,
    player_position: str | None = None,
    report_position: str | None = None,
    source_name: str | None = None,
) -> tuple[str | None, str | None]:
    """
    Devuelve (grupo_objetivo, código_crudo_G/D/M/F).
    Prioriza posición por partidos; nunca usa posición scouting del informe.
    """
    _ = (player_position, report_position, source_name)
    group, raw_pos, _meta = resolve_objective_comparison_position_from_match_entries(
        metrics_rows
    )
    if group:
        return group, raw_pos
    for row in metrics_rows:
        payload = row.get("raw_payload")
        if isinstance(payload, dict):
            raw_pos = position_label_from_payload(payload)
            if raw_pos:
                break
    else:
        raw_pos = None
    return standardize_sofascore_position(raw_pos), raw_pos


def get_player_vs_position_average(
    conn: Connection,
    player_id: int,
    season: str | None,
    competition: str | None,
    metrics_rows: list[dict[str, Any]] | None = None,
    *,
    player_position: str | None = None,
    report_position: str | None = None,
    metric_names: list[str] | None = None,
    scope: str = "same_competition",
    source_name: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Comparativa vs media de posición objetiva.
    Returns (comparison_rows, diagnostics).
    """
    src = objective_source_name(source_name)
    if metrics_rows is None:
        metrics_rows = get_objective_metrics_for_player_block(
            conn, player_id, season, competition, source_name=src
        )
    position_group, raw_position = resolve_objective_comparison_position(
        metrics_rows,
        source_name=src,
    )
    diag: dict[str, Any] = {
        "position_group": position_group,
        "raw_position": raw_position,
        "season": season,
        "competition": competition,
        "scope": scope,
        "cohort_peers": 0,
    }
    if not position_group:
        return [], diag
    if metric_names is None:
        metric_names = objective_comparison_metrics_for_player(
            metrics_rows,
            position_group=position_group,
        )
    if not metric_names:
        return [], diag

    rows, cohort_peers = metrics_repository.get_player_vs_position_average(
        conn,
        player_id,
        season,
        competition,
        position_group,
        metric_names,
        scope,
        source_name=src,
    )
    diag["cohort_peers"] = cohort_peers
    return rows, diag


def get_player_position_percentile_rows(
    conn: Connection,
    player_id: int,
    season: str | None,
    competition: str | None,
    metrics_rows: list[dict[str, Any]] | None = None,
    *,
    metric_names: list[str] | None = None,
    source_name: str | None = None,
    peer_competitions: list[str] | None = None,
    cohort_seasons: list[str] | None = None,
    cohort_context: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Percentiles vs cohorte (posición/temporada; liga única o ligas combinadas).
    Returns (percentile_rows, diagnostics).
    """
    src = objective_source_name(source_name)
    if metrics_rows is None:
        metrics_rows = get_objective_metrics_for_player_block(
            conn, player_id, season, competition, source_name=src
        )
    position_group, raw_position = resolve_objective_comparison_position(
        metrics_rows,
        source_name=src,
    )
    ctx = cohort_context or {}
    diag: dict[str, Any] = {
        "position_group": position_group,
        "raw_position": raw_position,
        "season": season,
        "competition": competition,
        "cohort_peers": 0,
        "cohort_type": ctx.get("cohort_type"),
        "cohort_competitions": ctx.get("competitions")
        or ctx.get("peer_competitions")
        or ([competition] if competition else []),
        "cohort_seasons": ctx.get("cohort_seasons") or cohort_seasons,
        "cohort_ui_message": ctx.get("ui_message"),
    }
    if not position_group:
        return [], diag
    if metric_names is None:
        metric_names = objective_comparison_metrics_for_player(
            metrics_rows,
            position_group=position_group,
        )
    if not metric_names:
        return [], diag

    peer_pool = peer_competitions if peer_competitions else None
    season_pool = cohort_seasons or ctx.get("cohort_seasons")
    if ctx.get("use_shared_peer_pool") and ctx.get("cohort_seasons"):
        season_pool = ctx.get("cohort_seasons")
    if ctx.get("use_shared_peer_pool") and ctx.get("peer_competitions"):
        peer_pool = ctx.get("peer_competitions")
    rows, cohort_peers = metrics_repository.get_player_vs_position_percentiles(
        conn,
        player_id,
        season,
        competition,
        position_group,
        metric_names,
        source_name=src,
        peer_competitions=peer_pool,
        cohort_seasons=season_pool,
    )
    metric_direction.enrich_percentile_rows(rows)
    diag["cohort_peers"] = cohort_peers
    return rows, diag


def get_position_group_percentile_averages(
    conn: Connection,
    player_id: int,
    season: str | None,
    competition: str | None,
    metrics_rows: list[dict[str, Any]] | None = None,
    *,
    metric_names: list[str] | None = None,
    source_name: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Media de percentiles de rendimiento por métrica vs cohorte
    (misma posición, competición y temporada).
    """
    src = objective_source_name(source_name)
    if metrics_rows is None:
        metrics_rows = get_objective_metrics_for_player_block(
            conn, player_id, season, competition, source_name=src
        )
    position_group, raw_position = resolve_objective_comparison_position(
        metrics_rows,
        source_name=src,
    )
    diag: dict[str, Any] = {
        "position_group": position_group,
        "raw_position": raw_position,
        "season": season,
        "competition": competition,
        "cohort_peers": 0,
    }
    if not position_group:
        return [], diag
    if metric_names is None:
        metric_names = objective_comparison_metrics_for_player(
            metrics_rows,
            position_group=position_group,
        )
    if not metric_names:
        return [], diag

    rows, cohort_peers = metrics_repository.get_position_group_percentile_averages(
        conn,
        player_id,
        season,
        competition,
        position_group,
        metric_names,
        source_name=src,
    )
    diag["cohort_peers"] = cohort_peers
    return rows, diag


def get_comparison_percentile_rows_for_player(
    conn: Connection,
    player_id: int,
    season: str | None,
    competition: str | None,
    metrics_rows: list[dict[str, Any]],
    metric_names: list[str],
    cohort_resolution: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Percentiles de un jugador según resolución de cohorte de comparación."""
    peer_pool: list[str] | None = None
    season_pool: list[str] | None = None
    if cohort_resolution.get("use_shared_peer_pool"):
        peer_pool = cohort_resolution.get("peer_competitions")
        season_pool = cohort_resolution.get("cohort_seasons")
    return get_player_position_percentile_rows(
        conn,
        player_id,
        season,
        competition,
        metrics_rows=metrics_rows,
        metric_names=metric_names,
        peer_competitions=peer_pool,
        cohort_seasons=season_pool,
        cohort_context=cohort_resolution,
    )


def comparable_metric_names_from_block(metrics_rows: list[dict[str, Any]]) -> list[str]:
    """Nombres crudos de métricas comparables presentes en el bloque (sin ocultas)."""
    out: list[str] = []
    seen: set[str] = set()
    for r in metrics_rows:
        name = str(r.get("metric_name") or "").strip()
        if not name or name in seen or is_hidden_metric_name(name):
            continue
        if metric_labels.is_chart_excluded_metric(name, r.get("metric_unit")):
            continue
        out.append(name)
        seen.add(name)
    out.sort(key=metric_labels.metric_sort_key)
    return out


def block_metric_names_for_ui(metrics_rows: list[dict[str, Any]]) -> list[str]:
    """Métricas visibles del bloque con valor numérico (selector UI / tablas)."""
    out: list[str] = []
    seen: set[str] = set()
    for r in metrics_rows:
        name = str(r.get("metric_name") or "").strip()
        if not name or name in seen or is_hidden_metric_name(name):
            continue
        if r.get("metric_value") is None:
            continue
        out.append(name)
        seen.add(name)
    out.sort(key=metric_labels.metric_sort_key)
    return out


ADVANCED_PROFILE_METRICS: frozenset[str] = frozenset({
    "expectedGoals_per90",
    "expectedAssists_per90",
    "expectedGoalsOnTarget_per90",
    "totalCross_per90",
    "accurateCross_per90",
    "cross_accuracy_pct",
    "wonTackle_per90",
    "tackle_success_pct",
    "penaltySave_per90",
    "penalty_save_pct",
    "totalKeeperSweeper_per90",
})


def build_player_objective_scouting_table_rows(
    conn: Connection,
    player_id: int,
    season: str | None,
    competition: str | None,
    metrics_rows: list[dict[str, Any]],
    *,
    priority_metric_names: set[str] | None = None,
    position_group: str | None = None,
) -> list[dict[str, Any]]:
    """Tabla completa del bloque con percentil, ranking y media de posición."""
    priority = priority_metric_names or set()
    visible = [
        r
        for r in metrics_rows
        if not is_hidden_metric_name(str(r.get("metric_name") or ""))
        and r.get("metric_value") is not None
    ]
    if not visible:
        return []

    all_names = block_metric_names_for_ui(metrics_rows)
    percentile_rows, _ = get_player_position_percentile_rows(
        conn,
        player_id,
        season,
        competition,
        metrics_rows=metrics_rows,
        metric_names=all_names,
    )
    pct_by_name = {str(r["metric_name"]): r for r in percentile_rows}

    avg_rows, _ = get_player_vs_position_average(
        conn,
        player_id,
        season,
        competition,
        metrics_rows=metrics_rows,
        metric_names=all_names,
        scope="same_competition",
    )
    avg_by_name = {str(r["metric_name"]): r for r in avg_rows}

    group_order = {g: i for i, g in enumerate(metric_labels.METRIC_GROUP_ORDER)}

    out: list[dict[str, Any]] = []
    for r in visible:
        mname = str(r.get("metric_name") or "")
        unit = r.get("metric_unit")
        grp = metric_labels.metric_group(mname)
        pct_row = pct_by_name.get(mname)
        avg_row = avg_by_name.get(mname)

        pct_disp = "—"
        rank_disp = "—"
        pct_num: int | None = None
        if pct_row and pct_row.get("percentile") is not None:
            pct_num = int(round(float(pct_row["percentile"])))
            pct_disp = f"P{pct_num}"
            cohort_n = int(pct_row.get("players_count") or 0)
            rank_n = int(pct_row.get("cohort_rank") or 0)
            if cohort_n > 0 and rank_n > 0:
                rank_disp = f"{rank_n} / {cohort_n}"

        avg_disp = "—"
        if avg_row and avg_row.get("position_avg_value") is not None:
            avg_disp = metric_labels.format_metric_value(
                avg_row["position_avg_value"],
                unit,
                metric_name=mname,
            )

        interpretation = "—"
        if pct_row and pct_row.get("percentile") is not None:
            if metric_labels.is_zero_centered_normalized_metric(mname):
                interpretation = metric_labels.interpret_normalized_metric(
                    float(r["metric_value"]) if r.get("metric_value") is not None else None,
                    float(pct_row["percentile"]),
                )
            else:
                interpretation = metric_labels.interpret_percentile(
                    float(pct_row["percentile"]),
                    position_group=position_group,
                    metric_name=mname,
                )

        row_dict: dict[str, Any] = {
            "Grupo": grp,
            "Métrica": metric_labels.metric_label(mname),
            "Valor": metric_labels.format_metric_value(
                r.get("metric_value"), unit, metric_name=mname
            ),
            "Unidad": metric_labels.display_unit_for_table(mname, unit),
            "Percentil": pct_disp,
            "Ranking": rank_disp,
            "Media posición": avg_disp,
            "Interpretación": interpretation,
            "_metric_name": mname,
            "_group_sort": group_order.get(grp, len(group_order)),
            "_priority": mname in priority,
            "_pct_num": pct_num,
        }
        out.append(row_dict)

    out.sort(
        key=lambda row: (
            row["_group_sort"],
            0 if row["_priority"] else 1,
            str(row["Métrica"]).lower(),
        )
    )
    for row in out:
        row.pop("_metric_name", None)
        row.pop("_group_sort", None)
        row.pop("_priority", None)
    return out


def summarize_normalized_metrics_distribution(
    percentile_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resumen min/max/media de cohorte para métricas centradas en cero."""
    out: list[dict[str, Any]] = []
    for r in percentile_rows:
        mname = str(r.get("metric_name") or "")
        if not metric_labels.is_zero_centered_normalized_metric(mname):
            continue
        cohort = [float(v) for v in (r.get("cohort_values") or []) if v is not None]
        if not cohort:
            continue
        out.append(
            {
                "Métrica": metric_labels.metric_label(mname),
                "Min cohorte": round(min(cohort), 3),
                "Max cohorte": round(max(cohort), 3),
                "Media cohorte": round(sum(cohort) / len(cohort), 3),
                "Valor jugador": round(float(r["player_value"]), 3)
                if r.get("player_value") is not None
                else None,
                "Percentil": int(round(float(r["percentile"])))
                if r.get("percentile") is not None
                else None,
            }
        )
    return out


def comparison_row_has_signal(row: dict[str, Any], *, epsilon: float = 0.0005) -> bool:
    """True si jugador o cohorte tienen valor distinto de cero (evita ruido numérico)."""
    from scouting.services import metrics_quality_service as mq

    return mq.comparison_row_has_signal(row, epsilon=epsilon)


def filter_comparison_rows_with_signal(
    rows: list[dict[str, Any]],
    *,
    epsilon: float = 0.0005,
) -> list[dict[str, Any]]:
    return [r for r in rows if comparison_row_has_signal(r, epsilon=epsilon)]


def filter_non_informative_comparison_rows(
    rows: list[dict[str, Any]],
    *,
    position_group: str | None = None,
) -> list[dict[str, Any]]:
    from scouting.services import metrics_quality_service as mq

    return mq.filter_non_informative_comparison_rows(rows, position_group=position_group)


def partition_metrics_for_ui(
    available_metrics: list[str],
    comparison_rows: list[dict[str, Any]],
    metrics_rows: list[dict[str, Any]],
    *,
    position_group: str | None = None,
) -> tuple[list[str], list[str]]:
    from scouting.services import metrics_quality_service as mq

    return mq.partition_metrics_for_ui(
        available_metrics,
        comparison_rows,
        metrics_rows,
        position_group=position_group,
    )


def applied_metrics_have_chart_content(
    selected_metrics: list[str],
    metrics_rows: list[dict[str, Any]],
    comparison_rows: list[dict[str, Any]],
) -> bool:
    from scouting.services import metrics_quality_service as mq

    return mq.applied_metrics_have_chart_content(
        selected_metrics, metrics_rows, comparison_rows
    )


def filter_comparison_rows_by_metrics(
    rows: list[dict[str, Any]],
    metric_names: list[str],
) -> list[dict[str, Any]]:
    wanted = {str(m).strip() for m in metric_names if m}
    order = {m: i for i, m in enumerate(metric_names)}
    filtered = [r for r in rows if str(r.get("metric_name") or "") in wanted]
    filtered.sort(key=lambda r: order.get(str(r.get("metric_name") or ""), 999))
    return filtered


def default_comparison_metrics_for_charts(
    metrics_rows: list[dict[str, Any]],
    comparison_rows: list[dict[str, Any]],
    *,
    position_group: str | None = None,
) -> list[str]:
    """
    Métricas por defecto en gráficos: perfil del grupo con señal informativa.
    Excluye degeneradas (todo-cero, lista explícita, portero en campo, etc.).
    """
    from scouting.config.metric_quality_config import default_excluded_metrics_for_position
    from scouting.services import metrics_quality_service as mq

    available = comparable_metric_names_from_block(metrics_rows)
    if not available:
        return []
    profile = objective_comparison_metrics_for_player(
        metrics_rows,
        position_group=position_group,
    )
    informative_rows = mq.filter_non_informative_comparison_rows(
        comparison_rows,
        position_group=position_group,
    )
    with_signal = {str(r["metric_name"]) for r in informative_rows if r.get("metric_name")}
    excluded = default_excluded_metrics_for_position(position_group)
    defaults = [m for m in profile if m in with_signal and m not in excluded]
    if len(defaults) < 2:
        for m in profile:
            if m in with_signal and m not in excluded and m not in defaults:
                defaults.append(m)
    if not defaults:
        defaults = [
            str(r["metric_name"])
            for r in informative_rows
            if str(r.get("metric_name") or "") not in excluded
        ]
    if not defaults:
        rec, _ = mq.partition_metrics_for_ui(
            available, comparison_rows, metrics_rows, position_group=position_group
        )
        defaults = rec[: min(8, len(rec))]
    return defaults


def selected_metrics_include_disciplinary_totals(metric_names: list[str]) -> bool:
    from scouting.config.card_disciplinary_metrics import DISCIPLINARY_HIGHER_NOT_BETTER

    names = {str(m).strip() for m in metric_names if m}
    return bool(names & DISCIPLINARY_HIGHER_NOT_BETTER)


def objective_position_distribution(
    rows: list[dict[str, Any]],
) -> dict[str, int]:
    """Cuenta bloques por grupo objetivo (Portero/Defensa/…)."""
    counts: dict[str, int] = {}
    for r in rows:
        grp = r.get("objective_position_group")
        key = str(grp).strip() if grp and str(grp).strip() else "—"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: (-x[1], x[0])))


def count_distinct_resolved_teams(rows: list[dict[str, Any]]) -> int:
    teams = {
        str(r.get("objective_team") or "").strip()
        for r in rows
        if str(r.get("objective_team") or "").strip() not in ("", "—")
    }
    return len(teams)


def has_position_comparison_data(
    comparison_rows: list[dict[str, Any]],
    *,
    min_peers: int = 2,
) -> bool:
    return any(
        int(r.get("players_count") or 0) >= min_peers for r in comparison_rows
    )


def objective_block_chart_metric_names(metrics_rows: list[dict[str, Any]]) -> list[str]:
    """Métricas aptas para gráfico de barras en detalle de jugador."""
    out: list[str] = []
    for r in metrics_rows:
        name = str(r.get("metric_name") or "").strip()
        if not name or is_hidden_metric_name(name):
            continue
        if metric_labels.is_chart_excluded_metric(name, r.get("metric_unit")):
            continue
        out.append(name)
    out.sort(key=metric_labels.metric_sort_key)
    return out


def compare_metric_by_players(
    conn: Connection,
    metric_name: str,
    *,
    source_name: str | None = None,
    player_ids: list[int] | None = None,
    position: str | None = None,
    season: str | None = None,
    competition: str | None = None,
    current_team: str | None = None,
) -> list[dict[str, Any]]:
    return metrics_repository.get_metric_comparison(
        conn,
        metric_name,
        source_name=source_name,
        player_ids=player_ids,
        position=position,
        season=season,
        competition=competition,
        current_team=current_team,
    )


def is_hidden_metric_name(name: str) -> bool:
    n = str(name).strip()
    if not n or n in METRIC_SELECT_BLOCKLIST:
        return True
    return any(p.search(n) for p in METRIC_SELECT_BLOCKLIST_PATTERNS)


def metric_column_names(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in WIDE_INDEX_COLS]


def selectable_metric_names(df: pd.DataFrame) -> list[str]:
    """Métricas numéricas útiles (excluye IDs/texto/raw y columnas casi vacías)."""
    cols = metric_column_names(df)
    if df.empty:
        return sorted(cols)
    out: list[str] = []
    for col in cols:
        if is_hidden_metric_name(col):
            continue
        series = pd.to_numeric(df[col], errors="coerce")
        if series.notna().sum() == 0:
            continue
        null_ratio = float(series.isna().mean())
        if null_ratio >= NULL_RATIO_HIDE_THRESHOLD:
            continue
        out.append(col)
    return sorted(out)


def _unique_players(df: pd.DataFrame) -> int:
    if df.empty or "player_id" not in df.columns:
        return 0
    return int(df["player_id"].nunique())


def _age_years_from_birth(birth_date: Any) -> float | None:
    if birth_date is None or (isinstance(birth_date, float) and pd.isna(birth_date)):
        return None
    try:
        if hasattr(birth_date, "date") and callable(birth_date.date):
            bd = birth_date.date()
        elif isinstance(birth_date, date):
            bd = birth_date
        else:
            bd = pd.to_datetime(birth_date, errors="coerce")
            if pd.isna(bd):
                return None
            bd = bd.date()
        age = calculate_age(bd)
        return float(age) if age is not None else None
    except (TypeError, ValueError):
        return None


def _prepare_long_for_pivot(long_df: pd.DataFrame) -> pd.DataFrame:
    """Enriquece filas largas antes del pivot; no incluye birth_date en el índice."""
    df = long_df.copy()
    if "position" in df.columns:
        df["position_standardized"] = df["position"].apply(
            lambda p: standardize_position_for_analysis(p) if pd.notna(p) else None
        )
        df["standard_position"] = df["position_standardized"]
    if "season" in df.columns:
        df["season_label"] = df["season"].apply(
            lambda s: metric_labels.format_season_label(s) if pd.notna(s) else "—"
        )
    if "reports_count" not in df.columns:
        df["reports_count"] = 0
    if "has_subjective_report" not in df.columns:
        df["has_subjective_report"] = False
    return df


def build_wide_analysis_dataframe(
    conn: Connection,
    *,
    source_name: str | None = None,
    season: str | None = None,
    competition: str | None = None,
    position_internal: str | None = None,
    position_standardized: str | None = None,
    current_team: str | None = None,
    nationality: str | None = None,
    preferred_foot: str | None = None,
    player_type: str = metrics_repository.PLAYER_TYPE_ALL,
    age_min: int | None = None,
    age_max: int | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Una fila por (jugador, temporada, competición, …) con métricas en columnas (metric_name crudo).
    Solo jugadores presentes en objective_metrics. No filtra por métrica de ranking.
    """
    diag: dict[str, Any] = {
        "long_rows": 0,
        "long_unique_players": 0,
        "wide_rows": 0,
        "wide_unique_players": 0,
        "long_columns": [],
        "index_cols_used": [],
    }
    rows = metrics_repository.get_metrics_long_aggregated(
        conn,
        source_name=source_name,
        season=season,
        competition=competition,
        position=position_internal,
        current_team=current_team,
        nationality=nationality,
        preferred_foot=preferred_foot,
        player_type=player_type,
        age_min=age_min if age_min and age_min > 0 else None,
        age_max=age_max if age_max and age_max > 0 else None,
    )
    if not rows:
        return pd.DataFrame(columns=list(WIDE_INDEX_COLS)), diag

    long_df = pd.DataFrame(rows)
    diag["long_rows"] = len(long_df)
    diag["long_unique_players"] = _unique_players(long_df)
    diag["long_columns"] = list(long_df.columns)
    long_df["metric_value"] = pd.to_numeric(long_df["metric_value"], errors="coerce")

    long_df = _prepare_long_for_pivot(long_df)

    # birth_date fuera del índice del pivot (evita colapso con NaT)
    birth_by_player = (
        long_df.groupby("player_id", as_index=False)["birth_date"].first()
        if "birth_date" in long_df.columns
        else pd.DataFrame(columns=["player_id", "birth_date"])
    )
    source_by_group = (
        long_df.groupby(["player_id", "season", "competition"], as_index=False)["source_name"].first()
        if "source_name" in long_df.columns
        else None
    )

    index_cols = [c for c in PIVOT_INDEX_COLS if c in long_df.columns]
    diag["index_cols_used"] = index_cols
    if not index_cols:
        return pd.DataFrame(columns=list(WIDE_INDEX_COLS)), diag

    wide = long_df.pivot_table(
        index=index_cols,
        columns="metric_name",
        values="metric_value",
        aggfunc="mean",
    )
    if wide.empty:
        diag["wide_rows"] = 0
        diag["wide_unique_players"] = 0
        return pd.DataFrame(columns=list(WIDE_INDEX_COLS)), diag

    wide.columns = [str(c) for c in wide.columns]
    df = wide.reset_index()

    if not birth_by_player.empty:
        df = df.merge(birth_by_player, on="player_id", how="left")
    if source_by_group is not None and not source_by_group.empty:
        df = df.merge(source_by_group, on=["player_id", "season", "competition"], how="left")

    if "birth_date" in df.columns:
        df["age"] = df["birth_date"].apply(_age_years_from_birth)
    else:
        df["age"] = None

    if "season" in df.columns and "season_label" not in df.columns:
        df["season_label"] = df["season"].apply(
            lambda s: metric_labels.format_season_label(s) if pd.notna(s) else "—"
        )
    if "position" in df.columns and "position_standardized" not in df.columns:
        df["position_standardized"] = df["position"].apply(
            lambda p: standardize_position_for_analysis(p) if pd.notna(p) else None
        )
    if "position_standardized" in df.columns:
        df["standard_position"] = df["position_standardized"]

    if position_standardized and str(position_standardized).strip():
        df = df[df["position_standardized"] == str(position_standardized).strip()].copy()

    diag["wide_rows"] = len(df)
    diag["wide_unique_players"] = _unique_players(df)
    return df, diag


def cohort_diagnostics_after_minutes(df: pd.DataFrame, min_minutes: float) -> dict[str, int]:
    """Conteos tras filtro de minutos (para UI de diagnóstico)."""
    filtered = apply_min_minutes_filter(df, min_minutes)
    return {
        "after_minutes_rows": len(filtered),
        "after_minutes_unique_players": _unique_players(filtered),
    }


def count_with_metric_value(df: pd.DataFrame, metric_name: str) -> int:
    """Filas con valor numérico no nulo para la métrica (ranking, no cohorte base)."""
    col = str(metric_name).strip()
    if df.empty or col not in df.columns:
        return 0
    return int(pd.to_numeric(df[col], errors="coerce").notna().sum())


def chartable_metric_names(selectable: list[str], df: pd.DataFrame | None = None) -> list[str]:
    """Métricas aptas para gráficos de barras (sin escala enorme)."""
    out: list[str] = []
    for name in selectable:
        if metric_labels.is_chart_excluded_metric(name):
            continue
        if df is not None and name in df.columns:
            out.append(name)
        elif df is None:
            if name.endswith("_per90") or name.endswith("_pct") or name == "avg_rating":
                out.append(name)
    return out


def resolve_club_for_metrics_group(metrics: list[dict[str, Any]]) -> str:
    """Equipo objetivo del bloque: solo team_name/team en raw_payload (sin ficha scouting)."""
    for m in metrics:
        payload = m.get("raw_payload")
        if not isinstance(payload, dict):
            continue
        for key in ("team_name", "team"):
            team = payload.get(key)
            if team is not None and str(team).strip():
                return str(team).strip()
        raw_row = payload.get("raw_row")
        if isinstance(raw_row, dict):
            for key in ("team_name", "team"):
                team = raw_row.get(key)
                if team is not None and str(team).strip():
                    return str(team).strip()
    return "—"


def build_objective_season_summary_rows(
    summary: list[dict[str, Any]],
    grouped: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resumen UI: Temporada, Equipo objetivo, Liga, Nº métricas (sin fuente)."""
    group_by_key: dict[tuple[str | None, str | None], list[dict[str, Any]]] = {}
    for g in grouped:
        key = (g.get("season"), g.get("competition"))
        group_by_key[key] = g.get("metrics") or []

    out: list[dict[str, Any]] = []
    for s in summary:
        season = s.get("season")
        competition = s.get("competition")
        metrics = group_by_key.get((season, competition), [])
        club = resolve_club_for_metrics_group(metrics)
        out.append(
            {
                "Temporada": metric_labels.format_season_label(season),
                "Equipo objetivo": club,
                "Liga": competition or "—",
                "Nº métricas": s.get("metrics_count") or s.get("distinct_metrics") or "—",
            }
        )
    return out


def format_player_block_metrics_rows(
    metrics_rows: list[dict[str, Any]],
    *,
    include_group: bool = False,
) -> list[dict[str, Any]]:
    """Todas las métricas visibles del bloque, ordenadas y en español."""
    visible = [
        r
        for r in metrics_rows
        if not is_hidden_metric_name(str(r.get("metric_name") or ""))
    ]
    visible.sort(key=lambda r: metric_labels.metric_sort_key(str(r.get("metric_name") or "")))

    out: list[dict[str, Any]] = []
    for r in visible:
        mname = str(r.get("metric_name") or "")
        unit = r.get("metric_unit")
        row: dict[str, Any] = {
            "Métrica": metric_labels.metric_label(mname),
            "Valor": metric_labels.format_metric_value(r.get("metric_value"), unit),
            "Unidad": metric_labels.display_unit_for_table(mname, unit),
        }
        if include_group:
            row["Grupo"] = metric_labels.metric_group(mname)
        out.append(row)
    return out


def format_metrics_table_rows(
    rows: list[dict[str, Any]],
    *,
    show_source: bool | None = None,
    technical: bool = False,
) -> list[dict[str, Any]]:
    """Traduce métricas para tablas UI. Vista técnica incluye metric_name y fuente."""
    if show_source is None:
        show_source = metric_labels.should_show_source_column(rows)
    visible = [
        r for r in rows if not is_hidden_metric_name(str(r.get("metric_name") or ""))
    ]
    visible.sort(key=lambda r: metric_labels.metric_sort_key(str(r.get("metric_name") or "")))

    out: list[dict[str, Any]] = []
    for r in visible:
        mname = str(r.get("metric_name") or "")
        unit = r.get("metric_unit")
        if technical:
            row = {
                "temporada": metric_labels.format_season_label(r.get("season")),
                "competición": r.get("competition"),
                "metric_name": mname,
                "métrica": metric_labels.metric_label(mname),
                "valor": metric_labels.format_metric_value(r.get("metric_value"), unit),
                "unidad": metric_labels.display_unit_for_table(mname, unit),
                "fuente": r.get("source_name"),
            }
        else:
            row = {
                "temporada": metric_labels.format_season_label(r.get("season")),
                "competición": r.get("competition"),
                "métrica": metric_labels.metric_label(mname),
                "valor": metric_labels.format_metric_value(r.get("metric_value"), unit),
                "unidad": metric_labels.display_unit_for_table(mname, unit),
            }
            if show_source:
                row["fuente"] = r.get("source_name")
        out.append(row)
    return out


def apply_min_minutes_filter(df: pd.DataFrame, min_minutes: float) -> pd.DataFrame:
    """
    Filtra por minutesPlayed (columna metric_name cruda).
    min_minutes <= 0: sin filtro. Si min_minutes > 0: excluye filas sin minutos o por debajo del umbral.
    """
    if df.empty or min_minutes <= 0:
        return df
    if "minutesPlayed" not in df.columns:
        return df.iloc[0:0].copy()
    mins = pd.to_numeric(df["minutesPlayed"], errors="coerce")
    return df.loc[mins.notna() & (mins >= float(min_minutes))].copy()


def add_metric_percentile(df: pd.DataFrame, metric_name: str) -> pd.DataFrame:
    """Añade columna {metric}_percentile (0–100) dentro del conjunto filtrado."""
    out = df.copy()
    col = str(metric_name).strip()
    if col not in out.columns or out.empty:
        out[f"{col}_percentile"] = pd.NA
        return out
    values = pd.to_numeric(out[col], errors="coerce")
    out[f"{col}_percentile"] = values.rank(pct=True, method="average") * 100.0
    return out


def normalize_metrics_0_100(df: pd.DataFrame, metric_names: list[str]) -> pd.DataFrame:
    """Escala cada métrica a 0–100 según min/max del dataframe pasado."""
    out = pd.DataFrame(index=df.index)
    for col in metric_names:
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors="coerce")
        mn = series.min()
        mx = series.max()
        if pd.isna(mn) or pd.isna(mx):
            out[col] = pd.NA
        elif mx == mn:
            out[col] = 50.0
        else:
            out[col] = (series - mn) / (mx - mn) * 100.0
    return out


def player_row_label(row: pd.Series) -> str:
    name = row.get("player_name") or "?"
    team = row.get("objective_team") or row.get("current_team") or "—"
    comp = row.get("competition") or "—"
    season = metric_labels.format_season_label(row.get("season"))
    pid = row.get("player_id")
    return f"{name} · {team} · {comp} · {season} (id {pid})"


def resolve_analysis_profile(
    profile_choice: str,
    *,
    position: str | None = None,
) -> str | None:
    """Clave de perfil de análisis (None = personalizado)."""
    return metric_profiles.resolve_analysis_profile_key(profile_choice, position=position)


def default_ranking_metric(
    selectable: list[str],
    *,
    profile_choice: str = metric_profiles.PROFILE_AUTO,
    position: str | None = None,
) -> str:
    profile_key = resolve_analysis_profile(profile_choice, position=position)
    return metric_profiles.default_ranking_metric_for_profile(profile_key, selectable)


def default_radar_metrics(
    selectable: list[str],
    *,
    profile_choice: str = metric_profiles.PROFILE_AUTO,
    position: str | None = None,
) -> list[str]:
    profile_key = resolve_analysis_profile(profile_choice, position=position)
    return metric_profiles.default_radar_for_profile(profile_key, selectable)


def profile_metric_list(
    selectable: list[str],
    *,
    profile_choice: str,
    position: str | None = None,
) -> list[str]:
    """Métricas del perfil activo presentes en datos (vacío si personalizado)."""
    profile_key = resolve_analysis_profile(profile_choice, position=position)
    return metric_profiles.metrics_for_analysis_profile(profile_key, selectable)


def compare_table_metrics(
    selectable: list[str],
    *,
    profile_choice: str = metric_profiles.PROFILE_AUTO,
    position: str | None = None,
) -> list[str]:
    ordered: list[str] = []
    for m in COMPARE_BASE_METRICS:
        if m in selectable and m not in ordered:
            ordered.append(m)
    for m in profile_metric_list(
        selectable, profile_choice=profile_choice, position=position
    ):
        if m not in ordered:
            ordered.append(m)
    for m in selectable:
        if m not in ordered:
            ordered.append(m)
    return ordered
