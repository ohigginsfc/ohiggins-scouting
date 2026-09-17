"""Manual Sofascore ↔ scouted player matching."""

from __future__ import annotations

from typing import Any

from psycopg import Connection

from scouting.repositories import matching_repository
from scouting.services.players_service import normalize_player_name

# Posición de ficha → grupo grueso Sofascore (G/D/M/F)
FICHA_TO_COARSE: dict[str, str] = {
    "portero": "G",
    "central derecho": "D",
    "central izquierdo": "D",
    "lateral derecho": "D",
    "lateral izquierdo": "D",
    "mediocentro defensivo": "M",
    "mediocentro": "M",
    "mediocentro ofensivo": "M",
    "extremo derecho": "F",
    "extremo izquierdo": "F",
    "delantero": "F",
}


def coarse_position_from_ficha(position: str | None) -> str | None:
    if not position or not str(position).strip():
        return None
    return FICHA_TO_COARSE.get(str(position).strip().lower())


def _name_tokens(normalized: str) -> list[str]:
    return [t for t in normalized.split() if len(t) >= 2]


def _names_match(scouted_norm: str, candidate_norm: str) -> bool:
    if not scouted_norm or not candidate_norm:
        return False
    if scouted_norm == candidate_norm:
        return True
    s_tokens = _name_tokens(scouted_norm)
    c_tokens = _name_tokens(candidate_norm)
    if not s_tokens or not c_tokens:
        return False
    # Apellido o nombre principal: algún token del scouteado en el candidato (o viceversa)
    for t in s_tokens:
        if t in candidate_norm:
            return True
    for t in c_tokens:
        if t in scouted_norm:
            return True
    return False


def _team_match(scouted_team: str | None, candidate_team: str | None) -> bool:
    if not scouted_team or not candidate_team:
        return True
    a = str(scouted_team).strip().lower()
    b = str(candidate_team).strip().lower()
    if not a or not b:
        return True
    return a in b or b in a


def _nationality_match(scouted_nat: str | None, candidate_nat: str | None) -> bool:
    if not scouted_nat or not candidate_nat:
        return True
    return str(scouted_nat).strip().lower() == str(candidate_nat).strip().lower()


def _position_coarse_match(scouted_pos: str | None, candidate_pos: str | None) -> bool:
    coarse_s = coarse_position_from_ficha(scouted_pos)
    if not coarse_s:
        return True
    coarse_c = coarse_position_from_ficha(candidate_pos)
    if not coarse_c:
        # Candidato puede tener posición Sofascore en ficha ya mapeada
        return True
    return coarse_s == coarse_c


def get_scouted_players_without_sofascore_match(conn: Connection) -> list[dict[str, Any]]:
    return matching_repository.get_scouted_players_without_sofascore_match(conn)


def find_sofascore_candidates_for_player(
    conn: Connection,
    player_id: int,
    *,
    filter_by_team: bool = False,
    filter_by_nationality: bool = False,
    filter_by_position: bool = False,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Candidatos Sofascore con matching determinista por nombre (+ filtros opcionales).
    """
    scouted = matching_repository.get_player_row(conn, player_id)
    if not scouted:
        return []

    scouted_norm = str(scouted.get("normalized_name") or normalize_player_name(scouted.get("full_name") or ""))

    pool = matching_repository.get_sofascore_candidate_pool(conn, exclude_player_id=player_id)
    matched: list[dict[str, Any]] = []

    for row in pool:
        cand_norm = str(row.get("normalized_name") or normalize_player_name(row.get("full_name") or ""))
        if not _names_match(scouted_norm, cand_norm):
            continue
        if filter_by_team and not _team_match(scouted.get("current_team"), row.get("current_team")):
            continue
        if filter_by_nationality and not _nationality_match(
            scouted.get("nationality"), row.get("nationality")
        ):
            continue
        if filter_by_position and not _position_coarse_match(
            scouted.get("position"), row.get("position")
        ):
            continue

        cid = int(row["candidate_player_id"])
        extras = matching_repository.get_candidate_metric_extras(conn, cid)
        matched.append(
            {
                **row,
                "competitions": ", ".join(extras["competitions"]) if extras["competitions"] else "—",
                "minutes_played": extras["minutes_played"],
                "avg_rating": extras["avg_rating"],
                "match_reason": "normalized_name" if scouted_norm == cand_norm else "name_token",
            }
        )
        if len(matched) >= limit:
            break

    # Orden: exact name primero, luego por minutos
    def sort_key(r: dict[str, Any]) -> tuple:
        exact = 0 if r.get("match_reason") == "normalized_name" else 1
        mins = r.get("minutes_played")
        try:
            mins_f = -float(mins) if mins is not None else 0.0
        except (TypeError, ValueError):
            mins_f = 0.0
        return (exact, mins_f)

    matched.sort(key=sort_key)
    return matched


def get_merge_preview(
    conn: Connection,
    scouted_player_id: int,
    candidate_player_id: int,
) -> dict[str, Any]:
    scouted = matching_repository.get_player_row(conn, scouted_player_id)
    candidate = matching_repository.get_player_row(conn, candidate_player_id)
    if not scouted or not candidate:
        raise ValueError("Jugador scouteado o candidato no encontrado.")

    return {
        "scouted": scouted,
        "candidate": candidate,
        "metrics_to_move": matching_repository.count_sofascore_metrics_for_player(
            conn, candidate_player_id
        ),
        "external_ids": matching_repository.get_sofascore_external_ids_for_player(
            conn, candidate_player_id
        ),
        "scouted_has_external": matching_repository.scouted_player_has_sofascore_external(
            conn, scouted_player_id
        ),
    }


def merge_sofascore_candidate_into_scouted_player(
    conn: Connection,
    scouted_player_id: int,
    candidate_player_id: int,
) -> dict[str, int]:
    return matching_repository.merge_sofascore_candidate_into_scouted_player(
        conn, scouted_player_id, candidate_player_id
    )
