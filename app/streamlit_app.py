"""Streamlit UI: navegación y orquestación (sin SQL directo)."""

from __future__ import annotations

import html
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from scouting.db import check_database_connection, get_connection
from scouting.services import (
    attribute_ratings_service,
    comparison_cohort_service,
    dashboard_service,
    images_service,
    matching_service,
    metrics_service,
    players_service,
    season_comparison_service,
    sofascore_incremental_runner,
    templates_service,
)
from scouting.config import metric_direction, metric_labels
from scouting.config.sofascore_seasons import get_active_season, get_historical_season, season_ui_label
from scouting.services.templates_service import PRIMARY_POSITIONS_ORDER, get_available_positions
from scouting.services.reports_service import (
    create_scouting_report_from_dict,
    delete_report_permanently,
    fetch_hidden_reports,
    fetch_visible_reports,
    hide_report,
    restore_report,
    update_report_recommendation,
)

_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from ui.debug_mode import is_debug_mode
from auth import clear_authentication, get_auth_setup_error, is_authenticated
from ui.layout import render_page_heading, render_top_header
from ui.login import render_login_page
from ui.components import (
    empty_state,
    form_section,
    metric_card,
    player_header,
    recommendation_tone,
    section_header,
)
from ui.icons import labeled
from ui.presentation import (
    ensure_unique_labels,
    format_date_for_ui,
    format_datetime_for_ui,
    format_number_for_ui,
    player_report_option_label,
    render_data_source_notice,
    render_report_metadata,
    report_option_label,
)
from ui.manual_report_state import (
    apply_pending_manual_report_reset as apply_pending_manual_report_reset_pure,
    attribute_slider_key,
    manual_report_widget_defaults,
    mark_manual_report_reset_pending,
)
from ui.navigation import (
    PREVIOUS_PAGE_KEY,
    build_nav_pages,
)
from ui.pitch_map import render_interactive_pitch
from ui.styles import build_full_width_layout_css
from ui.percentile_markers import (
    comparison_legend_html,
    comparison_percentile_card_html,
    single_player_strip_html,
)
from scouting.config.attribute_rating_scale import (
    RATING_DEFAULT,
    RATING_MAX,
    RATING_MIN,
    RATING_QUARTER_OPTIONS,
    rating_star_fill_percent,
    snap_rating_to_quarters,
)
from ui.theme import (  # noqa: E402
    RADAR_COHORT_FILL,
    RADAR_COHORT_LINE,
    RADAR_PLAYER_FILL,
    RADAR_PLAYER_LINE,
    apply_ohiggins_plotly_theme,
    inject_ohiggins_theme,
    ohiggins_percentile_cell_style,
    ohiggins_percentile_color,
    plotly_radar_chart_config,
)

POSITION_SHORT_LABELS: dict[str, str] = {
    "Portero": "POR",
    "Central derecho": "CD",
    "Central izquierdo": "CI",
    "Lateral derecho": "LD",
    "Lateral izquierdo": "LI",
    "Mediocentro defensivo": "MCD",
    "Mediocentro": "MC",
    "Mediocentro ofensivo": "MCO",
    "Extremo derecho": "ED",
    "Extremo izquierdo": "EI",
    "Delantero": "DC",
}

# Compatibilidad opcional con ?dashboard_position=<slug>
TMAP_SLUG_TO_POSITION: dict[str, str] = {
    "por": "Portero",
    "li": "Lateral izquierdo",
    "ci": "Central izquierdo",
    "cd": "Central derecho",
    "ld": "Lateral derecho",
    "mcd": "Mediocentro defensivo",
    "mc": "Mediocentro",
    "mco": "Mediocentro ofensivo",
    "ei": "Extremo izquierdo",
    "dc": "Delantero",
    "ed": "Extremo derecho",
}

def _nav_pages() -> tuple[str, ...]:
    return build_nav_pages(
        debug_mode=is_debug_mode(),
        show_admin=os.environ.get("SHOW_ADMIN_TAB", "").lower() in ("1", "true", "yes"),
    )


NAV_PAGES: tuple[str, ...] = _nav_pages()

PLAYER_LOOKUP_NONE_LABEL = "— Sin selección —"


def _metric_display_value(value: Any, *, fmt: str | None = None) -> str | int | float:
    """Convierte valores de BD (p. ej. Decimal) a tipos aceptados por st.metric."""
    if value is None:
        return "—"
    if isinstance(value, Decimal):
        num = float(value)
        return format(num, fmt) if fmt else num
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return format(value, fmt) if fmt else value
    if isinstance(value, float):
        return format(value, fmt) if fmt else value
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else "—"
    text = str(value).strip()
    return text if text else "—"


def _ficha_field_html(label: str, value: Any, *, long_text: bool = False) -> str:
    """Campo de ficha con etiqueta azul y valor legible (sin ellipsis)."""
    if value is None or (isinstance(value, str) and not value.strip()):
        disp = "—"
    elif isinstance(value, (int, float, Decimal)):
        disp = _metric_display_value(value)
    else:
        disp = str(value).strip() or "—"
    val_class = "oh-ficha-value oh-ficha-value-long" if long_text else "oh-ficha-value"
    return (
        f'<div class="oh-ficha-field">'
        f'<div class="oh-ficha-label">{html.escape(label)}</div>'
        f'<div class="{val_class}">{html.escape(str(disp))}</div>'
        f"</div>"
    )


def _render_ficha_fields_row(
    fields: list[tuple[str, Any, bool]],
    *,
    columns: int,
) -> None:
    """Renderiza fila de campos de ficha; cada tupla es (label, value, long_text)."""
    if not fields:
        return
    cols = st.columns(columns)
    for col, (label, value, long_text) in zip(cols, fields, strict=True):
        with col:
            st.markdown(_ficha_field_html(label, value, long_text=long_text), unsafe_allow_html=True)


UI_SELECTION_KEYS: tuple[str, ...] = (
    "dashboard_selected_position",
    "selected_player_id",
    "selected_player",
    "player_lookup_selectbox",
    "obj_simple_search",
    "obj_simple_season",
    "obj_simple_competition",
    "obj_simple_position",
    "obj_simple_team",
    "obj_simple_selected_player",
    "obj_simple_chart_metrics",
)



RECOMMENDATION_OPTIONS = (
    "Seguir monitorizando",
    "Interesante",
    "Prioritario",
    "Descartar",
)

PREFERRED_FOOT_OPTIONS = ("Derecho", "Izquierdo", "Ambos", "Desconocido")

# Escala subjetiva: 1.0 … 4.0 en pasos de 0.25 (ver attribute_rating_scale).
SUBJECTIVE_RATING_SCALE_LABEL = "Escala 1-4"


def _project_root() -> Path:
    """Raíz del repo (directorio que contiene `app/` y `data/`). Válido en local y Docker (/app)."""
    return Path(__file__).resolve().parent.parent


def _crest_path() -> Path:
    return _project_root() / "data" / "images" / "escudo.png"


def _sport_logo_path() -> Path:
    return _project_root() / "data" / "images" / "sport.png"


def _crest_available() -> bool:
    return _crest_path().is_file()


def _ohiggins_page_icon() -> str | Any:
    """Escudo O'Higgins para favicon/pestaña del navegador (cuadrado si hace falta)."""
    crest = _crest_path()
    if not crest.is_file():
        return "⚽"
    try:
        from PIL import Image

        with Image.open(crest) as img:
            rgba = img.convert("RGBA")
            side = max(rgba.size)
            canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
            canvas.paste(rgba, ((side - rgba.width) // 2, (side - rgba.height) // 2), rgba)
            return canvas.resize((64, 64), Image.Resampling.LANCZOS)
    except Exception:  # noqa: BLE001
        return str(crest)


def _sport_logo_available() -> bool:
    return _sport_logo_path().is_file()


def _render_player_photo(player: dict[str, Any]) -> None:
    """Muestra la foto del jugador o un placeholder."""
    img_path = images_service.get_player_image_path(player)
    if img_path is not None:
        try:
            st.image(str(img_path), use_container_width=True)
        except Exception:  # noqa: BLE001
            st.warning(
                "No se pudo mostrar la imagen. Para MVP usa PNG/JPG/WebP; "
                "`.avif` depende del soporte AVIF de Pillow en el entorno."
            )
    else:
        st.markdown('<div class="player-photo-placeholder">Sin imagen</div>', unsafe_allow_html=True)


def _position_counts_lookup(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for r in rows:
        pos = r.get("position")
        if not pos:
            continue
        out[str(pos)] = {
            "players_count": int(r.get("players_count") or 0),
            "reports_count": int(r.get("reports_count") or 0),
        }
    return out


def _clear_query_params() -> None:
    st.query_params.clear()


def _clear_ui_selection_state() -> None:
    """Limpia selección/filtros de UI. No toca claves mr_* (formulario Nuevo informe)."""
    for key in UI_SELECTION_KEYS:
        st.session_state.pop(key, None)
    for key in list(st.session_state.keys()):
        if (
            key.startswith("player_lookup_")
            or key.startswith("obj_")
            or key.startswith("matching_")
            or key.startswith("cmp_")
        ):
            st.session_state.pop(key, None)


def _reset_ui_state_on_page_change(new_page: str) -> None:
    """Reset al cambiar de vista (deja mr_* intacto)."""
    _ = new_page
    _clear_ui_selection_state()
    _clear_query_params()


def _handle_page_navigation(current_page: str) -> bool:
    """
    Detecta cambio de página. Si cambió, limpia UI y devuelve True (conviene st.rerun).
    """
    previous_page = st.session_state.get(PREVIOUS_PAGE_KEY)
    if previous_page is None:
        st.session_state[PREVIOUS_PAGE_KEY] = current_page
        return False
    if previous_page != current_page:
        _reset_ui_state_on_page_change(current_page)
        st.session_state[PREVIOUS_PAGE_KEY] = current_page
        return True
    return False


def _logout_current_session() -> None:
    """Cierra sesión sin vaciar todo session_state ni tocar la BD."""
    clear_authentication(st.session_state)


def _sync_dashboard_position_from_query_params(*, clear_url: bool = True) -> str | None:
    """Compatibilidad opcional: lee ?dashboard_position= sin recargar vía <a href>."""
    raw = st.query_params.get("dashboard_position")
    if raw:
        slug = (raw[0] if isinstance(raw, list) else str(raw)).strip().lower()
        position = TMAP_SLUG_TO_POSITION.get(slug)
        if position:
            st.session_state["dashboard_selected_position"] = position
        if clear_url and "dashboard_position" in st.query_params:
            del st.query_params["dashboard_position"]
    return st.session_state.get("dashboard_selected_position")


def _clear_dashboard_position() -> None:
    st.session_state.pop("dashboard_selected_position", None)


def _render_pitch_position_map(counts: dict[str, dict[str, int]], selected: str | None) -> str | None:
    """Campograma Plotly (campo + marcadores en el mismo componente)."""
    return render_interactive_pitch(
        short_labels=POSITION_SHORT_LABELS,
        counts=counts,
        selected=selected,
        on_clear=_clear_dashboard_position,
    )


def _render_position_summary_table(conn, position: str) -> None:
    rows = dashboard_service.get_position_summary(conn, position)
    st.markdown(f"### Jugadores e informes — {position}")
    if not rows:
        st.caption("Sin jugadores para esta posición.")
        return

    table_rows = []
    for r in rows:
        bd_raw = r.get("birth_date")
        bd_val = bd_raw if isinstance(bd_raw, date) else None
        if bd_val is None and bd_raw is not None:
            try:
                bd_val = date.fromisoformat(str(bd_raw)[:10])
            except ValueError:
                bd_val = None
        age = players_service.calculate_age(bd_val)
        lr = r.get("latest_rating")
        reports_n = int(r.get("reports_count") or 0)
        metrics_n = int(r.get("metrics_count") or 0)
        origin = players_service.derive_player_origin(
            has_subjective_reports=reports_n > 0,
            has_objective_metrics=metrics_n > 0,
        )
        table_rows.append(
            {
                "Jugador": r.get("full_name"),
                "Equipo": r.get("current_team") or "—",
                "Edad": age if age is not None else "—",
                "Nacionalidad": r.get("nationality") or "—",
                "Origen": origin,
                "Último informe": r.get("latest_report_date") or "—",
                "Scout": r.get("latest_scout_name") or "—",
                "Rating último informe": float(lr) if lr is not None else "—",
                "Recomendación": r.get("latest_recommendation") or "—",
                "Nº informes": reports_n,
                "Nº métricas objetivas": metrics_n,
            }
        )
    st.dataframe(table_rows, use_container_width=True, hide_index=True)


def _blank_to_none(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _is_plausible_video_url(url: str | None) -> bool:
    if not url or not str(url).strip():
        return False
    try:
        p = urlparse(str(url).strip())
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:  # noqa: BLE001
        return False


def _attr_slider_key(position: str, group: str, attribute: str) -> str:
    return attribute_slider_key(position, group, attribute)


def render_star_rating(rating: float | int, max_rating: float = RATING_MAX) -> str:
    """Estrellas con color contextual según nivel (1–4)."""
    m = float(max_rating)
    if m <= 0:
        m = RATING_MAX
    r = max(RATING_MIN, min(float(rating), m))
    pct = rating_star_fill_percent(r, m)
    tone = _rating_tone_class(r)
    r_txt = f"{r:.2f}".rstrip("0").rstrip(".")
    if abs(m - round(m)) < 1e-9:
        m_txt = str(int(round(m)))
    else:
        m_txt = f"{m:.2f}".rstrip("0").rstrip(".")
    r_s = html.escape(r_txt)
    m_s = html.escape(m_txt)
    return (
        f'<div class="star-rating-row star-rating-row--{tone}">'
        '<div class="star-rating-wrap star-rating-wrap--four">'
        '<div class="stars-bg">★★★★</div>'
        f'<div class="stars-fill" style="width:{pct:.2f}%">★★★★</div>'
        "</div>"
        f'<span class="star-rating-pill star-rating-pill--{tone}">{r_s}</span>'
        f'<span class="star-rating-num">/{m_s}</span>'
        "</div>"
    )


def _rating_tone_class(value: float) -> str:
    """Bajo / medio / bueno / alto para la escala subjetiva 1–4."""
    v = float(value)
    if v < 2.0:
        return "low"
    if v < 3.0:
        return "mid"
    if v < 3.75:
        return "good"
    return "high"


def _snap_rating_to_quarters(value: float, max_rating: float = RATING_MAX) -> float:
    return snap_rating_to_quarters(value, min_value=RATING_MIN, max_value=max_rating)


def render_star_rating_input(
    attribute_key: str,
    label: str,
    default: float = RATING_DEFAULT,
    max_rating: float = RATING_MAX,
) -> float:
    """
    Selector visual por estrellas (sin slider): session_state + botones ±0.25 y atajos 1–4.
    Debe renderizarse fuera de st.form (los botones no funcionan dentro del formulario).
    Sin contenedor bordeado: la jerarquía viene del color del nivel.
    """
    mx = float(max_rating)
    if attribute_key not in st.session_state:
        st.session_state[attribute_key] = float(_snap_rating_to_quarters(default, mx))

    v = max(RATING_MIN, min(mx, float(_snap_rating_to_quarters(float(st.session_state[attribute_key]), mx))))
    st.session_state[attribute_key] = v
    tone = _rating_tone_class(v)
    r_txt = f"{v:.2f}".rstrip("0").rstrip(".")

    st.markdown(
        f'<div class="rating-attr-row rating-attr-row--{tone}">'
        f'<div class="rating-attr-head">'
        f'<span class="rating-attr-label">{html.escape(label)}</span>'
        f'<span class="star-rating-pill star-rating-pill--{tone}">{html.escape(r_txt)}</span>'
        f"</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="manual-form-big-stars rating-stars--{tone}">{render_star_rating(v, mx)}</div>',
        unsafe_allow_html=True,
    )
    row1 = st.columns([1.0, 1.0, 5.0], gap="small")
    with row1[0]:
        if st.button("−0.25", key=f"{attribute_key}__dec", use_container_width=True):
            st.session_state[attribute_key] = max(RATING_MIN, _snap_rating_to_quarters(v - 0.25, mx))
            st.rerun()
    with row1[1]:
        if st.button("+0.25", key=f"{attribute_key}__inc", use_container_width=True):
            st.session_state[attribute_key] = min(mx, _snap_rating_to_quarters(v + 0.25, mx))
            st.rerun()
    with row1[2]:
        qcols = st.columns(4, gap="small")
        for i, q in enumerate((1.0, 2.0, 3.0, 4.0)):
            with qcols[i]:
                selected = abs(v - q) < 1e-9
                if st.button(
                    str(int(q)),
                    key=f"{attribute_key}__q{i}",
                    use_container_width=True,
                    type="primary" if selected else "secondary",
                ):
                    st.session_state[attribute_key] = float(q)
                    st.rerun()
    st.caption(f"Escala {SUBJECTIVE_RATING_SCALE_LABEL} · paso 0.25")

    return float(st.session_state[attribute_key])


def _float01(x: Any) -> float:
    if x is None:
        return 0.0
    return float(x)


def _ordered_attribute_groups(attr_rows: list[dict[str, Any]], player_position: str | None) -> list[str]:
    keys = {str(r.get("attribute_group") or "—") for r in attr_rows}
    return templates_service.ordered_attribute_groups_for_position(keys, player_position)


def _sort_rows_in_group(
    rows: list[dict[str, Any]], player_position: str | None, group: str
) -> list[dict[str, Any]]:
    if not player_position:
        return sorted(rows, key=lambda r: str(r.get("attribute_name") or ""))
    idx = templates_service.attribute_order_index_within_group(player_position, group)
    if not idx:
        return sorted(rows, key=lambda r: str(r.get("attribute_name") or ""))

    def sort_key(r: dict[str, Any]) -> tuple[int, str]:
        name = str(r.get("attribute_name") or "")
        return (idx.get(name, 999), name)

    return sorted(rows, key=sort_key)


def _build_position_radar_figure(
    bench_rows: list[dict[str, Any]],
    player_name: str,
    position: str,
) -> go.Figure | None:
    if not bench_rows:
        return None
    theta = [str(r["attribute_name"]) for r in bench_rows]
    r1 = [float(r["player_avg_rating"]) for r in bench_rows]
    r2 = [float(r["position_avg_rating"]) for r in bench_rows]
    theta_c = theta + [theta[0]]
    r1_c = r1 + [r1[0]]
    r2_c = r2 + [r2[0]]
    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=r1_c,
            theta=theta_c,
            name="Jugador",
            line=dict(color=RADAR_PLAYER_LINE, width=2.5),
            fillcolor=RADAR_PLAYER_FILL,
            fill="toself",
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=r2_c,
            theta=theta_c,
            name="Media posición",
            line=dict(color=RADAR_COHORT_LINE, width=2),
            fillcolor=RADAR_COHORT_FILL,
            fill="toself",
        )
    )
    fig.update_layout(
        title=dict(text=f"{player_name} — Media vs {position}", font=dict(size=16)),
        polar=dict(radialaxis=dict(visible=True, range=[RATING_MIN, RATING_MAX], tick0=RATING_MIN, dtick=0.5), angularaxis=dict(direction="clockwise")),
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-0.12, x=0.5, xanchor="center"),
        margin=dict(l=80, r=80, t=80, b=90),
        height=480,
    )
    return apply_ohiggins_plotly_theme(fig)


def _render_db_banner(*, page: str | None = None) -> None:
    ok, message = check_database_connection()
    _ = page
    if not ok:
        st.error(message)
        st.stop()


def _current_auth_username() -> str | None:
    return (os.environ.get("SCOUTING_USERNAME") or "").strip() or None


def _dashboard_flash_pop() -> None:
    msg = st.session_state.pop("dashboard_flash_success", None)
    if msg:
        st.success(msg)
    err = st.session_state.pop("dashboard_flash_error", None)
    if err:
        st.error(err)
    # Limpieza diferida de checkboxes/selects (antes de crear widgets).
    if st.session_state.pop("dashboard_clear_action_widgets", False):
        for key in (
            "dashboard_confirm_hide",
            "dashboard_selected_report_label",
            "hidden_selected_report_label",
        ):
            st.session_state.pop(key, None)
        # Confirmaciones de borrado ligadas a un report_id concreto.
        for key in list(st.session_state.keys()):
            if str(key).startswith("dashboard_confirm_delete_") or str(key).startswith(
                "hidden_confirm_delete_"
            ):
                st.session_state.pop(key, None)


def _render_visible_reports_management(reports: list[dict[str, Any]]) -> None:
    """Editar recomendación / ocultar / eliminar sobre informes visibles del dashboard."""
    if not reports:
        empty_state(
            "Todavía no hay informes disponibles.",
            "Cuando registres evaluaciones, podrás editarlas u ocultarlas aquí.",
            icon="document",
        )
        return

    raw_labels = [report_option_label(r) for r in reports]
    unique_labels = ensure_unique_labels(raw_labels)
    labels: dict[str, int] = {}
    by_id: dict[int, dict[str, Any]] = {}
    for r, lab in zip(reports, unique_labels, strict=True):
        rid = int(r["id"])
        by_id[rid] = r
        labels[lab] = rid

    selected_label = st.selectbox(
        "Seleccionar informe",
        options=list(labels.keys()),
        key="dashboard_selected_report_label",
    )
    report_id = labels[selected_label]
    report = by_id[report_id]

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"**Jugador:** {report.get('player_full_name') or '—'}")
    c2.markdown(f"**Scout:** {report.get('scout_name') or '—'}")
    c3.markdown(f"**Posición:** {report.get('player_position') or '—'}")
    st.caption(render_report_metadata(report))

    current_rec = str(report.get("recommendation") or RECOMMENDATION_OPTIONS[0])
    if current_rec not in RECOMMENDATION_OPTIONS:
        current_rec = RECOMMENDATION_OPTIONS[0]
    rec_index = list(RECOMMENDATION_OPTIONS).index(current_rec)

    new_recommendation = st.selectbox(
        "Recomendación",
        options=list(RECOMMENDATION_OPTIONS),
        index=rec_index,
        key=f"dashboard_rec_editor_{report_id}",
    )

    b1, b2 = st.columns(2)
    save_clicked = b1.button(labeled("save", "Guardar cambios"), type="primary", key="dashboard_save_report")
    hide_clicked = b2.button(labeled("hide", "Ocultar informe"), type="secondary", key="dashboard_hide_report")

    confirm_hide = st.checkbox(
        "Confirmo que quiero ocultar este informe",
        key="dashboard_confirm_hide",
    )

    player_name = report.get("player_full_name") or "el jugador"
    if save_clicked:
        try:
            with get_connection() as conn:
                update_report_recommendation(conn, report_id, new_recommendation)
            st.session_state["dashboard_flash_success"] = (
                f"Recomendación actualizada · {player_name}."
            )
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"No se pudo guardar: {exc}")

    if hide_clicked:
        if not confirm_hide:
            st.warning("Marca la casilla de confirmación para ocultar el informe.")
        else:
            try:
                with get_connection() as conn:
                    hide_report(conn, report_id, hidden_by=_current_auth_username())
                st.session_state["dashboard_clear_action_widgets"] = True
                st.session_state["dashboard_flash_success"] = (
                    f"Informe de {player_name} ocultado. Puedes recuperarlo en «Informes ocultos»."
                )
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"No se pudo ocultar: {exc}")

    with st.expander("Eliminar permanentemente (irreversible)", expanded=False):
        st.markdown(
            f"- **Jugador:** {report.get('player_full_name') or '—'}\n"
            f"- **Fecha:** {format_date_for_ui(report.get('report_date'))}\n"
            f"- **Scout:** {report.get('scout_name') or '—'}"
        )
        st.caption("Esta acción no se puede deshacer.")
        confirm_delete = st.checkbox(
            "Confirmo que quiero eliminar este informe de forma permanente",
            key=f"dashboard_confirm_delete_{report_id}",
        )
        if st.button(
            labeled("delete", "Eliminar permanentemente"),
            type="secondary",
            key=f"dashboard_delete_permanent_{report_id}",
            disabled=not confirm_delete,
        ):
            try:
                with get_connection() as conn:
                    deleted = delete_report_permanently(conn, report_id)
                if deleted:
                    st.session_state["dashboard_clear_action_widgets"] = True
                    st.session_state["dashboard_flash_success"] = (
                        f"Informe de {player_name} eliminado permanentemente."
                    )
                    st.rerun()
                else:
                    st.error("No se encontró el informe a eliminar.")
            except Exception as exc:  # noqa: BLE001
                st.error(f"No se pudo eliminar: {exc}")


