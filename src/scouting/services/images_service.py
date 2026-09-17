"""Guardado y resolución de rutas de imágenes de jugadores (ficheros en disco)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

ALLOWED_EXTENSIONS = frozenset({"png", "jpg", "jpeg", "webp"})
# Extensiones adicionales solo para visualización (p. ej. demo .avif referenciada en BD).
DISPLAY_EXTENSIONS = frozenset(ALLOWED_EXTENSIONS | {"avif", "gif"})


def project_root() -> Path:
    """Raíz del repo (contiene `data/`). Válido en local y Docker (/app)."""
    return Path(__file__).resolve().parent.parent.parent.parent


PLAYERS_IMAGES_REL_DIR = "data/images/players"
LEGACY_PLAYER_IMAGES_REL_DIR = "data/player_images"


def player_images_dir() -> Path:
    """Directorio canónico para fotos de jugador (nuevas subidas)."""
    d = project_root() / PLAYERS_IMAGES_REL_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_filename_part(normalized_name: str) -> str:
    s = normalized_name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "jugador"


def save_player_image(uploaded_file: Any, player_id: int, normalized_name: str) -> str:
    """
    Guarda el fichero subido en data/images/players/ y devuelve ruta relativa para BD.

    `uploaded_file` es un UploadedFile de Streamlit (name, getvalue()).
    """
    if uploaded_file is None:
        raise ValueError("uploaded_file is required")

    original_name = getattr(uploaded_file, "name", None) or "image.png"
    ext = Path(original_name).suffix.lower().lstrip(".")
    if ext == "jpeg":
        ext = "jpg"
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValueError(f"Formato no permitido. Usa: {allowed}")

    safe = _safe_filename_part(normalized_name)
    filename = f"player_{player_id}_{safe}.{ext}"
    dest = player_images_dir() / filename
    data = uploaded_file.getvalue()
    if not data:
        raise ValueError("El fichero de imagen está vacío")

    dest.write_bytes(data)
    return f"{PLAYERS_IMAGES_REL_DIR}/{filename}"


def resolve_image_path(relative_path: str | None) -> Path | None:
    """Convierte ruta relativa de BD a Path absoluto si el fichero existe."""
    if not relative_path or not str(relative_path).strip():
        return None
    rel = str(relative_path).strip().replace("\\", "/")
    candidates: list[Path] = []
    if rel.startswith("/"):
        candidates.append(Path(rel))
    else:
        root = project_root()
        candidates.append(root / rel)
        # Compatibilidad: rutas antiguas en BD bajo data/player_images/
        if rel.startswith(LEGACY_PLAYER_IMAGES_REL_DIR + "/"):
            name = rel.split("/", maxsplit=2)[-1]
            candidates.append(root / PLAYERS_IMAGES_REL_DIR / name)
    for p in candidates:
        if p.is_file():
            return p
    return None


def get_player_image_path(player: dict[str, Any]) -> Path | None:
    """Path absoluto de la imagen del jugador, o None."""
    return resolve_image_path(player.get("image_path"))


def player_image_exists(player: dict[str, Any]) -> bool:
    p = get_player_image_path(player)
    return p is not None and p.is_file()
