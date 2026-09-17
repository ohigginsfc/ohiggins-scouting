"""Helpers de presentación orientados al usuario final (sin lógica de negocio)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

_MONTHS_ES = (
    "",
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)

_STATUS_LABELS = {
    "processed": "Procesado",
    "completed": "Completado",
    "failed": "Error",
    "error": "Error",
    "running": "En curso",
    "hidden": "Oculto",
    "idle": "Listo",
    "success": "Completado",
    "no_news": "Sin novedades",
    "completed_no_changes": "Sin novedades",
    "downloaded": "Descargado",
    "pending": "Pendiente",
    "manual": "Informe del scout",
    "imported": "Informe importado",
    "demo": "Demostración",
    "sofascore": "Datos oficiales",
}

_SOURCE_LABELS = {
    "manual": "Informe del scout",
    "imported": "Informe importado",
    "demo": "Demostración",
    "sofascore": "Datos oficiales",
}


def format_number_for_ui(value: Any, *, decimals: int | None = None) -> str:
    """Formato español: 160160 → 160.160"""
    if value is None or value == "":
        return "—"
    try:
        if decimals is not None:
            num = float(value)
            formatted = f"{num:,.{decimals}f}"
        else:
            try:
                num_i = int(value)
                if float(value) == float(num_i):
                    formatted = f"{num_i:,}"
                else:
                    formatted = f"{float(value):,.2f}"
            except (TypeError, ValueError):
                formatted = f"{float(value):,.2f}"
        return (
            formatted.replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
    except (TypeError, ValueError):
        return str(value)


def _parse_date_like(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value).strip()
    if not raw or raw in ("—", "-", "s/f", "sin fecha"):
        return None
    # ISO date or datetime
    try:
        if "T" in raw or " " in raw:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")[:19]).date()
        return date.fromisoformat(raw[:10])
    except ValueError:
        pass
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw[:10], fmt).date()
        except ValueError:
            continue
    return None


def _parse_datetime_like(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime(value.year, value.month, value.day)
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")[:19])
    except ValueError:
        pass
    # dd/mm/YYYY HH:MM
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(raw[:19], fmt)
        except ValueError:
            continue
    d = _parse_date_like(raw)
    if d:
        return datetime(d.year, d.month, d.day)
    return None


def format_date_for_ui(value: Any, *, long: bool = True) -> str:
    """Fecha legible: '22 de mayo de 2026' (long) o '22/05/2026'."""
    d = _parse_date_like(value)
    if d is None:
        return "—" if value in (None, "") else str(value)
    if long:
        return f"{d.day} de {_MONTHS_ES[d.month]} de {d.year}"
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def format_datetime_for_ui(value: Any, *, long_date: bool = False) -> str:
    """Fecha y hora legibles sin ISO ni zona horaria."""
    dt = _parse_datetime_like(value)
    if dt is None:
        return "—" if value in (None, "") else str(value)
    if long_date:
        return f"{format_date_for_ui(dt.date(), long=True)} · {dt.hour:02d}:{dt.minute:02d}"
    return f"{dt.day:02d}/{dt.month:02d}/{dt.year} {dt.hour:02d}:{dt.minute:02d}"


def humanize_status(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "—"
    key = raw.lower()
    if key in _STATUS_LABELS:
        return _STATUS_LABELS[key]
    # Never surface raw snake_case internal states
    if "_" in raw or raw.isupper():
        return raw.replace("_", " ").strip().capitalize()
    return raw


def humanize_source_type(value: Any) -> str | None:
    """Traduce origen; None si no aporta valor (p. ej. manual habitual)."""
    raw = str(value or "").strip().lower()
    if not raw or raw == "manual":
        return None
    return _SOURCE_LABELS.get(raw, None)


def render_report_metadata(
    report: dict[str, Any],
    *,
    include_source: bool = False,
) -> str:
    """
    Metadatos de informe orientados al usuario.
    Ejemplo: «Informe de Juan Pérez · 22 de mayo de 2026»
    """
    scout = str(report.get("scout_name") or "").strip()
    date_txt = format_date_for_ui(report.get("report_date"), long=True)
    if scout:
        base = f"Informe de {scout} · {date_txt}"
    else:
        base = date_txt
    if include_source:
        source = humanize_source_type(report.get("source_type"))
        if source:
            return f"{base} · {source}"
    return base


def report_option_label(report: dict[str, Any]) -> str:
    """Etiqueta de selector sin IDs internos."""
    player = str(report.get("player_full_name") or "Jugador").strip()
    date_txt = format_date_for_ui(report.get("report_date"), long=False)
    rec = str(report.get("recommendation") or "").strip()
    parts = [player, date_txt]
    if rec:
        parts.append(rec)
    return " · ".join(parts)


def player_report_option_label(report: dict[str, Any]) -> str:
    """Etiqueta al elegir entre informes del mismo jugador."""
    scout = str(report.get("scout_name") or "").strip()
    date_txt = format_date_for_ui(report.get("report_date"), long=True)
    if scout:
        return f"{date_txt} · {scout}"
    return date_txt


def render_data_source_notice(
    *,
    metrics_are_demo: bool,
    active_season: str | None = None,
) -> str | None:
    """Aviso breve bajo KPIs; None si no hace falta texto."""
    if metrics_are_demo:
        return "Estás utilizando datos de demostración."
    if active_season:
        return f"Estadísticas de la temporada {active_season}."
    return None


def ensure_unique_labels(labels: list[str]) -> list[str]:
    """Desambiguar etiquetas duplicadas sin usar IDs visibles."""
    seen: dict[str, int] = {}
    out: list[str] = []
    for lab in labels:
        n = seen.get(lab, 0) + 1
        seen[lab] = n
        out.append(lab if n == 1 else f"{lab} · ({n})")
    return out
