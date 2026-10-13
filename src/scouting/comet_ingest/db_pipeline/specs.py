from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional
import re
import pandas as pd

# =========================
# Especificación por tabla
# =========================


@dataclass
class TableSpec:
    # Identidad de la tabla
    table: str
    # Columnas en el orden deseado (superconjunto posible)
    cols: List[str]
    # Grupos de tipado
    int_cols: List[str] = field(default_factory=list)  # a Int64 (nullable)
    float_cols: List[str] = field(default_factory=list)  # a float
    text_cols: List[str] = field(default_factory=list)  # limpiar string/NA
    bool_cols: List[str] = field(default_factory=list)  # normalizar sí/no
    tz_cols: List[str] = field(default_factory=list)  # epoch -> datetime UTC

    # Claves/Conflictos
    pk: List[str] = field(default_factory=list)  # clave(s) para ON CONFLICT
    conflict_on_constraint: Optional[str] = (
        None  # nombre de constraint única (si aplica)
    )

    # Requisitos (no nulos)
    required: List[str] = field(default_factory=list)

    # Deduplicación
    dedupe_by: List[str] = field(
        default_factory=list
    )  # clave lógica para dedupe (default pk)
    order_desc_by: List[str] = field(
        default_factory=list
    )  # ordenar desc para elegir el “más reciente”

    # Alias de columnas (fuente -> destino)
    aliases: Dict[str, str] = field(default_factory=dict)

    # Hook opcional de pre-limpieza específico por tabla
    pre_clean: Optional[Callable[[pd.DataFrame], pd.DataFrame]] = None


# ---------- Hooks específicos ----------


def _competiciones_preclean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Corregir categorías basándose en el nombre de la competición.
    Problema: COMET agrupa Sub-18 y Sub-20 en U-19.
    Solución: Extraer la edad real del nombre (ej. "Sub 18", "U-20").
    """
    def _fix_category(row):
        name = str(row.get("name", ""))
        # Regex para buscar U-XX o Sub-XX o Sub XX
        # Case insensitive
        # Matches: "Sub 18", "Sub-18", "U18", "U-18", "U 18"
        match = re.search(r'\b(?:Sub|U)[\s-]*(\d{2})\b', name, re.IGNORECASE)
        
        if match:
            age = match.group(1)
            # Mapeamos explícitamente a U-XX
            return f"U-{age}"
        
        # Si no tiene Sub X y es Seniores, lo cambiamos a Primer Equipo
        current_cat = row.get("category")
        if current_cat == "Seniores":
            return "Primer Equipo"

        return current_cat

    if "category" not in df.columns:
        return df

    # Aplicamos la corrección fila por fila
    df["category"] = df.apply(_fix_category, axis=1)
    return df



def _equipos_preclean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pre-limpieza específica de 'equipos':
    - Asegura 'club' (fallback a 'clubLongName')
    - Elige por clubId el registro "más completo" (longitud de campos)
    """
    if "club" in df.columns and "clubLongName" in df.columns:
        df["club"] = df["club"].fillna(df["clubLongName"])
    if "club" in df.columns:
        df = df[~df["club"].isna()].copy()

    for c in ("clubLongName", "club", "place"):
        if c not in df.columns:
            df[c] = pd.NA
    df["_len_long"] = df["clubLongName"].astype("string").str.len().fillna(-1)
    df["_len_club"] = df["club"].astype("string").str.len().fillna(-1)
    df["_len_place"] = df["place"].astype("string").str.len().fillna(-1)
    df = (
        df.sort_values(
            ["_len_long", "_len_club", "_len_place"], ascending=[False, False, False]
        )
        .drop_duplicates(subset=["clubId"], keep="first")
        .drop(columns=["_len_long", "_len_club", "_len_place"])
        .copy()
    )
    return df


# ---------- Definición de SPECS ----------

