"""Tema claro forzado: config.toml + CSS sin herencia de modo oscuro del SO."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_TOML = PROJECT_ROOT / ".streamlit" / "config.toml"
DOCKERIGNORE = PROJECT_ROOT / ".dockerignore"
GITIGNORE = PROJECT_ROOT / ".gitignore"
STYLES = PROJECT_ROOT / "app" / "ui" / "styles.py"
THEME_CSS = PROJECT_ROOT / "app" / "ui" / "theme_css.py"
DOCKERFILE = PROJECT_ROOT / "Dockerfile"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_streamlit_config_toml_exists() -> None:
    assert CONFIG_TOML.is_file()


def test_streamlit_theme_base_is_light() -> None:
    text = _read(CONFIG_TOML)
    assert re.search(r'(?m)^base\s*=\s*"light"\s*$', text)
    assert 'base = "auto"' not in text
    assert 'base = "dark"' not in text


def test_streamlit_theme_colors_are_light() -> None:
    text = _read(CONFIG_TOML)
    assert 'backgroundColor = "#eaf2fb"' in text
    assert 'secondaryBackgroundColor = "#ffffff"' in text
    assert 'textColor = "#111827"' in text


def test_no_prefers_color_scheme_dark_in_ui() -> None:
    for path in (STYLES, THEME_CSS):
        content = _read(path).lower()
        assert "prefers-color-scheme: dark" not in content
        assert "prefers-color-scheme:dark" not in content


def test_inputs_force_white_bg_and_dark_text() -> None:
    css = _read(STYLES)
    assert "background-color: #ffffff" in css
    assert "color: #111827" in css
    assert "-webkit-text-fill-color: #111827" in css
    assert "caret-color: #111827" in css
    assert "#6b7280" in css  # placeholder


def test_password_autofill_uses_webkit_text_fill() -> None:
    styles = _read(STYLES)
    login = _read(THEME_CSS)
    assert "input:-webkit-autofill" in styles
    assert "-webkit-text-fill-color: #111827" in styles
    assert "input:-webkit-autofill" in login
    assert "-webkit-text-fill-color: #111827" in login


def test_nav_unselected_white_selected_not_black() -> None:
    css = _read(STYLES)
    assert "st-key-nav_" in css
    assert "background-color: #ffffff !important" in css
    assert "background-color: #ff4b4b !important" in css
    # La regla primary de navegación no usa fondo negro
    primary_idx = css.find(
        '[class*="st-key-nav_"] .stButton > button[data-testid="baseButton-primary"] {'
    )
    assert primary_idx != -1
    block = css[primary_idx : primary_idx + 500].lower()
    assert "background-color: #ff4b4b" in block
    assert "background-color: #000" not in block
    assert "background: #000" not in block
    assert "background: black" not in block


def test_nav_defines_hover_focus_active_disabled() -> None:
    css = _read(STYLES)
    assert 'st-key-nav_' in css
    for needle in (
        '[class*="st-key-nav_"] .stButton > button:hover',
        '[class*="st-key-nav_"] .stButton > button:focus',
        '[class*="st-key-nav_"] .stButton > button:active',
        '[class*="st-key-nav_"] .stButton > button:disabled',
    ):
        assert needle in css


def test_tables_have_light_bg_and_dark_text() -> None:
    css = _read(STYLES)
    assert 'data-testid="stDataFrame"' in css
    assert "background: #ffffff !important" in css or "background-color: #ffffff !important" in css
    assert "color: #111827 !important" in css
    assert "color-scheme: light" in css


def test_gitignore_does_not_exclude_config_toml() -> None:
    text = _read(GITIGNORE)
    assert ".streamlit/config.toml" not in text
    # secrets sí pueden ignorarse
    assert ".streamlit/secrets.toml" in text


def test_dockerignore_does_not_exclude_streamlit_config() -> None:
    if not DOCKERIGNORE.is_file():
        pytest.skip(".dockerignore ausente")
    text = _read(DOCKERIGNORE)
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        assert stripped not in {".streamlit", ".streamlit/", ".streamlit/**", ".streamlit/config.toml"}
        assert not stripped.startswith(".streamlit/") or "secrets" in stripped


def test_dockerfile_copies_project_including_streamlit() -> None:
    text = _read(DOCKERFILE)
    assert "COPY . ." in text
    # No forzar STREAMLIT_THEME_* que pueda diverger de config.toml
    assert "STREAMLIT_THEME_" not in text


def test_color_scheme_light_forced() -> None:
    assert "color-scheme: light" in _read(STYLES)
    assert "color-scheme: light" in _read(THEME_CSS)


def test_no_global_button_selector_in_forced_styles() -> None:
    """Evitar `button { ... }` genérico que rompa formularios."""
    css = _read(STYLES)
    # Extraer solo bloques de navegación y comprobar que usamos keys
    assert ".stApp [class*=\"st-key-nav_\"] .stButton > button" in css
    assert not re.search(r"(?m)^\s*button\s*\{", css)
