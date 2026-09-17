"""Vista unificada «Datos deportivos» del dashboard (descarga / actualización Sofascore).

Solo presentación: reutiliza assess_platform_sync / runner existentes.
No decide qué descargar; traduce estados internos a textos comprensibles.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import streamlit as st

from scouting.services import sofascore_incremental_runner
from ui.components import status_badge, _esc, _icon_html
from ui.icons import labeled

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT_NAME = "checkpoint_raw.json"
SOFASCORE_OUTPUT = PROJECT_ROOT / "web_scraping_sofascore" / "sofascore_output"

METHOD_AUTO = "Automático"
METHOD_DOWNLOAD = "Descargar de Sofascore"
METHOD_REUSE = "Reutilizar archivos ya descargados"


@dataclass(frozen=True)
class SyncProgressView:
    current_step: int
    total_steps: int
    current_title: str
    next_hint: str | None
    phase_labels: tuple[str, ...]


@dataclass
class SyncCardViewModel:
    """Modelo de presentación compacto (testeable sin Streamlit)."""

    badge_label: str
    badge_tone: str
    message: str = ""
    summary_line: str = ""
    progress_detail: str = ""
    help_text: str = ""
    primary_label: str = "Buscar nuevos partidos"
    primary_type: str = "primary"
    show_primary: bool = True
    show_refresh: bool = False
    refresh_label: str = "Actualizar progreso"
    show_advanced: bool = False
    show_last_update: bool = False
    show_error_details: bool = False
    in_progress: bool = False
    is_error: bool = False
    progress: SyncProgressView | None = None
    platform_state: str = ""
    last_check: str = "—"
    technical_lines: list[str] = field(default_factory=list)
    history_notes: list[str] = field(default_factory=list)
    # Compat / tests legacy
    info_rows: list[tuple[str, str]] = field(default_factory=list)


def friendly_platform_state(state: str) -> str:
    return {
        "demo_only": "Datos de demostración",
        "initial_sync_required": "Datos de demostración",
        "historical_sync_required": "Histórico incompleto",
        "current_sync_required": "Temporada pendiente",
        "fully_initialized": "Datos actualizados",
        "running": "Descargando",
        "failed": "Error",
        "error": "Error",
    }.get(str(state or "").strip(), "Datos deportivos")


def show_sync_technical_details_env() -> bool:
    return os.environ.get("SHOW_SYNC_TECHNICAL_DETAILS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def checkpoint_info_for_slug(slug: str) -> dict[str, Any]:
    path = SOFASCORE_OUTPUT / str(slug).strip() / CHECKPOINT_NAME
    if not path.is_file():
        return {"exists": False, "path": str(path), "mtime_label": None, "size_kb": None}
    try:
        stat = path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime)
        return {
            "exists": True,
            "path": str(path),
            "mtime_label": mtime.strftime("%d/%m/%Y %H:%M"),
            "size_kb": round(stat.st_size / 1024),
        }
    except OSError:
        return {"exists": False, "path": str(path), "mtime_label": None, "size_kb": None}


def resolve_import_method(method: str, *, checkpoint_exists: bool) -> bool:
    """Devuelve process_existing para el runner histórico."""
    if method == METHOD_REUSE:
        return True
    if method == METHOD_DOWNLOAD:
        return False
    return bool(checkpoint_exists)


def _format_int(n: int | None) -> str:
    try:
        return f"{int(n):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def _parse_step_from_headline(headline: str | None) -> tuple[int | None, int | None]:
    raw = str(headline or "")
    match = re.search(r"Paso\s+(\d+)\s*/\s*(\d+)", raw)
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def derive_sync_progress(
    plan: dict[str, Any],
    ui_state: sofascore_incremental_runner.FriendlyUpdateResult,
) -> SyncProgressView:
    active = str(plan.get("active_season") or "")
    historical = str(plan.get("historical_season") or "")
    state = str(plan.get("state") or "")
    step_labels = [str(x) for x in (plan.get("step_labels") or []) if str(x).strip()]

    if state == "initial_sync_required":
        phases = (
            f"Temporada histórica {historical}",
            f"Temporada activa {active}",
            "Finalizando importación",
        )
        default_titles = (
            f"Primera División de Chile · Temporada {historical}",
            f"Ligas activas · Temporada {active}",
            "Finalizando importación",
        )
    elif state == "historical_sync_required":
        phases = (
            f"Temporada histórica {historical}",
            f"Actualización de {active}",
            "Finalizando importación",
        )
        default_titles = phases
    elif state == "current_sync_required":
        phases = (f"Temporada activa {active}", "Finalizando importación")
        default_titles = phases
    else:
        phases = tuple(step_labels) or (f"Temporada activa {active}",)
        default_titles = phases

    total = max(len(step_labels), len(phases), 1)
    current, parsed_total = _parse_step_from_headline(ui_state.headline)
    if parsed_total:
        total = parsed_total
    if current is None:
        current = 1
        for line in ui_state.summary_lines or []:
            if line.startswith("Paso actual:"):
                label = line.split(":", 1)[1].strip()
                if label in step_labels:
                    current = step_labels.index(label) + 1
                break

    current = max(1, min(int(current), total))
    if step_labels and current <= len(step_labels):
        title = step_labels[current - 1]
    elif current <= len(default_titles):
        title = default_titles[current - 1]
    else:
        title = ui_state.message or "Descarga en curso"

    next_hint = None
    if current < total:
        if current < len(default_titles):
            next_hint = f"A continuación: {default_titles[current]}."
        elif current < len(step_labels):
            next_hint = f"A continuación: {step_labels[current]}."

    return SyncProgressView(
        current_step=current,
        total_steps=total,
        current_title=title,
        next_hint=next_hint,
        phase_labels=phases,
    )


def _progress_detail_line(
    ui_state: sofascore_incremental_runner.FriendlyUpdateResult,
    progress: SyncProgressView | None,
) -> str:
    for line in ui_state.summary_lines or []:
        low = line.lower()
        if "liga" in low or "partido" in low or "/" in line:
            if line.startswith("Paso actual:"):
                continue
            return line.strip()
    if progress:
        return f"Paso {progress.current_step} de {progress.total_steps}"
    return ""


def _technical_lines_for(
    plan: dict[str, Any],
    ui_state: sofascore_incremental_runner.FriendlyUpdateResult,
    *,
    state: str,
) -> list[str]:
    history_notes = list(getattr(ui_state, "history_notes", None) or [])
    technical = [
        f"Estado interno: {state or '—'}",
        f"Modo UI: {ui_state.mode or '—'}",
        f"Status runner: {ui_state.status or '—'}",
        f"Log: {_log_path(ui_state)}",
    ]
    for note in history_notes:
        technical.append(note)
    superseded = (getattr(ui_state, "assessment", None) or {}).get("superseded_error")
    if isinstance(superseded, dict):
        technical.append(
            f"Historial de error: {superseded.get('message') or superseded.get('headline') or '—'}"
        )
        if superseded.get("note"):
            technical.append(str(superseded["note"]))
        for path in superseded.get("log_paths") or []:
            technical.append(f"Log histórico: {path}")
    for line in ui_state.summary_lines or []:
        if any(
            token in line.lower()
            for token in ("slug", "tournament", "season_id", "cl_primera", "backfill", "falló")
        ):
            technical.append(line)
    return technical


def build_sync_card_view(
    plan: dict[str, Any],
    ui_state: sofascore_incremental_runner.FriendlyUpdateResult,
    *,
    in_progress: bool,
) -> SyncCardViewModel:
    state = str(plan.get("state") or ui_state.platform_state or "")
    active = str(plan.get("active_season") or sofascore_incremental_runner.get_active_season())
    historical = str(plan.get("historical_season") or "")
    demo_n = int(plan.get("demo_metrics") or 0)
    sofa_n = int(plan.get("sofascore_metrics") or 0)
    hist_sofa_n = int(plan.get("historical_sofascore_metrics") or 0)
    last_check = ui_state.last_check_at or ui_state.last_update_at or "—"
    history_notes = list(getattr(ui_state, "history_notes", None) or [])
    is_error = (
        ui_state.status in ("error", "failed")
        and not in_progress
        and not bool(getattr(ui_state, "reconciled", False))
    )
    technical = _technical_lines_for(plan, ui_state, state=state)

    if in_progress:
        progress = derive_sync_progress(plan, ui_state)
        if state in ("initial_sync_required", "demo_only"):
            msg = f"Descargando datos reales ({historical} y {active})"
        elif state == "historical_sync_required":
            msg = f"Descargando temporada histórica {historical}"
        elif state == "current_sync_required":
            msg = f"Descargando temporada {active}"
        else:
            msg = ui_state.message or f"Descargando temporada {active}"
        return SyncCardViewModel(
            badge_label="Descargando",
            badge_tone="info",
            message=msg,
            progress_detail=_progress_detail_line(ui_state, progress),
            primary_label="",
            show_primary=False,
            show_refresh=True,
            refresh_label="Actualizar progreso",
            show_advanced=False,
            show_last_update=False,
            in_progress=True,
            is_error=False,
            progress=progress,
            platform_state=state,
            last_check=str(last_check),
            technical_lines=technical,
            history_notes=history_notes,
        )

    if is_error:
        progress = derive_sync_progress(plan, ui_state)
        failed_phase = progress.current_title
        for line in ui_state.summary_lines or []:
            if line.startswith("Falló:"):
                failed_phase = line.split(":", 1)[1].strip()
                break
        season_hint = active
        if "2024" in (ui_state.message or "") or historical in (ui_state.message or ""):
            season_hint = historical or active
        return SyncCardViewModel(
            badge_label="Error",
            badge_tone="danger",
            message=f"No se pudo completar la descarga de {season_hint}.",
            help_text=f"Fase: {failed_phase}",
            primary_label="Reintentar",
            primary_type="primary",
            show_primary=True,
            show_refresh=False,
            show_advanced=False,
            show_last_update=False,
            show_error_details=True,
            in_progress=False,
            is_error=True,
            platform_state=state,
            last_check=str(last_check),
            technical_lines=technical + [ui_state.technical_details or ""],
            history_notes=history_notes,
        )

    if state in ("initial_sync_required", "demo_only") or (
        sofa_n <= 0
        and demo_n > 0
        and state
        not in (
            "current_sync_required",
            "historical_sync_required",
            "fully_initialized",
        )
    ):
        return SyncCardViewModel(
            badge_label="Datos de demostración",
            badge_tone="warning",
            message="Estás usando datos de demostración.",
            primary_label="Descargar datos reales",
            primary_type="primary",
            show_primary=True,
            show_refresh=False,
            show_advanced=False,
            show_last_update=False,
            platform_state=state or "initial_sync_required",
            last_check=str(last_check),
            technical_lines=technical,
            history_notes=history_notes,
        )

    if state == "historical_sync_required":
        return SyncCardViewModel(
            badge_label="Histórico incompleto",
            badge_tone="warning",
            summary_line=f"Temporada {active} disponible",
            message=(
                f"Falta descargar los datos históricos de {historical}. "
                f"{_format_int(sofa_n)} estadísticas de jugadores."
            ),
            primary_label=f"Completar temporada {historical}",
            primary_type="primary",
            show_primary=True,
            show_refresh=False,
            show_advanced=False,
            show_last_update=True,
            platform_state=state,
            last_check=str(last_check),
            technical_lines=technical,
            history_notes=history_notes,
        )

    if state == "current_sync_required":
        metrics_label = _format_int(hist_sofa_n or sofa_n)
        return SyncCardViewModel(
            badge_label="Temporada pendiente",
            badge_tone="warning",
            summary_line=(
                f"Temporada {historical} disponible · {metrics_label} estadísticas de jugadores"
            ),
            message=f"Falta descargar los datos de la temporada {active}.",
            primary_label=f"Descargar temporada {active}",
            primary_type="primary",
            show_primary=True,
            show_refresh=False,
            show_advanced=False,
            show_last_update=True,
            platform_state=state,
            last_check=str(last_check),
            technical_lines=technical,
            history_notes=history_notes,
        )

    # fully_initialized
    no_news = ui_state.status in ("no_news", "completed_no_changes")
    return SyncCardViewModel(
        badge_label="Datos actualizados",
        badge_tone="success",
        summary_line=f"Temporadas {historical} y {active} disponibles",
        message=(
            "No hay nuevos partidos finalizados."
            if no_news
            else f"{_format_int(sofa_n)} estadísticas de jugadores"
        ),
        primary_label="Buscar nuevos partidos",
        primary_type="primary",
        show_primary=True,
        show_refresh=False,
        show_advanced=False,
        show_last_update=True,
        platform_state=state or "fully_initialized",
        last_check=str(last_check),
        technical_lines=technical,
        history_notes=history_notes,
    )


def _log_path(ui_state: sofascore_incremental_runner.FriendlyUpdateResult) -> str:
    if ui_state.log_paths:
        return ui_state.log_paths[-1]
    last = sofascore_incremental_runner.latest_log_path()
    return str(last) if last else "—"


def sports_data_panel_html(view: SyncCardViewModel) -> str:
    """HTML legacy (tests / escape). Preferir render_sports_data_panel nativo."""
    badge = status_badge(view.badge_label, tone=view.badge_tone)
    summary_html = (
        f'<div class="scouting-sports-summary">{_esc(view.summary_line)}</div>'
        if view.summary_line
        else ""
    )
    message_html = (
        f'<div class="scouting-sports-message">{_esc(view.message)}</div>'
        if view.message
        else ""
    )
    progress_html = (
        f'<div class="scouting-sports-help">{_esc(view.progress_detail)}</div>'
        if view.progress_detail
        else ""
    )
    date_html = (
        f'<div class="scouting-sofascore-date">Última actualización: {_esc(view.last_check)}</div>'
        if view.show_last_update
        else ""
    )
    return f"""
    <div class="scouting-sofascore-panel scouting-sports-panel">
      <div class="scouting-sofascore-accent"></div>
      <div class="scouting-sofascore-main">
        <div class="scouting-sports-header">
          <div class="scouting-sofascore-title">
            {_icon_html("chart", size=15)}
            Datos deportivos
          </div>
          {badge}
        </div>
        {summary_html}
        {message_html}
        {progress_html}
        {date_html}
      </div>
    </div>
    """


def render_sports_data_panel(view: SyncCardViewModel) -> None:
    """Tarjeta compacta con componentes nativos de Streamlit."""
    from ui.presentation import format_datetime_for_ui

    title_col, badge_col = st.columns([3, 2])
    with title_col:
        st.markdown("##### Datos deportivos")
    with badge_col:
        st.markdown(
            status_badge(view.badge_label, tone=view.badge_tone),
            unsafe_allow_html=True,
        )

    if view.summary_line:
        st.caption(view.summary_line)

    if view.message:
        st.write(view.message)

    if view.progress_detail:
        st.caption(view.progress_detail)

    if view.show_last_update and view.last_check:
        st.caption(f"Última actualización: {format_datetime_for_ui(view.last_check)}")


def _render_error_details(view: SyncCardViewModel, *, key_prefix: str) -> None:
    with st.expander("Ver información del error", expanded=False):
        if view.help_text:
            st.caption(view.help_text)
        st.caption(f"Log: {_log_path_from_lines(view)}")
        lines = [ln for ln in view.technical_lines if str(ln).strip()]
        if lines:
            for ln in lines[:40]:
                st.text(str(ln)[:500])
        if st.checkbox("Mostrar log completo", value=False, key=f"{key_prefix}_sports_full_log"):
            _render_full_log_area(key_prefix=key_prefix)


def _log_path_from_lines(view: SyncCardViewModel) -> str:
    for line in view.technical_lines:
        if str(line).startswith("Log:"):
            return str(line).split(":", 1)[1].strip()
    return "—"


def _render_full_log_area(*, key_prefix: str) -> None:
    runner_diag = sofascore_incremental_runner.load_runner_diagnostics()
    text_parts: list[str] = []
    if runner_diag and runner_diag.summary_text:
        text_parts.append(runner_diag.summary_text)
    ui_state = sofascore_incremental_runner.load_ui_state()
    if ui_state.technical_details:
        text_parts.append(ui_state.technical_details)
    for path_str in ui_state.log_paths or []:
        path = Path(path_str)
        if path.is_file():
            try:
                text_parts.append(path.read_text(encoding="utf-8")[:20000])
            except OSError as exc:
                text_parts.append(f"(no legible: {exc})")
    st.text_area(
        "Log",
        value="\n\n".join(text_parts) if text_parts else "(sin log)",
        height=280,
        disabled=True,
        label_visibility="collapsed",
        key=f"{key_prefix}_sports_log_area",
    )


def _render_technical_details_admin(view: SyncCardViewModel, *, key_prefix: str) -> None:
    with st.expander("Detalles técnicos de sincronización", expanded=False):
        lines = [ln for ln in view.technical_lines if str(ln).strip()]
        if not lines:
            st.caption("Sin detalles técnicos.")
            return
        st.markdown("\n".join(f"- {ln}" for ln in lines))
        if st.checkbox("Mostrar log completo", value=False, key=f"{key_prefix}_admin_full_log"):
            _render_full_log_area(key_prefix=f"{key_prefix}_admin")


def render_advanced_sync_options(*, key_prefix: str, disabled: bool = False) -> None:
    """Opciones de mantenimiento (solo Administración / entorno técnico)."""
    active_season = sofascore_incremental_runner.get_active_season()
    docker_ok = sofascore_incremental_runner.check_docker_runtime().ok
    actions_disabled = disabled or not docker_ok

    with st.expander("Opciones avanzadas de sincronización", expanded=False):
        st.markdown("#### Resincronizar temporada activa")
        st.caption(
            f"Vuelve a descargar e importar todos los partidos finalizados de la temporada "
            f"{active_season}. Úsalo únicamente para reparar datos incompletos."
        )
        confirm_resync = st.checkbox(
            f"Confirmo resincronizar la temporada {active_season}",
            key=f"{key_prefix}_adv_resync_confirm",
            disabled=actions_disabled,
        )
        if st.button(
            labeled("refresh", f"Resincronizar temporada {active_season}"),
            type="secondary",
            disabled=actions_disabled or not confirm_resync,
            key=f"{key_prefix}_adv_resync",
            use_container_width=True,
        ):
            with st.spinner("Resincronizando temporada activa…"):
                sofascore_incremental_runner.run_resync_season_for_ui()
            st.rerun()

        st.divider()
        st.markdown("#### Importar otra temporada histórica")
        hist_opts = sofascore_incremental_runner.HISTORICAL_IMPORT_OPTIONS
        hist_labels = [o["label"] for o in hist_opts]
        hist_by_label = {o["label"]: o for o in hist_opts}
        selected_hist = st.selectbox(
            "Temporada histórica",
            hist_labels,
            key=f"{key_prefix}_adv_hist_select",
            disabled=actions_disabled,
        )
        opt = hist_by_label[selected_hist]
        cp = checkpoint_info_for_slug(opt["slug"])

        method_options = [METHOD_AUTO, METHOD_DOWNLOAD]
        if cp["exists"]:
            method_options.append(METHOD_REUSE)
        method = st.selectbox(
            "Método de importación",
            method_options,
            key=f"{key_prefix}_adv_hist_method",
            disabled=actions_disabled,
            help=(
                "Automático usa archivos locales si existen; "
                "Descargar fuerza una nueva descarga; "
                "Reutilizar solo procesa el checkpoint local."
            ),
        )
        if cp["exists"]:
            st.caption(
                f"Archivos locales disponibles · {cp['mtime_label']} · {cp['size_kb']} KB"
            )
        else:
            st.caption("No hay archivos locales previos para esta temporada.")

        confirm_hist = st.checkbox(
            "Confirmo importar la temporada histórica (no modifica la temporada activa)",
            key=f"{key_prefix}_adv_hist_confirm",
            disabled=actions_disabled,
        )
        if st.button(
            labeled("document", "Importar temporada histórica"),
            type="secondary",
            disabled=actions_disabled or not confirm_hist,
            key=f"{key_prefix}_adv_hist_import",
            use_container_width=True,
        ):
            process_existing = resolve_import_method(
                method, checkpoint_exists=bool(cp["exists"])
            )
            with st.spinner(f"Importando {opt['label']}…"):
                sofascore_incremental_runner.run_historical_import_for_ui(
                    league_slug=opt["slug"],
                    season=opt["season"],
                    process_existing=process_existing,
                )
            st.rerun()


def render_admin_sync_section(*, key_prefix: str = "admin") -> None:
    """Sección Administración: mantenimiento e información técnica."""
    st.markdown("### Actualización de datos")
    st.caption(
        "Acciones de mantenimiento. El estado habitual se gestiona desde el Dashboard."
    )
    docker_ok = sofascore_incremental_runner.check_docker_runtime().ok
    update_blocked = (
        not docker_ok
        or os.environ.get("DISABLE_SOFASCORE_UPDATE", "").strip() == "1"
    )
    render_advanced_sync_options(key_prefix=key_prefix, disabled=update_blocked)

    plan, ui_state = sofascore_incremental_runner.refresh_sync_card_state()
    in_progress = sofascore_incremental_runner.is_update_in_progress()
    view = build_sync_card_view(plan, ui_state, in_progress=in_progress)

    with st.expander("Información técnica", expanded=False):
        st.caption(
            "Detalle interno para administración: estados, logs e identificadores."
        )
        st.text(f"Estado plataforma: {plan.get('state') or '—'}")
        st.text(f"Estado ejecución: {ui_state.status or '—'}")
        st.text(f"Temporada activa: {plan.get('active_season') or '—'}")
        st.text(f"Temporada histórica: {plan.get('historical_season') or '—'}")
        st.text(
            f"Métricas activas: {plan.get('active_sofascore_metrics') or 0} · "
            f"históricas: {plan.get('historical_sofascore_metrics') or 0} · "
            f"total: {plan.get('sofascore_metrics') or 0}"
        )
        log_path = "—"
        if ui_state.log_paths:
            log_path = ui_state.log_paths[-1]
        st.text(f"Log: {log_path}")
        if view.technical_lines:
            st.markdown("##### Detalle")
            for ln in view.technical_lines[:60]:
                if str(ln).strip():
                    st.text(str(ln)[:800])
        if st.checkbox("Mostrar log completo", value=False, key=f"{key_prefix}_tech_full_log"):
            _render_full_log_area(key_prefix=f"{key_prefix}_tech")


def render_data_sync_card(*, key_prefix: str = "dashboard") -> None:
    """Tarjeta principal compacta de datos deportivos (Dashboard)."""
    plan, ui_state = sofascore_incremental_runner.refresh_sync_card_state()
    in_progress = sofascore_incremental_runner.is_update_in_progress()
    docker_ok = sofascore_incremental_runner.check_docker_runtime().ok
    update_blocked = (
        not docker_ok
        or os.environ.get("DISABLE_SOFASCORE_UPDATE", "").strip() == "1"
    )

    view = build_sync_card_view(plan, ui_state, in_progress=in_progress)
    render_sports_data_panel(view)

    if view.in_progress:
        if view.show_refresh:
            if st.button(
                labeled("refresh", view.refresh_label),
                key=f"{key_prefix}_sports_refresh",
                use_container_width=False,
            ):
                sofascore_incremental_runner.refresh_sync_card_state()
                st.rerun()
        try:

            @st.fragment(run_every=timedelta(seconds=10))
            def _poll_sync_completion() -> None:
                if not sofascore_incremental_runner.is_update_in_progress():
                    st.rerun()

            _poll_sync_completion()
        except Exception:  # noqa: BLE001
            pass
        return

    if view.show_primary:
        btn_type = view.primary_type if view.primary_type in ("primary", "secondary") else "primary"
        if st.button(
            view.primary_label,
            type=btn_type,
            disabled=update_blocked or view.in_progress,
            key=f"{key_prefix}_sports_primary",
            use_container_width=True,
        ):
            sofascore_incremental_runner.start_dashboard_sync_background()
            st.rerun()

    if view.show_error_details:
        _render_error_details(view, key_prefix=key_prefix)
    elif show_sync_technical_details_env():
        _render_technical_details_admin(view, key_prefix=key_prefix)
