"""Consistencia de credenciales PostgreSQL en Docker Compose (sin secretos en claro)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from check_compose_db_credentials import (  # noqa: E402
    assert_password_hashes_match,
    check_compose_file,
    extract_password_hashes,
    load_compose_config,
)

COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"
EC2_COMPOSE_FILE = PROJECT_ROOT / "docker-compose.ec2.yml"


def _docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    result = subprocess.run(
        ["docker", "compose", "version"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


pytestmark = pytest.mark.skipif(not _docker_available(), reason="docker compose no disponible")


def _base_env(**overrides: str) -> dict[str, str]:
    env = os.environ.copy()
    # Evitar que variables del shell del desarrollador contaminen la prueba.
    for key in (
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "SCOUTING_USERNAME",
        "SCOUTING_PASSWORD_HASH",
        "SOFASCORE_ACTIVE_SEASON",
        "SOFASCORE_HISTORICAL_SEASON",
        "SOFASCORE_FETCH_MODE",
        "SCOUTING_DEBUG_MODE",
        "SHOW_ADMIN_TAB",
        "DISABLE_SOFASCORE_UPDATE",
        "SHOW_SYNC_TECHNICAL_DETAILS",
        "HOST_PROJECT_ROOT",
        "SCOUTING_APP_PORT",
    ):
        env.pop(key, None)
    env.update(overrides)
    return env


def test_main_compose_password_hashes_match() -> None:
    hashes = check_compose_file(COMPOSE_FILE, env=_base_env())
    assert len(set(hashes.values())) == 1


def test_ec2_compose_password_hashes_match() -> None:
    hashes = check_compose_file(EC2_COMPOSE_FILE, env=_base_env())
    assert len(set(hashes.values())) == 1


def test_shell_conflict_keeps_services_aligned(tmp_path: Path) -> None:
    """Shell y .env distintos: los tres servicios deben seguir alineados."""
    project = tmp_path / "compose-conflict"
    project.mkdir()
    compose_src = COMPOSE_FILE.read_text(encoding="utf-8")
    (project / "docker-compose.yml").write_text(compose_src, encoding="utf-8")
    (project / ".env").write_text(
        textwrap.dedent(
            """\
            DB_HOST=postgres
            DB_PORT=5432
            DB_NAME=scouting_db
            DB_USER=scouting_user
            DB_PASSWORD=valor_env
            SOFASCORE_ACTIVE_SEASON=2025
            SOFASCORE_HISTORICAL_SEASON=2024
            SCOUTING_USERNAME=admin
            SCOUTING_PASSWORD_HASH=$$2b$$12$$testhashforcomposeinterpolationonlyxx
            SCOUTING_DEBUG_MODE=0
            SHOW_ADMIN_TAB=0
            DISABLE_SOFASCORE_UPDATE=0
            SHOW_SYNC_TECHNICAL_DETAILS=0
            """
        ),
        encoding="utf-8",
    )

    env = _base_env(DB_PASSWORD="valor_shell")
    config = load_compose_config(
        project / "docker-compose.yml",
        env=env,
        project_directory=project,
    )
    hashes = extract_password_hashes(config)
    assert_password_hashes_match(hashes)

    # Confirmar valor efectivo único sin imprimirlo: ambos lados del conflicto
    # no deben producir hashes distintos entre servicios.
    app_pwd = config["services"]["app"]["environment"]["DB_PASSWORD"]
    init_pwd = config["services"]["db-init"]["environment"]["DB_PASSWORD"]
    pg_pwd = config["services"]["postgres"]["environment"]["POSTGRES_PASSWORD"]
    assert app_pwd == init_pwd == pg_pwd
    # Precedencia actual de Compose: shell > .env del proyecto.
    assert app_pwd == "valor_shell"


def test_mixed_env_file_strategy_would_be_detected() -> None:
    """Documento el fallo histórico: hashes distintos = configuración mixta."""
    with pytest.raises(AssertionError, match="Contraseñas efectivas distintas"):
        assert_password_hashes_match(
            {
                "app.DB_PASSWORD": "a" * 64,
                "db-init.DB_PASSWORD": "a" * 64,
                "postgres.POSTGRES_PASSWORD": "b" * 64,
            }
        )


def test_bcrypt_dollars_survive_compose_interpolation() -> None:
    """compose config reescapa '$' como '$$'; el valor en contenedor usa '$' simple."""
    config = load_compose_config(COMPOSE_FILE, env=_base_env())
    rendered = config["services"]["app"]["environment"]["SCOUTING_PASSWORD_HASH"]
    # Salida de `docker compose config` es round-trip-safe: $$ → $ al aplicar.
    effective = rendered.replace("$$", "$")
    assert effective.startswith("$2b$") or effective.startswith("$2a$")
    assert "$$" not in effective

    # Confirmación en contenedor (fuente de verdad para autenticación).
    env = _base_env()
    result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(COMPOSE_FILE),
            "run",
            "--rm",
            "--no-deps",
            "--entrypoint",
            "",
            "app",
            "python",
            "-c",
            (
                "import os; h=os.environ['SCOUTING_PASSWORD_HASH'];"
                "assert h.startswith('$2b$') or h.startswith('$2a$');"
                "assert '$$' not in h; print('hash-ok')"
            ),
        ],
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "hash-ok" in result.stdout


def test_ec2_dashboard_worker_runs_inside_app_with_persistent_output():
    cfg=load_compose_config(EC2_COMPOSE_FILE,env=_base_env(COMPOSE_PROFILES='worker'))
    app=cfg['services']['app']
    assert app['environment']['SOFASCORE_WORKER_MODE']=='local'
    assert app['environment']['SOFASCORE_IMPORT_MODE']=='direct'
    assert app['environment']['SOFASCORE_FETCH_MODE']=='browser'
    assert cfg['services']['sofascore-worker']['environment']['SOFASCORE_FETCH_MODE']=='browser'
    mounts={mount['target'] for mount in app['volumes']}
    assert {'/app/data','/app/web_scraping_sofascore/sofascore_output'} <= mounts
    assert '/var/run/docker.sock' not in mounts