def _render_hidden_reports_page() -> None:
    _dashboard_flash_pop()
    st.caption("Restaura informes ocultos o elimínalos de forma permanente.")

    with get_connection() as conn:
        hidden = fetch_hidden_reports(conn, limit=200)

    if not hidden:
        empty_state(
            "No hay informes ocultos.",
            "Cuando ocultes un informe desde el Dashboard, aparecerá aquí.",
            icon="hidden",
        )
        return

    rows = [
        {
            "Jugador": r.get("player_full_name"),
            "Posición": r.get("player_position"),
            "Scout": r.get("scout_name"),
            "Fecha": format_date_for_ui(r.get("report_date"), long=False),
            "Recomendación": r.get("recommendation"),
            "Ocultado": format_datetime_for_ui(r.get("hidden_at")),
            "Ocultado por": r.get("hidden_by") or "—",
        }
        for r in hidden
    ]
    st.dataframe(_style_recommendation_dataframe(rows), use_container_width=True, hide_index=True)

    raw_labels = [
        f"{r.get('player_full_name') or 'Jugador'} · {format_datetime_for_ui(r.get('hidden_at'))}"
        for r in hidden
    ]
    unique_labels = ensure_unique_labels(raw_labels)
    labels = {lab: int(r["id"]) for lab, r in zip(unique_labels, hidden, strict=True)}
    by_id = {int(r["id"]): r for r in hidden}
    selected_label = st.selectbox(
        "Seleccionar informe oculto",
        options=list(labels.keys()),
        key="hidden_selected_report_label",
    )
    report_id = labels[selected_label]
    report = by_id[report_id]
    player_name = report.get("player_full_name") or "el jugador"

    st.markdown(
        f"**{report.get('player_full_name') or '—'}** · "
        f"{format_date_for_ui(report.get('report_date'))} · "
        f"Scout: {report.get('scout_name') or '—'}"
    )

    r1, r2 = st.columns([1, 1.4])
    if r1.button(labeled("restore", "Restaurar"), type="secondary", key="hidden_restore_report"):
        try:
            with get_connection() as conn:
                restore_report(conn, report_id)
            st.session_state["dashboard_clear_action_widgets"] = True
            st.session_state["dashboard_flash_success"] = (
                f"Informe de {player_name} restaurado; vuelve a aparecer en el dashboard."
            )
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"No se pudo restaurar: {exc}")

    with r2:
        confirm = st.checkbox(
            "Confirmo eliminación permanente",
            key=f"hidden_confirm_delete_{report_id}",
        )
        if st.button(
            labeled("delete", "Eliminar permanentemente"),
            key=f"hidden_delete_permanent_{report_id}",
            type="secondary",
            disabled=not confirm,
        ):
            try:
                with get_connection() as conn:
                    deleted = delete_report_permanently(conn, report_id)
                if deleted:
                    st.session_state["dashboard_clear_action_widgets"] = True
                    st.session_state["dashboard_flash_success"] = (
                        f"Informe de {player_name} eliminado permanentemente."
                    )
                    st.rerun()
                else:
                    st.error("No se encontró el informe.")
            except Exception as exc:  # noqa: BLE001
                st.error(f"No se pudo eliminar: {exc}")


def _style_recommendation_dataframe(rows: list[dict[str, Any]]) -> Any:
    """Aplica badge de color solo a la columna Recomendación (sin colorear filas)."""
    if not rows:
        return rows
    df = pd.DataFrame(rows)

    def _rec_style(val: Any) -> str:
        styles = recommendation_tone(str(val) if val is not None else None)
        return "; ".join(f"{k}: {v}" for k, v in styles.items())

    if "Recomendación" not in df.columns:
        return df
    return df.style.map(_rec_style, subset=["Recomendación"])


def _render_dashboard() -> None:
    _dashboard_flash_pop()

    with get_connection() as conn:
        snap = dashboard_service.get_dashboard_snapshot(conn, recent_reports_limit=25)
        pos_counts_rows = dashboard_service.get_position_counts(conn)
        counts_map = _position_counts_lookup(pos_counts_rows)
        visible_reports = fetch_visible_reports(conn, limit=50)

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        metric_card(
            "Jugadores scouteados",
            format_number_for_ui(snap["player_count"]),
            icon="users",
            tone="blue",
        )
    with k2:
        metric_card(
            "Informes activos",
            format_number_for_ui(snap["report_count"]),
            icon="document",
            tone="green",
        )
    with k3:
        metric_card(
            "Informes ocultos",
            format_number_for_ui(snap.get("hidden_report_count", 0)),
            icon="hidden",
            tone="yellow",
        )
    with k4:
        metric_card(
            "Scouts",
            format_number_for_ui(snap["scout_count"]),
            icon="scout",
            tone="info",
        )
    with k5:
        metric_card(
            "Métricas objetivas",
            format_number_for_ui(snap["metric_count"]),
            icon="chart",
            tone="slate",
        )
    kpi_notice = render_data_source_notice(
        metrics_are_demo=bool(snap.get("metrics_are_demo")),
        active_season=get_active_season(),
    )
    if kpi_notice:
        st.caption(kpi_notice)

    section_header(
        "Actividad reciente",
        "Últimos informes registrados.",
        icon="activity",
    )
    recent = snap["recent_reports"]
    if not recent:
        empty_state(
            "Todavía no hay informes disponibles.",
            "Cuando se registren evaluaciones, aparecerán aquí.",
            icon="document",
        )
    else:
        rows = [
            {
                "Fecha": format_date_for_ui(r.get("report_date"), long=False),
                "Jugador": r.get("player_full_name"),
                "Posición": r.get("player_position"),
                "Scout": r.get("scout_name"),
                "Competición": r.get("competition"),
                "Valoración": r.get("rating"),
                "Recomendación": r.get("recommendation"),
            }
            for r in recent
        ]
        st.dataframe(_style_recommendation_dataframe(rows), use_container_width=True, hide_index=True)

    from ui.data_sync_card import render_data_sync_card

    render_data_sync_card(key_prefix="dashboard")

    section_header(
        "Gestión de informes",
        "Edita, oculta o elimina informes.",
        icon="edit",
    )
    _render_visible_reports_management(visible_reports)

    _sync_dashboard_position_from_query_params()
    selected_position = st.session_state.get("dashboard_selected_position")
    selected_position = _render_pitch_position_map(counts_map, selected_position)

    if selected_position:
        with get_connection() as conn:
            _render_position_summary_table(conn, str(selected_position))


def _manual_report_init_defaults() -> None:
    """Valores por defecto del alta manual (st.session_state)."""
    defaults = manual_report_widget_defaults(
        recommendation_default=RECOMMENDATION_OPTIONS[0],
        preferred_foot_default=PREFERRED_FOOT_OPTIONS[0],
    )
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def _apply_pending_manual_report_reset() -> None:
    """
    Limpia el formulario ANTES de instanciar widgets mr_* / attr_*.
    Debe llamarse al inicio de _render_new_report, nunca tras crear los widgets.
    """
    template_position = st.session_state.get("manual_report_reset_template_position")
    template_for_position = None
    if template_position and not st.session_state.get("manual_report_reset_attr_keys"):
        template_for_position = templates_service.get_template_for_position(str(template_position))

    apply_pending_manual_report_reset_pure(
        st.session_state,
        recommendation_default=RECOMMENDATION_OPTIONS[0],
        preferred_foot_default=PREFERRED_FOOT_OPTIONS[0],
        rating_default=float(RATING_DEFAULT),
        template_for_position=template_for_position,
    )


def _render_new_report() -> None:
    # Reset diferido: limpiar claves de widgets ANTES de crearlos.
    _apply_pending_manual_report_reset()
    _manual_report_init_defaults()

    success_message = st.session_state.pop("manual_report_success_message", None)
    if success_message:
        st.success(success_message)

    positions = templates_service.get_available_positions()
    template_position = st.selectbox(
        "Posición principal (plantilla de atributos subjetivos)",
        options=positions,
        index=0,
        key="manual_report_template_position",
        help=(
            "Carga la plantilla por rol (CONSTRUCCIÓN EN SALIDA, DEFENSIVO, OFENSIVO, …). "
            "Lateral izquierdo → plantilla Lateral; Mediocentro defensivo → Volante central."
        ),
    )
    template = templates_service.get_template_for_position(template_position)

    with st.container(border=False):
        form_section(
            "1. Jugador y posición",
            "Identificación básica y plantilla de atributos.",
            icon="player",
        )
        pc1, pc2 = st.columns(2)
        player_name = pc1.text_input("Nombre del jugador *", placeholder="Ej. João Silva", key="mr_player_name")
        current_team = pc2.text_input("Equipo actual", placeholder="Opcional", key="mr_current_team")

        pc3, pc4 = st.columns(2)
        nationality = pc3.text_input("Nacionalidad", placeholder="Opcional", key="mr_nationality")
        st.caption(f"Posición en ficha: **{template_position}** (coincide con la plantilla seleccionada arriba).")

        st.markdown("**Datos del jugador · físicos / identificación**")
        st.checkbox("Registrar fecha de nacimiento", key="mr_register_birth")
        if st.session_state.get("mr_register_birth"):
            bd_input = st.date_input(
                "Fecha de nacimiento",
                min_value=date(1955, 1, 1),
                max_value=date.today(),
                key="mr_birth_date",
            )
            age_est = players_service.calculate_age(bd_input)
            if age_est is not None:
                st.caption(f"Edad estimada (respecto a hoy): **{age_est}** años")

        pf1, pf2 = st.columns(2)
        pf1.selectbox("Pie hábil", PREFERRED_FOOT_OPTIONS, key="mr_preferred_foot")
        pf2.number_input(
            "Altura (cm) · usar **0** si no aplica",
            min_value=0,
            max_value=260,
            step=1,
            key="mr_height_cm",
        )
        player_photo = st.file_uploader(
            "Foto del jugador",
            type=["png", "jpg", "jpeg", "webp"],
            help="Se guarda en data/images/players/ tras crear el jugador. Si ya tenía foto, se sustituye.",
        )

        form_section(
            "2. Contexto del partido",
            "Scout, fecha y condiciones de observación.",
            icon="activity",
        )
        rc1, rc2, rc3 = st.columns(3)
        scout_name = rc1.text_input("Scout *", placeholder="Nombre del ojeador", key="mr_scout_name")
        report_date = rc2.date_input("Fecha del informe", key="mr_report_date")
        competition = rc3.text_input("Competición", placeholder="Opcional", key="mr_competition")

        rc4, rc5, rc6 = st.columns(3)
        match_observed = rc4.text_input("Partido observado", placeholder="Opcional", key="mr_match_observed")
        position_observed = rc5.text_input(
            "Posición observada en partido", placeholder="Ej. carril izquierdo", key="mr_position_observed"
        )
        st.multiselect(
            "Posiciones alternativas",
            options=get_available_positions(),
            key="mr_alternative_positions",
            help="Roles adicionales observados en el informe (opcional).",
        )
        minutes_observed = rc6.number_input(
            "Minutos observados",
            min_value=0,
            max_value=130,
            key="mr_minutes",
            help="Usa 0 si no aplica o no se registraron minutos.",
        )

        st.text_input(
            "URL de vídeo (jugador o partido observado)",
            placeholder="https://…",
            key="mr_video_url",
            help="Enlace externo; no se incrusta el reproductor en esta versión.",
        )

        form_section(
            "3. Evaluación general",
            "Rating, fortalezas, debilidades y recomendación.",
            icon="edit",
        )
        rating = st.slider("Rating general (0–10)", min_value=0.0, max_value=10.0, step=0.5, key="mr_rating_scout")
        strengths = st.text_area("Fortalezas", height=100, key="mr_strengths")
        weaknesses = st.text_area("Debilidades", height=100, key="mr_weaknesses")
        summary = st.text_area("Resumen", height=100, key="mr_summary")
        recommendation = st.selectbox("Recomendación final", RECOMMENDATION_OPTIONS, key="mr_recommendation")

    form_section(
        "4. Atributos por posición",
        f"{SUBJECTIVE_RATING_SCALE_LABEL}, paso 0.25.",
        icon="chart",
    )
    st.caption(
        "Pulsa **◀ −0.25** / **+0.25 ▶** o un atajo **1–4**. Las estrellas doradas reflejan el valor; "
        f"escala **{SUBJECTIVE_RATING_SCALE_LABEL}**. La cifra bajo los botones es orientativa."
    )
    for group_name, attr_list in template.items():
        st.markdown(f"**{group_name}**")
        for attr in attr_list:
            ak = _attr_slider_key(template_position, group_name, attr)
            render_star_rating_input(ak, attr, RATING_DEFAULT, RATING_MAX)

    save_col, clear_col = st.columns([1.2, 1.2])
    with save_col:
        save_clicked = st.button(labeled("save", "Guardar informe"), type="primary", key="mr_submit")
    with clear_col:
        clear_clicked = st.button(
            labeled("clear", "Limpiar formulario"),
            type="secondary",
            key="mr_clear_form",
        )

    if clear_clicked:
        mark_manual_report_reset_pending(
            st.session_state,
            success_message="",
            template_position=str(template_position),
            template=template,
        )
        st.rerun()

    if not save_clicked:
        return

    if not (player_name and str(player_name).strip()):
        st.error("El nombre del jugador es obligatorio.")
        return
    if not (scout_name and str(scout_name).strip()):
        st.error("El scout es obligatorio.")
        return

    mins = int(minutes_observed) if minutes_observed is not None else 0
    if mins == 0:
        mins = None

    ratings_payload = []
    for g, attrs in template.items():
        for a in attrs:
            ak = _attr_slider_key(template_position, g, a)
            rv = float(st.session_state.get(ak, RATING_DEFAULT))
            rv = float(_snap_rating_to_quarters(rv, RATING_MAX))
            rv = max(RATING_MIN, min(RATING_MAX, rv))
            ratings_payload.append(
                {"attribute_group": g, "attribute_name": a, "rating": rv, "max_rating": RATING_MAX}
            )

    birth_date_submit = (
        st.session_state["mr_birth_date"] if st.session_state.get("mr_register_birth") else None
    )
    h_cm = int(st.session_state.get("mr_height_cm") or 0)
    height_submit = float(h_cm) if h_cm > 0 else None

    payload = {
        "player_name": str(player_name).strip(),
        "source_type": "manual",
        "source_name": "Formulario Streamlit",
        "scout_name": str(scout_name).strip(),
        "report_date": report_date,
        "competition": _blank_to_none(competition),
        "match_observed": _blank_to_none(match_observed),
        "position_observed": _blank_to_none(position_observed),
        "minutes_observed": mins,
        "summary": _blank_to_none(summary),
        "strengths": _blank_to_none(strengths),
        "weaknesses": _blank_to_none(weaknesses),
        "recommendation": recommendation,
        "rating": rating,
        "nationality": _blank_to_none(nationality),
        "position": template_position,
        "current_team": _blank_to_none(current_team),
        "birth_date": birth_date_submit,
        "preferred_foot": st.session_state.get("mr_preferred_foot"),
        "height_cm": height_submit,
        "video_url": _blank_to_none(st.session_state.get("mr_video_url")),
        "alternative_positions": st.session_state.get("mr_alternative_positions") or [],
        "raw_payload": {
            "entry": "streamlit_manual_form",
            "ui_version": 3,
            "template_position": template_position,
        },
    }

    try:
        with get_connection() as conn:
            report_id, player_created, player_id = create_scouting_report_from_dict(conn, payload)
            attribute_ratings_service.save_attribute_ratings_for_report(conn, report_id, ratings_payload)
            if player_photo is not None:
                player_row = players_service.fetch_player(conn, player_id)
                norm = (player_row or {}).get("normalized_name") or players_service.normalize_player_name(
                    str(player_name).strip()
                )
                rel_path = images_service.save_player_image(player_photo, player_id, norm)
                players_service.update_player_image_path(conn, player_id, rel_path)
    except Exception as exc:  # noqa: BLE001
        st.error(f"No se pudo guardar el informe: {exc}")
        return

    # No modificar claves de widgets ya instanciados: reset diferido en el próximo run.
    created_note = " (jugador nuevo)" if player_created else ""
    mark_manual_report_reset_pending(
        st.session_state,
        success_message=(
            f"Informe guardado correctamente{created_note}."
        ),
        template_position=template_position,
        template=template,
    )
    st.rerun()


