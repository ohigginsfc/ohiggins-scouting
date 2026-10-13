"""Cálculos del reporte por categoría, trasladados del importador anterior."""
from __future__ import annotations
from typing import Optional, Dict
import pandas as pd

def _normalize_season(season) -> Optional[str]:
    if season is None:
        return None
    season_str = str(season).strip()
    return season_str if season_str else None


def _fetch_supabase_table(
    supabase_client, table: str, columns: str, page_size: int = 1000
) -> pd.DataFrame:
    rows = []
    offset = 0
    while True:
        response = (
            supabase_client.table(table)
            .select(columns)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = getattr(response, "data", None) or []
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return pd.DataFrame(rows)


def get_club_id(supabase_client, club_name: str) -> Optional[int]:
    df_equipos = _fetch_supabase_table(
        supabase_client, table="equipos", columns="clubid,club,clublongname"
    )
    if df_equipos.empty:
        return None

    q = str(club_name).strip().lower()
    if not q:
        return None

    club = df_equipos.get("club", pd.Series("", index=df_equipos.index)).astype(str)
    club_long = df_equipos.get("clublongname", pd.Series("", index=df_equipos.index)).astype(str)

    mask_exact = (club.str.lower() == q) | (club_long.str.lower() == q)
    candidates = df_equipos[mask_exact].copy()
    if candidates.empty:
        mask_like = club.str.lower().str.contains(q, na=False, regex=False) | club_long.str.lower().str.contains(
            q, na=False, regex=False
        )
        candidates = df_equipos[mask_like].copy()

    if candidates.empty or "clubid" not in candidates.columns:
        return None

    clubid_series = pd.to_numeric(candidates["clubid"], errors="coerce").dropna()
    if clubid_series.empty:
        return None
    return int(clubid_series.iloc[0])


def parse_category_age_limit(
    category: Optional[str], max_age: Optional[float]
) -> Optional[int]:

    if not category:
        return None

    cat = str(category).upper().strip()

    if cat in {"PRIMER EQUIPO", "SENIORES", "ADULTOS", "PRIMERA"}:
        return None

    if cat.startswith("U-"):
        try:
            return int(cat.split("-")[1])
        except Exception:
            return None
    if cat.startswith("U"):
        try:
            return int(cat[1:])
        except Exception:
            pass

    if max_age is not None and not pd.isna(max_age):
        try:
            age_val = int(max_age)
            if 8 <= age_val <= 25:
                return age_val
        except Exception:
            pass

    return None


def load_base_data(
    supabase_client, club_id: Optional[int] = None, season: Optional[str] = None
) -> Dict[str, pd.DataFrame]:
    season_norm = _normalize_season(season)

    df_jugadores = _fetch_supabase_table(
        supabase_client,
        table="jugadores",
        columns=(
            "personid,firstname,lastname,displayname,dateofbirth,gender,"
            "nationality,country,height,weight,datefrom"
        ),
    )

    df_competiciones = _fetch_supabase_table(
        supabase_client,
        table="competiciones",
        columns="id,name,season,category,matchlength,playermaxage,playerminage",
    )
    if df_competiciones.empty:
        df_competiciones = pd.DataFrame(
            columns=[
                "competition_id",
                "name",
                "season",
                "category",
                "matchlength",
                "playermaxage",
                "playerminage",
            ]
        )
    else:
        df_competiciones = df_competiciones.rename(columns={"id": "competition_id"})
        df_competiciones["competition_id"] = pd.to_numeric(
            df_competiciones["competition_id"], errors="coerce"
        ).astype("Int64")
        if season_norm is not None and "season" in df_competiciones.columns:
            df_competiciones = df_competiciones[
                df_competiciones["season"].astype("string").str.strip() == season_norm
            ].copy()

    valid_comp_ids = set(
        pd.to_numeric(
            df_competiciones.get("competition_id", pd.Series(dtype="float")),
            errors="coerce",
        )
        .dropna()
        .astype(int)
        .tolist()
    )
    season_filter_active = season_norm is not None

    df_partidos = _fetch_supabase_table(
        supabase_client,
        table="partidos",
        columns="matchid,id,hometeam,awayteam,matchdate,matchstatus",
    )
    if df_partidos.empty:
        df_partidos = pd.DataFrame(
            columns=["matchid", "competition_id", "home_team", "away_team", "match_date", "matchstatus"]
        )
    else:
        df_partidos = df_partidos.rename(
            columns={
                "id": "competition_id",
                "hometeam": "home_team",
                "awayteam": "away_team",
                "matchdate": "match_date",
            }
        )
        df_partidos["competition_id"] = pd.to_numeric(
            df_partidos["competition_id"], errors="coerce"
        ).astype("Int64")
        if season_filter_active:
            if valid_comp_ids:
                df_partidos = df_partidos[
                    df_partidos["competition_id"].isin(valid_comp_ids)
                ].copy()
            else:
                df_partidos = df_partidos.iloc[0:0].copy()

    df_act = _fetch_supabase_table(
        supabase_client,
        table="actuaciones_jugadores",
        columns=(
            "personid,clubid,id,matchid,startinglineup,played,minutesplayed,"
            "singleyellow,secondyellow,redcards,result,goals,home"
        ),
    )
    if df_act.empty:
        df_act = pd.DataFrame(
            columns=[
                "personid",
                "clubid",
                "competition_id",
                "matchid",
                "startinglineup",
                "played",
                "minutesplayed",
                "singleyellow",
                "secondyellow",
                "redcards",
                "result",
                "goals",
                "home",
            ]
        )
    else:
        df_act = df_act.rename(columns={"id": "competition_id"})
        df_act["competition_id"] = pd.to_numeric(
            df_act["competition_id"], errors="coerce"
        ).astype("Int64")
        if season_filter_active:
            if valid_comp_ids:
                df_act = df_act[df_act["competition_id"].isin(valid_comp_ids)].copy()
            else:
                df_act = df_act.iloc[0:0].copy()
        if club_id is not None:
            df_act["clubid"] = pd.to_numeric(df_act["clubid"], errors="coerce").astype("Int64")
            df_act = df_act[df_act["clubid"] == int(club_id)].copy()

    df_arq = _fetch_supabase_table(
        supabase_client,
        table="actuaciones_arqueros",
        columns=(
            "personid,clubid,id,matchid,startinglineup,played,minutesplayed,"
            "goalsconceded,goals"
        ),
    )
    if df_arq.empty:
        df_arq = pd.DataFrame(
            columns=[
                "personid",
                "clubid",
                "competition_id",
                "matchid",
                "startinglineup",
                "played",
                "minutesplayed",
                "goalsconceded",
                "goals",
            ]
        )
    else:
        df_arq = df_arq.rename(columns={"id": "competition_id"})
        df_arq["competition_id"] = pd.to_numeric(
            df_arq["competition_id"], errors="coerce"
        ).astype("Int64")
        if season_filter_active:
            if valid_comp_ids:
                df_arq = df_arq[df_arq["competition_id"].isin(valid_comp_ids)].copy()
            else:
                df_arq = df_arq.iloc[0:0].copy()
        if club_id is not None:
            df_arq["clubid"] = pd.to_numeric(df_arq["clubid"], errors="coerce").astype("Int64")
            df_arq = df_arq[df_arq["clubid"] == int(club_id)].copy()

    return {
        "jugadores": df_jugadores,
        "competiciones": df_competiciones,
        "partidos": df_partidos,
        "actuaciones": df_act,
        "arqueros": df_arq,
    }


def compute_age(dob_series: pd.Series) -> pd.Series:
    today = pd.Timestamp.today().normalize()
    s = pd.to_datetime(dob_series, errors="coerce")
    try:
        s = s.dt.tz_localize(None)
    except Exception:
        pass
    return (today - s).dt.days // 365


def compute_tenure(start_series: pd.Series) -> pd.Series:
    today = pd.Timestamp.today().normalize()
    s = pd.to_datetime(start_series, errors="coerce")
    try:
        s = s.dt.tz_localize(None)
    except Exception:
        pass
    return (today - s).dt.days // 365


def compute_master_category_data(
    df_data: Dict[str, pd.DataFrame],
) -> Dict[str, pd.DataFrame]:

    df_j = df_data["jugadores"].copy()
    df_c = df_data["competiciones"].copy()
    df_p = df_data["partidos"].copy()
    df_a = df_data["actuaciones"].copy()
    df_arq = df_data["arqueros"].copy()

    if df_a.empty:
        return {}

    df_p_played = df_p.copy()
    if "matchstatus" in df_p_played.columns:
        played_mask = (
            df_p_played["matchstatus"].fillna("").astype(str).str.strip().str.upper()
            == "JUGADO"
        )
        df_p_played = df_p_played[played_mask].copy()

    if "matchid" in df_p_played.columns:
        played_match_ids = set(df_p_played["matchid"].dropna().tolist())
        df_a = df_a[df_a["matchid"].isin(played_match_ids)].copy()
        if not df_arq.empty and "matchid" in df_arq.columns:
            df_arq = df_arq[df_arq["matchid"].isin(played_match_ids)].copy()

    if df_a.empty:
        return {}

    df_j["edad"] = compute_age(df_j["dateofbirth"])
    df_j["antiguedad"] = compute_tenure(df_j["datefrom"])

    df_a["minutesplayed"] = df_a["minutesplayed"].fillna(0).astype(float)
    df_a["goals"] = df_a["goals"].fillna(0).astype(float)

    df_a["startinglineup"] = df_a["startinglineup"].fillna(False).astype(bool)
    df_a["played"] = df_a["played"].fillna(False).astype(bool)

    for col in ["singleyellow", "secondyellow", "redcards"]:
        if col in df_a.columns:
            df_a[col] = df_a[col].fillna(False).astype(bool)

    df_a["amarillas"] = df_a[["singleyellow", "secondyellow"]].astype(int).sum(axis=1)
    df_a["rojas"] = df_a["redcards"].astype(int)

    df_a["result_upper"] = df_a["result"].fillna("").astype(str).str.upper()
    win_values = {"WIN", "W", "GANADO", "VICTORIA"}
    df_a["win"] = df_a["result_upper"].isin(win_values).astype(int)

    df_a["played_any"] = (df_a["played"]) | (df_a["minutesplayed"] > 0)
    df_a["win_on_field"] = (df_a["win"] * df_a["played_any"].astype(int)).astype(int)

    df = df_a.merge(df_c, on="competition_id", how="left")
    df = df.merge(
        df_p_played[["matchid", "match_date", "home_team", "away_team"]],
        on="matchid",
        how="left",
    )
    df = df.merge(
        df_j[
            [
                "personid",
                "displayname",
                "firstname",
                "lastname",
                "dateofbirth",
                "edad",
                "antiguedad",
                "nationality",
                "height",
                "weight",
                "datefrom",
            ]
        ],
        on="personid",
        how="left",
    )
    df = df.dropna(subset=["personid", "competition_id"])

    club_ids = df_a["clubid"].dropna().unique()
    club_id_report: Optional[int] = int(club_ids[0]) if len(club_ids) >= 1 else None

    df_matches = df_p_played.merge(
        df_c[["competition_id", "category", "matchlength"]],
        on="competition_id",
        how="left",
    )

    if club_id_report is not None:
        df_matches = df_matches[
            (df_matches["home_team"] == club_id_report)
            | (df_matches["away_team"] == club_id_report)
        ]

    df_matches = df_matches.drop_duplicates(subset=["matchid"])
    df_matches["matchlength"] = df_matches["matchlength"].fillna(0).astype(float)

    matches_by_comp = (
        df_matches.groupby("competition_id", dropna=False)["matchid"]
        .nunique()
        .reset_index()
        .rename(columns={"matchid": "matches_played_team"})
    )

    matches_by_comp = matches_by_comp.merge(
        df_c[["competition_id", "matchlength", "category"]],
        on="competition_id",
        how="left",
    )
    matches_by_comp["matchlength"] = (
        matches_by_comp["matchlength"].fillna(0).astype(float)
    )
    matches_by_comp["minutes_possible_team"] = (
        matches_by_comp["matches_played_team"] * matches_by_comp["matchlength"]
    )

    minutes_possible_by_comp = matches_by_comp.set_index("competition_id")[
        "minutes_possible_team"
    ].to_dict()

    gk_stats = pd.DataFrame()
    if not df_arq.empty:
        df_arq["goalsconceded"] = df_arq["goalsconceded"].fillna(0).astype(float)
        gk_stats = (
            df_arq.groupby(["competition_id", "personid"], dropna=False)[
                "goalsconceded"
            ]
            .sum()
            .reset_index()
        )

    cat_age_limit_map: Dict[str, Optional[int]] = {}
    if "category" in df_c.columns:
        for cat, grp in df_c.groupby("category", dropna=False):
            if pd.isna(cat):
                continue
            max_age = None
            if "playermaxage" in grp.columns and not grp["playermaxage"].dropna().empty:
                max_age = grp["playermaxage"].dropna().max()
            cat_age_limit_map[str(cat)] = parse_category_age_limit(cat, max_age)

    df["role_suplente_entra"] = (~df["startinglineup"]) & (df["played_any"])
    df["role_banco_no_entra"] = (~df["startinglineup"]) & (~df["played_any"])

    group_keys = ["category", "competition_id", "personid"]

    agg_stats = df.groupby(group_keys, dropna=False).agg(
        Categoria=("category", "first"),
        Competition_ID=("competition_id", "first"),
        Competicion=("name", "first"),
        Temporada=("season", "first"),
        Displayname=("displayname", "first"),
        Firstname=("firstname", "first"),
        Lastname=("lastname", "first"),
        DOB=("dateofbirth", "first"),
        Edad=("edad", "max"),
        Antiguedad=("antiguedad", "max"),
        Nacionalidad=("nationality", "first"),
        Altura=("height", "max"),
        Peso=("weight", "max"),
        Minutos=("minutesplayed", "sum"),
        Partidos_Convocado=("matchid", "nunique"),
        Partidos_Jugados=("played_any", "sum"),
        Goles=("goals", "sum"),
        Amarillas=("amarillas", "sum"),
        Rojas=("rojas", "sum"),
        Partidos_ganados=("win_on_field", "sum"),
        Titular=("startinglineup", "sum"),
    )

    role_stats = df.groupby(group_keys, dropna=False).agg(
        Suplente_entra=("role_suplente_entra", "sum"),
        Banco_sin_entrar=("role_banco_no_entra", "sum"),
    )

    combined_all = agg_stats.join(role_stats)

    combined_all["Jugador"] = combined_all["Displayname"].fillna(
        (
            combined_all["Firstname"].fillna("")
            + " "
            + combined_all["Lastname"].fillna("")
        ).str.strip()
    )
    combined_all = combined_all[combined_all["Jugador"] != ""]

    combined_all["Minutos Posibles Equipo"] = (
        combined_all["Competition_ID"].map(minutes_possible_by_comp).fillna(0.0)
    )
    mp = combined_all["Minutos Posibles Equipo"].astype(float)
    combined_all["% Participación"] = 0.0
    mask_mp = mp > 0
    combined_all.loc[mask_mp, "% Participación"] = (
        combined_all.loc[mask_mp, "Minutos"] / mp[mask_mp] * 100
    ).round(1)

    wins = pd.to_numeric(combined_all["Partidos_ganados"], errors="coerce").astype(
        float
    )
    pj = pd.to_numeric(combined_all["Partidos_Jugados"], errors="coerce").astype(float)
    pj = pj.replace(0.0, float("nan"))

    combined_all["% Victorias"] = (wins / pj * 100).round(1).fillna(0.0)

    if not gk_stats.empty:
        gk_idx = gk_stats.set_index(["competition_id", "personid"])
        combined_all = combined_all.reset_index()
        combined_all = combined_all.merge(
            gk_idx.reset_index(),
            left_on=["competition_id", "personid"],
            right_on=["competition_id", "personid"],
            how="left",
        )
        combined_all["Goles Recibidos"] = combined_all["goalsconceded"].fillna(0.0)
        combined_all = combined_all.drop(columns=["goalsconceded"])
        combined_all = combined_all.set_index(group_keys)
    else:
        combined_all["Goles Recibidos"] = 0.0

    def adelantado_for_row(cat_val: Any, age_val: Any) -> str:
        if pd.isna(age_val):
            return "No"
        cat_str = str(cat_val) if cat_val is not None else ""
        limit = cat_age_limit_map.get(cat_str)
        if limit is None:
            c = str(cat_str).upper()
            if c in {"SENIORES", "PRIMER EQUIPO", "ADULTOS", "PRIMERA"}:
                return "Si" if float(age_val) < 18 else "No"
            return "No"

        try:
            age_int = int(age_val)
        except Exception:
            return "No"

        c = str(cat_str).upper().strip()
        if c.startswith("U") and limit > age_int + 1:
            return "Si"
        return "No"

    combined_all = combined_all.reset_index()

    combined_all["Limite Categoria"] = (
        combined_all["Categoria"].astype(str).map(cat_age_limit_map)
    )
    combined_all["Adelantado"] = combined_all.apply(
        lambda r: adelantado_for_row(r["Categoria"], r["Edad"]), axis=1
    )
    combined_all["Gap Edad"] = combined_all.apply(
        lambda r: (
            (r["Limite Categoria"] - r["Edad"])
            if pd.notna(r["Limite Categoria"]) and pd.notna(r["Edad"])
            else pd.NA
        ),
        axis=1,
    )

    combined_all["DOB"] = pd.to_datetime(
        combined_all["DOB"], errors="coerce"
    ).dt.strftime("%d/%m/%Y")

    combined_all["Ranking"] = (
        combined_all.groupby(["Categoria", "Competition_ID"], dropna=False)["Minutos"]
        .rank(method="first", ascending=False)
        .astype(int)
    )

    master_files: Dict[str, pd.DataFrame] = {}
    categories = combined_all["Categoria"].dropna().unique()

    final_cols = [
        "Ranking",
        "Categoria",
        "Competition_ID",
        "Competicion",
        "Temporada",
        "Jugador",
        "DOB",
        "Edad",
        "Limite Categoria",
        "Gap Edad",
        "Adelantado",
        "Nacionalidad",
        "Altura",
        "Peso",
        "Antiguedad",
        "Partidos_Convocado",
        "Partidos_Jugados",
        "Titular",
        "Suplente_entra",
        "Banco_sin_entrar",
        "Minutos",
        "Minutos Posibles Equipo",
        "% Participación",
        "Goles",
        "Goles Recibidos",
        "Partidos_ganados",
        "% Victorias",
        "Amarillas",
        "Rojas",
    ]

    for cat in categories:
        cat_df = combined_all[combined_all["Categoria"] == cat].copy()
        if cat_df.empty:
            continue

        for col in final_cols:
            if col not in cat_df.columns:
                cat_df[col] = 0

        cat_df = cat_df.sort_values(
            by=["Competicion", "Temporada", "Ranking", "Minutos"],
            ascending=[True, True, True, False],
            kind="mergesort",
        )

        master_files[str(cat)] = cat_df[final_cols]

    return master_files


