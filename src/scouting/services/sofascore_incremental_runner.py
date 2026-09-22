"""Ejecutar actualización incremental Sofascore vía docker compose (worker)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field, fields as dataclass_fields, replace
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"
COMPOSE_PROJECT_NAME = os.environ.get("COMPOSE_PROJECT_NAME", "scouting-platform")
LOCK_PATH = PROJECT_ROOT / "data" / "runtime" / "sofascore_update.lock"
UI_STATE_PATH = PROJECT_ROOT / "data" / "runtime" / "sofascore_update_ui_state.json"
LOG_DIR = PROJECT_ROOT / "data" / "logs" / "sofascore_incremental"
WORKER_SERVICE = "sofascore-worker"
DOCKER_SOCKET = Path("/var/run/docker.sock")
JSON_MARKER = "SOFASCORE_INCREMENTAL_JSON="

COMPOSE_FILE_CLIENT = "/app/docker-compose.yml"
DIAG_PATH = PROJECT_ROOT / "data" / "runtime" / "sofascore_runner_diagnostics.json"


@dataclass
class RunnerDiagnostics:
    host_project_root: str
    project_root: str
    compose_project_name: str
    compose_file: str
    cwd: str
    preflight_command: str = ""
    preflight_ok: bool | None = None
    preflight_output: str = ""
    last_command: str = ""
    resolve_source: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "host_project_root": self.host_project_root,
            "project_root": self.project_root,
            "compose_project_name": self.compose_project_name,
            "compose_file": self.compose_file,
            "cwd": self.cwd,
            "preflight_command": self.preflight_command,
            "preflight_ok": self.preflight_ok,
            "preflight_output": self.preflight_output,
            "last_command": self.last_command,
            "resolve_source": self.resolve_source,
            "error": self.error,
        }

    @property
    def summary_text(self) -> str:
        lines = [
            f"resolve_source: {self.resolve_source}",
            f"HOST_PROJECT_ROOT: {self.host_project_root}",
            f"PROJECT_ROOT: {self.project_root}",
            f"COMPOSE_PROJECT_NAME: {self.compose_project_name}",
            f"COMPOSE_FILE: {self.compose_file}",
            f"cwd: {self.cwd}",
            f"preflight_ok: {self.preflight_ok}",
            f"preflight_command: {self.preflight_command}",
        ]
        if self.preflight_output:
            lines.append(f"preflight_output:\n{self.preflight_output}")
        if self.last_command:
            lines.append(f"last_command: {self.last_command}")
        if self.error:
            lines.append(f"error: {self.error}")
        return "\n".join(lines)


class HostProjectRootError(ValueError):
    """No se pudo resolver la ruta del repo en el host."""


LEAGUE_LABELS: dict[str, str] = {
    "cl_primera_2025": "Primera División Chile",
    "cl_segunda_2025": "Liga de Ascenso Chile",
    "ar_primera_2025": "Liga Profesional Argentina",
    "ar_segunda_2025": "Primera Nacional Argentina",
    "uy_primera_2025": "Liga AUF Uruguay",
    "uy_segunda_2025": "Segunda División Uruguay",
    "cl_primera_2024": "Primera División Chile 2024",
}

# Temporadas históricas importables desde la UI (no se ejecutan con «Actualizar datos»).
HISTORICAL_IMPORT_OPTIONS: tuple[dict[str, str], ...] = (
    {
        "slug": "cl_primera_2024",
        "season": "2024",
        "label": "Primera División Chile 2024",
        "tournament_id": "11653",
        "season_id": "71131",
    },
)



@dataclass(frozen=True)
class DockerRuntimeInfo:
    ok: bool
    docker_path: str | None
    docker_version: str | None
    compose_invocation: tuple[str, ...] | None
    compose_version: str | None
    socket_present: bool
    socket_readable: bool
    messages: tuple[str, ...] = field(default_factory=tuple)
    error: str | None = None

    @property
    def diagnostics_text(self) -> str:
        return "\n".join(self.messages)


@dataclass
class WorkerRunOutput:
    ok: bool
    command: str
    stdout: str
    stderr: str
    returncode: int
    log_path: Path | None
    json_payload: dict[str, Any] | None = None
    error_message: str | None = None
    locked: bool = False

    @property
    def combined_output(self) -> str:
        parts = []
        if self.stdout.strip():
            parts.append(self.stdout.strip())
        if self.stderr.strip():
            parts.append(self.stderr.strip())
        return "\n\n".join(parts) if parts else ""


@dataclass
class FriendlyUpdateResult:
    ok: bool
    status: str  # idle | running | no_news | partial | success | error | backfill | failed | completed
    headline: str
    message: str
    last_check_at: str | None = None
    last_update_at: str | None = None
    leagues_reviewed: int = 0
    leagues_updated: int = 0
    new_matches: int = 0
    modified_matches: int = 0
    updated_league_labels: list[str] = field(default_factory=list)
    unchanged_league_labels: list[str] = field(default_factory=list)
    active_season: str | None = None
    historical_leagues_skipped: int = 0
    leagues_checked: list[str] = field(default_factory=list)
    locked: bool = False
    technical_details: str = ""
    log_paths: list[str] = field(default_factory=list)
    mode: str = "incremental"
    needs_initial_backfill: bool = False
    summary_lines: list[str] = field(default_factory=list)
    matches_downloaded: int = 0
    players_updated: int = 0
    metrics_imported: int = 0
    errors_count: int = 0
    remote_events_total: int = 0
    assessment: dict[str, Any] = field(default_factory=dict)
    platform_state: str = ""
    button_label: str = ""
    background_pid: int | None = None
    reconciled: bool = False
    history_notes: list[str] = field(default_factory=list)


def get_active_season() -> str:
    """Temporada Sofascore que el Dashboard actualiza (SOFASCORE_ACTIVE_SEASON)."""
    from scouting.config.sofascore_seasons import get_active_season as _cfg_active

    return _cfg_active()


def _ensure_dirs() -> None:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    UI_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _quote_arg(arg: str) -> str:
    if not arg or any(c in arg for c in " \t\"'"):
        return f'"{arg}"'
    return arg


def _mount_source_for(mountpoint: str) -> str | None:
    """Ruta en el host del bind mount (campo root en /proc/self/mountinfo)."""
    target = mountpoint.rstrip("/") or "/"
    try:
        for line in Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines():
            parts = line.split(" - ")
            if len(parts) != 2:
                continue
            left_fields = parts[0].split()
            if len(left_fields) < 5:
                continue
            mp = left_fields[4].replace("\\040", " ")
            if mp != target:
                continue
            root_path = left_fields[3].replace("\\040", " ")
            if root_path.startswith("/") and root_path not in ("/", target):
                return root_path
    except OSError:
        pass
    return None


def resolve_host_project_root() -> tuple[str, str]:
    """
    Ruta absoluta del repo en el host para volúmenes docker compose.

    Returns (path, source) where source is 'env' | 'mountinfo'.
    """
    explicit = os.environ.get("HOST_PROJECT_ROOT", "").strip()
    if explicit and explicit not in ("/app", ".") and not explicit.startswith("/app/"):
        return explicit, "env"
    host = _mount_source_for("/app")
    if host:
        return host, "mountinfo"
    raise HostProjectRootError(
        "No se pudo resolver HOST_PROJECT_ROOT. "
        "Define HOST_PROJECT_ROOT en .env con la ruta absoluta del repo en el host."
    )


def save_runner_diagnostics(diag: RunnerDiagnostics) -> None:
    _ensure_dirs()
    DIAG_PATH.write_text(json.dumps(diag.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def load_runner_diagnostics() -> RunnerDiagnostics | None:
    if not DIAG_PATH.is_file():
        return None
    try:
        data = json.loads(DIAG_PATH.read_text(encoding="utf-8"))
        return RunnerDiagnostics(**data)
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def build_compose_env() -> dict[str, str]:
    host_root, _source = resolve_host_project_root()
    env = os.environ.copy()
    env["HOST_PROJECT_ROOT"] = host_root
    env["PROJECT_ROOT"] = host_root
    env["COMPOSE_PROJECT_NAME"] = "scouting-platform"
    env["COMPOSE_FILE"] = COMPOSE_FILE_CLIENT
    return env


def _compose_file_for_client() -> str:
    return COMPOSE_FILE_CLIENT


def _compose_subprocess_env() -> dict[str, str]:
    return build_compose_env()


def build_preflight_command(*, compose_invocation: tuple[str, ...] | None = None) -> list[str]:
    compose = compose_invocation or _default_compose_invocation()
    return [
        *compose,
        "--project-name",
        "scouting-platform",
        "-f",
        COMPOSE_FILE_CLIENT,
        "--profile",
        "worker",
        "run",
        "--rm",
        "--no-deps",
        WORKER_SERVICE,
        "test",
        "-f",
        "/app/scripts/update_sofascore_incremental.py",
    ]


def run_worker_preflight(
    *,
    compose_invocation: tuple[str, ...] | None = None,
    env: dict[str, str] | None = None,
) -> tuple[bool, str, str]:
    """Ejecuta test -f en el worker con el mismo env que el run real."""
    cmd = build_preflight_command(compose_invocation=compose_invocation)
    cmd_str = command_to_string(cmd)
    run_env = env or build_compose_env()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
            env=run_env,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0, cmd_str, output.strip()
    except FileNotFoundError:
        return False, cmd_str, "docker no encontrado"
    except subprocess.TimeoutExpired:
        return False, cmd_str, "preflight timeout"


def _format_env_block(env: dict[str, str]) -> str:
    keys = ("HOST_PROJECT_ROOT", "PROJECT_ROOT", "COMPOSE_PROJECT_NAME", "COMPOSE_FILE")
    lines = [f"cwd: {PROJECT_ROOT}", "--- env ---"]
    for key in keys:
        lines.append(f"{key}={env.get(key, '')}")
    return "\n".join(lines)


def get_host_project_root_label() -> str:
    try:
        path, source = resolve_host_project_root()
        return f"{path} ({source})"
    except HostProjectRootError as exc:
        return f"no resuelto — {exc}"


def _format_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%d/%m/%Y %H:%M")


def _league_label(slug: str, competition: str | None = None) -> str:
    return competition or LEAGUE_LABELS.get(slug, slug)


def _run_capture(cmd: list[str], *, timeout: int = 15) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()
    except FileNotFoundError:
        return -1, "", f"no encontrado: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


@lru_cache(maxsize=1)
def check_docker_runtime() -> DockerRuntimeInfo:
    messages: list[str] = []
    docker_path = shutil.which("docker")
    if not docker_path:
        messages.append("which docker: (no encontrado)")
        return DockerRuntimeInfo(
            ok=False,
            docker_path=None,
            docker_version=None,
            compose_invocation=None,
            compose_version=None,
            socket_present=DOCKER_SOCKET.exists(),
            socket_readable=False,
            messages=tuple(messages),
            error="Docker no disponible en el contenedor app.",
        )

    messages.append(f"which docker: {docker_path}")
    rc, dv_out, dv_err = _run_capture([docker_path, "--version"])
    docker_version = dv_out or dv_err
    messages.append(f"docker --version: {docker_version}")

    socket_present = DOCKER_SOCKET.exists()
    socket_readable = os.access(DOCKER_SOCKET, os.R_OK | os.W_OK) if socket_present else False
    if socket_present:
        try:
            stat = DOCKER_SOCKET.stat()
            messages.append(
                f"ls -l docker.sock: s{oct(stat.st_mode)[-3:]} "
                f"uid={stat.st_uid} gid={stat.st_gid}"
            )
        except OSError as exc:
            messages.append(f"docker.sock: {exc}")
    else:
        messages.append("docker.sock: no montado")

    compose_invocation: tuple[str, ...] | None = None
    compose_version: str | None = None
    rc, out, err = _run_capture([docker_path, "compose", "version"])
    if rc == 0:
        compose_invocation = (docker_path, "compose")
        compose_version = out or err
        messages.append(f"docker compose version: {compose_version}")
    else:
        dc_path = shutil.which("docker-compose")
        if dc_path:
            rc2, out2, err2 = _run_capture([dc_path, "version"])
            if rc2 == 0:
                compose_invocation = (dc_path,)
                compose_version = out2 or err2
                messages.append(f"docker-compose version: {compose_version}")

    error: str | None = None
    if not compose_invocation:
        error = "Docker Compose no disponible."
    elif not socket_present:
        error = "Socket Docker no montado."
    elif not socket_readable:
        error = "Sin permisos en /var/run/docker.sock."

    ok = bool(docker_path and compose_invocation and socket_present and socket_readable and not error)
    return DockerRuntimeInfo(
        ok=ok,
        docker_path=docker_path,
        docker_version=docker_version,
        compose_invocation=compose_invocation,
        compose_version=compose_version,
        socket_present=socket_present,
        socket_readable=socket_readable,
        messages=tuple(messages),
        error=error,
    )


def _pid_is_alive(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        pid_i = int(pid)
    except (TypeError, ValueError):
        return False
    if pid_i <= 0:
        return False
    try:
        os.kill(pid_i, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # El proceso existe pero no es accesible desde este UID.
        return True
    except OSError:
        return False
    return True


def clear_orphan_sync_lock(*, ui_background_pid: int | None = None) -> dict[str, Any]:
    """
    Elimina el lock solo si no hay proceso vivo asociado.

    No borra el lock de un proceso en ejecución.
    """
    report: dict[str, Any] = {"cleared": False, "reason": "no_lock", "pids_checked": []}
    if not LOCK_PATH.is_file():
        return report

    info = read_lock_info() or {}
    candidates: list[int] = []
    for key in ("pid", "background_pid", "worker_pid"):
        raw = info.get(key)
        if raw is None:
            continue
        try:
            candidates.append(int(raw))
        except (TypeError, ValueError):
            continue
    if ui_background_pid is not None:
        try:
            candidates.append(int(ui_background_pid))
        except (TypeError, ValueError):
            pass

    report["pids_checked"] = candidates
    if any(_pid_is_alive(pid) for pid in candidates):
        report["reason"] = "process_alive"
        return report

    # Ventana de arranque: lock escrito antes de registrar el pid.
    if not candidates:
        started = info.get("started_at")
        if started:
            try:
                started_dt = datetime.fromisoformat(str(started))
                age = (datetime.now() - started_dt).total_seconds()
                if 0 <= age < 45:
                    report["reason"] = "startup_grace"
                    return report
            except ValueError:
                pass

    try:
        LOCK_PATH.unlink(missing_ok=True)
        report["cleared"] = True
        report["reason"] = "orphan"
    except OSError as exc:
        report["reason"] = f"unlink_failed:{exc}"
    return report


def is_update_in_progress() -> bool:
    """True si hay proceso vivo, o lock en ventana de arranque sin pid aún."""
    if not LOCK_PATH.is_file():
        return False
    info = read_lock_info() or {}
    for key in ("pid", "background_pid", "worker_pid"):
        if _pid_is_alive(info.get(key)):
            return True
    # Sin pid vivo: solo "en curso" durante la gracia de arranque.
    has_pid_field = any(info.get(k) is not None for k in ("pid", "background_pid", "worker_pid"))
    if has_pid_field:
        return False
    started = info.get("started_at")
    if not started:
        return False
    try:
        started_dt = datetime.fromisoformat(str(started))
        age = (datetime.now() - started_dt).total_seconds()
        return 0 <= age < 45
    except ValueError:
        return False


def read_lock_info() -> dict | None:
    if not LOCK_PATH.is_file():
        return None
    try:
        return json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"raw": LOCK_PATH.read_text(encoding="utf-8", errors="replace")}


def _failure_targets_historical(ui: FriendlyUpdateResult) -> bool:
    blob = " ".join(
        [
            str(ui.message or ""),
            str(ui.headline or ""),
            str(ui.technical_details or ""),
            " ".join(str(x) for x in (ui.summary_lines or [])),
            str(ui.platform_state or ""),
            str((ui.assessment or {}).get("state") or ""),
        ]
    ).lower()
    markers = (
        "cl_primera_2024",
        "backfill histórico",
        "backfill historico",
        "temporada histórica",
        "temporada historica",
        "histórico cl_primera",
        "historico cl_primera",
        "paso histórico",
        "paso historico",
    )
    if any(m in blob for m in markers):
        return True
    if ui.platform_state in ("initial_sync_required", "historical_sync_required"):
        return "2024" in blob or "histórico" in blob or "historico" in blob
    return False


def reconcile_sync_state(
    platform_assessment: dict[str, Any],
    persisted_run_state: FriendlyUpdateResult,
    *,
    persist: bool = True,
) -> FriendlyUpdateResult:
    """
    Combina el estado actual de plataforma (PostgreSQL) con el resultado de la última ejecución.

    Un error antiguo no sobrescribe el estado real de la plataforma. Si el histórico
    falló en UI pero ya está acreditado en BD, se marca reconciliado y el error pasa
    a historial técnico.
    """
    plan = platform_assessment if isinstance(platform_assessment, dict) else {}
    ui = persisted_run_state
    notes: list[str] = list(ui.history_notes or [])

    lock_report = clear_orphan_sync_lock(ui_background_pid=ui.background_pid)
    if lock_report.get("cleared"):
        note = "Lock huérfano eliminado (sin proceso activo)."
        if note not in notes:
            notes.append(note)

    has_hist = bool(plan.get("has_historical_sofascore"))
    has_active = bool(plan.get("has_active_sofascore"))
    platform_state = str(plan.get("state") or "")
    button_label = str(plan.get("button_label") or ui.button_label or "")
    banner = str(plan.get("banner_message") or "").strip()
    in_progress = is_update_in_progress()

    result = replace(
        ui,
        platform_state=platform_state or ui.platform_state,
        button_label=button_label or ui.button_label,
        locked=in_progress,
    )

    if result.status == "running" and not in_progress and not _pid_is_alive(result.background_pid):
        note = "Estado running obsoleto reconciliado (sin proceso ni lock válido)."
        if note not in notes:
            notes.append(note)
        result = replace(
            result,
            ok=True,
            status="idle",
            headline="Estado actualizado.",
            message=banner or result.message,
            background_pid=None,
            reconciled=True,
            history_notes=notes,
        )

    superseded_historical = (
        result.status in ("failed", "error")
        and has_hist
        and _failure_targets_historical(result)
    )
    superseded_fully = result.status in ("failed", "error") and has_hist and has_active

    if superseded_historical or superseded_fully:
        note = "El paso histórico fue completado posteriormente."
        if note not in notes:
            notes.append(note)
        archived = {
            "status": result.status,
            "message": result.message,
            "headline": result.headline,
            "last_check_at": result.last_check_at,
            "log_paths": list(result.log_paths or []),
            "platform_state_at_failure": result.platform_state,
            "note": note,
        }
        assessment = dict(result.assessment or {})
        assessment["superseded_error"] = archived
        assessment["reconciled"] = True
        assessment["history_notes"] = list(notes)
        tech = (result.technical_details or "").strip()
        history_block = "\n".join(notes)
        if history_block and history_block not in tech:
            tech = f"{tech}\n\n{history_block}".strip() if tech else history_block

        if platform_state == "current_sync_required" and not banner:
            banner = (
                f"Los datos históricos de {plan.get('historical_season') or '2024'} están "
                f"disponibles. Falta descargar la temporada activa "
                f"{plan.get('active_season') or get_active_season()}."
            )
        elif platform_state == "fully_initialized" and not banner:
            banner = "Los datos reales están disponibles para consulta y comparación."

        result = replace(
            result,
            ok=True,
            status="idle",
            headline="Histórico disponible"
            if platform_state == "current_sync_required"
            else "Datos reales disponibles",
            message=banner or result.message,
            platform_state=platform_state,
            button_label=button_label,
            errors_count=0,
            reconciled=True,
            history_notes=notes,
            assessment=assessment,
            technical_details=tech,
            background_pid=None,
            needs_initial_backfill=platform_state
            in ("initial_sync_required", "current_sync_required", "historical_sync_required"),
        )
    elif notes and notes != list(ui.history_notes or []):
        result = replace(result, history_notes=notes, reconciled=True)

    if persist and result != ui:
        save_ui_state(result)
    return result


def refresh_sync_card_state() -> tuple[dict[str, Any], FriendlyUpdateResult]:
    """Relee PostgreSQL + estado persistido, reconcilia y no lanza sincronización."""
    plan = load_platform_sync_plan()
    ui = load_ui_state()
    reconciled = reconcile_sync_state(plan, ui, persist=True)
    return plan, reconciled


def load_ui_state() -> FriendlyUpdateResult:
    _ensure_dirs()
    if not UI_STATE_PATH.is_file():
        return FriendlyUpdateResult(
            ok=True,
            status="idle",
            headline="Datos listos.",
            message="Datos listos. Última comprobación: —",
        )
    try:
        data = json.loads(UI_STATE_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise TypeError("ui state must be object")
        allowed = {f.name for f in dataclass_fields(FriendlyUpdateResult)}
        filtered = {k: v for k, v in data.items() if k in allowed}
        return FriendlyUpdateResult(**filtered)
    except (OSError, json.JSONDecodeError, TypeError):
        return FriendlyUpdateResult(
            ok=True,
            status="idle",
            headline="Datos listos.",
            message="Datos listos.",
        )


def save_ui_state(result: FriendlyUpdateResult) -> None:
    _ensure_dirs()
    payload = {
        "ok": result.ok,
        "status": result.status,
        "headline": result.headline,
        "message": result.message,
        "last_check_at": result.last_check_at,
        "last_update_at": result.last_update_at,
        "leagues_reviewed": result.leagues_reviewed,
        "leagues_updated": result.leagues_updated,
        "new_matches": result.new_matches,
        "modified_matches": result.modified_matches,
        "updated_league_labels": result.updated_league_labels,
        "unchanged_league_labels": result.unchanged_league_labels,
        "active_season": result.active_season,
        "historical_leagues_skipped": result.historical_leagues_skipped,
        "leagues_checked": result.leagues_checked,
        "locked": False,
        "technical_details": result.technical_details,
        "log_paths": result.log_paths,
        "mode": result.mode,
        "needs_initial_backfill": result.needs_initial_backfill,
        "summary_lines": result.summary_lines,
        "matches_downloaded": result.matches_downloaded,
        "players_updated": result.players_updated,
        "metrics_imported": result.metrics_imported,
        "errors_count": result.errors_count,
        "remote_events_total": result.remote_events_total,
        "assessment": result.assessment,
        "platform_state": result.platform_state,
        "button_label": result.button_label,
        "background_pid": result.background_pid,
        "reconciled": result.reconciled,
        "history_notes": result.history_notes,
    }
    UI_STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def latest_log_path() -> Path | None:
    if not LOG_DIR.is_dir():
        return None
    logs = sorted(LOG_DIR.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    return logs[0] if logs else None


def _default_compose_invocation() -> tuple[str, ...]:
    info = check_docker_runtime()
    if info.compose_invocation:
        return info.compose_invocation
    return (shutil.which("docker") or "docker", "compose")


def build_worker_command(
    script_args: list[str],
    *,
    compose_invocation: tuple[str, ...] | None = None,
) -> list[str]:
    compose = compose_invocation or _default_compose_invocation()
    return [
        *compose,
        "--project-name",
        "scouting-platform",
        "-f",
        COMPOSE_FILE_CLIENT,
        "--profile",
        "worker",
        "run",
        "--rm",
        "--no-deps",
        WORKER_SERVICE,
        "python",
        "scripts/update_sofascore_incremental.py",
        *script_args,
    ]


def command_to_string(cmd: list[str]) -> str:
    return " ".join(_quote_arg(a) for a in cmd)


def parse_json_summary(stdout: str) -> dict[str, Any] | None:
    for line in stdout.splitlines():
        if line.startswith(JSON_MARKER):
            try:
                return json.loads(line[len(JSON_MARKER) :])
            except json.JSONDecodeError:
                return None
    match = re.search(rf"{re.escape(JSON_MARKER)}(\{{.*\}})\s*$", stdout, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


def _summary_error(payload: Any) -> str | None:
    """An exit code alone does not establish that any league was checked."""
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        return "El worker no confirmó un resumen válido y satisfactorio."
    leagues = payload.get("leagues")
    if not isinstance(leagues, list) or not leagues:
        return "El worker no confirmó ninguna competición revisada."
    for league in leagues:
        if not isinstance(league, dict) or not league.get("slug"):
            return "El resumen contiene una competición inválida."
        for field in ("errors", "pending_total", "total_calendar"):
            value = league.get(field)
            if type(value) is not int or value < 0:
                return "El resumen contiene contadores ausentes o inválidos."
        if league["errors"] or league.get("error_messages"):
            return "El worker informó errores en una competición."
    return None


def _log_filename(suffix: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return LOG_DIR / f"{ts}_{suffix}.log"


def _execute_worker(
    script_args: list[str],
    *,
    log_suffix: str,
    timeout_sec: int,
    acquire_lock: bool = True,
    lock_meta: dict[str, Any] | None = None,
) -> WorkerRunOutput:
    _ensure_dirs()
    runtime = check_docker_runtime()
    cmd = build_worker_command(script_args, compose_invocation=runtime.compose_invocation)
    cmd_str = command_to_string(cmd)

    if not runtime.ok:
        return WorkerRunOutput(
            ok=False,
            command=cmd_str,
            stdout=runtime.diagnostics_text,
            stderr=runtime.error or "Docker no disponible.",
            returncode=-1,
            log_path=None,
            error_message=runtime.error,
        )

    if acquire_lock and is_update_in_progress():
        return WorkerRunOutput(
            ok=False,
            command=cmd_str,
            stdout="",
            stderr="",
            returncode=-1,
            log_path=None,
            locked=True,
            error_message="Actualización en curso.",
        )

    try:
        run_env = build_compose_env()
        host_root, resolve_source = resolve_host_project_root()
    except HostProjectRootError as exc:
        diag = RunnerDiagnostics(
            host_project_root="",
            project_root="",
            compose_project_name="scouting-platform",
            compose_file=COMPOSE_FILE_CLIENT,
            cwd=str(PROJECT_ROOT),
            error=str(exc),
            resolve_source="error",
        )
        save_runner_diagnostics(diag)
        return WorkerRunOutput(
            ok=False,
            command=cmd_str,
            stdout=diag.summary_text,
            stderr=str(exc),
            returncode=-1,
            log_path=None,
            error_message=str(exc),
        )

    log_path = _log_filename(log_suffix)
    if acquire_lock:
        payload = lock_meta or {}
        payload.update(
            {
                "command": cmd_str,
                "log_path": str(log_path),
                "started_at": datetime.now().isoformat(timespec="seconds"),
                "pid": os.getpid(),
            }
        )
        LOCK_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    preflight_ok, preflight_cmd, preflight_out = run_worker_preflight(
        compose_invocation=runtime.compose_invocation,
        env=run_env,
    )
    diag = RunnerDiagnostics(
        host_project_root=host_root,
        project_root=run_env["PROJECT_ROOT"],
        compose_project_name=run_env["COMPOSE_PROJECT_NAME"],
        compose_file=run_env["COMPOSE_FILE"],
        cwd=str(PROJECT_ROOT),
        preflight_command=preflight_cmd,
        preflight_ok=preflight_ok,
        preflight_output=preflight_out,
        last_command=cmd_str,
        resolve_source=resolve_source,
    )
    if not preflight_ok:
        diag.error = f"Worker no ve el repositorio. HOST_PROJECT_ROOT usado: {host_root}"
        save_runner_diagnostics(diag)
        log_path.write_text(
            f"{_format_env_block(run_env)}\n\n"
            f"$ {preflight_cmd}\nexit_code=fail\n\n{preflight_out}\n",
            encoding="utf-8",
        )
        return WorkerRunOutput(
            ok=False,
            command=cmd_str,
            stdout=diag.summary_text,
            stderr=diag.error,
            returncode=-1,
            log_path=log_path,
            error_message=diag.error,
        )

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            env=run_env,
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        env_block = _format_env_block(run_env)
        log_path.write_text(
            f"{env_block}\n\n"
            f"$ {preflight_cmd}\nok\n\n"
            f"$ {cmd_str}\nexit_code={proc.returncode}\n\n"
            f"--- stdout ---\n{stdout}\n\n"
            f"--- stderr ---\n{stderr}\n",
            encoding="utf-8",
        )
        save_runner_diagnostics(diag)
        json_payload = parse_json_summary(stdout)
        error_message = _summary_error(json_payload) if "--json-summary" in script_args else None
        if proc.returncode != 0:
            if "already in use" in (stdout + stderr).lower():
                error_message = "Conflicto de contenedores Docker (project name)."
            elif "Cannot connect to the Docker daemon" in (stdout + stderr):
                error_message = "No se pudo conectar al daemon Docker."
            elif "can't open file" in (stdout + stderr).lower():
                error_message = (
                    f"Worker no ve el script incremental. HOST_PROJECT_ROOT usado: {host_root}"
                )
            else:
                error_message = f"Error en la ejecución (código {proc.returncode})."
        return WorkerRunOutput(
            ok=proc.returncode == 0 and error_message is None,
            command=cmd_str,
            stdout=stdout,
            stderr=stderr,
            returncode=proc.returncode,
            log_path=log_path,
            json_payload=json_payload,
            error_message=error_message,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + f"\nTimeout ({timeout_sec}s)."
        log_path.write_text(
            f"$ {cmd_str}\nTIMEOUT\n\n--- stdout ---\n{stdout}\n\n--- stderr ---\n{stderr}\n",
            encoding="utf-8",
        )
        return WorkerRunOutput(
            ok=False,
            command=cmd_str,
            stdout=stdout,
            stderr=stderr,
            returncode=-1,
            log_path=log_path,
            error_message=f"Tiempo agotado ({timeout_sec}s).",
        )
    except FileNotFoundError:
        return WorkerRunOutput(
            ok=False,
            command=cmd_str,
            stdout=check_docker_runtime().diagnostics_text,
            stderr="docker no encontrado",
            returncode=-1,
            log_path=None,
            error_message="Docker no encontrado.",
        )
    finally:
        if acquire_lock and LOCK_PATH.is_file():
            try:
                LOCK_PATH.unlink()
            except OSError:
                pass


def _leagues_with_pending(json_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not json_payload:
        return []
    out: list[dict[str, Any]] = []
    for lg in json_payload.get("leagues", []):
        pending = int(lg.get("pending_total") or 0)
        if pending <= 0:
            pending = (
                int(lg.get("new_events") or 0)
                + int(lg.get("updated_events") or 0)
                + int(lg.get("pending_events") or 0)
            )
        if pending > 0:
            out.append(lg)
    return out


def _summarize_payload(
    json_payload: dict[str, Any] | None,
    *,
    updated_slugs: set[str] | None = None,
) -> tuple[int, int, int, int, list[str], list[str]]:
    if not json_payload:
        return 0, 0, 0, 0, [], []
    leagues = json_payload.get("leagues", [])
    reviewed = len(leagues)
    new_total = 0
    modified_total = 0
    updated_labels: list[str] = []
    unchanged_labels: list[str] = []

    for lg in leagues:
        slug = str(lg.get("slug", ""))
        label = _league_label(slug, lg.get("competition"))
        new_n = int(lg.get("new_events") or 0)
        mod_n = int(lg.get("updated_events") or 0)
        pending = int(lg.get("pending_total") or 0)
        if pending <= 0:
            pending = new_n + mod_n + int(lg.get("pending_events") or 0)

        if updated_slugs is not None:
            if slug in updated_slugs:
                updated_labels.append(label)
                new_total += new_n
                modified_total += mod_n
            else:
                unchanged_labels.append(label)
        elif pending > 0:
            updated_labels.append(label)
            new_total += new_n
            modified_total += mod_n
        else:
            unchanged_labels.append(label)

    updated_count = len(updated_labels) if updated_slugs is None else len(updated_slugs)
    return reviewed, updated_count, new_total, modified_total, updated_labels, unchanged_labels


def _season_context_from_payload(json_payload: dict[str, Any] | None) -> tuple[str | None, int, list[str]]:
    if not json_payload:
        return None, 0, []
    active = json_payload.get("active_season")
    if active is not None:
        active = str(active)
    skipped = int(json_payload.get("historical_leagues_skipped") or 0)
    checked_raw = json_payload.get("leagues_checked")
    if isinstance(checked_raw, list):
        checked = [str(s) for s in checked_raw]
    else:
        checked = [str(lg.get("slug", "")) for lg in json_payload.get("leagues", []) if lg.get("slug")]
    return active, skipped, checked


def _active_season_message(
    active_season: str | None,
    historical_skipped: int,
    *,
    prefix: str = "",
) -> str:
    season = active_season or get_active_season()
    msg = f"{prefix}Temporada activa {season} revisada."
    if historical_skipped > 0:
        msg += " No se tocaron temporadas históricas."
    return msg


def _payload_totals(json_payload: dict[str, Any] | None) -> dict[str, int]:
    if not json_payload:
        return {
            "downloaded": 0,
            "players_updated": 0,
            "metrics_imported": 0,
            "errors": 0,
            "remote_events": 0,
            "new_events": 0,
            "updated_events": 0,
        }
    downloaded = players = metrics = errors = remote = new_events = updated_events = 0
    for lg in json_payload.get("leagues", []):
        downloaded += int(lg.get("downloaded") or 0)
        players += int(lg.get("players_updated") or 0)
        metrics += int(lg.get("metrics_imported") or 0)
        errors += int(lg.get("errors") or 0)
        remote += int(lg.get("total_calendar") or 0)
        new_events += int(lg.get("new_events") or 0)
        updated_events += int(lg.get("updated_events") or 0)
    return {
        "downloaded": downloaded,
        "players_updated": players,
        "metrics_imported": metrics,
        "errors": errors,
        "remote_events": remote,
        "new_events": new_events,
        "updated_events": updated_events,
    }


def _build_summary_lines(
    *,
    mode: str,
    active_season: str | None,
    json_payload: dict[str, Any] | None,
    assessment: dict[str, Any] | None = None,
) -> list[str]:
    totals = _payload_totals(json_payload)
    lines = [
        "Proveedor: Sofascore",
        f"Modo: {mode}",
        f"Temporada: {active_season or '—'}",
    ]
    if assessment:
        lines.append(
            f"Métricas reales previas: {assessment.get('sofascore_metrics', 0)} · "
            f"demo: {assessment.get('demo_metrics', 0)}"
        )
    if json_payload:
        leagues = json_payload.get("leagues") or []
        if leagues:
            sample = leagues[0]
            lines.append(
                f"Ejemplo liga: {sample.get('competition')} · "
                f"tournament_id={sample.get('tournament_id')} · "
                f"season_id={sample.get('season_id')}"
            )
            lines.append(f"Competiciones revisadas: {len(leagues)}")
    lines.extend(
        [
            f"Eventos remotos finalizados: {totals['remote_events']}",
            f"Partidos nuevos (clasificación): {totals['new_events']}",
            f"Partidos actualizados (clasificación): {totals['updated_events']}",
            f"Partidos descargados: {totals['downloaded']}",
            f"Jugadores tocados: {totals['players_updated']}",
            f"Filas CSV métricas importadas: {totals['metrics_imported']}",
            f"Errores: {totals['errors']}",
        ]
    )
    return lines


def _load_season_assessment(active_season: str) -> dict[str, Any]:
    try:
        from scouting.db import get_connection
        from scouting.services.sofascore_sync_assessment import assess_season_sync

        with get_connection() as conn:
            return assess_season_sync(conn, active_season).to_dict()
    except Exception as exc:  # noqa: BLE001
        return {"season": active_season, "error": str(exc), "needs_initial_backfill": True}


def load_platform_sync_plan() -> dict[str, Any]:
    try:
        from scouting.db import get_connection
        from scouting.services.platform_sync_plan import assess_platform_sync

        with get_connection() as conn:
            return assess_platform_sync(conn).to_dict()
    except Exception as exc:  # noqa: BLE001
        return {
            "state": "initial_sync_required",
            "button_label": "Descargar datos reales",
            "banner_message": f"No se pudo evaluar el estado Sofascore: {exc}",
            "error": str(exc),
        }


def start_dashboard_sync_background() -> FriendlyUpdateResult:
    """
    Lanza scripts/run_dashboard_sofascore_sync.py en segundo plano.

    No bloquea el hilo de Streamlit; el orquestador actualiza el estado y el lock.
    """
    now = datetime.now()
    now_str = _format_dt(now)
    plan = load_platform_sync_plan()
    runtime = check_docker_runtime()
    clear_orphan_sync_lock()

    if is_update_in_progress():
        return FriendlyUpdateResult(
            ok=False,
            status="running",
            headline="Actualización en curso.",
            message="Actualización en curso. Espera a que finalice.",
            locked=True,
            platform_state=str(plan.get("state") or ""),
            button_label=str(plan.get("button_label") or "Actualizar datos"),
            mode="dashboard",
        )

    if not runtime.ok:
        result = FriendlyUpdateResult(
            ok=False,
            status="failed",
            headline="No se pudo iniciar la sincronización.",
            message="Docker/worker no disponible. Revisa el log técnico.",
            last_check_at=now_str,
            technical_details=runtime.diagnostics_text,
            platform_state=str(plan.get("state") or ""),
            button_label=str(plan.get("button_label") or "Actualizar datos"),
            mode="dashboard",
        )
        save_ui_state(result)
        return result

    _ensure_dirs()
    log_path = _log_filename("dashboard_bg")
    script = PROJECT_ROOT / "scripts" / "run_dashboard_sofascore_sync.py"
    import sys as _sys

    cmd = [_sys.executable, str(script), "--mode", "auto"]

    progress = str(plan.get("progress_message") or "Sincronizando Sofascore…")
    running = FriendlyUpdateResult(
        ok=True,
        status="running",
        headline="Sincronización en curso",
        message=progress,
        last_check_at=now_str,
        active_season=str(plan.get("active_season") or get_active_season()),
        mode="dashboard",
        platform_state=str(plan.get("state") or ""),
        button_label=str(plan.get("button_label") or "Actualizar datos"),
        summary_lines=[
            f"Estado plataforma: {plan.get('state')}",
            f"Acción: {plan.get('button_label')}",
            *(plan.get("step_labels") or []),
        ],
        log_paths=[str(log_path)],
        assessment=plan if isinstance(plan, dict) else {},
        needs_initial_backfill=str(plan.get("state") or "")
        in ("initial_sync_required", "current_sync_required", "historical_sync_required"),
    )
    save_ui_state(running)
    LOCK_PATH.write_text(
        json.dumps(
            {
                "phase": "dashboard_background",
                "started_at": now.isoformat(),
                "plan_state": plan.get("state"),
                "log_path": str(log_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    log_fh = open(log_path, "w", encoding="utf-8")  # noqa: SIM115
    log_fh.write(f"$ {' '.join(cmd)}\nstarted_at={now.isoformat()}\n\n")
    log_fh.flush()
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src")},
        )
    except OSError as exc:
        log_fh.close()
        if LOCK_PATH.is_file():
            LOCK_PATH.unlink(missing_ok=True)
        result = FriendlyUpdateResult(
            ok=False,
            status="failed",
            headline="No se pudo lanzar el proceso de sincronización.",
            message=str(exc),
            last_check_at=now_str,
            log_paths=[str(log_path)],
            platform_state=str(plan.get("state") or ""),
            button_label=str(plan.get("button_label") or "Actualizar datos"),
            mode="dashboard",
        )
        save_ui_state(result)
        return result

    running.background_pid = proc.pid
    lock_payload = {
        "phase": "dashboard_background",
        "started_at": now.isoformat(),
        "plan_state": plan.get("state"),
        "log_path": str(log_path),
        "pid": proc.pid,
    }
    LOCK_PATH.write_text(json.dumps(lock_payload, indent=2), encoding="utf-8")
    save_ui_state(running)
    # El orquestador hijo posee el trabajo; no cerramos el FH aquí (lo hereda el hijo).
    return running


def run_dashboard_sync_for_ui() -> FriendlyUpdateResult:
    """
    Ejecuta el plan A/B/C/D de forma síncrona (llamado por el proceso en background).

    A/B/C: pasos force-backfill secuenciales.
    D: reutiliza la lógica incremental existente.
    """
    from scouting.services.platform_sync_plan import assess_platform_sync

    now = datetime.now()
    now_str = _format_dt(now)
    runtime = check_docker_runtime()
    technical_parts: list[str] = [runtime.diagnostics_text]
    log_paths: list[str] = []

    try:
        from scouting.db import get_connection

        with get_connection() as conn:
            plan = assess_platform_sync(conn)
    except Exception as exc:  # noqa: BLE001
        result = FriendlyUpdateResult(
            ok=False,
            status="failed",
            headline="No se pudo evaluar el plan de sincronización.",
            message=str(exc),
            last_check_at=now_str,
            mode="dashboard",
            platform_state="failed",
        )
        save_ui_state(result)
        return result

    if is_update_in_progress():
        # Permitir continuar si este proceso ya posee el lock (background launcher).
        lock_info = read_lock_info() or {}
        phase = str(lock_info.get("phase") or "")
        if phase not in (
            "dashboard_background",
            "dashboard_sync",
            "ui_dashboard",
        ):
            return FriendlyUpdateResult(
                ok=False,
                status="running",
                headline="Actualización en curso.",
                message="Actualización en curso. Espera a que finalice.",
                locked=True,
                platform_state=plan.state,
                button_label=plan.button_label,
            )

    if not runtime.ok:
        result = FriendlyUpdateResult(
            ok=False,
            status="failed",
            headline="No se pudo sincronizar.",
            message="Docker/worker no disponible.",
            last_check_at=now_str,
            technical_details="\n".join(technical_parts),
            platform_state=plan.state,
            button_label=plan.button_label,
            mode="dashboard",
        )
        save_ui_state(result)
        return result

    LOCK_PATH.write_text(
        json.dumps(
            {
                "phase": "dashboard_sync",
                "started_at": now.isoformat(),
                "plan_state": plan.state,
                "pid": os.getpid(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    save_ui_state(
        FriendlyUpdateResult(
            ok=True,
            status="running",
            headline="Sincronización en curso",
            message=plan.progress_message,
            last_check_at=now_str,
            active_season=plan.active_season,
            mode="dashboard",
            platform_state=plan.state,
            button_label=plan.button_label,
            summary_lines=[f"Estado: {plan.state}", *plan.step_labels],
            assessment=plan.to_dict(),
            needs_initial_backfill=plan.state != "fully_initialized",
        )
    )

    try:
        if plan.state == "fully_initialized":
            # Liberar lock para que _run_update_for_ui gestione el suyo.
            if LOCK_PATH.is_file():
                try:
                    LOCK_PATH.unlink()
                except OSError:
                    pass
            result = _run_update_for_ui(mode="incremental")
            result.platform_state = "fully_initialized"
            result.button_label = plan.button_label
            if result.status == "no_news":
                result.message = plan.completion_message
                result.headline = "Sin novedades"
            elif result.ok:
                result.message = result.message or plan.completion_message
            save_ui_state(result)
            return result

        totals_all = {
            "downloaded": 0,
            "players_updated": 0,
            "metrics_imported": 0,
            "errors": 0,
            "remote_events": 0,
        }
        failed = False
        for idx, (args, label) in enumerate(zip(plan.worker_steps, plan.step_labels, strict=False)):
            save_ui_state(
                FriendlyUpdateResult(
                    ok=True,
                    status="running",
                    headline=f"Paso {idx + 1}/{len(plan.worker_steps)}",
                    message=f"{plan.progress_message} ({label})",
                    last_check_at=_format_dt(datetime.now()),
                    active_season=plan.active_season,
                    mode="dashboard",
                    platform_state=plan.state,
                    button_label=plan.button_label,
                    summary_lines=[
                        f"Estado: {plan.state}",
                        f"Paso actual: {label}",
                        *plan.step_labels,
                    ],
                    assessment=plan.to_dict(),
                    log_paths=log_paths,
                    matches_downloaded=totals_all["downloaded"],
                    metrics_imported=totals_all["metrics_imported"],
                    errors_count=totals_all["errors"],
                )
            )
            out = _execute_worker(
                list(args),
                log_suffix=f"dashboard_step{idx + 1}",
                timeout_sec=14400,
                acquire_lock=False,
            )
            technical_parts.append(f"$ {out.command}\n{out.combined_output}")
            if out.log_path:
                log_paths.append(str(out.log_path))
            step_totals = _payload_totals(out.json_payload)
            for k in totals_all:
                totals_all[k] += int(step_totals.get(k) or 0)
            if not out.ok:
                failed = True
                result = FriendlyUpdateResult(
                    ok=False,
                    status="failed",
                    headline="Falló la sincronización Sofascore.",
                    message=(
                        f"Error en «{label}». Errores: {step_totals.get('errors') or 'ver log'}. "
                        "Los datos demo se conservan."
                    ),
                    last_check_at=_format_dt(datetime.now()),
                    technical_details="\n\n".join(technical_parts),
                    log_paths=log_paths,
                    mode="dashboard",
                    platform_state=plan.state,
                    button_label=plan.button_label,
                    summary_lines=[
                        f"Estado: {plan.state}",
                        f"Falló: {label}",
                        f"Descargados: {totals_all['downloaded']}",
                        f"Métricas: {totals_all['metrics_imported']}",
                    ],
                    matches_downloaded=totals_all["downloaded"],
                    players_updated=totals_all["players_updated"],
                    metrics_imported=totals_all["metrics_imported"],
                    errors_count=totals_all["errors"],
                    assessment=plan.to_dict(),
                )
                save_ui_state(result)
                return result

        post_plan = load_platform_sync_plan()
        result = FriendlyUpdateResult(
            ok=True,
            status="completed" if not failed else "failed",
            headline="Sincronización completada",
            message=plan.completion_message,
            last_check_at=_format_dt(datetime.now()),
            last_update_at=_format_dt(datetime.now()),
            active_season=plan.active_season,
            technical_details="\n\n".join(technical_parts),
            log_paths=log_paths,
            mode="dashboard",
            platform_state=str(post_plan.get("state") or plan.state),
            button_label=str(post_plan.get("button_label") or plan.button_label),
            summary_lines=[
                f"Estado inicial: {plan.state}",
                f"Estado final: {post_plan.get('state')}",
                f"Partidos descargados: {totals_all['downloaded']}",
                f"Métricas importadas: {totals_all['metrics_imported']}",
                f"Errores: {totals_all['errors']}",
                *plan.step_labels,
            ],
            matches_downloaded=totals_all["downloaded"],
            players_updated=totals_all["players_updated"],
            metrics_imported=totals_all["metrics_imported"],
            errors_count=totals_all["errors"],
            remote_events_total=totals_all["remote_events"],
            assessment=post_plan if isinstance(post_plan, dict) else plan.to_dict(),
            needs_initial_backfill=str(post_plan.get("state") or "")
            in ("initial_sync_required", "current_sync_required", "historical_sync_required"),
        )
        save_ui_state(result)
        return result
    finally:
        if LOCK_PATH.is_file():
            try:
                LOCK_PATH.unlink()
            except OSError:
                pass


def run_incremental_all_for_ui() -> FriendlyUpdateResult:
    """Actualización incremental; si no hay sync real, inicia backfill inicial."""
    return _run_update_for_ui(mode="incremental")


def run_resync_season_for_ui() -> FriendlyUpdateResult:
    """Resincroniza toda la temporada activa (fuerza descarga de eventos finalizados)."""
    return _run_update_for_ui(mode="resync")


def run_historical_import_for_ui(
    *,
    league_slug: str,
    season: str,
    process_existing: bool = False,
) -> FriendlyUpdateResult:
    """
    Importa una temporada histórica configurada (p. ej. cl_primera_2024).

    No se ejecuta con el botón normal del dashboard. Usa --only + --season
    + --force-backfill (o --process-existing-output si hay checkpoint).
    """
    now = datetime.now()
    now_str = _format_dt(now)
    runtime = check_docker_runtime()
    technical_parts: list[str] = [runtime.diagnostics_text]
    log_paths: list[str] = []
    mode = "historical"
    slug = str(league_slug).strip()
    season_str = str(season).strip()

    known = {opt["slug"]: opt for opt in HISTORICAL_IMPORT_OPTIONS}
    if slug not in known:
        result = FriendlyUpdateResult(
            ok=False,
            status="error",
            headline="Temporada histórica no configurada.",
            message=f"Slug desconocido: {slug}. Opciones: {', '.join(known)}",
            last_check_at=now_str,
            technical_details="\n".join(technical_parts),
            mode=mode,
        )
        save_ui_state(result)
        return result

    if is_update_in_progress():
        return FriendlyUpdateResult(
            ok=False,
            status="running",
            headline="Actualización en curso.",
            message="Actualización en curso. Espera a que finalice.",
            locked=True,
            technical_details="\n".join(technical_parts),
            mode=mode,
        )

    if not runtime.ok:
        result = FriendlyUpdateResult(
            ok=False,
            status="error",
            headline="No se pudo importar la temporada histórica.",
            message="Docker/worker no disponible. Revisa el log técnico.",
            last_check_at=now_str,
            technical_details="\n".join(technical_parts),
            mode=mode,
        )
        save_ui_state(result)
        return result

    LOCK_PATH.write_text(
        json.dumps(
            {
                "phase": "ui_historical",
                "started_at": now.isoformat(),
                "season": season_str,
                "slug": slug,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    try:
        args = ["--only", slug, "--season", season_str, "--json-summary"]
        if process_existing:
            args.append("--process-existing-output")
        else:
            args.append("--force-backfill")

        update_out = _execute_worker(
            args,
            log_suffix=f"hist_{slug}",
            timeout_sec=14400,
            acquire_lock=False,
        )
        technical_parts.append(f"$ {update_out.command}\n{update_out.combined_output}")
        if update_out.log_path:
            log_paths.append(str(update_out.log_path))

        totals = _payload_totals(update_out.json_payload)
        if not update_out.ok:
            result = FriendlyUpdateResult(
                ok=False,
                status="error",
                headline="Falló la importación histórica.",
                message=(
                    f"No se importó {known[slug]['label']}. "
                    f"Errores: {totals['errors'] or 'ver log'}."
                ),
                last_check_at=now_str,
                technical_details="\n\n".join(technical_parts),
                log_paths=log_paths,
                mode=mode,
                summary_lines=[
                    f"Modo: histórico ({slug})",
                    f"Temporada: {season_str}",
                    f"Descargados: {totals['downloaded']}",
                    f"Métricas: {totals['metrics_imported']}",
                    f"Errores: {totals['errors']}",
                ],
                matches_downloaded=totals["downloaded"],
                metrics_imported=totals["metrics_imported"],
                errors_count=totals["errors"],
            )
            save_ui_state(result)
            return result

        if totals["metrics_imported"] <= 0 and totals["downloaded"] <= 0:
            result = FriendlyUpdateResult(
                ok=False,
                status="error",
                headline="Importación histórica sin métricas.",
                message=(
                    "El worker terminó sin importar métricas. "
                    "Revisa el preflight y el log (no es «sin novedades»)."
                ),
                last_check_at=now_str,
                technical_details="\n\n".join(technical_parts),
                log_paths=log_paths,
                mode=mode,
                errors_count=totals["errors"],
            )
            save_ui_state(result)
            return result

        result = FriendlyUpdateResult(
            ok=True,
            status="success",
            headline=f"Temporada histórica {season_str} importada.",
            message=(
                f"{known[slug]['label']}: partidos descargados {totals['downloaded']}, "
                f"métricas {totals['metrics_imported']}."
            ),
            last_check_at=now_str,
            last_update_at=now_str,
            active_season=get_active_season(),
            technical_details="\n\n".join(technical_parts),
            log_paths=log_paths,
            mode=mode,
            summary_lines=[
                f"Modo: histórico ({slug})",
                f"Temporada importada: {season_str}",
                f"Partidos descargados: {totals['downloaded']}",
                f"Jugadores: {totals['players_updated']}",
                f"Métricas importadas: {totals['metrics_imported']}",
                "La temporada activa del dashboard no se ha reescrito.",
            ],
            matches_downloaded=totals["downloaded"],
            players_updated=totals["players_updated"],
            metrics_imported=totals["metrics_imported"],
            errors_count=totals["errors"],
            remote_events_total=totals["remote_events"],
        )
        save_ui_state(result)
        return result
    finally:
        if LOCK_PATH.is_file():
            try:
                LOCK_PATH.unlink()
            except OSError:
                pass


def _run_update_for_ui(*, mode: str) -> FriendlyUpdateResult:
    now = datetime.now()
    now_str = _format_dt(now)
    runtime = check_docker_runtime()
    technical_parts: list[str] = [runtime.diagnostics_text]
    log_paths: list[str] = []
    active_season = get_active_season()
    assessment = _load_season_assessment(active_season)
    needs_backfill = bool(assessment.get("needs_initial_backfill"))

    if is_update_in_progress():
        return FriendlyUpdateResult(
            ok=False,
            status="running",
            headline="Actualización en curso.",
            message="Actualización en curso. Espera a que finalice.",
            locked=True,
            technical_details="\n".join(technical_parts),
            mode=mode,
            assessment=assessment,
        )

    if not runtime.ok:
        result = FriendlyUpdateResult(
            ok=False,
            status="error",
            headline="No se pudo actualizar.",
            message="No se pudo actualizar. Revisa el log técnico.",
            last_check_at=now_str,
            technical_details="\n".join(technical_parts),
            mode=mode,
            assessment=assessment,
            needs_initial_backfill=needs_backfill,
        )
        save_ui_state(result)
        return result

    LOCK_PATH.write_text(
        json.dumps(
            {"phase": f"ui_{mode}", "started_at": now.isoformat(), "season": active_season},
            indent=2,
        ),
        encoding="utf-8",
    )

    try:
        force_full = mode == "resync" or (mode == "incremental" and needs_backfill)

        if force_full:
            flag = "--resync-season" if mode == "resync" else "--force-backfill"
            effective_mode = "resync" if mode == "resync" else "backfill"
            if needs_backfill and mode == "incremental":
                technical_parts.append(
                    "No existe sincronización real de la temporada. Iniciando importación inicial."
                )
                for reason in assessment.get("reasons") or []:
                    technical_parts.append(f"  · {reason}")

            update_out = _execute_worker(
                ["--all", "--season", active_season, flag, "--json-summary"],
                log_suffix=f"all_{effective_mode}",
                timeout_sec=14400,
                acquire_lock=False,
            )
            technical_parts.append(f"$ {update_out.command}\n{update_out.combined_output}")
            if update_out.log_path:
                log_paths.append(str(update_out.log_path))

            totals = _payload_totals(update_out.json_payload)
            season_active, historical_skipped, leagues_checked = _season_context_from_payload(
                update_out.json_payload
            )
            reviewed, updated_count, new_total, mod_total, updated_labels, unchanged_labels = (
                _summarize_payload(update_out.json_payload)
            )

            if not update_out.ok:
                result = FriendlyUpdateResult(
                    ok=False,
                    status="error",
                    headline="Falló la sincronización Sofascore.",
                    message=(
                        f"Falló la descarga/importación. Errores: {totals['errors'] or 'ver log'}. "
                        "Consulta los logs técnicos."
                    ),
                    last_check_at=now_str,
                    technical_details="\n\n".join(technical_parts),
                    log_paths=log_paths,
                    mode=effective_mode,
                    needs_initial_backfill=needs_backfill,
                    assessment=assessment,
                    summary_lines=_build_summary_lines(
                        mode=effective_mode,
                        active_season=active_season,
                        json_payload=update_out.json_payload,
                        assessment=assessment,
                    ),
                    matches_downloaded=totals["downloaded"],
                    players_updated=totals["players_updated"],
                    metrics_imported=totals["metrics_imported"],
                    errors_count=totals["errors"],
                    remote_events_total=totals["remote_events"],
                )
                save_ui_state(result)
                return result

            post_assessment = _load_season_assessment(active_season)
            headline = (
                "Importación inicial completada."
                if effective_mode == "backfill"
                else "Resincronización de temporada completada."
            )
            if totals["downloaded"] <= 0 and totals["metrics_imported"] <= 0:
                result = FriendlyUpdateResult(
                    ok=False,
                    status="error",
                    headline="La sincronización no importó datos.",
                    message=(
                        "Se consultó el calendario pero no se persistieron métricas. "
                        "No se marca como sincronización correcta. Revisa los logs."
                    ),
                    last_check_at=now_str,
                    leagues_reviewed=reviewed,
                    active_season=season_active or active_season,
                    historical_leagues_skipped=historical_skipped,
                    leagues_checked=leagues_checked,
                    technical_details="\n\n".join(technical_parts),
                    log_paths=log_paths,
                    mode=effective_mode,
                    needs_initial_backfill=bool(post_assessment.get("needs_initial_backfill")),
                    assessment=post_assessment,
                    summary_lines=_build_summary_lines(
                        mode=effective_mode,
                        active_season=active_season,
                        json_payload=update_out.json_payload,
                        assessment=post_assessment,
                    ),
                    matches_downloaded=totals["downloaded"],
                    players_updated=totals["players_updated"],
                    metrics_imported=totals["metrics_imported"],
                    errors_count=totals["errors"],
                    remote_events_total=totals["remote_events"],
                )
                save_ui_state(result)
                return result

            result = FriendlyUpdateResult(
                ok=True,
                status="backfill" if effective_mode == "backfill" else "success",
                headline=headline,
                message=(
                    f"{headline} Partidos descargados: {totals['downloaded']}. "
                    f"Métricas importadas (filas CSV): {totals['metrics_imported']}."
                ),
                last_check_at=now_str,
                last_update_at=now_str,
                leagues_reviewed=reviewed,
                leagues_updated=updated_count,
                new_matches=new_total,
                modified_matches=mod_total,
                updated_league_labels=updated_labels,
                unchanged_league_labels=unchanged_labels,
                active_season=season_active or active_season,
                historical_leagues_skipped=historical_skipped,
                leagues_checked=leagues_checked,
                technical_details="\n\n".join(technical_parts),
                log_paths=log_paths,
                mode=effective_mode,
                needs_initial_backfill=bool(post_assessment.get("needs_initial_backfill")),
                assessment=post_assessment,
                summary_lines=_build_summary_lines(
                    mode=effective_mode,
                    active_season=active_season,
                    json_payload=update_out.json_payload,
                    assessment=post_assessment,
                ),
                matches_downloaded=totals["downloaded"],
                players_updated=totals["players_updated"],
                metrics_imported=totals["metrics_imported"],
                errors_count=totals["errors"],
                remote_events_total=totals["remote_events"],
            )
            save_ui_state(result)
            return result

        dry_run_args = ["--all", "--season", active_season, "--dry-run", "--json-summary"]
        dry_run = _execute_worker(
            dry_run_args,
            log_suffix="all_dryrun",
            timeout_sec=900,
            acquire_lock=False,
        )
        technical_parts.append(f"$ {dry_run.command}\n{dry_run.combined_output}")
        if dry_run.log_path:
            log_paths.append(str(dry_run.log_path))

        if dry_run.locked:
            return FriendlyUpdateResult(
                ok=False,
                status="running",
                headline="Actualización en curso.",
                message="Actualización en curso. Espera a que finalice.",
                locked=True,
                technical_details="\n\n".join(technical_parts),
                mode=mode,
                assessment=assessment,
            )

        if not dry_run.ok:
            result = FriendlyUpdateResult(
                ok=False,
                status="error",
                headline="No se pudo consultar el calendario remoto.",
                message="Falló la revisión remota. Consulta los logs (no es «sin novedades»).",
                last_check_at=now_str,
                technical_details="\n\n".join(technical_parts),
                log_paths=log_paths,
                mode=mode,
                assessment=assessment,
                needs_initial_backfill=needs_backfill,
            )
            save_ui_state(result)
            return result

        pending_leagues = _leagues_with_pending(dry_run.json_payload)
        reviewed, _, _, _, _, unchanged_labels = _summarize_payload(dry_run.json_payload)
        season_active, historical_skipped, leagues_checked = _season_context_from_payload(
            dry_run.json_payload
        )
        dry_totals = _payload_totals(dry_run.json_payload)

        if not pending_leagues:
            no_news_lines = _build_summary_lines(
                mode="incremental",
                active_season=season_active or active_season,
                json_payload=dry_run.json_payload,
                assessment=assessment,
            )
            no_news_lines.append("Partidos pendientes: 0")
            no_news_lines.append(
                f"Métricas Sofascore reales: {assessment.get('sofascore_metrics', 0)}"
            )
            result = FriendlyUpdateResult(
                ok=True,
                status="no_news",
                headline="Sin novedades",
                message=(
                    f"La temporada {season_active or active_season} ya estaba sincronizada. "
                    f"Eventos remotos revisados: {dry_totals['remote_events']}. "
                    "No había partidos ni métricas pendientes."
                ),
                last_check_at=now_str,
                last_update_at=load_ui_state().last_update_at,
                leagues_reviewed=reviewed,
                leagues_updated=0,
                new_matches=0,
                modified_matches=0,
                unchanged_league_labels=unchanged_labels,
                active_season=season_active or active_season,
                historical_leagues_skipped=historical_skipped,
                leagues_checked=leagues_checked,
                technical_details="\n\n".join(technical_parts),
                log_paths=log_paths,
                mode="incremental",
                needs_initial_backfill=False,
                assessment=assessment,
                summary_lines=no_news_lines,
                remote_events_total=dry_totals["remote_events"],
            )
            save_ui_state(result)
            return result

        slugs_to_update = [str(lg["slug"]) for lg in pending_leagues]
        update_out = _execute_worker(
            ["--only", *slugs_to_update, "--season", active_season, "--json-summary"],
            log_suffix="all_update",
            timeout_sec=7200,
            acquire_lock=False,
        )
        technical_parts.append(f"$ {update_out.command}\n{update_out.combined_output}")
        if update_out.log_path:
            log_paths.append(str(update_out.log_path))

        totals = _payload_totals(update_out.json_payload)
        if not update_out.ok:
            result = FriendlyUpdateResult(
                ok=False,
                status="error",
                headline="Falló la actualización incremental.",
                message=(
                    f"Falló la descarga de estadísticas. Errores: {totals['errors'] or 'ver log'}."
                ),
                last_check_at=now_str,
                technical_details="\n\n".join(technical_parts),
                log_paths=log_paths,
                mode="incremental",
                assessment=assessment,
                summary_lines=_build_summary_lines(
                    mode="incremental",
                    active_season=active_season,
                    json_payload=update_out.json_payload,
                    assessment=assessment,
                ),
                errors_count=totals["errors"],
            )
            save_ui_state(result)
            return result

        updated_slugs = set(slugs_to_update)
        reviewed, updated_count, new_total, mod_total, updated_labels, unchanged_labels = (
            _summarize_payload(update_out.json_payload, updated_slugs=updated_slugs)
        )
        _, update_historical_skipped, update_leagues_checked = _season_context_from_payload(
            update_out.json_payload
        )
        post_assessment = _load_season_assessment(active_season)

        if updated_count > 0 and len(unchanged_labels) > 0:
            status = "partial"
            headline = f"Se actualizaron {updated_count} competiciones."
            message = (
                f"Se actualizaron {updated_count} competiciones. "
                f"{len(unchanged_labels)} competición(es) no tenían novedades. "
                f"Descargados: {totals['downloaded']} · Métricas: {totals['metrics_imported']}."
            )
        else:
            status = "success"
            headline = "Actualización completada"
            message = (
                f"Partidos descargados: {totals['downloaded']}. "
                f"Métricas importadas: {totals['metrics_imported']}."
            )

        result = FriendlyUpdateResult(
            ok=True,
            status=status,
            headline=headline,
            message=message,
            last_check_at=now_str,
            last_update_at=now_str,
            leagues_reviewed=reviewed,
            leagues_updated=updated_count,
            new_matches=new_total,
            modified_matches=mod_total,
            updated_league_labels=updated_labels,
            unchanged_league_labels=unchanged_labels,
            active_season=season_active or active_season,
            historical_leagues_skipped=historical_skipped or update_historical_skipped,
            leagues_checked=leagues_checked or update_leagues_checked,
            technical_details="\n\n".join(technical_parts),
            log_paths=log_paths,
            mode="incremental",
            needs_initial_backfill=bool(post_assessment.get("needs_initial_backfill")),
            assessment=post_assessment,
            summary_lines=_build_summary_lines(
                mode="incremental",
                active_season=active_season,
                json_payload=update_out.json_payload,
                assessment=post_assessment,
            ),
            matches_downloaded=totals["downloaded"],
            players_updated=totals["players_updated"],
            metrics_imported=totals["metrics_imported"],
            errors_count=totals["errors"],
            remote_events_total=totals["remote_events"],
        )
        save_ui_state(result)
        return result
    finally:
        if LOCK_PATH.is_file():
            try:
                LOCK_PATH.unlink()
            except OSError:
                pass


# Compatibilidad con llamadas antiguas (CLI / tests)
def run_incremental_via_worker(
    *,
    league_slug: str,
    dry_run: bool,
    since: date | None = None,
    timeout_sec: int | None = None,
) -> WorkerRunOutput:
    args = ["--only", league_slug]
    if dry_run:
        args.append("--dry-run")
    if since is not None:
        args.extend(["--since", since.isoformat()])
    args.append("--json-summary")
    return _execute_worker(
        args,
        log_suffix=f"{league_slug}_{'dryrun' if dry_run else 'update'}",
        timeout_sec=timeout_sec or (600 if dry_run else 7200),
    )


def build_host_fallback_command(*, league_slug: str, dry_run: bool, since: date | None = None) -> str:
    args = ["--only", league_slug]
    if dry_run:
        args.append("--dry-run")
    if since is not None:
        args.extend(["--since", since.isoformat()])
    return command_to_string(build_worker_command(args))
