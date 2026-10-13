from __future__ import annotations
from typing import Optional
import pandas as pd

from .helpers import (
    _normalize_bool_series,
    fix_unix_timestamptz,
    _clean_text,
)

from .specs import TableSpec

# =========================
# Motor genérico: limpiar + upsert
# =========================


def clean_df(df_raw: pd.DataFrame, spec: TableSpec) -> pd.DataFrame:
    """
    Limpieza genérica basada en la especificación de la tabla:
    - alias -> filtro de columnas en orden
    - pre_clean -> tipado (int/float/text/bool/tz)
    - validación de requeridos -> dropna
    - deduplicación (por pk o dedupe_by) priorizando order_desc_by
    """
    df = df_raw.copy()
    source_rows = len(df)

    # 1) Aliases primero
    if spec.aliases:
        to_rename = {
            src: dst
            for src, dst in spec.aliases.items()
            if src in df.columns and dst not in df.columns
        }
        if to_rename:
            df = df.rename(columns=to_rename)

    # 2) Conservar solo columnas esperadas (presentes) en orden
    present = [c for c in spec.cols if c in df.columns]
    df = df.loc[:, present].copy()

    # 3) Hook de pre-limpieza (casos especiales)
    if spec.pre_clean:
        df = spec.pre_clean(df)
    preclean_rows = len(df)

    # 4) Tipado numérico entero
    ints_present = [c for c in spec.int_cols if c in df.columns]
    if ints_present:
        df[ints_present] = (
            df.loc[:, ints_present]
            .apply(pd.to_numeric, errors="coerce")
            .astype("Int64")
        )

    # 5) Tipado float
    floats_present = [c for c in spec.float_cols if c in df.columns]
    if floats_present:
        df[floats_present] = df.loc[:, floats_present].apply(
            pd.to_numeric, errors="coerce"
        )

    # 6) Textos
    txt_present = [c for c in spec.text_cols if c in df.columns]
    for c in txt_present:
        df[c] = _clean_text(df[c])

    # 7) Booleanos
    bool_present = [c for c in spec.bool_cols if c in df.columns]
    for c in bool_present:
        df[c] = _normalize_bool_series(df[c])

    # 8) Timestamps
    for c in [c for c in spec.tz_cols if c in df.columns]:
        df = fix_unix_timestamptz(df, c, default_unit="ms")

    # 9) Requeridos
    missing = [c for c in spec.required if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas requeridas para {spec.table}: {missing}")
    before_required = len(df)
    if spec.required:
        df = df.dropna(subset=[c for c in spec.required if c in df.columns]).copy()
    invalid_required_rows = before_required - len(df)
    before_dedupe = len(df)

    # 10) Deduplicación (elige la fila “más reciente” según order_desc_by)
    key = spec.dedupe_by or spec.pk
    if key:
        if spec.order_desc_by and any(col in df.columns for col in spec.order_desc_by):
            sort_by = [col for col in spec.order_desc_by if col in df.columns]
            df = df.sort_values(
                sort_by, ascending=[False] * len(sort_by), na_position="last"
            )
        df = df.drop_duplicates(
            subset=[c for c in key if c in df.columns], keep="first"
        ).copy()

    # 11) Orden final (solo presentes)
    final_cols = [c for c in spec.cols if c in df.columns]
    result = df.loc[:, final_cols].copy()
    result.attrs['cleaning'] = {
        'source_rows': source_rows,
        'preclean_removed_rows': source_rows - preclean_rows,
        'invalid_required_rows': invalid_required_rows,
        'deduplicated_rows': before_dedupe - len(result),
        'output_rows': len(result),
    }
    return result

