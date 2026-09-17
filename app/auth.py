"""Autenticación básica de demostración (un único usuario, sin BD)."""

from __future__ import annotations

import hmac
import os

import bcrypt

SESSION_AUTHENTICATED_KEY = "auth_authenticated"


def get_auth_setup_error() -> str | None:
    """
    Devuelve un mensaje de error si falta configuración en el entorno.
    No expone valores de usuario ni hash.
    """
    missing: list[str] = []
    if not (os.environ.get("SCOUTING_USERNAME") or "").strip():
        missing.append("SCOUTING_USERNAME")
    if not (os.environ.get("SCOUTING_PASSWORD_HASH") or "").strip():
        missing.append("SCOUTING_PASSWORD_HASH")
    if not missing:
        return None
    return (
        "La autenticación no está configurada. "
        f"Define en `.env`: {', '.join(missing)}. "
        "Consulta `.env.example`."
    )


def _auth_credentials() -> tuple[str, bytes]:
    username = (os.environ.get("SCOUTING_USERNAME") or "").strip()
    password_hash_raw = (os.environ.get("SCOUTING_PASSWORD_HASH") or "").strip()
    return username, password_hash_raw.encode("utf-8")


def verify_credentials(username: str, password: str) -> bool:
    """
    Valida usuario y contraseña contra el hash bcrypt del entorno.
    No registra credenciales en logs.
    """
    if get_auth_setup_error():
        return False

    expected_user, password_hash = _auth_credentials()
    user_ok = hmac.compare_digest((username or "").strip(), expected_user)
    pwd_bytes = (password or "").encode("utf-8")

    if not user_ok:
        bcrypt.checkpw(b"\x00", password_hash)
        return False

    try:
        return bcrypt.checkpw(pwd_bytes, password_hash)
    except ValueError:
        return False


def is_authenticated(session_state: dict) -> bool:
    return bool(session_state.get(SESSION_AUTHENTICATED_KEY))


def mark_authenticated(session_state: dict) -> None:
    session_state[SESSION_AUTHENTICATED_KEY] = True


def clear_authentication(session_state: dict) -> None:
    session_state.pop(SESSION_AUTHENTICATED_KEY, None)
