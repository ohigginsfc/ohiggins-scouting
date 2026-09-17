"""Plan de sincronización Sofascore para el botón del dashboard (demo → real)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from psycopg import Connection

from scouting.config.sofascore_seasons import get_active_season, get_historical_season
from scouting.services.sofascore_sync_assessment import assess_season_sync, count_metrics_by_origin

PlatformSyncState = Literal[
    "demo_only",
    "initial_sync_required",
    "historical_sync_required",
    "current_sync_required",
    "fully_initialized",
]

HISTORICAL_LEAGUE_SLUG = "cl_primera_2024"


@dataclass
class PlatformSyncPlan:
    """Qué debe hacer el botón principal según datos reales presentes."""

    state: PlatformSyncState
    button_label: str
    banner_message: str
    completion_message: str
    progress_message: str
    active_season: str
    historical_season: str
    has_active_sofascore: bool
    has_historical_sofascore: bool
    demo_metrics: int
    sofascore_metrics: int
    sofascore_players: int = 0
    historical_sofascore_metrics: int = 0
    active_sofascore_metrics: int = 0
    worker_steps: list[list[str]] = field(default_factory=list)
    step_labels: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def assess_platform_sync(conn: Connection) -> PlatformSyncPlan:
    """
    A. Sin reales 2024 ni activa → Descarga completa (histórica + activa).
    B. Activa real, falta histórica → Completar histórica (+ incremental activa).
    C. Histórica real, falta activa → Descargar temporada actual.
    D. Ambas reales → Actualizar incremental de la activa.
    """
    from scouting.services.sofascore_sync_assessment import count_sofascore_players

    active = get_active_season()
    historical = get_historical_season()
    active_a = assess_season_sync(conn, active)
    hist_a = assess_season_sync(conn, historical)
    totals = count_metrics_by_origin(conn, season=None)

    has_active = active_a.sofascore_metrics > 0
    has_hist = hist_a.sofascore_metrics > 0
    demo_n = int(totals.get("demo") or 0)
    sofa_n = int(totals.get("sofascore") or 0)
    sofascore_players = int(count_sofascore_players(conn) or 0)
    hist_sofa_n = int(hist_a.sofascore_metrics or 0)
    active_sofa_n = int(active_a.sofascore_metrics or 0)

    if not has_active and not has_hist:
        return PlatformSyncPlan(
            state="initial_sync_required",
            button_label="Descargar datos reales",
            banner_message=(
                "La aplicación está utilizando datos de demostración. Descarga los datos "
                "reales para consultar estadísticas actualizadas y comparar temporadas."
            ),
            progress_message=(
                f"Descargando temporada histórica {historical} y temporada activa {active}…"
            ),
            completion_message=(
                "Datos reales disponibles. Las vistas utilizarán Sofascore y los datos demo "
                "quedarán como respaldo."
            ),
            active_season=active,
            historical_season=historical,
            has_active_sofascore=False,
            has_historical_sofascore=False,
            demo_metrics=demo_n,
            sofascore_metrics=sofa_n,
            sofascore_players=sofascore_players,
            historical_sofascore_metrics=hist_sofa_n,
            active_sofascore_metrics=active_sofa_n,
            worker_steps=[
                [
                    "--only",
                    HISTORICAL_LEAGUE_SLUG,
                    "--season",
                    historical,
                    "--force-backfill",
                    "--json-summary",
                ],
                [
                    "--all",
                    "--season",
                    active,
                    "--force-backfill",
                    "--json-summary",
                ],
            ],
            step_labels=[
                f"Primera División de Chile · Temporada {historical}",
                f"Ligas activas · Temporada {active}",
            ],
        )

    if has_active and not has_hist:
        return PlatformSyncPlan(
            state="historical_sync_required",
            button_label="Completar datos históricos",
            banner_message=(
                f"Hay datos reales de {active}, pero falta la temporada histórica "
                f"{historical} para comparaciones fiables."
            ),
            progress_message=f"Importando temporada histórica {historical}…",
            completion_message=(
                f"Temporada histórica {historical} disponible. "
                "La comparación entre temporadas usará datos reales."
            ),
            active_season=active,
            historical_season=historical,
            has_active_sofascore=True,
            has_historical_sofascore=False,
            demo_metrics=demo_n,
            sofascore_metrics=sofa_n,
            sofascore_players=sofascore_players,
            historical_sofascore_metrics=hist_sofa_n,
            active_sofascore_metrics=active_sofa_n,
            worker_steps=[
                [
                    "--only",
                    HISTORICAL_LEAGUE_SLUG,
                    "--season",
                    historical,
                    "--force-backfill",
                    "--json-summary",
                ],
                ["--all", "--season", active, "--json-summary"],
            ],
            step_labels=[
                f"Primera División de Chile · Temporada {historical}",
                f"Actualización de {active}",
            ],
        )

    if has_hist and not has_active:
        return PlatformSyncPlan(
            state="current_sync_required",
            button_label="Descargar temporada actual",
            banner_message=(
                f"Los datos históricos de {historical} están disponibles. "
                f"Falta descargar la temporada activa {active}."
            ),
            progress_message=f"Descargando temporada activa {active}…",
            completion_message=f"Temporada {active} sincronizada. Las vistas usarán datos reales.",
            active_season=active,
            historical_season=historical,
            has_active_sofascore=False,
            has_historical_sofascore=True,
            demo_metrics=demo_n,
            sofascore_metrics=sofa_n,
            sofascore_players=sofascore_players,
            historical_sofascore_metrics=hist_sofa_n,
            active_sofascore_metrics=active_sofa_n,
            worker_steps=[
                [
                    "--all",
                    "--season",
                    active,
                    "--force-backfill",
                    "--json-summary",
                ],
            ],
            step_labels=[f"Ligas activas · Temporada {active}"],
        )

    return PlatformSyncPlan(
        state="fully_initialized",
        button_label="Buscar nuevos partidos",
        banner_message="",
        progress_message=f"Buscando partidos nuevos finalizados en {active}…",
        completion_message=(
            "No hay nuevos partidos finalizados desde la última actualización."
        ),
        active_season=active,
        historical_season=historical,
        has_active_sofascore=True,
        has_historical_sofascore=True,
        demo_metrics=demo_n,
        sofascore_metrics=sofa_n,
        sofascore_players=sofascore_players,
        historical_sofascore_metrics=hist_sofa_n,
        active_sofascore_metrics=active_sofa_n,
        worker_steps=[],
        step_labels=[f"Buscar nuevos partidos · {active}"],
    )


def is_demo_only_platform(conn: Connection) -> bool:
    totals = count_metrics_by_origin(conn, season=None)
    return int(totals.get("sofascore") or 0) <= 0 and int(totals.get("demo") or 0) > 0
