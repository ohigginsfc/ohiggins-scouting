"""Política centralizada de origen de métricas objetivas (Sofascore vs demo).

Regla por ámbito (jugador / temporada / competición):
1. Si hay datos source_type='sofascore' → solo Sofascore.
2. Si no → permitir demo y marcar demo_mode=True.
Nunca mezclar ambos orígenes en el mismo resultado.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from psycopg import Connection

SOURCE_TYPE_SOFASCORE = "sofascore"
SOURCE_TYPE_DEMO = "demo"
OriginKind = Literal["sofascore", "demo", "none"]


def sofascore_origin_sql(alias: str = "om") -> str:
    return (
        f"({alias}.source_type = '{SOURCE_TYPE_SOFASCORE}' OR "
        f"({alias}.source_type IS NULL AND {alias}.import_batch_id IS NOT NULL))"
    )


def demo_origin_sql(alias: str = "om") -> str:
    return (
        f"({alias}.source_type = '{SOURCE_TYPE_DEMO}' OR "
        f"({alias}.source_type IS NULL AND {alias}.import_batch_id IS NULL))"
    )


def origin_sql_for(kind: OriginKind | str, alias: str = "om") -> str | None:
    if kind == SOURCE_TYPE_SOFASCORE:
        return sofascore_origin_sql(alias)
    if kind == SOURCE_TYPE_DEMO:
        return demo_origin_sql(alias)
    return None


@dataclass(frozen=True)
class OriginResolution:
    """Resultado de la prioridad Sofascore → demo para un ámbito."""

    origin: OriginKind
    demo_mode: bool
    sofascore_count: int = 0
    demo_count: int = 0

    @property
    def has_data(self) -> bool:
        return self.origin != "none"


def resolve_scope_origin(
    conn: Connection,
    *,
    season: str | None,
    competition: str | None = None,
    player_id: int | None = None,
    source_name: str = "Sofascore",
) -> OriginResolution:
    """Decide el origen preferido para un ámbito sin mezclar filas."""
    clauses = ["source_name = %s"]
    params: list[Any] = [source_name]
    if season is not None and str(season).strip():
        clauses.append("season IS NOT DISTINCT FROM %s")
        params.append(str(season).strip())
    if competition is not None and str(competition).strip():
        clauses.append("competition IS NOT DISTINCT FROM %s")
        params.append(str(competition).strip())
    if player_id is not None:
        clauses.append("player_id = %s")
        params.append(int(player_id))
    where = " AND ".join(clauses)

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT
              COUNT(*) FILTER (
                WHERE source_type = %s
                   OR (source_type IS NULL AND import_batch_id IS NOT NULL)
              )::int AS sofascore_n,
              COUNT(*) FILTER (
                WHERE source_type = %s
                   OR (source_type IS NULL AND import_batch_id IS NULL)
              )::int AS demo_n
            FROM objective_metrics
            WHERE {where}
            """,
            (SOURCE_TYPE_SOFASCORE, SOURCE_TYPE_DEMO, *params),
        )
        row = cur.fetchone() or (0, 0)
        sofascore_n = int(row[0] or 0)
        demo_n = int(row[1] or 0)

    if sofascore_n > 0:
        return OriginResolution(
            origin=SOURCE_TYPE_SOFASCORE,
            demo_mode=False,
            sofascore_count=sofascore_n,
            demo_count=demo_n,
        )
    if demo_n > 0:
        return OriginResolution(
            origin=SOURCE_TYPE_DEMO,
            demo_mode=True,
            sofascore_count=sofascore_n,
            demo_count=demo_n,
        )
    return OriginResolution(origin="none", demo_mode=False)


def can_compare_seasons(
    origin_active: OriginResolution,
    origin_historical: OriginResolution,
    *,
    allow_demo_fallback: bool = False,
) -> tuple[bool, str | None]:
    """
    Por defecto solo permite comparar Sofascore vs Sofascore.
    Con allow_demo_fallback=True permite demo en cualquiera, con advertencia.
    """
    if not origin_active.has_data or not origin_historical.has_data:
        return False, "Faltan datos objetivos en una de las temporadas."

    if origin_active.origin == SOURCE_TYPE_SOFASCORE and origin_historical.origin == SOURCE_TYPE_SOFASCORE:
        return True, None

    if not allow_demo_fallback:
        if origin_historical.origin != SOURCE_TYPE_SOFASCORE:
            return (
                False,
                "No hay datos reales de Sofascore para la temporada histórica. "
                "Sincroniza la temporada histórica para habilitar una comparación fiable.",
            )
        if origin_active.origin != SOURCE_TYPE_SOFASCORE:
            return (
                False,
                "No hay datos reales de Sofascore para la temporada activa.",
            )
        return False, "Orígenes incompatibles para la comparación."

    return True, "Comparación con datos demo (referencia no oficial)."