def _fmt_objective_summary_value(val: Any) -> str:
    if val is None:
        return "—"
    try:
        num = float(val)
    except (TypeError, ValueError):
        return str(val)
    if abs(num - round(num)) < 0.001:
        return str(int(round(num)))
    return f"{num:.2f}"


def _objective_block_label(row: dict[str, Any]) -> str:
    season = metric_labels.format_season_label(row.get("season"))
    comp = row.get("competition") or "—"
    team = row.get("objective_team") or "—"
    return f"{row.get('player_name')} · {team} · {season} · {comp}"


def _build_vs_position_grouped_bar(
    comparison_rows: list[dict[str, Any]],
    *,
    x_title: str = "",
) -> go.Figure | None:
    if not comparison_rows:
        return None
    labels = [metric_labels.metric_label(str(r["metric_name"])) for r in comparison_rows]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Jugador",
            y=labels,
            x=[float(r["player_value"]) for r in comparison_rows],
            orientation="h",
            text=[
                metric_labels.format_metric_value(
                    r.get("player_value"),
                    r.get("metric_unit"),
                    metric_name=str(r.get("metric_name") or ""),
                )
                for r in comparison_rows
            ],
            textposition="outside",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Media posición",
            y=labels,
            x=[float(r["position_avg_value"]) for r in comparison_rows],
            orientation="h",
            text=[
                metric_labels.format_metric_value(
                    r.get("position_avg_value"),
                    r.get("metric_unit"),
                    metric_name=str(r.get("metric_name") or ""),
                )
                for r in comparison_rows
            ],
            textposition="outside",
        )
    )
    layout: dict[str, Any] = {
        "barmode": "group",
        "height": max(360, 32 * len(labels)),
        "margin": dict(l=12, r=12, t=36, b=12),
        "legend": dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    }
    if x_title:
        layout["xaxis"] = {"title": x_title}
    fig.update_layout(**layout)
    return apply_ohiggins_plotly_theme(fig)


_RADAR_SHORT_LABEL_OVERRIDES: dict[str, str] = {
    "Encuentra línea de pases": "Líneas pase",
    "Lectura de juego": "Lectura",
    "Va a campo rival": "Agresividad",
    "Salida de balón": "Salida",
    "Primer toque": "1er toque",
    "Juego entre líneas": "Entre líneas",
    "Presión al portador": "Presión",
    "Coberturas y ayudas": "Coberturas",
    "Duelos aéreos": "Aéreos",
    "1 contra 1 defensivo": "1v1 def.",
    "Anticipación": "Anticip.",
    "Desmarques": "Desmarques",
    "Finalización": "Finaliz.",
    "Creatividad": "Creativ.",
    "Centros": "Centros",
    "Regates": "Regates",
    "Juego de espaldas": "Espaldas",
}


def _short_radar_label(full: str, *, attribute_group: str = "") -> tuple[str, str]:
    """Devuelve (etiqueta corta, etiqueta completa para tooltip)."""
    full_s = str(full or "").strip()
    short = full_s
    if " · " in full_s:
        short = full_s.rsplit(" · ", 1)[-1].strip()
    elif " – " in full_s:
        short = full_s.rsplit(" – ", 1)[-1].strip()
    short = _RADAR_SHORT_LABEL_OVERRIDES.get(short, short)
    grp = str(attribute_group or "").lower()
    if "agresividad" in grp and "campo rival" in short.lower():
        short = "Agresividad"
    if len(short) > 10:
        words = short.split()
        if len(words) > 1 and len(words[0]) <= 8:
            short = words[0]
        if len(short) > 10:
            short = short[:9] + "…"
    return short, full_s


def _build_subjective_radar_figure(
    rows: list[dict[str, Any]],
    *,
    label_key: str,
    player_key: str = "player_avg_rating",
    position_key: str = "position_avg_rating",
    player_trace_name: str = "Jugador",
    cohort_trace_name: str = "Media plantilla",
    title: str = "",
    height: int = 480,
    attribute_group: str = "",
    compact_labels: bool = True,
    radar_size: str = "detail",
) -> go.Figure | None:
    if not rows:
        return None

    full_theta = [str(r[label_key]) for r in rows]
    if compact_labels and label_key == "attribute_name":
        theta = [_short_radar_label(t, attribute_group=attribute_group)[0] for t in full_theta]
    elif compact_labels and label_key == "attribute_group":
        theta = [_short_radar_label(t)[0] for t in full_theta]
    else:
        theta = full_theta

    r1 = [float(r[player_key]) for r in rows]
    r2 = [float(r[position_key]) for r in rows]
    theta_c = theta + [theta[0]]
    r1_c = r1 + [r1[0]]
    r2_c = r2 + [r2[0]]

    hover_player = [
        f"<b>{full}</b><br>{player_trace_name}: {v:.2f}"
        for full, v in zip(full_theta, r1, strict=True)
    ]
    hover_player.append(hover_player[0])
    hover_cohort = [
        f"<b>{full}</b><br>{cohort_trace_name}: {v:.2f}"
        for full, v in zip(full_theta, r2, strict=True)
    ]
    hover_cohort.append(hover_cohort[0])

    n_axes = len(theta)
    tick_font = max(7, min(9, 11 - n_axes // 2))

    if radar_size == "blocks":
        height = 460
        margins = dict(l=40, r=40, t=50, b=40)
        legend_y = 1.06
        polar_domain = dict(x=[0.06, 0.94], y=[0.06, 0.94])
        show_legend = True
    else:
        height = 400
        margins = dict(l=30, r=30, t=40, b=30)
        legend_y = -0.15
        polar_domain = dict(x=[0.04, 0.96], y=[0.04, 0.96])
        show_legend = False
        if n_axes >= 10:
            tick_font = max(6, tick_font - 1)
            margins = dict(l=26, r=26, t=36, b=28)

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=r1_c,
            theta=theta_c,
            name=player_trace_name,
            line=dict(color=RADAR_PLAYER_LINE, width=2.5),
            fillcolor=RADAR_PLAYER_FILL,
            fill="toself",
            hovertext=hover_player,
            hoverinfo="text",
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=r2_c,
            theta=theta_c,
            name=cohort_trace_name,
            line=dict(color=RADAR_COHORT_LINE, width=2),
            fillcolor=RADAR_COHORT_FILL,
            fill="toself",
            hovertext=hover_cohort,
            hoverinfo="text",
        )
    )
    layout: dict[str, Any] = dict(
        polar=dict(
            domain=polar_domain,
            radialaxis=dict(
                visible=True,
                range=[RATING_MIN, RATING_MAX],
                tick0=RATING_MIN,
                dtick=0.5,
                tickfont=dict(size=9),
            ),
            angularaxis=dict(
                direction="clockwise",
                tickfont=dict(size=tick_font),
                layer="below traces",
            ),
        ),
        showlegend=show_legend,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=legend_y,
            x=0.5,
            xanchor="center",
            font=dict(size=10),
        ) if show_legend else dict(),
        margin=margins,
        height=height,
    )
    if title:
        layout["title"] = dict(text=title, font=dict(size=15), x=0.5, xanchor="center")
    fig.update_layout(**layout)
    return apply_ohiggins_plotly_theme(
        fig,
        height=height,
        margin=margins,
        showlegend=show_legend,
    )


def _render_detail_radar_grid(group_figures: list[tuple[str, go.Figure]]) -> None:
    """Radares de detalle en filas de 3 columnas (izquierda → derecha)."""
    if not group_figures:
        return

    chart_cfg = plotly_radar_chart_config()
    st.markdown(
        '<span class="subjective-radar-detail-grid-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="subjective-radar-legend-once">'
        '<span class="subjective-radar-legend-swatch subjective-radar-legend-swatch--player"></span> Jugador '
        '<span class="subjective-radar-legend-swatch subjective-radar-legend-swatch--cohort"></span> Media plantilla'
        "</p>",
        unsafe_allow_html=True,
    )

    for i in range(0, len(group_figures), 3):
        chunk = group_figures[i : i + 3]
        cols = st.columns(3, gap="small")
        for col, (group_name, fig_detail) in zip(cols, chunk, strict=True):
            with col:
                st.markdown(f"**{html.escape(group_name)}**")
                st.plotly_chart(fig_detail, use_container_width=True, config=chart_cfg)


def _build_subjective_grouped_bar(
    rows: list[dict[str, Any]],
    *,
    label_key: str,
    player_key: str,
    position_key: str,
    x_title: str = "Rating (1–4)",
    attribute_group: str = "",
) -> go.Figure | None:
    if not rows:
        return None
    full_labels = [str(r[label_key]) for r in rows]
    if label_key == "attribute_name":
        labels = [_short_radar_label(t, attribute_group=attribute_group)[0] for t in full_labels]
    else:
        labels = [_short_radar_label(t)[0] for t in full_labels]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Jugador",
            y=labels,
            x=[float(r[player_key]) for r in rows],
            orientation="h",
            customdata=full_labels,
            hovertemplate="<b>%{customdata}</b><br>Jugador: %{x:.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Media plantilla",
            y=labels,
            x=[float(r[position_key]) for r in rows],
            orientation="h",
            customdata=full_labels,
            hovertemplate="<b>%{customdata}</b><br>Media plantilla: %{x:.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        barmode="group",
        height=max(280, 40 * len(labels)),
        margin=dict(l=12, r=12, t=36, b=72),
        xaxis=dict(title=x_title, range=[RATING_MIN, RATING_MAX]),
        legend=dict(orientation="h", yanchor="top", y=-0.18, x=0.5, xanchor="center"),
    )
    return apply_ohiggins_plotly_theme(fig)


def _aggregate_subjective_benchmark_by_group(
    bench: list[dict[str, Any]],
    *,
    position: str | None,
) -> list[dict[str, Any]]:
    """Media por bloque (attribute_group) para jugador y cohorte."""
    from collections import defaultdict

    player_acc: dict[str, list[float]] = defaultdict(list)
    cohort_acc: dict[str, list[float]] = defaultdict(list)
    for b in bench:
        g = str(b.get("attribute_group") or "—")
        player_acc[g].append(float(b["player_avg_rating"]))
        cohort_acc[g].append(float(b["position_avg_rating"]))

    groups = templates_service.ordered_attribute_groups_for_position(
        set(player_acc.keys()) | set(cohort_acc.keys()),
        position,
    )
    out: list[dict[str, Any]] = []
    for g in groups:
        pv = player_acc.get(g)
        cv = cohort_acc.get(g)
        if not pv or not cv:
            continue
        out.append(
            {
                "attribute_group": g,
                "player_avg_rating": sum(pv) / len(pv),
                "position_avg_rating": sum(cv) / len(cv),
            }
        )
    return out