SPECS: Dict[str, TableSpec] = {
    "competiciones": TableSpec(
        table="competiciones",
        cols=[
            "id",
            "parentCompetitionId",
            "name",
            "season",
            "category",
            "rank",
            "competitionType",
            "system",
            "status",
            "allocationInitialStatusMatch",
            "matchLength",
            "maxPlayers",
            "playersOnTheField",
            "maxSubstitutions",
            "playerMaxAge",
            "playerMinAge",
            "maxForeignersRegistered",
            "maxForeignersSquad",
            "maxForeignersField",
            "tableRules",
            "numberOfClubs",
            "competitionTypeId",
            "penaltyShootoutShort",
            "extraTimeShort",
            "catalogueRestriction",
            "lastupdateddatetime",
            "gender",
        ],
        int_cols=[
            "id",
            "parentCompetitionId",
            "matchLength",
            "maxPlayers",
            "playersOnTheField",
            "maxSubstitutions",
            "playerMaxAge",
            "playerMinAge",
            "maxForeignersRegistered",
            "maxForeignersSquad",
            "maxForeignersField",
            "numberOfClubs",
            "competitionTypeId",
        ],
        text_cols=[
            "name",
            "season",
            "category",
            "competitionType",
            "system",
            "status",
            "allocationInitialStatusMatch",
            "tableRules",
            "catalogueRestriction",
            "gender",
        ],
        bool_cols=["rank", "penaltyShootoutShort", "extraTimeShort"],
        tz_cols=["lastupdateddatetime"],
        pk=["id"],
        required=["id", "name"],
        pre_clean=_competiciones_preclean,
    ),
    "equipos": TableSpec(
        table="equipos",
        cols=["clubId", "club", "clubLongName", "place"],
        int_cols=["clubId"],
        text_cols=["club", "clubLongName", "place"],
        pk=["clubId"],
        required=["clubId", "club"],
        pre_clean=_equipos_preclean,
    ),
    "competidores": TableSpec(
        table="competidores",
        cols=[
            "uid",
            "id",
            "clubId",
            "season",
            "gender",
            "status",
            "lastupdateddatetime",
        ],
        int_cols=["uid", "id", "clubId"],
        text_cols=["season", "gender", "status"],
        tz_cols=["lastupdateddatetime"],
        required=["uid", "id", "clubId"],
        conflict_on_constraint="uq_competidores_id_club",
        pk=["id", "clubId"],  # PostgREST necesita las columnas, no el nombre del constraint.
        dedupe_by=["id", "clubId"],
        order_desc_by=["lastupdateddatetime", "uid"],
    ),
    "partidos": TableSpec(
        table="partidos",
        cols=[
            "matchId",
            "id",
            "homeTeam",
            "awayTeam",
            "matchDate",
            "matchType",
            "matchStatus",
            "inStatusSince",
            "liveStatus",
            "homeTeamStatus",
            "homeTeamInStatusSince",
            "awayTeamStatus",
            "awayTeamInStatusSince",
            "round",
            "facilityId",
            "country",
            "facility",
            "facilityPlaceName",
            "facilityRegionName",
            "attendance",
            "matchNumber",
            "status",
            "lastupdateddatetime",
            "matchSummary",
            "season",
        ],
        int_cols=[
            "matchId",
            "id",
            "homeTeam",
            "awayTeam",
            "round",
            "facilityId",
            "attendance",
            "matchNumber",
        ],
        text_cols=[
            "matchType",
            "matchStatus",
            "liveStatus",
            "homeTeamStatus",
            "awayTeamStatus",
            "country",
            "facility",
            "facilityPlaceName",
            "facilityRegionName",
            "status",
            "matchSummary",
            "season",
        ],
        tz_cols=[
            "matchDate",
            "inStatusSince",
            "homeTeamInStatusSince",
            "awayTeamInStatusSince",
            "lastupdateddatetime",
        ],
        pk=["matchId"],
        required=["matchId", "id", "homeTeam", "awayTeam"],
        dedupe_by=["matchId"],
        order_desc_by=["lastupdateddatetime"],
    ),
    "posiciones": TableSpec(
        table="posiciones",
        cols=[
            "id",
            "season",
            "clubId",
            "position",
            "matches",
            "wins",
            "draws",
            "losses",
            "points",
            "negativePoints",
            "goalsFor",
            "goalsAgainst",
            "goalDifference",
            "winsAfterExtraTime",
            "drawsAfterExtraTime",
            "lossesAfterExtraTime",
            "winsAfterPenalties",
            "lossesAfterPenalties",
            "status",
        ],
        int_cols=[
            "id",
            "clubId",
            "position",
            "matches",
            "wins",
            "draws",
            "losses",
            "points",
            "negativePoints",
            "goalsFor",
            "goalsAgainst",
            "goalDifference",
            "winsAfterExtraTime",
            "drawsAfterExtraTime",
            "lossesAfterExtraTime",
            "winsAfterPenalties",
            "lossesAfterPenalties",
        ],
        text_cols=["season", "status"],
        pk=["id", "season", "clubId"],
        required=["id", "season", "clubId"],
        dedupe_by=["id", "season", "clubId"],
    ),
    "jugadores": TableSpec(
        table="jugadores",
        cols=[
            "personId",
            "registrationID",
            "fifaFirstProRegId",
            "fifaid",
            "firstName",
            "lastName",
            "displayName",
            "dateOfBirth",
            "gender",
            "nationality",
            "countryOfBirth",
            "country",
            "titlePlayer",
            "notes",
            "height",
            "weight",
            "passportNumber",
            "orgName",
            "level",
            "reregistrationMarked",
            "dateFrom",
            "inStatusSince",
            "registrationType",
            "intCategory",
            "status",
            "photo",
            "dateTo",
            "lastupdateddatetime",
        ],
        int_cols=["personId", "registrationID", "intCategory"],
        float_cols=["height", "weight"],
        text_cols=[
            "fifaFirstProRegId",
            "fifaid",
            "firstName",
            "lastName",
            "displayName",
            "gender",
            "nationality",
            "countryOfBirth",
            "country",
            "titlePlayer",
            "notes",
            "passportNumber",
            "orgName",
            "level",
            "registrationType",
            "status",
            "photo",
        ],
        bool_cols=["reregistrationMarked"],
        tz_cols=[
            "dateOfBirth",
            "dateFrom",
            "inStatusSince",
            "dateTo",
            "lastupdateddatetime",
        ],
        pk=["personId"],
        required=["personId"],
        dedupe_by=["personId"],
        order_desc_by=["lastupdateddatetime"],
    ),
    "partidos_fases": TableSpec(
        table="partidos_fases",
        cols=[
            "uid",
            "id",
            "matchId",
            "phase",
            "homeResult",
            "awayResult",
            "startTime",
            "endTime",
            "startTimeLocal",
            "endTimeLocal",
            "timezoneLocal",
            "regularTimeShort",
            "stoppageTimeShort",
            "lastupdateddatetime",
        ],
        int_cols=[
            "uid",
            "id",
            "matchId",
            "homeResult",
            "awayResult",
            "regularTimeShort",
            "stoppageTimeShort",
        ],
        text_cols=["phase", "timezoneLocal"],
        tz_cols=[
            "startTime",
            "endTime",
            "startTimeLocal",
            "endTimeLocal",
            "lastupdateddatetime",
        ],
        pk=["uid"],
        required=["uid", "id", "matchId"],
        dedupe_by=["uid"],
        order_desc_by=["lastupdateddatetime"],
    ),
    "eventos_partido": TableSpec(
        table="eventos_partido",
        cols=[
            "uid",
            "id",
            "matchId",
            "teamId",
            "personId",
            "secondPersonId",
            "minute",
            "displayMinute",
            "phase",
            "registrationType",
            "matchEventType",
            "eventSubType",
            "accumulatedYellow",
            "secondYellowCard",
            "stoppageTime",
            "home",
            "lastupdateddatetime",
        ],
        int_cols=[
            "uid",
            "id",
            "matchId",
            "teamId",
            "personId",
            "secondPersonId",
            "minute",
            "stoppageTime",
        ],
        text_cols=[
            "displayMinute",
            "phase",
            "registrationType",
            "matchEventType",
            "eventSubType",
            "accumulatedYellow",
        ],
        bool_cols=["secondYellowCard", "home"],
        tz_cols=["lastupdateddatetime"],
        pk=["uid"],
        required=["uid", "id", "matchId", "teamId"],
        dedupe_by=["uid"],
        order_desc_by=["lastupdateddatetime"],
    ),
    "partidos_cambios_estado": TableSpec(
        table="partidos_cambios_estado",
        cols=[
            "uid",
            "matchId",
            "minutesToStart",
            "transitionDateTime",
            "transitionStatus",
            "lastupdateddatetime",
        ],
        int_cols=["uid", "matchId", "minutesToStart"],
        text_cols=["transitionStatus"],
        tz_cols=["transitionDateTime", "lastupdateddatetime"],
        pk=["uid"],
        required=["uid", "matchId"],
        dedupe_by=["uid"],
        order_desc_by=["lastupdateddatetime"],
    ),
    "partidos_cambios_estado_equipo": TableSpec(
        table="partidos_cambios_estado_equipo",
        cols=[
            "uid",
            "matchId",
            "teamId",
            "transitionNotes",
            "inStatusSince",
            "minutesToStart",
            "transitionDateTime",
            "transitionStatus",
        ],
        int_cols=["uid", "matchId", "teamId", "minutesToStart"],
        text_cols=["transitionNotes", "transitionStatus"],
        tz_cols=["inStatusSince", "transitionDateTime"],
        pk=["uid"],
        required=["uid", "matchId", "teamId"],
        dedupe_by=["uid"],
        order_desc_by=["transitionDateTime", "inStatusSince"],
    ),
    "actuaciones_jugadores": TableSpec(
        table="actuaciones_jugadores",
        cols=[
            "uid",
            "personId",
            "registrationId",
            "clubId",
            "id",
            "matchId",
            "startingLineup",
            "played",
            "minutesPlayed",
            "goalkeeper",
            "captain",
            "singleYellow",
            "secondYellow",
            "redCards",
            "result",
            "goals",
            "ownGoals",
            "home",
            "shirtNumber",
            "lastupdateddatetime",
        ],
        aliases={"registrationID": "registrationId"},
        int_cols=[
            "uid",
            "personId",
            "registrationId",
            "clubId",
            "id",
            "matchId",
            "minutesPlayed",
            "goals",
            "ownGoals",
        ],
        text_cols=["result", "shirtNumber"],
        bool_cols=[
            "startingLineup",
            "played",
            "goalkeeper",
            "captain",
            "singleYellow",
            "secondYellow",
            "redCards",
            "home",
        ],
        tz_cols=["lastupdateddatetime"],
        pk=["uid"],
        required=["uid", "personId", "clubId", "id", "matchId"],
        dedupe_by=["uid"],
        order_desc_by=["lastupdateddatetime"],
    ),
    "actuaciones_arqueros": TableSpec(
        table="actuaciones_arqueros",
        cols=[
            "uid",
            "personId",
            "registrationId",
            "clubId",
            "id",
            "matchId",
            "startingLineup",
            "played",
            "minutesPlayed",
            "goalsConceded",
            "goals",
            "ownGoals",
            "singleYellow",
            "secondYellow",
            "redCards",
            "captain",
            "result",
            "shirtNumber",
            "home",
            "lastupdateddatetime",
        ],
        aliases={"registrationID": "registrationId"},
        int_cols=[
            "uid",
            "personId",
            "registrationId",
            "clubId",
            "id",
            "matchId",
            "minutesPlayed",
            "goalsConceded",
            "goals",
            "ownGoals",
        ],
        text_cols=["result", "shirtNumber"],
        bool_cols=[
            "startingLineup",
            "played",
            "singleYellow",
            "secondYellow",
            "redCards",
            "captain",
            "home",
        ],
        tz_cols=["lastupdateddatetime"],
        pk=["uid"],
        required=["uid", "personId", "clubId", "id", "matchId"],
        dedupe_by=["uid"],
        order_desc_by=["lastupdateddatetime"],
    ),
}
