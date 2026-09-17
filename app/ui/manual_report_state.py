"""Estado del formulario de alta manual (reset diferido sin tocar widgets vivos)."""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Any, Mapping, MutableMapping


def attribute_slider_key(position: str, group: str, attribute: str) -> str:
    digest = hashlib.sha256(f"{position}|{group}|{attribute}".encode("utf-8")).hexdigest()[:20]
    return f"attr_{digest}"


def manual_report_widget_defaults(
    *,
    recommendation_default: str,
    preferred_foot_default: str,
) -> dict[str, Any]:
    """Valores por defecto de los widgets del alta manual (claves mr_*)."""
    return {
        "mr_player_name": "",
        "mr_current_team": "",
        "mr_nationality": "",
        "mr_scout_name": "",
        "mr_competition": "",
        "mr_match_observed": "",
        "mr_position_observed": "",
        "mr_minutes": 0,
        "mr_rating_scout": 6.0,
        "mr_strengths": "",
        "mr_weaknesses": "",
        "mr_summary": "",
        "mr_recommendation": recommendation_default,
        "mr_register_birth": False,
        "mr_preferred_foot": preferred_foot_default,
        "mr_height_cm": 0,
        "mr_video_url": "",
        "mr_alternative_positions": [],
        "mr_report_date": date.today(),
        "mr_birth_date": date(2000, 1, 1),
    }


def manual_report_attribute_keys(
    template: Mapping[str, list[str]],
    template_position: str,
) -> list[str]:
    keys: list[str] = []
    for group_name, attr_list in template.items():
        for attr in attr_list:
            keys.append(attribute_slider_key(template_position, group_name, attr))
    return keys


def apply_pending_manual_report_reset(
    session_state: MutableMapping[str, Any],
    *,
    recommendation_default: str,
    preferred_foot_default: str,
    rating_default: float,
    template_for_position: Mapping[str, list[str]] | None = None,
) -> bool:
    """
    Si hay reset pendiente, reinicializa claves mr_* y attr_* ANTES de crear widgets.
    Devuelve True si se aplicó el reset.
    """
    if not session_state.pop("manual_report_reset_pending", False):
        return False

    attr_keys = session_state.pop("manual_report_reset_attr_keys", None)
    template_position = session_state.pop("manual_report_reset_template_position", None)

    for key, value in manual_report_widget_defaults(
        recommendation_default=recommendation_default,
        preferred_foot_default=preferred_foot_default,
    ).items():
        session_state[key] = value

    if attr_keys is None and template_position and template_for_position is not None:
        attr_keys = manual_report_attribute_keys(template_for_position, str(template_position))

    for attr_key in attr_keys or []:
        session_state[attr_key] = float(rating_default)

    return True


def mark_manual_report_reset_pending(
    session_state: MutableMapping[str, Any],
    *,
    success_message: str,
    template_position: str,
    template: Mapping[str, list[str]],
) -> None:
    """Marca el formulario para limpiarse en el siguiente run (tras st.rerun)."""
    session_state["manual_report_success_message"] = success_message
    session_state["manual_report_reset_pending"] = True
    session_state["manual_report_reset_template_position"] = template_position
    session_state["manual_report_reset_attr_keys"] = manual_report_attribute_keys(
        template, template_position
    )
