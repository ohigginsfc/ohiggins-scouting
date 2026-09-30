"""Cálculo completo a partir de los datos de COMET, compartido por las pantallas y el resumen semanal.

Una sola definición de las reglas, los períodos de selección y las alertas: la pantalla y el correo no
pueden mostrar cifras distintas para la misma semana.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from . import metrics, quality
from .facts import Dataset, build_dataset
from .rules import Rules


@dataclass(frozen=True)
class Computed:
    ds: Dataset
    comp: pd.DataFrame        # una fila por jugador y competición
    cat: pd.DataFrame         # una fila por jugador, temporada y categoría
    principal: pd.DataFrame   # categoría principal de cada jugador y temporada
    quality: pd.DataFrame
    raw_counts: dict


def compute_all(raw: dict, stored_rules: Optional[dict] = None, periods: Optional[pd.DataFrame] = None) -> Computed:
    """Dataset, resúmenes por jugador y control de calidad con las reglas y períodos vigentes."""
    ds = build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers'], Rules(stored_rules))
    comp = metrics.add_percentages(metrics.player_competition_summary(ds, periods))
    cat = metrics.category_summary(comp)
    return Computed(ds=ds, comp=comp, cat=cat, principal=metrics.principal_categories(cat),
                    quality=quality.data_quality(ds, raw['sheet'], raw['matches'], periods, comp),
                    raw_counts={k: len(v) for k, v in raw.items()})
