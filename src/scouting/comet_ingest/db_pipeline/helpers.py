from __future__ import annotations
import pandas as pd


def _normalize_bool_series(s: pd.Series) -> pd.Series:
    """
    Normaliza booleanos de forma robusta:
    'sí/si/yes/true/1/t/y' -> True
    'no/false/0/f/n' -> False
    Resto -> <NA> (boolean nulo)
    """
    st = s.astype("string").str.strip().str.lower()
    st = st.str.replace("í", "i", regex=False)
    return st.map(
        {
            "si": True,
            "s": True,
            "1": True,
            "1.0": True,
            "true": True,
            "t": True,
            "yes": True,
            "y": True,
            "no": False,
            "n": False,
            "0": False,
            "0.0": False,
            "false": False,
            "f": False,
        }
    ).astype("boolean")


def fix_unix_timestamptz(
    df: pd.DataFrame, colname: str, default_unit: str = "ms"
) -> pd.DataFrame:
    """
    Convierte épocas Unix (ms/s; incluso incrustadas en strings tipo '/Date(1753290673946)/')
    a pandas datetime con zona horaria UTC, preservando la posición de la columna.

    Distingue segundos y milisegundos por magnitud en cada fila (valor absoluto
    fuera del rango de segundos representable en ns indica ms). Acepta números, /Date(...)/ y fechas legibles completas.
    Los valores no interpretables quedan como NaT; no extrae dígitos de texto libre.
    """
    if colname not in df.columns:
        return df

    if default_unit not in {"ms", "s"}:
        raise ValueError("default_unit debe ser ms o s")
    series = df[colname]
    text = series.astype("string").str.strip()
    # Only parse complete numeric values or the documented /Date(...)/ wrapper.
    wrapped = text.str.extract(r"^/Date\((-?\d+)(?:[+-]\d{4})?\)/$", expand=False)
    numbers = pd.to_numeric(text.where(wrapped.isna(), wrapped), errors="coerce")
    # Dates before 1970 can have millisecond magnitudes below 1e11.
    # Keep seconds only when representable in pandas nanosecond timestamps.
    milliseconds = numbers.lt(pd.Timestamp.min.value / 1e9) | numbers.gt(pd.Timestamp.max.value / 1e9)
    seconds_dt = pd.to_datetime(numbers.where(~milliseconds), unit="s", utc=True, errors="coerce")
    # errors='coerce' does not protect pandas' numeric conversion from overflow
    # for extreme provider values (including infinity). Filter before conversion.
    valid_millis = numbers.between(
        pd.Timestamp.min.value / 1e6, pd.Timestamp.max.value / 1e6
    )
    millis_dt = pd.to_datetime(numbers.where(milliseconds & valid_millis), unit="ms", utc=True, errors="coerce")
    parsed = pd.to_datetime(text.where(numbers.isna()), format="mixed", utc=True, errors="coerce")
    result = df.copy()
    result[colname] = seconds_dt.fillna(millis_dt).fillna(parsed)
    return result


def _clean_text(s: pd.Series) -> pd.Series:
    """Limpia textos: strip + normaliza valores vacíos/comunes a <NA>."""
    st = s.astype("string").str.strip()
    return st.replace(
        {
            "": pd.NA,
            "nan": pd.NA,
            "NaN": pd.NA,
            "null": pd.NA,
            "NULL": pd.NA,
            "None": pd.NA,
            "none": pd.NA,
        }
    )