def _build_subjective_benchmark_for_report(
    conn,
    position: str,
    player_id: int,
    report_attrs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Comparativa informe seleccionado vs media de cohorte (misma plantilla)."""
    if not position or not str(position).strip() or not report_attrs:
        return []
    cohort_bench = attribute_ratings_service.get_position_attribute_benchmark(
        conn, position.strip(), player_id
    )
    cohort_map = {
        (str(b["attribute_group"]), str(b["attribute_name"])): float(b["position_avg_rating"])
        for b in cohort_bench
    }
    out: list[dict[str, Any]] = []
    for r in report_attrs:
        k = (str(r.get("attribute_group") or ""), str(r.get("attribute_name") or ""))
        pos_avg = cohort_map.get(k)
        rating = r.get("rating")
        if pos_avg is None or rating is None:
            continue
        out.append(
            {
                "attribute_group": r["attribute_group"],
                "attribute_name": r["attribute_name"],
                "player_avg_rating": float(rating),
                "position_avg_rating": pos_avg,
                "difference": float(rating) - pos_avg,
            }
        )
    return templates_service.sort_attributes_by_position_template(position.strip(), out)


def _report_label(rep: dict[str, Any]) -> str:
    return player_report_option_label(rep)


def _pick_player_report(reports: list[dict[str, Any]], player_id: int) -> dict[str, Any]:
    """Selector visual de informe (cronológico, más reciente primero)."""
    if not reports:
        raise ValueError("reports vacío")
    raw_labels = [_report_label(r) for r in reports]
    labels = ensure_unique_labels(raw_labels)
    ctx_key = f"player_lookup_report_ctx_{player_id}"
    sel_key = f"player_lookup_report_sel_{player_id}"
    if st.session_state.get(ctx_key) != player_id:
        st.session_state[ctx_key] = player_id
        st.session_state[sel_key] = labels[0]

    if len(labels) == 1:
        st.caption(f"Informe: **{labels[0]}**")
        return reports[0]

    st.caption("Informe analizado")
    label_to_rep = {lab: rep for lab, rep in zip(labels, reports, strict=True)}
    picked = st.radio(
        "Informe",
        labels,
        horizontal=True,
        key=sel_key,
        label_visibility="collapsed",
    )
    return label_to_rep[picked]


def _player_demographics(player: dict[str, Any]) -> tuple[date | None, int | None, str, str]:
    """Edad, fecha nacimiento y altura formateados."""
    bd_raw = player.get("birth_date")
    bd_val = bd_raw if isinstance(bd_raw, date) else None
    if bd_val is None and bd_raw is not None:
        try:
            bd_val = date.fromisoformat(str(bd_raw)[:10])
        except ValueError:
            bd_val = None
    age_now = players_service.calculate_age(bd_val)
    bd_disp = bd_val.isoformat() if bd_val else "—"

    h_cm = player.get("height_cm")
    if h_cm is not None:
        try:
            h_disp = f"{float(h_cm):g} cm"
        except (TypeError, ValueError):
            h_disp = "—"
    else:
        h_disp = "—"
    return bd_val, age_now, bd_disp, h_disp


def _render_player_executive_ficha(
    player: dict[str, Any],
    rep: dict[str, Any] | None,
) -> None:
    """Cabecera ejecutiva unificada: ficha + datos del informe seleccionado."""
    img_col, info_col = st.columns([1, 2.6])
    with img_col:
        _render_player_photo(player)

    _, age_now, bd_disp, h_disp = _player_demographics(player)

    with info_col:
        name = html.escape(str(player.get("full_name") or "—"))
        st.markdown(f'<p class="executive-ficha-name">{name}</p>', unsafe_allow_html=True)

        _render_ficha_fields_row(
            [
                ("Equipo", player.get("current_team"), False),
                ("Posición", player.get("position"), True),
                ("Nacionalidad", player.get("nationality"), False),
                ("Edad", str(age_now) if age_now is not None else "—", False),
            ],
            columns=4,
        )
        rating_val = (
            _metric_display_value(rep.get("rating"), fmt=".2f")
            if rep and rep.get("rating") is not None
            else "—"
        )
        _render_ficha_fields_row(
            [
                ("Fecha nacimiento", bd_disp, False),
                ("Altura", h_disp, False),
                ("Pie hábil", player.get("preferred_foot"), False),
                ("Valoración scouting", rating_val, False),
            ],
            columns=4,
        )

        st.markdown('<hr class="executive-ficha-divider"/>', unsafe_allow_html=True)

        if rep:
            alt_pos = rep.get("alternative_positions")
            alt_txt = ", ".join(str(p) for p in alt_pos if p) if alt_pos else "—"
            _render_ficha_fields_row(
                [
                    ("Scout", rep.get("scout_name"), True),
                    ("Posición observada", rep.get("position_observed"), True),
                ],
                columns=2,
            )
            st.markdown(_ficha_field_html("Posiciones alternativas", alt_txt, long_text=True), unsafe_allow_html=True)
            _render_ficha_fields_row(
                [
                    ("Competición observada", rep.get("competition"), True),
                    ("Partido observado", rep.get("match_observed"), True),
                ],
                columns=2,
            )
            _render_ficha_fields_row(
                [("Minutos observados", rep.get("minutes_observed"), False)],
                columns=1,
            )

            rec_col, vid_col = st.columns([2, 1])
            with rec_col:
                st.markdown(f"**Recomendación:** {rep.get('recommendation') or '—'}")
            with vid_col:
                vu_raw = rep.get("video_url")
                if vu_raw and str(vu_raw).strip():
                    vus = str(vu_raw).strip()
                    if _is_plausible_video_url(vus):
                        esc = html.escape(vus)
                        st.markdown(
                            f'**Vídeo:** <a href="{esc}" target="_blank" rel="noopener noreferrer">Ver</a>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(f"**Vídeo:** `{html.escape(vus)}`")
                else:
                    st.markdown("**Vídeo:** —")
        else:
            st.caption("Sin informe de scouting vinculado.")


def _render_scout_summary_highlight(rep: dict[str, Any]) -> None:
    summary = rep.get("summary")
    text = str(summary).strip() if summary else ""
    body = html.escape(text) if text else "<em>Sin resumen.</em>"
    st.markdown(
        f'<div class="oh-card scout-summary-box oh-report-summary">'
        f'<p class="scout-summary-label">Resumen del scout</p>'
        f'<p class="scout-summary-text">{body}</p>'
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_scout_strengths_weaknesses(rep: dict[str, Any]) -> None:
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown('<p class="sw-column-title">Fortalezas</p>', unsafe_allow_html=True)
        st.markdown(str(rep.get("strengths") or "—"))
    with c2:
        st.markdown('<p class="sw-column-title">Debilidades</p>', unsafe_allow_html=True)
        st.markdown(str(rep.get("weaknesses") or "—"))


def _render_subjective_attributes(
    attrs: list[dict[str, Any]],
    player: dict[str, Any],
) -> None:
    st.markdown("#### Atributos valorados")
    if not attrs:
        st.caption("Sin valoraciones por atributo en este informe.")
        return

    by_group: dict[str, list[dict[str, Any]]] = {}
    for row in attrs:
        g = str(row.get("attribute_group") or "—")
        by_group.setdefault(g, []).append(row)
    player_pos = player.get("position")
    pos_s = str(player_pos).strip() if player_pos else None
    for gname in _ordered_attribute_groups(attrs, pos_s):
        rows_g = _sort_rows_in_group(by_group.get(gname, []), pos_s, gname)
        if not rows_g:
            continue
        st.markdown(f"##### {html.escape(gname)}")
        ncols = min(3, max(1, len(rows_g)))
        acols = st.columns(ncols)
        for i, row in enumerate(rows_g):
            mx = _float01(row.get("max_rating") or RATING_MAX)
            rt = _float01(row.get("rating"))
            nm = html.escape(str(row.get("attribute_name") or ""))
            notes = row.get("notes")
            note_html = ""
            if notes and str(notes).strip():
                note_html = (
                    '<p style="font-size:0.78rem;color:#475569;margin:0.35rem 0 0 0;line-height:1.35;">'
                    f"{html.escape(str(notes).strip())}</p>"
                )
            block = (
                f'<div class="oh-card attr-card">'
                f'<div class="attr-card-title">{nm}</div>'
                f"{render_star_rating(rt, mx)}"
                f"{note_html}</div>"
            )
            with acols[i % ncols]:
                st.markdown(block, unsafe_allow_html=True)


def _render_player_subjective_report_content(
    rep: dict[str, Any],
    attrs: list[dict[str, Any]],
    player: dict[str, Any],
) -> None:
    """Contenido del informe tras la cabecera ejecutiva."""
    _render_scout_summary_highlight(rep)
    _render_scout_strengths_weaknesses(rep)
    _render_subjective_attributes(attrs, player)


def _objective_metrics_applied_key(key_prefix: str) -> str:
    return f"{key_prefix}_applied_metrics"


def _objective_metrics_context_key(key_prefix: str) -> str:
    return f"{key_prefix}_context_id"


def _sync_objective_metric_apply_state(
    *,
    key_prefix: str,
    context_id: str,
    available_metrics: list[str],
    default_metrics: list[str],
) -> None:
    """Reinicia applied si cambia jugador, bloque o grupo objetivo."""
    ctx_key = _objective_metrics_context_key(key_prefix)
    applied_key = _objective_metrics_applied_key(key_prefix)
    default_list = [m for m in default_metrics if m in available_metrics]
    if not default_list and available_metrics:
        default_list = available_metrics[: min(8, len(available_metrics))]

    if st.session_state.get(ctx_key) != context_id:
        st.session_state[ctx_key] = context_id
        st.session_state[applied_key] = list(default_list)
        for key in list(st.session_state.keys()):
            if key.startswith(f"{key_prefix}_pending_") or "_objective_metric_checkbox_" in key:
                st.session_state.pop(key, None)
    elif applied_key not in st.session_state:
        st.session_state[applied_key] = list(default_list)


def _read_applied_metric_names(
    key_prefix: str,
    available_metrics: list[str],
) -> list[str]:
    applied_raw = st.session_state.get(_objective_metrics_applied_key(key_prefix), [])
    applied_set = {str(m) for m in applied_raw if m}
    return [m for m in available_metrics if m in applied_set]


def _metric_multiselect_options(
    available_metrics: list[str],
) -> tuple[list[str], dict[str, str]]:
    """Etiquetas para multiselect y mapa etiqueta → metric_name crudo."""
    label_count: dict[str, int] = {}
    base_label: dict[str, str] = {}
    for m in available_metrics:
        lab = metric_labels.metric_label(m)
        base_label[m] = lab
        label_count[lab] = label_count.get(lab, 0) + 1

    options: list[str] = []
    label_to_metric: dict[str, str] = {}
    for m in available_metrics:
        lab = base_label[m]
        display = f"{lab} · {m}" if label_count[lab] > 1 else lab
        options.append(display)
        label_to_metric[display] = m
    return options, label_to_metric


def render_metric_apply_selector(
    key_prefix: str,
    available_metrics: list[str],
    default_metrics: list[str],
    label: str,
    context_id: str,
) -> list[str]:
    """
    Multiselect dentro de st.form: los cambios no recalculan gráficos hasta enviar.
    Devuelve metric_name crudos en applied_metrics.
    """
    if not available_metrics:
        return []

    _sync_objective_metric_apply_state(
        key_prefix=key_prefix,
        context_id=context_id,
        available_metrics=available_metrics,
        default_metrics=default_metrics,
    )

    applied = _read_applied_metric_names(key_prefix, available_metrics)
    options, label_to_metric = _metric_multiselect_options(available_metrics)
    metric_to_label = {m: lab for lab, m in label_to_metric.items()}
    applied_labels = [metric_to_label[m] for m in applied if m in metric_to_label]

    st.markdown(f"**{label}**")
    st.caption(
        "Elige métricas en el selector y pulsa **Aplicar métricas**. "
        "Los cambios dentro del formulario no actualizan los gráficos hasta enviar."
    )

    with st.form(f"{key_prefix}_metric_form", clear_on_submit=False):
        picked_labels = st.multiselect(
            "Métricas",
            options=options,
            default=applied_labels,
            help="Etiquetas en español; nombres crudos internos.",
        )
        submitted = st.form_submit_button("Aplicar métricas", type="primary")

    if submitted:
        picked = [label_to_metric[lab] for lab in picked_labels if lab in label_to_metric]
        st.session_state[_objective_metrics_applied_key(key_prefix)] = [
            m for m in available_metrics if m in picked
        ]
        st.rerun()

    applied = _read_applied_metric_names(key_prefix, available_metrics)
    if is_debug_mode():
        st.caption(f"Métricas aplicadas al gráfico: **{len(applied)}**")
    return applied


def _render_objective_quick_chart(
    metrics_rows: list[dict[str, Any]],
    selected_metrics: list[str],
    *,
    title: str,
) -> None:
    chartable = set(metrics_service.objective_block_chart_metric_names(metrics_rows))
    plot_names = [m for m in selected_metrics if m in chartable]
    skipped = len(selected_metrics) - len(plot_names)
    if is_debug_mode() and skipped and plot_names:
        st.caption(
            f"{skipped} métrica(s) no aptas para el gráfico rápido "
            "(minutos, partidos, valor de mercado, etc.)."
        )
    if not plot_names:
        if selected_metrics and is_debug_mode():
            st.caption("Ninguna métrica seleccionada es apta para el gráfico rápido.")
        return
    value_by_name = {
        str(m.get("metric_name") or ""): m.get("metric_value")
        for m in metrics_rows
        if m.get("metric_value") is not None
    }
    plot_df = pd.DataFrame(
        [
            {
                "métrica": metric_labels.metric_label(name),
                "valor": float(value_by_name[name]),
            }
            for name in plot_names
            if name in value_by_name
        ]
    )
    if plot_df.empty:
        st.caption("Sin valores numéricos para las métricas seleccionadas.")
        return
    fig = px.bar(
        plot_df,
        x="métrica",
        y="valor",
        labels={"métrica": "Métrica", "valor": "Valor"},
        title=title,
    )
    fig.update_layout(height=max(360, 28 * len(plot_df)), xaxis_tickangle=-35)
    apply_ohiggins_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)


def _percentile_strip_html(percentile: float) -> str:
    return single_player_strip_html(percentile)


def _metric_names_for_percentile_analysis(
    metrics_rows: list[dict[str, Any]],
) -> list[str]:
    """Todas las métricas del bloque con valor (sin selector manual)."""
    return metrics_service.block_metric_names_for_ui(metrics_rows)


def _group_metric_names_by_category(
    metric_names: list[str],
) -> list[tuple[str, list[str]]]:
    groups: dict[str, list[str]] = {}
    for name in metric_names:
        grp = metric_labels.metric_group(name)
        groups.setdefault(grp, []).append(name)
    order = {g: i for i, g in enumerate(metric_labels.METRIC_GROUP_ORDER)}

    def _group_sort_key(group: str) -> tuple[int, str]:
        return (order.get(group, len(order)), group)

    out: list[tuple[str, list[str]]] = []
    for group_name in sorted(groups.keys(), key=_group_sort_key):
        names = sorted(groups[group_name], key=metric_labels.metric_sort_key)
        out.append((group_name, names))
    return out


def _render_percentile_metric_cards_grouped(
    percentile_rows: list[dict[str, Any]],
    *,
    position_group: str | None = None,
) -> None:
    by_name = {str(r.get("metric_name")): r for r in percentile_rows if r.get("metric_name")}
    if not by_name:
        st.caption("Sin percentiles para mostrar.")
        return
    for group_name, names in _group_metric_names_by_category(list(by_name.keys())):
        rows_in_group = [by_name[m] for m in names if m in by_name]
        if not rows_in_group:
            continue
        with st.expander(group_name, expanded=True):
            half = (len(rows_in_group) + 1) // 2
            left, right = st.columns(2, gap="small")
            for i, row in enumerate(rows_in_group):
                with left if i < half else right:
                    _render_percentile_metric_card(row, position_group=position_group)


def _comparison_radar_fill_rgba(hex_color: str, alpha: float = 0.22) -> str:
    color = str(hex_color).lstrip("#")
    if len(color) != 6:
        return f"rgba(80, 145, 205, {alpha})"
    r = int(color[0:2], 16)
    g = int(color[2:4], 16)
    b = int(color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _comparison_objective_series_legend_html(
    *,
    label_a: str,
    label_b: str,
    color_a: str,
    color_b: str,
    note: str = "Percentil (P100 = mejor)",
) -> str:
    """Leyenda única (círculo + rombo) para radares objetivos."""
    return (
        '<div class="cmp-radar-legend-once">'
        '<span class="cmp-legend-item">'
        f'<span class="cmp-legend-shape cmp-legend-shape--circle" '
        f'style="background:{color_a};"></span>'
        f"<strong>{html.escape(label_a)}</strong></span>"
        '<span class="cmp-legend-item">'
        f'<span class="cmp-legend-shape cmp-legend-shape--diamond" '
        f'style="background:{color_b};"></span>'
        f"<strong>{html.escape(label_b)}</strong></span>"
        f'<span class="cmp-radar-legend-note">{html.escape(note)}</span>'
        "</div>"
    )


def _build_comparison_percentile_radar_figure(
    *,
    metric_names: list[str],
    by_metric_a: dict[str, dict[str, Any]],
    by_metric_b: dict[str, dict[str, Any]],
    name_a: str,
    name_b: str,
    color_a: str,
    color_b: str,
    height: int = 460,
) -> go.Figure | None:
    """Radar de percentiles (0–100) para un grupo de métricas comunes."""
    if len(metric_names) < metric_labels.MIN_COMPARISON_RADAR_METRICS:
        return None

    labels = [metric_labels.metric_label(m) for m in metric_names]
    r_a = [float(by_metric_a[m].get("percentile") or 0.0) for m in metric_names]
    r_b = [float(by_metric_b[m].get("percentile") or 0.0) for m in metric_names]
    labels_c = labels + [labels[0]]
    r_a_c = r_a + [r_a[0]]
    r_b_c = r_b + [r_b[0]]

    n_axes = len(labels)
    tick_font = max(7, min(9, 11 - n_axes // 3))

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=r_a_c,
            theta=labels_c,
            name=name_a,
            line=dict(color=color_a, width=2.5),
            fillcolor=_comparison_radar_fill_rgba(color_a),
            fill="toself",
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=r_b_c,
            theta=labels_c,
            name=name_b,
            line=dict(color=color_b, width=2.5),
            fillcolor=_comparison_radar_fill_rgba(color_b),
            fill="toself",
        )
    )
    fig.update_layout(
        polar=dict(
            domain=dict(x=[0.08, 0.92], y=[0.10, 0.92]),
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tick0=0,
                dtick=20,
                tickfont=dict(size=9),
            ),
            angularaxis=dict(
                direction="clockwise",
                tickfont=dict(size=tick_font),
                layer="below traces",
            ),
        ),
        showlegend=False,
        margin=dict(l=40, r=40, t=50, b=40),
        height=height,
    )
    return apply_ohiggins_plotly_theme(
        fig,
        height=height,
        margin=dict(l=40, r=40, t=50, b=40),
        showlegend=False,
    )


def _vs_position_comparison_to_cohort_norm_by_metric(
    rows: list[dict[str, Any]],
    *,
    units_by_metric: dict[str, str | None],
) -> dict[str, dict[str, Any]]:
    """Normaliza jugador y media con escala cohorte (P5–P95 por métrica)."""
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        mname = str(row.get("metric_name") or "").strip()
        if not mname:
            continue
        pval = row.get("player_value")
        avg = row.get("position_avg_value")
        scale_min = row.get("cohort_scale_min")
        scale_max = row.get("cohort_scale_max")
        if pval is None or avg is None or scale_min is None or scale_max is None:
            continue
        player_norm = metric_direction.normalize_to_cohort_scale(
            float(pval),
            float(scale_min),
            float(scale_max),
        )
        avg_norm = metric_direction.normalize_to_cohort_scale(
            float(avg),
            float(scale_min),
            float(scale_max),
        )
        if player_norm is None or avg_norm is None:
            continue
        unit = units_by_metric.get(mname)
        out[mname] = {
            "player_norm": float(player_norm),
            "avg_norm": float(avg_norm),
            "player_value": float(pval),
            "position_avg_value": float(avg),
            "cohort_scale_min": float(scale_min),
            "cohort_scale_max": float(scale_max),
            "metric_unit": unit,
            "avg_includes_player_fallback": bool(
                row.get("avg_includes_player_fallback")
            ),
        }
    return out


def _build_player_vs_position_cohort_norm_radar_figure(
    *,
    metric_names: list[str],
    by_metric: dict[str, dict[str, Any]],
    name_player: str,
    name_position_avg: str,
    color_player: str,
    color_position_avg: str,
    height: int = 450,
) -> go.Figure | None:
    """Radar jugador vs media (misma escala P5–P95 de cohorte por métrica)."""
    if len(metric_names) < metric_labels.MIN_COMPARISON_RADAR_METRICS:
        return None

    labels = [metric_labels.metric_label(m) for m in metric_names]
    labels_c = labels + [labels[0]]

    r_player: list[float] = []
    r_avg: list[float] = []
    hover_rows: list[list[str]] = []
    for m in metric_names:
        row = by_metric[m]
        unit = row.get("metric_unit")
        p_txt = metric_labels.format_metric_value(row["player_value"], unit)
        a_txt = metric_labels.format_metric_value(row["position_avg_value"], unit)
        r_player.append(float(row["player_norm"]))
        r_avg.append(float(row["avg_norm"]))
        hover_rows.append([p_txt, a_txt])

    r_player_c = r_player + [r_player[0]]
    r_avg_c = r_avg + [r_avg[0]]
    hover_c = hover_rows + [hover_rows[0]]

    n_axes = len(labels)
    tick_font = max(7, min(9, 11 - n_axes // 3))
    hover_tpl = (
        "%{theta}<br>"
        "Jugador: %{customdata[0]}<br>"
        "Media posición: %{customdata[1]}"
        "<extra></extra>"
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=r_avg_c,
            theta=labels_c,
            name=name_position_avg,
            line=dict(color=color_position_avg, width=2.5),
            fillcolor=_comparison_radar_fill_rgba(color_position_avg, alpha=0.15),
            fill="toself",
            customdata=hover_c,
            hovertemplate=hover_tpl,
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=r_player_c,
            theta=labels_c,
            name=name_player,
            line=dict(color=color_player, width=2.5),
            fillcolor=_comparison_radar_fill_rgba(color_player),
            fill="toself",
            customdata=hover_c,
            hovertemplate=hover_tpl,
        )
    )
    fig.update_layout(
        polar=dict(
            domain=dict(x=[0.08, 0.92], y=[0.10, 0.92]),
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                tick0=0,
                dtick=0.25,
                tickfont=dict(size=9),
            ),
            angularaxis=dict(
                direction="clockwise",
                tickfont=dict(size=tick_font),
                layer="below traces",
            ),
        ),
        showlegend=False,
        margin=dict(l=40, r=40, t=50, b=40),
        height=height,
    )
    return apply_ohiggins_plotly_theme(
        fig,
        height=height,
        margin=dict(l=40, r=40, t=50, b=40),
        showlegend=False,
    )


def _resolve_comparison_radar_position_group(
    pos_group_a: str | None,
    pos_group_b: str | None,
) -> str | None:
    """Portero si algún perfil es portero; si no, campo (usa grupo de A o B)."""
    if str(pos_group_a or "").strip() == "Portero" or str(pos_group_b or "").strip() == "Portero":
        return "Portero"
    return pos_group_a or pos_group_b


def _comparison_radar_sections(
    common_metrics: list[str],
    *,
    position_group: str | None,
) -> list[tuple[str, list[str]]]:
    """Grupos con al menos MIN métricas comunes y percentil disponible."""
    group_order = metric_labels.comparison_radar_groups_for_position(position_group)
    sections: list[tuple[str, list[str]]] = []
    for group_name in group_order:
        names = metric_labels.metrics_in_group(common_metrics, group_name)
        if len(names) >= metric_labels.MIN_COMPARISON_RADAR_METRICS:
            sections.append((group_name, names))
    return sections


OBJECTIVE_RADAR_PLAYER_COLOR = "#5091CD"
OBJECTIVE_RADAR_POSITION_AVG_COLOR = "#374151"
OBJECTIVE_RADAR_HEIGHT = 450


def _render_objective_percentile_radars_by_group(
    *,
    radar_metrics: list[str],
    by_metric_a: dict[str, dict[str, Any]],
    by_metric_b: dict[str, dict[str, Any]],
    position_group: str | None,
    series_name_a: str,
    series_name_b: str,
    color_a: str,
    color_b: str,
    empty_caption: str | None = None,
) -> None:
    """Radares de percentiles por bloque (2 por fila, leyenda Plotly desactivada)."""
    sections = _comparison_radar_sections(
        radar_metrics,
        position_group=position_group,
    )
    if not sections:
        msg = empty_caption or (
            "No hay bloques con al menos "
            f"{metric_labels.MIN_COMPARISON_RADAR_METRICS} métricas para mostrar radar."
        )
        st.caption(msg)
        return

    chart_cfg = plotly_radar_chart_config()
    for i in range(0, len(sections), 2):
        chunk = sections[i : i + 2]
        cols = st.columns(2, gap="medium")
        for col_idx, (group_name, metric_names) in enumerate(chunk):
            with cols[col_idx]:
                st.markdown(f"#### {html.escape(group_name)}")
                fig = _build_comparison_percentile_radar_figure(
                    metric_names=metric_names,
                    by_metric_a=by_metric_a,
                    by_metric_b=by_metric_b,
                    name_a=series_name_a,
                    name_b=series_name_b,
                    color_a=color_a,
                    color_b=color_b,
                    height=OBJECTIVE_RADAR_HEIGHT,
                )
                if fig is not None:
                    st.markdown(
                        '<span class="cmp-objective-radar-marker" aria-hidden="true"></span>',
                        unsafe_allow_html=True,
                    )
                    st.plotly_chart(fig, use_container_width=True, config=chart_cfg)
        if len(chunk) == 1:
            with cols[1]:
                st.empty()


def _render_player_vs_position_cohort_norm_radars_by_group(
    *,
    radar_metrics: list[str],
    by_metric: dict[str, dict[str, Any]],
    position_group: str | None,
    empty_caption: str | None = None,
) -> None:
    """Radares jugador vs media (escala cohorte P5–P95)."""
    sections = _comparison_radar_sections(
        radar_metrics,
        position_group=position_group,
    )
    if not sections:
        msg = empty_caption or (
            "No hay bloques con al menos "
            f"{metric_labels.MIN_COMPARISON_RADAR_METRICS} métricas para mostrar radar."
        )
        st.caption(msg)
        return

    chart_cfg = plotly_radar_chart_config()
    for i in range(0, len(sections), 2):
        chunk = sections[i : i + 2]
        cols = st.columns(2, gap="medium")
        for col_idx, (group_name, metric_names) in enumerate(chunk):
            with cols[col_idx]:
                st.markdown(f"#### {html.escape(group_name)}")
                fig = _build_player_vs_position_cohort_norm_radar_figure(
                    metric_names=metric_names,
                    by_metric=by_metric,
                    name_player="Jugador seleccionado",
                    name_position_avg="Media posición",
                    color_player=OBJECTIVE_RADAR_PLAYER_COLOR,
                    color_position_avg=OBJECTIVE_RADAR_POSITION_AVG_COLOR,
                    height=OBJECTIVE_RADAR_HEIGHT,
                )
                if fig is not None:
                    st.markdown(
                        '<span class="cmp-objective-radar-marker" aria-hidden="true"></span>',
                        unsafe_allow_html=True,
                    )
                    st.plotly_chart(fig, use_container_width=True, config=chart_cfg)
        if len(chunk) == 1:
            with cols[1]:
                st.empty()


def _render_player_vs_position_objective_radars(
    *,
    player_id: int,
    season: str | None,
    competition: str | None,
    metrics_rows: list[dict[str, Any]],
    pos_group: str | None,
    available_metrics: list[str],
) -> None:
    """Jugador vs media de posición en escala cohorte (P5–P95 por métrica)."""
    if not pos_group:
        return

    with get_connection() as conn:
        vs_rows, diag = metrics_service.get_player_vs_position_average(
            conn,
            player_id,
            season,
            competition,
            metrics_rows=metrics_rows,
            metric_names=available_metrics,
            scope="same_competition",
        )

    units_by_metric = {
        str(r.get("metric_name") or "").strip(): r.get("metric_unit")
        for r in metrics_rows
        if r.get("metric_name")
    }
    by_metric = _vs_position_comparison_to_cohort_norm_by_metric(
        vs_rows,
        units_by_metric=units_by_metric,
    )
    radar_metrics = sorted(by_metric.keys(), key=metric_labels.metric_sort_key)
    if not radar_metrics:
        st.caption(
            "No hay suficientes métricas con valor y media de posición para mostrar radares."
        )
        return

    st.markdown("#### Radar objetivo por grupos")
    st.caption("Jugador vs media de su posición en la liga")
    st.markdown(
        _comparison_objective_series_legend_html(
            label_a="Jugador seleccionado",
            label_b="Media posición",
            color_a=OBJECTIVE_RADAR_PLAYER_COLOR,
            color_b=OBJECTIVE_RADAR_POSITION_AVG_COLOR,
            note="Escala cohorte (P5–P95 por métrica)",
        ),
        unsafe_allow_html=True,
    )
    _render_player_vs_position_cohort_norm_radars_by_group(
        radar_metrics=radar_metrics,
        by_metric=by_metric,
        position_group=pos_group,
        empty_caption=(
            "No hay bloques con al menos "
            f"{metric_labels.MIN_COMPARISON_RADAR_METRICS} métricas con valor y media de posición."
        ),
    )

    if is_debug_mode():
        radar_set = set(radar_metrics)
        excluded = [m for m in available_metrics if m not in radar_set]
        with st.expander("Radar por grupos — detalle técnico", expanded=False):
            st.markdown(
                f"**Competición:** {competition or '—'} · "
                f"**Temporada:** {metric_labels.format_season_label(season)} · "
                f"**Posición:** {pos_group} · "
                f"**Cohorte (jugadores):** {diag.get('cohort_peers', 0)}"
            )
            tech = []
            for m in radar_metrics:
                row = by_metric[m]
                unit = row.get("metric_unit")
                tech.append(
                    {
                        "Métrica": metric_labels.metric_label(m),
                        "Jugador": metric_labels.format_metric_value(
                            row["player_value"],
                            unit,
                        ),
                        "Media posición": metric_labels.format_metric_value(
                            row["position_avg_value"],
                            unit,
                        ),
                        "P5 cohorte": metric_labels.format_metric_value(
                            row["cohort_scale_min"],
                            unit,
                        ),
                        "P95 cohorte": metric_labels.format_metric_value(
                            row["cohort_scale_max"],
                            unit,
                        ),
                        "Norm. jugador": f"{row['player_norm']:.2f}",
                        "Norm. media": f"{row['avg_norm']:.2f}",
                        "Media incl. jugador (fallback)": (
                            "Sí" if row.get("avg_includes_player_fallback") else "No"
                        ),
                    }
                )
            if tech:
                st.dataframe(pd.DataFrame(tech), use_container_width=True, hide_index=True)
            if excluded:
                st.markdown("**Métricas excluidas del radar**")
                st.caption(
                    ", ".join(metric_labels.metric_label(m) for m in excluded[:40])
                    + ("…" if len(excluded) > 40 else "")
                )


def _render_comparison_percentile_radars_by_group(
    *,
    common_metrics: list[str],
    by_metric_a: dict[str, dict[str, Any]],
    by_metric_b: dict[str, dict[str, Any]],
    pos_group_a: str | None,
    pos_group_b: str | None,
    radar_name_a: str,
    radar_name_b: str,
    color_a: str,
    color_b: str,
) -> None:
    """Radares de percentiles por bloque funcional (2 por fila); sin leyenda Plotly."""
    radar_pos = _resolve_comparison_radar_position_group(pos_group_a, pos_group_b)
    _render_objective_percentile_radars_by_group(
        radar_metrics=common_metrics,
        by_metric_a=by_metric_a,
        by_metric_b=by_metric_b,
        position_group=radar_pos,
        series_name_a=radar_name_a,
        series_name_b=radar_name_b,
        color_a=color_a,
        color_b=color_b,
        empty_caption=(
            "No hay bloques con al menos "
            f"{metric_labels.MIN_COMPARISON_RADAR_METRICS} métricas comparables para mostrar radar."
        ),
    )


def _render_comparison_percentile_cards_grouped(
    *,
    common_metrics: list[str],
    by_metric_a: dict[str, dict[str, Any]],
    by_metric_b: dict[str, dict[str, Any]],
    color_a: str,
    color_b: str,
    table_header_a: str,
    table_header_b: str,
) -> None:
    for group_name, names in _group_metric_names_by_category(common_metrics):
        in_group = [m for m in names if m in by_metric_a and m in by_metric_b]
        if not in_group:
            continue
        with st.expander(group_name, expanded=True):
            half = (len(in_group) + 1) // 2
            left, right = st.columns(2, gap="small")
            for i, metric_name in enumerate(in_group):
                row_ma = by_metric_a[metric_name]
                row_mb = by_metric_b[metric_name]
                card_html = _comparison_percentile_card_html(
                    metric_label=metric_labels.metric_label(metric_name),
                    pct_oh=float(row_ma.get("percentile") or 0.0),
                    pct_cmp=float(row_mb.get("percentile") or 0.0),
                    value_oh=metric_labels.format_metric_value(
                        row_ma.get("player_value"),
                        row_ma.get("metric_unit"),
                        metric_name=metric_name,
                    ),
                    value_cmp=metric_labels.format_metric_value(
                        row_mb.get("player_value"),
                        row_mb.get("metric_unit"),
                        metric_name=metric_name,
                    ),
                    oh_color=color_a,
                    cmp_color=color_b,
                    legend_oh=table_header_a,
                    legend_cmp=table_header_b,
                    metric_name=metric_name,
                )
                with left if i < half else right:
                    st.markdown(card_html, unsafe_allow_html=True)


def _render_percentile_metric_card(
    row: dict[str, Any],
    *,
    position_group: str | None = None,
) -> None:
    metric_name = str(row.get("metric_name") or "")
    label = metric_labels.metric_label(metric_name)
    pct = float(row["percentile"])
    unit = row.get("metric_unit")
    value_txt = metric_labels.format_metric_value(
        row.get("player_value"),
        unit,
        metric_name=metric_name,
    )
    if metric_labels.is_zero_centered_normalized_metric(metric_name):
        interp = metric_labels.interpret_normalized_metric(row.get("player_value"), pct)
    else:
        interp = metric_labels.interpret_percentile(
            pct,
            position_group=position_group,
            metric_name=metric_name,
        )
    pct_int = int(round(pct))
    badge_color = ohiggins_percentile_color(pct)
    direction_chip = ""
    if row.get("lower_is_better"):
        direction_chip = (
            '<span class="cmp-pct-direction-chip" title="En esta métrica, menos es mejor.">'
            "Menor es mejor"
            "</span>"
        )
    st.markdown(
        f'<div class="oh-card pct-metric-card pct-metric-card--compact">'
        f'<p class="pct-metric-title">{html.escape(label)}</p>'
        f"{_percentile_strip_html(pct)}"
        f'<p class="pct-summary-line">'
        f'<span class="pct-badge" style="background:{badge_color};">P{pct_int}</span>'
        f" · {html.escape(value_txt)}</p>"
        f'<span class="pct-interp">{html.escape(interp)}</span>'
        f"{direction_chip}"
        f"</div>",
        unsafe_allow_html=True,
    )
    if metric_labels.is_zero_centered_normalized_metric(metric_name):
        st.caption(
            "0 ≈ media de la competición · positivo = por encima · negativo = por debajo."
        )


def _global_profile_interpretation(percentile: float) -> str:
    pct = float(percentile)
    if pct >= 95:
        return "Elite"
    if pct >= 90:
        return "Excelente"
    if pct >= 75:
        return "Muy destacado"
    if pct >= 60:
        return "Por encima de la media"
    if pct >= 40:
        return "Promedio"
    if pct >= 25:
        return "Por debajo de la media"
    return "Bajo para la competición"


def _global_profile_plural(position_group: str | None) -> str:
    mapping = {
        "Portero": "porteros",
        "Defensa": "defensas",
        "Mediocampo": "mediocampistas",
        "Delantero": "delanteros",
    }
    return mapping.get(str(position_group or "").strip(), "jugadores")


def _compute_global_profile_percentile(
    percentile_rows: list[dict[str, Any]],
) -> tuple[float | None, list[str]]:
    used_metrics: list[str] = []
    values: list[float] = []
    for row in percentile_rows:
        metric_name = str(row.get("metric_name") or "")
        if not metric_name:
            continue
        pct = row.get("percentile")
        if pct is None:
            continue
        used_metrics.append(metric_name)
        values.append(float(pct))
    if not values:
        return None, used_metrics
    return sum(values) / len(values), used_metrics


def _render_global_profile_card(
    *,
    percentile: float,
    position_group: str | None,
    competition: str | None,
    metrics_used: int,
) -> None:
    pct = max(0.0, min(100.0, float(percentile)))
    pct_i = int(round(pct))
    top_pct = max(0, 100 - pct_i)
    role_plural = _global_profile_plural(position_group)
    interp = _global_profile_interpretation(pct)
    badge_color = ohiggins_percentile_color(pct)
    comp_txt = competition or "la competición"
    st.markdown(
        f'<div class="oh-card pct-metric-card pct-metric-card--compact">'
        f'<p class="pct-metric-title">PERFIL GLOBAL</p>'
        f"{_percentile_strip_html(pct)}"
        f'<p class="pct-summary-line">'
        f'<span class="pct-badge" style="background:{badge_color};">P{pct_i}</span>'
        f" · Top {top_pct}% de {html.escape(role_plural)} de {html.escape(comp_txt)}</p>"
        f'<span class="pct-interp">{html.escape(interp)} · Perfil global calculado sobre {metrics_used} métricas objetivas disponibles.</span>'
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_percentile_highlights(rows: list[dict[str, Any]]) -> None:
    valid = [r for r in rows if r.get("percentile") is not None]
    strengths = sorted(
        [r for r in valid if float(r["percentile"]) >= 75],
        key=lambda x: -float(x["percentile"]),
    )[:5]
    weaknesses = sorted(
        [r for r in valid if float(r["percentile"]) <= 40],
        key=lambda x: float(x["percentile"]),
    )[:5]
    if not strengths and not weaknesses:
        return

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("#### Fortalezas")
        if strengths:
            for r in strengths:
                lab = metric_labels.metric_label(str(r["metric_name"]))
                pct_int = int(round(float(r["percentile"])))
                st.markdown(f"- **{lab}** (P{pct_int})")
        else:
            st.caption("Sin métricas por encima del percentil 75.")
    with c2:
        st.markdown("#### Aspectos a mejorar")
        if weaknesses:
            for r in weaknesses:
                lab = metric_labels.metric_label(str(r["metric_name"]))
                pct_int = int(round(float(r["percentile"])))
                st.markdown(f"- **{lab}** (P{pct_int})")
        else:
            st.caption("Sin métricas por debajo del percentil 40.")


def _resolve_objective_position_context(
    metrics_rows: list[dict[str, Any]],
) -> tuple[str | None, str | None, dict[str, Any]]:
    pos_group, raw_pos, pos_meta = (
        metrics_service.resolve_objective_comparison_position_from_match_entries(metrics_rows)
    )
    if not pos_group:
        pos_group, raw_pos = metrics_service.resolve_objective_comparison_position(metrics_rows)
        pos_meta = {}
    return pos_group, raw_pos, pos_meta


def _default_profile_metrics_for_block(
    metrics_rows: list[dict[str, Any]],
    *,
    position_group: str | None,
) -> list[str]:
    available = set(metrics_service.block_metric_names_for_ui(metrics_rows))
    profile = metrics_service.objective_comparison_metrics_for_player(
        metrics_rows,
        position_group=position_group,
    )
    return [m for m in profile if m in available]


def _render_styled_objective_table(table_rows: list[dict[str, Any]]) -> None:
    if not table_rows:
        st.caption("Sin métricas para la tabla.")
        return
    df = pd.DataFrame(table_rows)
    display_cols = [c for c in df.columns if not str(c).startswith("_")]
    df_display = df[display_cols].copy()
    styled = df_display.style.map(ohiggins_percentile_cell_style, subset=["Percentil"])
    st.dataframe(styled, use_container_width=True, hide_index=True)


def _render_player_objective_scouting_block(
    *,
    player_id: int,
    season: str | None,
    competition: str | None,
    metrics_rows: list[dict[str, Any]],
    pos_group: str | None,
) -> list[dict[str, Any]]:
    """Percentiles vs cohorte misma posición · misma liga · misma temporada."""
    empty: list[dict[str, Any]] = []
    if not pos_group:
        st.info(
            "No hay posición objetiva suficiente en este bloque para calcular percentiles."
        )
        return empty

    comp_label = competition or "—"

    available = _metric_names_for_percentile_analysis(metrics_rows)
    if not available:
        st.caption("No hay métricas con valor en este bloque.")
        return empty

    with get_connection() as conn:
        percentile_rows, diag = metrics_service.get_player_position_percentile_rows(
            conn,
            player_id,
            season,
            competition,
            metrics_rows=metrics_rows,
            metric_names=available,
        )

    if not percentile_rows:
        st.warning(f"No hay datos suficientes para percentiles en **{comp_label}**.")
        return empty

    with get_connection() as conn:
        percentile_rows_global, _diag_global = metrics_service.get_player_position_percentile_rows(
            conn,
            player_id,
            season,
            competition,
            metrics_rows=metrics_rows,
            metric_names=available,
        )
    global_pct, global_used = _compute_global_profile_percentile(
        percentile_rows_global,
    )
    st.markdown("#### Perfil global")
    if global_pct is not None:
        _render_global_profile_card(
            percentile=global_pct,
            position_group=pos_group,
            competition=competition,
            metrics_used=len(global_used),
        )
    else:
        st.caption(
            "Sin métricas objetivas suficientes para calcular el percentil global."
        )

    _render_player_vs_position_objective_radars(
        player_id=player_id,
        season=season,
        competition=competition,
        metrics_rows=metrics_rows,
        pos_group=pos_group,
        available_metrics=available,
    )

    st.markdown("#### Percentiles por métrica")
    _render_percentile_metric_cards_grouped(
        percentile_rows,
        position_group=pos_group,
    )

    _render_percentile_highlights(percentile_rows)

    inverse_rows = [r for r in percentile_rows if r.get("lower_is_better")]
    if inverse_rows and is_debug_mode():
        with st.expander("Percentiles — detalle técnico (métricas inversas)", expanded=False):
            tech_rows = []
            for r in sorted(
                inverse_rows,
                key=lambda x: metric_labels.metric_sort_key(str(x.get("metric_name") or "")),
            ):
                mname = str(r.get("metric_name") or "")
                tech_rows.append(
                    {
                        "Métrica": metric_labels.metric_label(mname),
                        "Dirección": r.get("metric_direction") or "—",
                        "Percentil raw": r.get("raw_percentile"),
                        "Percentil rendimiento": r.get("performance_percentile"),
                    }
                )
            st.dataframe(pd.DataFrame(tech_rows), use_container_width=True, hide_index=True)

    st.markdown("#### Datos objetivos completos")
    with get_connection() as conn:
        table_rows = metrics_service.build_player_objective_scouting_table_rows(
            conn,
            player_id,
            season,
            competition,
            metrics_rows,
            priority_metric_names=None,
            position_group=pos_group,
        )
    if table_rows:
        _render_styled_objective_table(table_rows)
    else:
        st.caption("Sin métricas para la tabla.")

    return percentile_rows


def _render_objective_player_metrics_charts(
    *,
    player_id: int,
    season: str | None,
    competition: str | None,
    metrics_rows: list[dict[str, Any]],
    checkbox_key_prefix: str,
    scouting_position: str | None = None,
    quick_chart_title: str = "Gráfico rápido del jugador",
) -> None:
    """Selector único de métricas → gráfico rápido + comparativas liga / todas las ligas."""
    pos_group, raw_pos, pos_meta = (
        metrics_service.resolve_objective_comparison_position_from_match_entries(
            metrics_rows
        )
    )
    if not pos_group:
        pos_group, raw_pos = metrics_service.resolve_objective_comparison_position(
            metrics_rows,
        )

    if is_debug_mode():
        if scouting_position and str(scouting_position).strip():
            st.caption(f"Posición scouting (ficha): **{scouting_position}**")
        if pos_group:
            st.caption(f"Grupo objetivo: **{pos_group}**")
            if pos_meta.get("match_position_minutes"):
                mins_txt = ", ".join(
                    f"{code}: {int(float(m))} min"
                    for code, m in sorted(pos_meta["match_position_minutes"].items())
                )
                st.caption(f"Minutos por posición en partidos: {mins_txt}")
    if not pos_group:
        st.warning(
            "No hay posición objetiva en este bloque. No se puede calcular la comparativa."
        )
        return

    available = _metric_names_for_percentile_analysis(metrics_rows)
    if not available:
        st.caption("No hay métricas comparables en este bloque.")
        return

    selected = list(available)

    with get_connection() as conn:
        same_full, diag_same = metrics_service.get_player_vs_position_average(
            conn,
            player_id,
            season,
            competition,
            metrics_rows=metrics_rows,
            metric_names=selected,
            scope="same_competition",
        )
        all_full, diag_all = metrics_service.get_player_vs_position_average(
            conn,
            player_id,
            season,
            competition,
            metrics_rows=metrics_rows,
            metric_names=selected,
            scope="all_competitions",
        )

    comparison_union = same_full or all_full
    if not metrics_service.applied_metrics_have_chart_content(
        selected,
        metrics_rows,
        comparison_union,
    ):
        st.warning(
            "No hay métricas informativas para graficar con la selección actual."
        )
        return

    st.markdown(f"#### {quick_chart_title}")
    _render_objective_quick_chart(
        metrics_rows,
        selected,
        title=quick_chart_title,
    )

    if metrics_service.has_position_comparison_data(same_full):
        st.markdown("#### Comparativa vs media de su posición en la liga")
        same_comp = metrics_service.filter_comparison_rows_by_metrics(same_full, selected)
        fig_same = _build_vs_position_grouped_bar(same_comp)
        if fig_same is not None:
            st.plotly_chart(fig_same, use_container_width=True)
    elif is_debug_mode():
        st.markdown("#### Comparativa vs media de su posición en la liga")
        st.caption(
            f"Sin datos suficientes en la liga ({competition or '—'}): "
            f"referencia {diag_same.get('cohort_peers', 0)} jugadores."
        )

    if metrics_service.has_position_comparison_data(all_full):
        st.markdown("#### Comparativa vs media de su posición en todas las ligas")
        all_comp = metrics_service.filter_comparison_rows_by_metrics(all_full, selected)
        fig_all = _build_vs_position_grouped_bar(all_comp)
        if fig_all is not None:
            st.plotly_chart(fig_all, use_container_width=True)
    elif is_debug_mode():
        st.markdown("#### Comparativa vs media de su posición en todas las ligas")
        st.caption("Sin datos suficientes entre ligas.")


def _render_objective_explorer() -> None:

    ALL = "— Todas —"
    ALL_TEAM = "— Todos —"

    with get_connection() as conn:
        filt = metrics_service.get_objective_data_filter_options(conn)

    has_data = any(
        filt.get(k) for k in ("seasons", "competitions", "teams", "positions")
    )
    if not has_data:
        empty_state(
            "No se encontraron métricas para esta temporada.",
            "Importa o actualiza datos objetivos para comenzar el análisis.",
            icon="chart",
        )
        return

    seasons_raw = filt.get("seasons") or []
    season_labels, season_label_to_raw = metrics_service.season_filter_labels(seasons_raw)
    active_season = get_active_season()
    active_season_label = season_ui_label(active_season)
    default_season_index = 0
    if active_season_label in season_labels:
        default_season_index = season_labels.index(active_season_label)

    section_header(
        "Filtros",
        "Acota temporada, competición, equipo y posición.",
        icon="filter",
    )
    with st.container(border=False):
        r1a, r1b, r1c = st.columns(3)
        search = r1a.text_input(
            "Buscar jugador",
            value="",
            key="obj_simple_search",
            placeholder="Nombre o parte del nombre",
        )
        season_sel_label = r1b.selectbox(
            "Temporada",
            season_labels if season_labels else [active_season_label],
            index=default_season_index if season_labels else 0,
            key="obj_simple_season",
        )
        comp_sel = r1c.selectbox(
            "Liga / competición",
            [ALL] + (filt.get("competitions") or []),
            key="obj_simple_competition",
        )

        r2a, r2b = st.columns(2)
        pos_sel = r2a.selectbox(
            "Posición objetiva",
            [ALL] + (filt.get("positions") or []),
            key="obj_simple_position",
        )
        team_sel = r2b.selectbox(
            "Equipo objetivo",
            [ALL_TEAM] + (filt.get("teams") or []),
            key="obj_simple_team",
        )

    season_f = season_label_to_raw.get(season_sel_label, active_season)
    comp_f = None if comp_sel == ALL else comp_sel
    pos_f = None if pos_sel == ALL else pos_sel
    team_f = None if team_sel == ALL_TEAM else team_sel
    search_f = search.strip() or None

    with get_connection() as conn:
        rows = metrics_service.get_objective_players_summary(
            conn,
            season=season_f,
            competition=comp_f,
            position=pos_f,
            team=team_f,
            search_text=search_f,
        )

    if not rows:
        st.warning("No hay jugadores que cumplan los filtros.")
        return

    n_players = len({r["player_id"] for r in rows})
    n_teams = len(
        {
            r["objective_team"]
            for r in rows
            if r.get("objective_team") and str(r["objective_team"]).strip() not in ("", "—")
        }
    )
    n_comps = len({r["competition"] for r in rows if r.get("competition")})
    n_seasons = len({r["season"] for r in rows if r.get("season")})

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Jugadores", n_players)
    m2.metric("Equipos", n_teams)
    m3.metric("Ligas", n_comps)
    m4.metric("Temporadas", n_seasons)

    st.subheader("Jugadores")
    table_rows = [
        {
            "Jugador": r.get("player_name"),
            "Posición": r.get("objective_position_group") or "—",
            "Equipo": r.get("objective_team") or "—",
            "Temporada": metric_labels.format_season_label(r.get("season")),
            "Liga": r.get("competition") or "—",
            "Minutos": _fmt_objective_summary_value(r.get("minutes_played")),
            "Partidos": _fmt_objective_summary_value(r.get("matches_played")),
            "Valoración": _fmt_objective_summary_value(r.get("avg_rating")),
        }
        for r in rows
    ]
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    block_labels: list[str] = []
    label_to_block: dict[str, tuple[int, str | None, str | None]] = {}
    for r in rows:
        lab = _objective_block_label(r)
        if lab not in label_to_block:
            label_to_block[lab] = (
                int(r["player_id"]),
                r.get("season"),
                r.get("competition"),
            )
            block_labels.append(lab)

    st.markdown('<hr class="section-hr"/>', unsafe_allow_html=True)
    st.subheader("Scouting objetivo")

    player_sel = st.selectbox(
        "Jugador (temporada y liga)",
        block_labels,
        key="obj_simple_selected_player",
    )
    player_id, block_season, block_comp = label_to_block[player_sel]

    with get_connection() as conn:
        metrics_rows = metrics_service.get_objective_metrics_for_player_block(
            conn,
            player_id,
            block_season,
            block_comp,
        )

    pos_group, _raw_pos, _pos_meta = _resolve_objective_position_context(metrics_rows)
    _render_player_objective_scouting_block(
        player_id=player_id,
        season=block_season,
        competition=block_comp,
        metrics_rows=metrics_rows,
        pos_group=pos_group,
    )


def _is_ohiggins_team_name(team_name: str | None) -> bool:
    return season_comparison_service.is_ohiggins_team_name(team_name)


def _comparison_selector_label(
    row: dict[str, Any],
    player: dict[str, Any] | None,
) -> str:
    name = str((player or {}).get("full_name") or row.get("player_name") or "—")
    position = str(
        (player or {}).get("position")
        or row.get("objective_position_group")
        or "—"
    )
    team = str((player or {}).get("current_team") or row.get("objective_team") or "—")
    comp = str(row.get("competition") or "—")
    season = metric_labels.format_season_label(row.get("season"))
    return f"{name} · {position} · {team} · {comp} · {season}"


def _comparison_player_card(
    *,
    title: str,
    role_label: str,
    accent_color: str,
    player: dict[str, Any] | None,
    block_row: dict[str, Any],
) -> None:
    age_now: int | None = None
    if player:
        _, age_now, _bd_disp, _h_disp = _player_demographics(player)

    name = str((player or {}).get("full_name") or block_row.get("player_name") or "—")
    team = str((player or {}).get("current_team") or block_row.get("objective_team") or "—")
    pos = str(
        (player or {}).get("position")
        or block_row.get("objective_position_group")
        or "—"
    )
    age = f"{age_now} años" if age_now is not None else "—"

    st.markdown(
        (
            '<div class="cmp-identity-card" style="border-color:{color};">'
            '<div class="cmp-identity-head" style="background:{color};">'
            '{title}'
            "</div>"
            '<div class="cmp-identity-body">'
            '<div class="cmp-identity-role" style="color:{color};">{role}</div>'
            '<div class="cmp-identity-name">{name}</div>'
            '<div class="cmp-identity-line">{team}</div>'
            '<div class="cmp-identity-line">{pos}</div>'
            '<div class="cmp-identity-line">{age}</div>'
            "</div>"
            "</div>"
        ).format(
            color=accent_color,
            title=html.escape(title),
            role=html.escape(role_label),
            name=html.escape(name),
            team=html.escape(team),
            pos=html.escape(pos),
            age=html.escape(age),
        ),
        unsafe_allow_html=True,
    )


def _comparison_percentile_card_html(
    *,
    metric_label: str,
    pct_oh: float,
    pct_cmp: float,
    value_oh: str,
    value_cmp: str,
    oh_color: str,
    cmp_color: str,
    legend_oh: str = "O'Higgins",
    legend_cmp: str = "Comparado",
    metric_name: str = "",
) -> str:
    return comparison_percentile_card_html(
        metric_label=metric_label,
        pct_a=pct_oh,
        pct_b=pct_cmp,
        value_a=value_oh,
        value_b=value_cmp,
        color_a=oh_color,
        color_b=cmp_color,
        legend_a=legend_oh,
        legend_b=legend_cmp,
        lower_is_better=metric_direction.is_lower_better_metric(metric_name),
    )


def _comparison_percentile_badge_color(percentile: float) -> str:
    pct = max(0.0, min(100.0, float(percentile)))
    if pct < 25:
        return "#DC2626"
    if pct < 50:
        return "#F59E0B"
    if pct < 75:
        return "#FFDD00"
    if pct < 90:
        return "#7BC96F"
    return "#49A942"


def _comparison_diff_visual(diff: float) -> tuple[str, str, str]:
    if abs(diff) < 1.0:
        return "→", "cmp-diff-neutral", f"{diff:+.1f}"
    if diff >= 8:
        return "↑", "cmp-diff-positive", f"{diff:+.1f}"
    if diff >= 1:
        return "↗", "cmp-diff-positive-soft", f"{diff:+.1f}"
    if diff <= -8:
        return "↓", "cmp-diff-negative", f"{diff:+.1f}"
    return "↘", "cmp-diff-negative-soft", f"{diff:+.1f}"


def _comparison_metric_cell_html(
    *,
    value_text: str,
    percentile: float,
    owner_class: str,
    winner_class: str,
) -> str:
    pct = max(0.0, min(100.0, float(percentile)))
    pct_i = int(round(pct))
    badge_bg = _comparison_percentile_badge_color(pct)
    return (
        f'<div class="cmp-table-cell {owner_class} {winner_class}">'
        f'<div class="cmp-table-value-line"><span class="cmp-table-value">{html.escape(value_text)}</span>'
        f'<span class="cmp-pct-badge" style="background:{badge_bg};">P{pct_i}</span></div>'
        f'<div class="cmp-table-pct-track"><div class="cmp-table-pct-fill" style="width:{pct:.1f}%;background:{badge_bg};"></div></div>'
        f"</div>"
    )


def _render_comparison_tab() -> None:
    section_header(
        "Modo de comparación",
        "Elige entre jugadores o rendimiento por temporada.",
        icon="compare",
    )
    tab_players, tab_season = st.tabs(
        ["Comparar jugadores", "Comparar rendimiento por temporada"]
    )
    with tab_players:
        _render_comparison_players_mode()
    with tab_season:
        _render_comparison_season_mode()


def _render_comparison_players_mode() -> None:
    OH_BLUE = "#5091CD"
    CMP_GREEN = "#49A942"
    OH_YELLOW = "#FFDD00"
    OH_BLACK = "#000000"

    st.markdown(
        comparison_legend_html(
            label_a="Jugador O'Higgins",
            label_b="Jugador comparado",
            color_a=OH_BLUE,
            color_b=CMP_GREEN,
        ),
        unsafe_allow_html=True,
    )

    with get_connection() as conn:
        all_rows = metrics_service.get_objective_players_summary(conn)
        players_all = players_service.list_players_for_lookup(
            conn,
            include_objective_only=True,
        )

    if not all_rows:
        st.warning("No hay jugadores con métricas objetivas para comparar.")
        return

    player_map = {int(p["id"]): p for p in players_all}

    labels_all: list[str] = []
    label_to_row: dict[str, dict[str, Any]] = {}
    labels_oh: list[str] = []
    for row in all_rows:
        pid = int(row["player_id"])
        player = player_map.get(pid)
        lab = _comparison_selector_label(row, player)
        if lab in label_to_row:
            continue
        label_to_row[lab] = row
        labels_all.append(lab)
        scouting_team = (player or {}).get("current_team")
        if _is_ohiggins_team_name(row.get("objective_team")) or _is_ohiggins_team_name(
            scouting_team
        ):
            labels_oh.append(lab)

    if not labels_oh:
        labels_oh = list(labels_all)

    s1, s2 = st.columns(2)
    with s1:
        player_a_label = st.selectbox(
            "Jugador a analizar",
            labels_all,
            key="cmp_player_a",
        )
    with s2:
        player_b_label = st.selectbox(
            "Jugador O'Higgins",
            labels_oh,
            key="cmp_player_b",
        )

    selected_pair = (player_a_label, player_b_label)
    if st.session_state.get("cmp_last_pair") != selected_pair:
        st.session_state["cmp_compare_requested"] = False

    if st.button(labeled("compare", "Comparar jugadores"), type="primary", key="cmp_run"):
        st.session_state["cmp_last_pair"] = selected_pair
        st.session_state["cmp_compare_requested"] = True
    if not st.session_state.get("cmp_compare_requested", False):
        return

    row_a = label_to_row[player_a_label]
    row_b = label_to_row[player_b_label]
    pid_a = int(row_a["player_id"])
    pid_b = int(row_b["player_id"])

    with get_connection() as conn:
        player_a = players_service.fetch_player(conn, pid_a)
        player_b = players_service.fetch_player(conn, pid_b)
        metrics_a = metrics_service.get_objective_metrics_for_player_block(
            conn, pid_a, row_a.get("season"), row_a.get("competition")
        )
        metrics_b = metrics_service.get_objective_metrics_for_player_block(
            conn, pid_b, row_b.get("season"), row_b.get("competition")
        )

    if not metrics_a or not metrics_b:
        st.warning("No hay métricas suficientes para comparar estos jugadores.")
        return

    is_a_oh = _is_ohiggins_team_name(row_a.get("objective_team")) or _is_ohiggins_team_name(
        (player_a or {}).get("current_team")
    )
    is_b_oh = _is_ohiggins_team_name(row_b.get("objective_team")) or _is_ohiggins_team_name(
        (player_b or {}).get("current_team")
    )
    oh_key = "b" if (is_b_oh or not is_a_oh) else "a"
    cmp_key = "a" if oh_key == "b" else "b"
    pos_group_a, _raw_pos_a = metrics_service.resolve_objective_comparison_position(metrics_a)
    pos_group_b, _raw_pos_b = metrics_service.resolve_objective_comparison_position(metrics_b)
    same_position_group = bool(pos_group_a and pos_group_b and pos_group_a == pos_group_b)
    cohort_resolution = comparison_cohort_service.resolve_player_comparison_cohort(
        season_a=row_a.get("season"),
        season_b=row_b.get("season"),
        competition_a=row_a.get("competition"),
        competition_b=row_b.get("competition"),
        position_group_a=pos_group_a,
        position_group_b=pos_group_b,
    )
    if (
        cohort_resolution["cohort_type"]
        == comparison_cohort_service.COHORT_DIFFERENT_POSITIONS
    ):
        st.warning(
            "Los jugadores tienen posiciones distintas; la comparación puede no ser equivalente."
        )

    available_a = set(metrics_service.block_metric_names_for_ui(metrics_a))
    available_b = set(metrics_service.block_metric_names_for_ui(metrics_b))
    available_a_all = sorted(available_a, key=metric_labels.metric_sort_key)
    available_b_all = sorted(available_b, key=metric_labels.metric_sort_key)
    common_raw = sorted(available_a & available_b, key=metric_labels.metric_sort_key)

    with get_connection() as conn:
        rows_pct_a_global, _diag_a_global = (
            metrics_service.get_comparison_percentile_rows_for_player(
                conn,
                pid_a,
                row_a.get("season"),
                row_a.get("competition"),
                metrics_a,
                available_a_all,
                cohort_resolution,
            )
        )
        rows_pct_b_global, _diag_b_global = (
            metrics_service.get_comparison_percentile_rows_for_player(
                conn,
                pid_b,
                row_b.get("season"),
                row_b.get("competition"),
                metrics_b,
                available_b_all,
                cohort_resolution,
            )
        )
        rows_pct_a_all, _diag_a_all = (
            metrics_service.get_comparison_percentile_rows_for_player(
                conn,
                pid_a,
                row_a.get("season"),
                row_a.get("competition"),
                metrics_a,
                common_raw,
                cohort_resolution,
            )
        )
        rows_pct_b_all, _diag_b_all = (
            metrics_service.get_comparison_percentile_rows_for_player(
                conn,
                pid_b,
                row_b.get("season"),
                row_b.get("competition"),
                metrics_b,
                common_raw,
                cohort_resolution,
            )
        )

    by_metric_a_all = {str(r.get("metric_name")): r for r in rows_pct_a_all}
    by_metric_b_all = {str(r.get("metric_name")): r for r in rows_pct_b_all}
    comparable_a = set(by_metric_a_all.keys())
    comparable_b = set(by_metric_b_all.keys())
    available_metrics = sorted(
        set(common_raw) & comparable_a & comparable_b,
        key=metric_labels.metric_sort_key,
    )

    if not available_metrics:
        st.warning("No hay métricas comparables entre ambos jugadores.")
        return

    if is_debug_mode():
        union_metrics = sorted(available_a | available_b, key=metric_labels.metric_sort_key)
        excluded_rows: list[dict[str, str]] = []
        for metric_name in union_metrics:
            in_a = metric_name in available_a
            in_b = metric_name in available_b
            in_comparable = metric_name in comparable_a and metric_name in comparable_b
            if metric_name in available_metrics:
                continue
            if not (in_a and in_b):
                reason = "No disponible en ambos"
            elif not in_comparable:
                reason = "Sin percentil comparable en ambos"
            else:
                reason = "Excluida por filtros de comparación"
            excluded_rows.append(
                {
                    "Métrica": metric_labels.metric_label(metric_name),
                    "Disponible en jugador A": "Sí" if in_a else "No",
                    "Disponible en jugador B": "Sí" if in_b else "No",
                    "Motivo": reason,
                }
            )
        with st.expander("Métricas excluidas", expanded=False):
            if excluded_rows:
                st.dataframe(
                    pd.DataFrame(excluded_rows),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.caption("Sin métricas excluidas.")

    common_metrics = list(available_metrics)
    by_metric_a = {m: by_metric_a_all[m] for m in common_metrics if m in by_metric_a_all}
    by_metric_b = {m: by_metric_b_all[m] for m in common_metrics if m in by_metric_b_all}
    common_metrics = [m for m in common_metrics if m in by_metric_a and m in by_metric_b]
    if not common_metrics:
        st.warning("No hay percentiles comparables entre ambos jugadores.")
        return

    if oh_key == "b":
        _render_objective_dual_comparison_view(
            row_a=row_b,
            row_b=row_a,
            player_a=player_b,
            player_b=player_a,
            by_metric_a=by_metric_b,
            by_metric_b=by_metric_a,
            rows_pct_a_global=rows_pct_b_global,
            rows_pct_b_global=rows_pct_a_global,
            pos_group_a=pos_group_b,
            pos_group_b=pos_group_a,
            common_metrics=common_metrics,
            color_a=OH_BLUE,
            color_b=CMP_GREEN,
            title_a="Jugador O'Higgins",
            title_b="Jugador comparado",
            role_a="Referencia del club",
            role_b="Posible fichaje",
            table_header_a="O'Higgins",
            table_header_b="Comparado",
            profile_label_a="O'Higgins",
            profile_label_b="Jugador comparado",
            radar_name_a="O'Higgins",
            radar_name_b="Comparado",
            deltas_heading="### Diferencias clave",
            delta_a_better="O'Higgins superior en",
            delta_b_better="Jugador comparado superior en",
            diag_a=_diag_b_global,
            diag_b=_diag_a_global,
            cohort_resolution=cohort_resolution,
        )
    else:
        _render_objective_dual_comparison_view(
            row_a=row_a,
            row_b=row_b,
            player_a=player_a,
            player_b=player_b,
            by_metric_a=by_metric_a,
            by_metric_b=by_metric_b,
            rows_pct_a_global=rows_pct_a_global,
            rows_pct_b_global=rows_pct_b_global,
            pos_group_a=pos_group_a,
            pos_group_b=pos_group_b,
            common_metrics=common_metrics,
            color_a=OH_BLUE,
            color_b=CMP_GREEN,
            title_a="Jugador O'Higgins",
            title_b="Jugador comparado",
            role_a="Referencia del club",
            role_b="Posible fichaje",
            table_header_a="O'Higgins",
            table_header_b="Comparado",
            profile_label_a="O'Higgins",
            profile_label_b="Jugador comparado",
            radar_name_a="O'Higgins",
            radar_name_b="Comparado",
            deltas_heading="### Diferencias clave",
            delta_a_better="O'Higgins superior en",
            delta_b_better="Jugador comparado superior en",
            diag_a=_diag_a_global,
            diag_b=_diag_b_global,
            cohort_resolution=cohort_resolution,
        )


def _render_comparison_season_mode() -> None:
    OH_BLUE = "#5091CD"
    HIST_GREEN = "#49A942"
    active = get_active_season()
    historical = get_historical_season()
    active_label = season_ui_label(active)
    hist_label = season_ui_label(historical)

    st.markdown(
        comparison_legend_html(
            label_a=f"Temporada actual ({active_label})",
            label_b=f"Temporada anterior ({hist_label})",
            color_a=OH_BLUE,
            color_b=HIST_GREEN,
        ),
        unsafe_allow_html=True,
    )
    st.caption(
        "Se comparan estadísticas asociadas a O'Higgins en cada temporada."
    )

    allow_demo = st.checkbox(
        "Usar datos de demostración como referencia",
        value=False,
        key="cmp_season_allow_demo",
        help="Desactivado por defecto. No compares datos oficiales con demostración.",
    )
    if allow_demo:
        st.warning(
            "Comparación con datos de demostración (referencia no oficial). "
            "Prefiere descargar la temporada histórica."
        )

    with get_connection() as conn:
        gate, candidates = season_comparison_service.list_ohiggins_season_comparison_candidates(
            conn, allow_demo_fallback=allow_demo
        )

    if not gate.allowed:
        st.error(
            gate.message
            or (
                f"La comparación real requiere descargar las temporadas {hist_label} y {active_label}."
            )
        )
        if gate.origin_active != "sofascore" or gate.origin_historical != "sofascore":
            st.info(
                "La comparación real requiere descargar las temporadas "
                f"{hist_label} y {active_label}. "
                "Usa el botón del Dashboard («Descargar datos reales» / "
                "«Completar datos históricos»)."
            )
        return

    if gate.warning:
        st.warning(gate.warning)

    if not candidates:
        st.warning("No hay jugadores O'Higgins con datos en la temporada actual.")
        return

    labels = [
        season_comparison_service.season_candidate_selector_label(c) for c in candidates
    ]
    label_to_cand = dict(zip(labels, candidates, strict=True))
    selected_label = st.selectbox(
        "Jugador O'Higgins",
        labels,
        key="cmp_season_player",
    )
    candidate = label_to_cand[selected_label]
    st.caption(
        f"{candidate.status_message} · "
        f"Equipo {active_label}: {candidate.team_active}"
        + (
            f" · Equipo {hist_label}: {candidate.team_historical}"
            if candidate.team_historical
            else ""
        )
    )
    if candidate.external_id:
        # Matching es modo depuración: el ID externo queda en expander técnico.
        with st.expander("Detalle técnico del emparejamiento", expanded=False):
            st.caption(f"Identificador externo: {candidate.external_id}")

    if candidate.status != "comparable":
        st.info(candidate.status_message)
        return

    if st.button(labeled("compare", "Comparar temporadas"), type="primary", key="cmp_season_run"):
        st.session_state["cmp_season_requested"] = True
    if not st.session_state.get("cmp_season_requested", False):
        return

    row_a = candidate.row_active
    row_b = candidate.row_historical or {}
    pid_a = candidate.player_id_active
    pid_b = int(candidate.player_id_historical or 0)

    with get_connection() as conn:
        player_a = players_service.fetch_player(conn, pid_a)
        player_b = players_service.fetch_player(conn, pid_b)
        metrics_a = metrics_service.get_objective_metrics_for_player_block(
            conn, pid_a, row_a.get("season"), row_a.get("competition")
        )
        metrics_b = metrics_service.get_objective_metrics_for_player_block(
            conn, pid_b, row_b.get("season"), row_b.get("competition")
        )

    if not metrics_a or not metrics_b:
        st.warning("No hay métricas suficientes para comparar estas temporadas.")
        return

    pos_group_a, _ = metrics_service.resolve_objective_comparison_position(metrics_a)
    pos_group_b, _ = metrics_service.resolve_objective_comparison_position(metrics_b)
    if pos_group_a and pos_group_b and pos_group_a != pos_group_b:
        st.warning("La posición del jugador difiere entre temporadas; interpreta con cautela.")

    available_a = set(metrics_service.block_metric_names_for_ui(metrics_a))
    available_b = set(metrics_service.block_metric_names_for_ui(metrics_b))
    common_raw = sorted(available_a & available_b, key=metric_labels.metric_sort_key)

    cohort_mode = comparison_cohort_service.COHORT_MODE_COMBINED_SEASONS
    if is_debug_mode():
        with st.expander("Opciones técnicas de cohorte", expanded=False):
            cohort_mode = st.radio(
                "Cálculo de percentiles",
                options=[
                    comparison_cohort_service.COHORT_MODE_COMBINED_SEASONS,
                    comparison_cohort_service.COHORT_MODE_PER_SEASON,
                ],
                format_func=lambda x: (
                    "Cohorte común (temporadas combinadas)"
                    if x == comparison_cohort_service.COHORT_MODE_COMBINED_SEASONS
                    else "Cohorte propia por temporada"
                ),
                index=0,
                key="cmp_season_cohort_mode",
            )

    cohort_resolution = comparison_cohort_service.resolve_season_comparison_cohort(
        season_active=row_a.get("season"),
        season_historical=row_b.get("season"),
        competition_active=row_a.get("competition"),
        competition_historical=row_b.get("competition"),
        position_group_active=pos_group_a,
        position_group_historical=pos_group_b,
        cohort_mode=cohort_mode,
    )

    with get_connection() as conn:
        rows_pct_a_global, diag_a_global = (
            metrics_service.get_comparison_percentile_rows_for_player(
                conn,
                pid_a,
                row_a.get("season"),
                row_a.get("competition"),
                metrics_a,
                sorted(available_a, key=metric_labels.metric_sort_key),
                cohort_resolution,
            )
        )
        rows_pct_b_global, diag_b_global = (
            metrics_service.get_comparison_percentile_rows_for_player(
                conn,
                pid_b,
                row_b.get("season"),
                row_b.get("competition"),
                metrics_b,
                sorted(available_b, key=metric_labels.metric_sort_key),
                cohort_resolution,
            )
        )
        rows_pct_a_all, diag_a_all = (
            metrics_service.get_comparison_percentile_rows_for_player(
                conn,
                pid_a,
                row_a.get("season"),
                row_a.get("competition"),
                metrics_a,
                common_raw,
                cohort_resolution,
            )
        )
        rows_pct_b_all, diag_b_all = (
            metrics_service.get_comparison_percentile_rows_for_player(
                conn,
                pid_b,
                row_b.get("season"),
                row_b.get("competition"),
                metrics_b,
                common_raw,
                cohort_resolution,
            )
        )

    by_metric_a_all = {str(r.get("metric_name")): r for r in rows_pct_a_all}
    by_metric_b_all = {str(r.get("metric_name")): r for r in rows_pct_b_all}
    available_metrics = sorted(
        set(common_raw) & set(by_metric_a_all) & set(by_metric_b_all),
        key=metric_labels.metric_sort_key,
    )
    if not available_metrics:
        st.warning("No hay métricas comparables entre ambas temporadas.")
        return

    common_metrics = list(available_metrics)
    by_metric_a = {m: by_metric_a_all[m] for m in common_metrics if m in by_metric_a_all}
    by_metric_b = {m: by_metric_b_all[m] for m in common_metrics if m in by_metric_b_all}
    common_metrics = [m for m in common_metrics if m in by_metric_a and m in by_metric_b]
    if not common_metrics:
        st.warning("No hay percentiles comparables entre ambas temporadas.")
        return

    player_name = candidate.display_name
    _render_objective_dual_comparison_view(
        row_a=row_a,
        row_b=row_b,
        player_a=player_a,
        player_b=player_b,
        by_metric_a=by_metric_a,
        by_metric_b=by_metric_b,
        rows_pct_a_global=rows_pct_a_global,
        rows_pct_b_global=rows_pct_b_global,
        pos_group_a=pos_group_a,
        pos_group_b=pos_group_b,
        common_metrics=common_metrics,
        color_a=OH_BLUE,
        color_b=HIST_GREEN,
        title_a=f"{player_name} · {active_label}",
        title_b=f"{player_name} · {hist_label}",
        role_a="Temporada actual",
        role_b="Temporada anterior",
        table_header_a=active_label,
        table_header_b=hist_label,
        profile_label_a=active_label,
        profile_label_b=hist_label,
        radar_name_a=active_label,
        radar_name_b=hist_label,
        deltas_heading="### Evolución del rendimiento",
        delta_a_better="Mejoró en",
        delta_b_better="Empeoró en",
        diag_a=diag_a_global,
        diag_b=diag_b_global,
        cohort_resolution=cohort_resolution,
    )


def _cohort_technical_rows(
    *,
    label: str,
    diag: dict[str, Any] | None,
    row: dict[str, Any],
    pos_group: str | None,
) -> dict[str, str]:
    d = diag or {}
    leagues = d.get("cohort_competitions") or ([row.get("competition")] if row.get("competition") else [])
    leagues_txt = " · ".join(str(x) for x in leagues if x) or "—"
    seasons = d.get("cohort_seasons") or []
    if not seasons:
        seasons = [d.get("season") or row.get("season")]
    seasons_txt = " · ".join(str(s) for s in seasons if s) or "—"
    return {
        "Perfil": label,
        "Tipo cohorte": str(d.get("cohort_type") or "—"),
        "Competición": leagues_txt,
        "Temporadas cohorte": seasons_txt,
        "Temporada del bloque": str(row.get("season") or "—"),
        "Posición": str(d.get("position_group") or pos_group or "—"),
        "Jugadores en cohorte": str(int(d.get("cohort_peers") or 0)),
    }


def _render_comparison_cohort_banner(
    *,
    diag_a: dict[str, Any] | None,
    diag_b: dict[str, Any] | None,
    cohort_resolution: dict[str, Any] | None,
) -> None:
    """Mensajes de cohorte (solo modo depuración)."""
    if not is_debug_mode():
        return
    msg = (cohort_resolution or {}).get("ui_message")
    if not msg and diag_a:
        msg = diag_a.get("cohort_ui_message")
    if not msg and diag_b:
        msg = diag_b.get("cohort_ui_message")
    if not msg:
        return
    cohort_type = (cohort_resolution or {}).get("cohort_type") or (diag_a or {}).get(
        "cohort_type"
    )
    if cohort_type == comparison_cohort_service.COHORT_DIFFERENT_POSITIONS:
        st.warning(msg)
    else:
        st.info(msg)


def _render_comparison_cohort_technical(
    *,
    label_a: str,
    label_b: str,
    row_a: dict[str, Any],
    row_b: dict[str, Any],
    pos_group_a: str | None,
    pos_group_b: str | None,
    diag_a: dict[str, Any] | None,
    diag_b: dict[str, Any] | None,
) -> None:
    if not is_debug_mode():
        return
    with st.expander("Cohorte (detalle técnico)", expanded=False):
        rows = [
            _cohort_technical_rows(
                label=label_a,
                diag=diag_a,
                row=row_a,
                pos_group=pos_group_a,
            ),
            _cohort_technical_rows(
                label=label_b,
                diag=diag_b,
                row=row_b,
                pos_group=pos_group_b,
            ),
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_objective_dual_comparison_view(
    *,
    row_a: dict[str, Any],
    row_b: dict[str, Any],
    player_a: dict[str, Any] | None,
    player_b: dict[str, Any] | None,
    by_metric_a: dict[str, dict[str, Any]],
    by_metric_b: dict[str, dict[str, Any]],
    rows_pct_a_global: list[dict[str, Any]],
    rows_pct_b_global: list[dict[str, Any]],
    pos_group_a: str | None,
    pos_group_b: str | None,
    common_metrics: list[str],
    color_a: str,
    color_b: str,
    title_a: str,
    title_b: str,
    role_a: str,
    role_b: str,
    table_header_a: str,
    table_header_b: str,
    profile_label_a: str,
    profile_label_b: str,
    radar_name_a: str,
    radar_name_b: str,
    deltas_heading: str,
    delta_a_better: str,
    delta_b_better: str,
    diag_a: dict[str, Any] | None = None,
    diag_b: dict[str, Any] | None = None,
    cohort_resolution: dict[str, Any] | None = None,
) -> None:
    OH_YELLOW = "#FFDD00"
    OH_BLACK = "#000000"

    _render_comparison_cohort_banner(
        diag_a=diag_a,
        diag_b=diag_b,
        cohort_resolution=cohort_resolution,
    )
    _render_comparison_cohort_technical(
        label_a=table_header_a,
        label_b=table_header_b,
        row_a=row_a,
        row_b=row_b,
        pos_group_a=pos_group_a,
        pos_group_b=pos_group_b,
        diag_a=diag_a,
        diag_b=diag_b,
    )

    st.markdown("### Cabecera comparativa")
    c1, c_vs, c2 = st.columns([1, 0.25, 1], gap="medium")
    with c1:
        _comparison_player_card(
            title=title_a,
            role_label=role_a,
            accent_color=color_a,
            player=player_a,
            block_row=row_a,
        )
    with c_vs:
        st.markdown(
            (
                '<div class="cmp-vs-wrap">'
                '<div class="cmp-vs" style="background:{yellow};color:{black};">VS</div>'
                "</div>"
            ).format(yellow=OH_YELLOW, black=OH_BLACK),
            unsafe_allow_html=True,
        )
    with c2:
        _comparison_player_card(
            title=title_b,
            role_label=role_b,
            accent_color=color_b,
            player=player_b,
            block_row=row_b,
        )

    global_pct_a, global_used_a = _compute_global_profile_percentile(rows_pct_a_global)
    global_pct_b, global_used_b = _compute_global_profile_percentile(rows_pct_b_global)

    st.markdown("### Perfil global")
    if global_pct_a is not None and global_pct_b is not None:
        gg1, gg2 = st.columns(2, gap="medium")
        with gg1:
            st.markdown(f"#### {profile_label_a}")
            _render_global_profile_card(
                percentile=global_pct_a,
                position_group=pos_group_a,
                competition=row_a.get("competition"),
                metrics_used=len(global_used_a),
            )
        with gg2:
            st.markdown(f"#### {profile_label_b}")
            _render_global_profile_card(
                percentile=global_pct_b,
                position_group=pos_group_b,
                competition=row_b.get("competition"),
                metrics_used=len(global_used_b),
            )
        st.markdown(
            f"**PERFIL GLOBAL:** P{int(round(global_pct_a))} vs P{int(round(global_pct_b))}"
        )
    else:
        st.caption("Sin métricas suficientes para calcular el perfil global en ambos perfiles.")

    st.markdown("### Comparativa de percentiles")
    st.markdown(
        _comparison_objective_series_legend_html(
            label_a=radar_name_a,
            label_b=radar_name_b,
            color_a=color_a,
            color_b=color_b,
        ),
        unsafe_allow_html=True,
    )
    _render_comparison_percentile_cards_grouped(
        common_metrics=common_metrics,
        by_metric_a=by_metric_a,
        by_metric_b=by_metric_b,
        color_a=color_a,
        color_b=color_b,
        table_header_a=table_header_a,
        table_header_b=table_header_b,
    )

    _render_comparison_percentile_radars_by_group(
        common_metrics=common_metrics,
        by_metric_a=by_metric_a,
        by_metric_b=by_metric_b,
        pos_group_a=pos_group_a,
        pos_group_b=pos_group_b,
        radar_name_a=radar_name_a,
        radar_name_b=radar_name_b,
        color_a=color_a,
        color_b=color_b,
    )

    st.markdown(deltas_heading)
    deltas: list[tuple[str, float]] = []
    for m in common_metrics:
        p_a = float(by_metric_a[m].get("percentile") or 0.0)
        p_b = float(by_metric_b[m].get("percentile") or 0.0)
        deltas.append((m, p_a - p_b))
    best_a = sorted([x for x in deltas if x[1] > 0], key=lambda x: -x[1])[:5]
    best_b = sorted([x for x in deltas if x[1] < 0], key=lambda x: x[1])[:5]

    d1, d2 = st.columns(2, gap="large")
    with d1:
        st.markdown(f"#### {delta_a_better}")
        if best_a:
            for metric_name, diff in best_a:
                row_ma = by_metric_a[metric_name]
                row_mb = by_metric_b[metric_name]
                p_from = int(round(float(row_mb.get("percentile") or 0)))
                p_to = int(round(float(row_ma.get("percentile") or 0)))
                st.markdown(
                    f"- {metric_labels.metric_label(metric_name)}: P{p_from} → P{p_to} (+{diff:.0f})"
                )
        else:
            st.caption("Sin mejoras claras en la selección actual.")
    with d2:
        st.markdown(f"#### {delta_b_better}")
        if best_b:
            for metric_name, diff in best_b:
                row_ma = by_metric_a[metric_name]
                row_mb = by_metric_b[metric_name]
                p_from = int(round(float(row_ma.get("percentile") or 0)))
                p_to = int(round(float(row_mb.get("percentile") or 0)))
                st.markdown(
                    f"- {metric_labels.metric_label(metric_name)}: P{p_from} → P{p_to} ({diff:.0f})"
                )
        else:
            st.caption("Sin empeoramientos claros en la selección actual.")

    st.markdown("### Tabla comparativa")
    rows_html: list[str] = []
    for m in common_metrics:
        row_ma = by_metric_a[m]
        row_mb = by_metric_b[m]
        pct_a = float(row_ma.get("percentile") or 0.0)
        pct_b = float(row_mb.get("percentile") or 0.0)
        val_a = metric_labels.format_metric_value(
            row_ma.get("player_value"), row_ma.get("metric_unit"), metric_name=m
        )
        val_b = metric_labels.format_metric_value(
            row_mb.get("player_value"), row_mb.get("metric_unit"), metric_name=m
        )
        diff = pct_a - pct_b
        arrow, diff_class, diff_txt = _comparison_diff_visual(diff)
        winner_a = "cmp-winner-oh" if pct_a > pct_b else ""
        winner_b = "cmp-winner-cmp" if pct_b > pct_a else ""
        rows_html.append(
            (
                "<tr>"
                '<td class="cmp-col-metric">{metric}</td>'
                '<td>{cell_a}</td>'
                '<td>{cell_b}</td>'
                '<td class="cmp-col-diff {diff_class}">{diff_txt} <span class="cmp-diff-arrow">{arrow}</span></td>'
                "</tr>"
            ).format(
                metric=html.escape(metric_labels.metric_label(m)),
                cell_a=_comparison_metric_cell_html(
                    value_text=str(val_a),
                    percentile=pct_a,
                    owner_class="cmp-owner-oh",
                    winner_class=winner_a,
                ),
                cell_b=_comparison_metric_cell_html(
                    value_text=str(val_b),
                    percentile=pct_b,
                    owner_class="cmp-owner-cmp",
                    winner_class=winner_b,
                ),
                diff_class=diff_class,
                diff_txt=html.escape(diff_txt),
                arrow=arrow,
            )
        )
    st.markdown(
        (
            '<div class="cmp-table-wrap">'
            "<table>"
            "<thead>"
            "<tr>"
            "<th>Métrica</th>"
            f"<th>{html.escape(table_header_a)}</th>"
            f"<th>{html.escape(table_header_b)}</th>"
            "<th>Cambio</th>"
            "</tr>"
            "</thead>"
            "<tbody>"
            "{rows}"
            "</tbody>"
            "</table>"
            "</div>"
        ).format(rows="".join(rows_html)),
        unsafe_allow_html=True,
    )


def _render_player_subjective_comparison_block(
    *,
    player: dict[str, Any],
    player_id: int,
    report_attrs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Radares subjetivos; devuelve filas de detalle numérico para pestaña técnica."""
    st.markdown(
        '<span class="subjective-radars-section-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    st.markdown("#### Comparativa vs media de la misma posición")
    pos = player.get("position")
    if not pos or not str(pos).strip():
        st.info("Asigna una posición en la ficha para ver la comparativa subjetiva.")
        return []
    if not report_attrs:
        st.info("El informe seleccionado no tiene valoraciones por atributo.")
        return []

    pos_s = str(pos).strip()
    try:
        template_key = templates_service.get_template_key_for_position(pos_s)
    except KeyError:
        template_key = pos_s

    with get_connection() as conn:
        bench = _build_subjective_benchmark_for_report(
            conn, pos_s, player_id, report_attrs
        )

    if not bench:
        st.info("No hay datos suficientes de la plantilla para esta comparativa.")
        return []

    cohort_label = "Media plantilla" if not is_debug_mode() else f"Media plantilla ({template_key})"
    block_rows = _aggregate_subjective_benchmark_by_group(bench, position=pos_s)
    group_options = [r["attribute_group"] for r in block_rows]
    if not group_options:
        group_options = sorted(
            {str(b.get("attribute_group") or "—") for b in bench},
            key=lambda g: (g == "—", g),
        )

    detail_rows = [
        {
            "attribute_group": b.get("attribute_group"),
            "attribute_name": b["attribute_name"],
            "player_avg_rating": round(b["player_avg_rating"], 2),
            "position_avg_rating": round(b["position_avg_rating"], 2),
            "difference": round(b["difference"], 2),
        }
        for b in templates_service.sort_attributes_by_position_template(pos_s, bench)
    ]

    st.caption("Azul: jugador · Gris: media plantilla")

    if block_rows:
        st.markdown("##### Radar por bloques")
        block_chart_rows = [
            {
                "attribute_group": r["attribute_group"],
                "player_avg_rating": r["player_avg_rating"],
                "position_avg_rating": r["position_avg_rating"],
            }
            for r in block_rows
        ]
        if len(block_chart_rows) >= 3:
            fig_blocks = _build_subjective_radar_figure(
                block_chart_rows,
                label_key="attribute_group",
                cohort_trace_name=cohort_label,
                title="",
                height=460,
                radar_size="blocks",
            )
        else:
            fig_blocks = _build_subjective_grouped_bar(
                block_chart_rows,
                label_key="attribute_group",
                player_key="player_avg_rating",
                position_key="position_avg_rating",
            )
        if fig_blocks is not None:
            pad_l, pad_c, pad_r = st.columns([0.4, 9.2, 0.4])
            with pad_c:
                st.markdown(
                    '<span class="subjective-radar-blocks-marker" aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
                st.plotly_chart(
                    fig_blocks,
                    use_container_width=True,
                    config=plotly_radar_chart_config(),
                )

    ordered_groups = templates_service.ordered_attribute_groups_for_position(
        set(group_options),
        pos_s,
    )
    if not ordered_groups:
        ordered_groups = group_options

    group_figures: list[tuple[str, go.Figure]] = []
    for group_name in ordered_groups:
        detail_bench = [
            b for b in bench if str(b.get("attribute_group")) == group_name
        ]
        detail_bench = templates_service.sort_attributes_by_position_template(
            pos_s, detail_bench
        )
        if not detail_bench:
            continue
        detail_chart = [
            {
                "attribute_name": b["attribute_name"],
                "player_avg_rating": b["player_avg_rating"],
                "position_avg_rating": b["position_avg_rating"],
            }
            for b in detail_bench
        ]
        if len(detail_chart) >= 3:
            fig_detail = _build_subjective_radar_figure(
                detail_chart,
                label_key="attribute_name",
                attribute_group=group_name,
                cohort_trace_name=cohort_label,
                title="",
                height=400,
                radar_size="detail",
            )
        else:
            fig_detail = _build_subjective_grouped_bar(
                detail_chart,
                label_key="attribute_name",
                player_key="player_avg_rating",
                position_key="position_avg_rating",
                attribute_group=group_name,
            )
        if fig_detail is not None:
            group_figures.append((group_name, fig_detail))

    if group_figures:
        st.markdown("##### Radares por bloque")
        _render_detail_radar_grid(group_figures)

    return detail_rows


def _render_player_lookup() -> None:
    st.caption("Informe de scouting · valoración cualitativa y análisis estadístico.")

    include_objective_only = st.checkbox(
        "Incluir jugadores solo con datos objetivos (sin informes)",
        value=False,
        key="player_lookup_include_objective_only",
    )

    with get_connection() as conn:
        players = players_service.list_players_for_lookup(
            conn, include_objective_only=include_objective_only
        )

    if not players:
        empty_state(
            "No hay jugadores para consultar.",
            "Crea un informe manual o activa la inclusión de perfiles solo objetivos.",
            icon="player",
        )
        return

    labels = [
        f"{p['full_name']} ({p.get('current_team') or '—'})"
        for p in players
    ]
    label_to_id = {lab: int(p["id"]) for lab, p in zip(labels, players, strict=True)}
    select_options = [PLAYER_LOOKUP_NONE_LABEL, *labels]

    sel_col, clr_col = st.columns([4, 1])
    with sel_col:
        picked = st.selectbox(
            "Selecciona un jugador",
            options=select_options,
            key="player_lookup_selectbox",
        )
    with clr_col:
        st.write("")
        if st.button(labeled("clear", "Limpiar"), key="player_lookup_clear", type="secondary"):
            st.session_state.pop("selected_player_id", None)
            st.session_state.pop("player_lookup_selectbox", None)
            st.rerun()

    if picked == PLAYER_LOOKUP_NONE_LABEL:
        st.session_state.pop("selected_player_id", None)
        empty_state(
            "Selecciona un jugador para consultar su ficha.",
            "Usa el buscador superior para explorar informes, atributos y métricas.",
            icon="search",
        )
        return

    player_id = label_to_id[picked]
    st.session_state["selected_player_id"] = player_id

    with get_connection() as conn:
        player = players_service.fetch_player(conn, player_id)
        reports = players_service.fetch_reports_for_player(conn, player_id)
        obj_status = players_service.get_player_objective_data_status(conn, player_id)
        metrics_grouped = (
            metrics_service.get_metrics_by_player_grouped(conn, player_id)
            if obj_status["has_objective_metrics"]
            else []
        )

    if not player:
        st.error("No se pudo cargar la ficha del jugador.")
        return

    selected_rep: dict[str, Any] | None = None
    selected_attrs: list[dict[str, Any]] = []

    if reports:
        selected_rep = _pick_player_report(reports, player_id)
        with get_connection() as conn:
            selected_attrs = attribute_ratings_service.get_report_attribute_ratings(
                conn, int(selected_rep["id"])
            )

    player_header(
        name=str(player.get("full_name") or "—"),
        position=str(player.get("position") or "") or None,
        club=str(player.get("current_team") or "") or None,
        nationality=str(player.get("nationality") or "") or None,
        recommendation=(selected_rep or {}).get("recommendation"),
        rating=(selected_rep or {}).get("rating"),
    )

    with st.container(border=False):
        _render_player_executive_ficha(player, selected_rep)

    if selected_rep:
        _render_player_subjective_report_content(selected_rep, selected_attrs, player)
        _render_player_subjective_comparison_block(
            player=player,
            player_id=player_id,
            report_attrs=selected_attrs,
        )
    elif not reports:
        empty_state(
            "No hay informes de scouting para este jugador.",
            "Puedes registrar una evaluación desde Nuevo informe.",
            icon="document",
        )

    st.markdown('<hr class="section-hr section-hr--tight"/>', unsafe_allow_html=True)
    st.markdown("### Análisis objetivo")

    if obj_status["objective_metrics_count"] <= 0:
        st.info("No hay datos objetivos vinculados a este jugador.")
    elif metrics_grouped:
        group_labels = [
            f"{metric_labels.format_season_label(g.get('season'))} · {g.get('competition') or '—'}"
            for g in metrics_grouped
        ]
        if len(group_labels) > 1:
            sel_group = st.selectbox(
                "Temporada / competición",
                group_labels,
                key="player_lookup_metrics_group",
            )
            group_idx = group_labels.index(sel_group)
        else:
            group_idx = 0

        group = metrics_grouped[group_idx]
        metrics_rows = group.get("metrics") or []
        pos_group, _, _ = _resolve_objective_position_context(metrics_rows)

        _render_player_objective_scouting_block(
            player_id=player_id,
            season=group.get("season"),
            competition=group.get("competition"),
            metrics_rows=metrics_rows,
            pos_group=pos_group,
        )


def _render_matching() -> None:
    if not is_debug_mode():
        st.info("Esta sección solo está disponible con el modo depuración activado.")
        return
    st.caption(
        "Vincula jugadores **con informes subjetivos** a perfiles Sofascore. "
        "Los datos objetivos no crean informes; solo enriquecen la ficha tras el matching."
    )

    with get_connection() as conn:
        pending = matching_service.get_scouted_players_without_sofascore_match(conn)

    if not pending:
        st.success("No hay jugadores pendientes: todos los scouteados tienen vínculo Sofascore o no hay informes.")
        return

    st.subheader("Jugadores pendientes de matching")
    pending_table = [
        {
            "player_id": p["player_id"],
            "nombre": p.get("full_name"),
            "equipo": p.get("current_team") or "—",
            "posición": p.get("position") or "—",
            "nacionalidad": p.get("nationality") or "—",
            "fecha_nacimiento": p.get("birth_date") or "—",
            "nº informes": p.get("reports_count"),
        }
        for p in pending
    ]
    st.dataframe(pending_table, use_container_width=True, hide_index=True)

    labels = [f"{p['full_name']} · id {p['player_id']}" for p in pending]
    label_to_id = {lab: int(p["player_id"]) for lab, p in zip(labels, pending, strict=True)}

    selected_label = st.selectbox(
        "Selecciona jugador pendiente",
        labels,
        key="matching_pending_player",
    )
    scouted_id = label_to_id[selected_label]
    scouted_row = next(p for p in pending if int(p["player_id"]) == scouted_id)

    st.markdown('<hr class="section-hr"/>', unsafe_allow_html=True)
    st.subheader("Ficha del jugador scouteado")
    c1, c2, c3 = st.columns(3)
    c1.metric("Nombre", scouted_row.get("full_name") or "—")
    c2.metric("Equipo", scouted_row.get("current_team") or "—")
    c3.metric("Posición", scouted_row.get("position") or "—")
    st.caption(
        f"`player_id` **{scouted_id}** · nacionalidad: {scouted_row.get('nationality') or '—'} · "
        f"nacimiento: {scouted_row.get('birth_date') or '—'} · informes: **{scouted_row.get('reports_count')}**"
    )

    f1, f2, f3 = st.columns(3)
    filter_team = f1.checkbox("Filtrar por equipo", value=True, key="matching_filter_team")
    filter_nat = f2.checkbox("Filtrar por nacionalidad", value=False, key="matching_filter_nat")
    filter_pos = f3.checkbox("Filtrar por posición (G/D/M/F)", value=False, key="matching_filter_pos")

    if st.button("Buscar candidatos Sofascore", key="matching_search_btn", type="primary"):
        st.session_state["matching_search_for"] = scouted_id

    if st.session_state.get("matching_search_for") != scouted_id:
        st.info("Pulsa **Buscar candidatos Sofascore** para listar coincidencias por nombre.")
        return

    with get_connection() as conn:
        from scouting.repositories import matching_repository

        if matching_repository.scouted_player_has_sofascore_external(conn, scouted_id):
            st.error(
                "Este jugador ya tiene `player_external_ids` Sofascore. "
                "No se puede vincular otro candidato sin revisión manual avanzada."
            )
            return

        candidates = matching_service.find_sofascore_candidates_for_player(
            conn,
            scouted_id,
            filter_by_team=filter_team,
            filter_by_nationality=filter_nat,
            filter_by_position=filter_pos,
        )

    st.subheader("Candidatos Sofascore")
    if not candidates:
        st.warning(
            "No se encontraron candidatos con el criterio de nombre actual. "
            "Prueba desactivando filtros o revisa el nombre normalizado en ambas fichas."
        )
        return

    cand_table = [
        {
            "candidate_player_id": c["candidate_player_id"],
            "nombre": c.get("full_name"),
            "equipo": c.get("current_team") or "—",
            "posición": c.get("position") or "—",
            "nacionalidad": c.get("nationality") or "—",
            "fecha_nacimiento": c.get("birth_date") or "—",
            "sofascore_external_id": c.get("sofascore_external_id") or "—",
            "competiciones": c.get("competitions"),
            "minutesPlayed": c.get("minutes_played"),
            "avg_rating": c.get("avg_rating"),
            "match": c.get("match_reason"),
        }
        for c in candidates
    ]
    st.dataframe(cand_table, use_container_width=True, hide_index=True)

    cand_labels = [
        f"{c['full_name']} · id {c['candidate_player_id']} · ext {c.get('sofascore_external_id') or '—'}"
        for c in candidates
    ]
    cand_map = {lab: int(c["candidate_player_id"]) for lab, c in zip(cand_labels, candidates, strict=True)}
    picked_cand = st.selectbox("Selecciona candidato a vincular", cand_labels, key="matching_candidate_pick")
    candidate_id = cand_map[picked_cand]

    with get_connection() as conn:
        merge_preview = matching_service.get_merge_preview(conn, scouted_id, candidate_id)

    if merge_preview["scouted_has_external"]:
        st.error("El jugador scouteado ya tiene external_id Sofascore.")
        return

    st.markdown("#### Confirmación antes de vincular")
    st.markdown(
        f"- **Jugador scouteado:** {merge_preview['scouted'].get('full_name')} (`id` {scouted_id})\n"
        f"- **Candidato Sofascore:** {merge_preview['candidate'].get('full_name')} (`id` {candidate_id})\n"
        f"- **Métricas a mover:** {merge_preview['metrics_to_move']}\n"
        f"- **External IDs a mover:** {len(merge_preview['external_ids'])}"
    )
    for ext in merge_preview["external_ids"]:
        st.caption(f"  · Sofascore `#{ext.get('external_id')}` ({ext.get('external_name') or '—'})")

    confirm = st.checkbox(
        "Confirmo mover métricas y external_id Sofascore al jugador scouteado",
        key="matching_confirm_checkbox",
    )

    if st.button("Vincular", type="primary", disabled=not confirm, key="matching_merge_btn"):
        with get_connection() as conn:
            try:
                result = matching_service.merge_sofascore_candidate_into_scouted_player(
                    conn, scouted_id, candidate_id
                )
            except ValueError as exc:
                st.error(str(exc))
                return
            except Exception as exc:  # noqa: BLE001
                st.error(f"Error al vincular: {exc}")
                return

        st.success(
            f"Vinculación completada: {result['metrics_moved']} métricas y "
            f"{result['external_ids_moved']} external_id(s) asignados a `player_id` {scouted_id}."
        )
        st.warning(
            f"El jugador candidato (`id` {candidate_id}) permanece en `players`, "
            "pero sin métricas Sofascore asociadas. Puedes revisarlo en **Consultar jugador** "
            "(modo «solo datos objetivos») o ignorarlo."
        )
        st.session_state.pop("matching_search_for", None)
        st.session_state.pop("matching_confirm_checkbox", None)
        st.rerun()



def _render_administration() -> None:
    from ui.data_sync_card import render_admin_sync_section

    render_admin_sync_section(key_prefix="admin")


def main() -> None:
    st.set_page_config(
        page_title="Scouting Platform",
        page_icon=_ohiggins_page_icon(),
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_ohiggins_theme()
    st.markdown(build_full_width_layout_css(), unsafe_allow_html=True)

    auth_setup_error = get_auth_setup_error()
    if auth_setup_error:
        st.error(auth_setup_error)
        st.stop()

    if not is_authenticated(st.session_state):
        render_login_page()
        st.stop()

    pages = _nav_pages()
    page = render_top_header(
        pages=pages,
        username=_current_auth_username(),
        sport_logo_path=_sport_logo_path(),
        crest_path=_crest_path(),
        on_logout=_logout_current_session,
    )
    _render_db_banner(page=page)
    if _handle_page_navigation(page):
        st.rerun()

    render_page_heading(page)

    if page == "Dashboard":
        _render_dashboard()
    elif page == "Nuevo informe":
        _render_new_report()
    elif page == "Consultar jugador":
        _render_player_lookup()
    elif page == "Comparación":
        _render_comparison_tab()
    elif page == "Informes ocultos":
        _render_hidden_reports_page()
    elif page == "Matching":
        _render_matching()
    elif page == "Datos objetivos":
        _render_objective_explorer()
    elif page == "Administración":
        _render_administration()


main()
