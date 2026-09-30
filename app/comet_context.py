"""Carga de datos y contexto compartido de las pantallas de seguimiento COMET (solo administración).

Toda función pública lleva `@admin_only` por fuera de la caché, igual que `comet_dashboard`: los
resultados en caché no se entregan a quien no sea administrador y no se abre ninguna conexión.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd
import streamlit as st

import comet_dashboard as comet
from scouting.comet import alerts as alert_rules
from scouting.comet import config_store, metrics, queries, quality
from scouting.comet.facts import LOCAL_TZ, Dataset, build_dataset
from scouting.comet.rules import Rules
from scouting.portal.security import admin_only

EMPTY_MARKS = pd.DataFrame(columns=['personid', 'mark', 'active', 'note', 'updated_at'])
EMPTY_PERIODS = pd.DataFrame(columns=['id', 'personid', 'kind', 'starts_on', 'ends_on', 'note', 'active',
                                      'start', 'end'])


def now() -> pd.Timestamp:
    """Hora actual de Santiago. Las demostraciones y pruebas la sustituyen por una fecha fija."""
    return pd.Timestamp.now(tz=LOCAL_TZ).tz_localize(None)


@dataclass(frozen=True)
class Computed:
    ds: Dataset
    comp: pd.DataFrame        # una fila por jugador y competición
    cat: pd.DataFrame         # una fila por jugador, temporada y categoría
    principal: pd.DataFrame   # categoría principal de cada jugador y temporada
    quality: pd.DataFrame
    raw_counts: dict


@dataclass(frozen=True)
class Context:
    computed: Computed
    alert_config: dict
    marks: pd.DataFrame
    periods: pd.DataFrame
    store_error: Optional[str]
    today: pd.Timestamp
    season: Optional[int]

    @property
    def ds(self) -> Dataset:
        return self.computed.ds

    @property
    def rules(self) -> Rules:
        return self.computed.ds.rules

    @property
    def store_available(self) -> bool:
        return self.store_error is None


@admin_only
@st.cache_data(ttl=600, show_spinner='Cargando datos de COMET…')
def load_raw() -> dict:
    """Planillas, partidos, jugadores y arqueros de O'Higgins (solo lectura, con `comet_reader`)."""
    return queries.fetch_raw(lambda sql, params: comet.load_data(sql, params))


@admin_only
def load_config() -> tuple[dict, pd.DataFrame, pd.DataFrame, Optional[str]]:
    """Configuración guardada en Supabase; si no está disponible, valores por defecto y el motivo."""
    try:
        stored, marks, periods = config_store.load_all()
        return stored, marks, periods, None
    except config_store.StoreUnavailable as exc:
        return {}, EMPTY_MARKS, EMPTY_PERIODS, str(exc)


@admin_only
@st.cache_data(ttl=600, show_spinner='Calculando indicadores…')
def compute(raw: dict, stored_rules: dict, periods: pd.DataFrame) -> Computed:
    ds = build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers'], Rules(stored_rules))
    comp = metrics.add_percentages(metrics.player_competition_summary(ds, periods))
    cat = metrics.category_summary(comp)
    return Computed(ds=ds, comp=comp, cat=cat, principal=metrics.principal_categories(cat),
                    quality=quality.data_quality(ds, raw['sheet'], raw['matches']),
                    raw_counts={k: len(v) for k, v in raw.items()})


@admin_only
def context() -> Context:
    raw = load_raw()
    stored, marks, periods, error = load_config()
    computed = compute(raw, {k: v for k, v in stored.items() if k != config_store.ALERT_CONFIG_KEY}, periods)
    today = now()
    return Context(
        computed=computed,
        alert_config=alert_rules.resolve_config((stored.get(config_store.ALERT_CONFIG_KEY) or {}).get('value')),
        marks=marks, periods=periods, store_error=error, today=today,
        season=computed.ds.current_season(today))


def season_choices(ctx: Context) -> list[int]:
    """Temporadas con datos, la más reciente primero."""
    return sorted(ctx.ds.seasons, reverse=True)
