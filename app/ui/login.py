"""Pantalla de inicio de sesión (demo)."""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

from auth import mark_authenticated, verify_credentials
from ui.theme_css import build_login_css


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _crest_path() -> Path:
    return _project_root() / "data" / "images" / "escudo.png"


def _sport_logo_path() -> Path:
    return _project_root() / "data" / "images" / "sport.png"


def _img_data_uri(path: Path) -> str | None:
    if not path.is_file():
        return None
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _login_card_header_html() -> str:
    sport_uri = _img_data_uri(_sport_logo_path())
    crest_uri = _img_data_uri(_crest_path())

    logos: list[str] = []
    if sport_uri:
        logos.append(
            f'<img src="{sport_uri}" class="scouting-login-sport-logo" alt="Sport logo">'
        )
    if crest_uri:
        logos.append(
            f'<img src="{crest_uri}" class="scouting-login-crest" alt="Escudo O\'Higgins">'
        )

    logos_html = ""
    if logos:
        logos_html = (
            '<div class="scouting-login-logos">' + "".join(logos) + "</div>"
        )

    return (
        '<div class="scouting-login-header">'
        f"{logos_html}"
        '<h1 class="scouting-login-title">Scouting Platform</h1>'
        '<p class="scouting-login-subtitle">Digital Scouting &amp; Player Analysis</p>'
        "</div>"
    )


def render_login_page() -> None:
    """Muestra el formulario de acceso y detiene el resto de la app."""
    st.markdown(build_login_css(), unsafe_allow_html=True)
    # Marcador de página (oculto): permite acotar CSS al login sin crear una tarjeta.
    st.markdown('<div class="scouting-login-page"></div>', unsafe_allow_html=True)

    _left, center, _right = st.columns([1, 1.15, 1])
    with center:
        # La tarjeta visual es el propio st.form (clase st-key-login_form).
        # No usar div HTML abierto/cerrado alrededor de widgets Streamlit.
        with st.form("login_form", clear_on_submit=False):
            st.markdown(_login_card_header_html(), unsafe_allow_html=True)

            auth_error = st.session_state.pop("login_auth_error", None)
            if auth_error:
                st.markdown(
                    f'<p class="scouting-login-error">{auth_error}</p>',
                    unsafe_allow_html=True,
                )

            username = st.text_input(
                "Usuario",
                placeholder="admin",
                autocomplete="username",
            )
            password = st.text_input(
                "Contraseña",
                type="password",
                placeholder="••••••••",
                autocomplete="current-password",
            )
            submitted = st.form_submit_button(
                "Iniciar sesión",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            if verify_credentials(username, password):
                st.session_state.pop("login_auth_error", None)
                mark_authenticated(st.session_state)
                st.rerun()
            else:
                st.session_state["login_auth_error"] = (
                    "Usuario o contraseña incorrectos."
                )
                st.rerun()
