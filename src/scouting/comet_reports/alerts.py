"""Alertas de Sheets: ciclos de amarillas, baja participación y categoría superior."""
from __future__ import annotations
from datetime import date
import pandas as pd

def _to_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def _to_int64(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int64")


def _to_float(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _to_bool(series: pd.Series) -> pd.Series:
    return series.fillna(False).astype(bool)


def _safe_bool(value) -> bool:
    if pd.isna(value):
        return False
    return bool(value)


def _normalize_season(season) -> str | None:
    if season is None:
        return None
    season_str = str(season).strip()
    return season_str if season_str else None


def _filter_competitions_by_season(df_comp: pd.DataFrame, season) -> pd.DataFrame:
    season_norm = _normalize_season(season)
    if season_norm is None:
        return df_comp
    if df_comp.empty or "season" not in df_comp.columns:
        return pd.DataFrame()
    return df_comp[df_comp["season"].astype("string").str.strip() == season_norm].copy()


def _fetch_supabase_table(supabase_client, table: str, columns: str, page_size: int = 1000) -> pd.DataFrame:
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


def _compute_yellow_card_alerts(df_events: pd.DataFrame, df_all_matches: pd.DataFrame) -> pd.DataFrame:
    if df_events.empty:
        return pd.DataFrame()

    df_events = df_events.copy()
    df_events["personid"] = _to_int64(df_events["personid"])
    df_events["competition_id"] = _to_int64(df_events["competition_id"])
    df_events["clubid"] = _to_int64(df_events["clubid"])
    df_events["matchdate"] = _to_datetime(df_events["matchdate"])
    df_events = df_events.dropna(subset=["personid", "competition_id", "clubid", "matchdate"])
    df_events = df_events.sort_values(
        ["personid", "competition_id", "matchdate"], ascending=True
    )
    if df_events.empty:
        return pd.DataFrame()

    df_all_matches = df_all_matches.copy()
    df_all_matches["competition_id"] = _to_int64(df_all_matches["competition_id"])
    df_all_matches["hometeam"] = _to_int64(df_all_matches["hometeam"])
    df_all_matches["awayteam"] = _to_int64(df_all_matches["awayteam"])
    df_all_matches["matchdate"] = _to_datetime(df_all_matches["matchdate"])
    df_all_matches = df_all_matches.dropna(
        subset=["competition_id", "hometeam", "awayteam", "matchdate"]
    )

    alerts = []
    for (personid, competition_id, competition_name), group in df_events.groupby(
        ["personid", "competition_id", "competition_name"], dropna=False
    ):
        accumulated_yellows = 0
        firstname = group.iloc[0]["firstname"]
        lastname = group.iloc[0]["lastname"]
        displayname = group.iloc[0]["displayname"]
        category_name = group.iloc[-1]["category_name"]

        for _, row in group.iterrows():
            is_second_yellow = _safe_bool(row["secondyellow"])
            is_single_yellow = _safe_bool(row["singleyellow"])
            # Rule: double yellow (red) does not count for accumulation.
            if is_second_yellow:
                continue
            if is_single_yellow:
                accumulated_yellows += 1

        is_suspended = False
        if accumulated_yellows == 5:
            is_suspended = True
            next_threshold = 8
        elif accumulated_yellows == 8:
            is_suspended = True
            next_threshold = 10
        elif accumulated_yellows > 8 and (accumulated_yellows - 8) % 2 == 0:
            is_suspended = True
            next_threshold = accumulated_yellows + 2
        else:
            if accumulated_yellows < 5:
                next_threshold = 5
            elif accumulated_yellows < 8:
                next_threshold = 8
            else:
                next_threshold = accumulated_yellows + 1

        cards_until_suspension = next_threshold - accumulated_yellows
        status = None
        suspension_served = False
        last_match_date = _to_datetime(pd.Series([group.iloc[-1]["matchdate"]])).iloc[0]
        last_team_match_date = None

        if is_suspended:
            status = "SUSPENDED_NEXT_MATCH"
            club_id = group.iloc[-1]["clubid"]

            subsequent_matches = df_all_matches[
                (df_all_matches["competition_id"] == competition_id)
                & (
                    (df_all_matches["hometeam"] == club_id)
                    | (df_all_matches["awayteam"] == club_id)
                )
                & (df_all_matches["matchdate"] > last_match_date)
            ]
            if not subsequent_matches.empty:
                suspension_served = True

            team_matches = df_all_matches[
                (df_all_matches["competition_id"] == competition_id)
                & (
                    (df_all_matches["hometeam"] == club_id)
                    | (df_all_matches["awayteam"] == club_id)
                )
            ]
            last_team_match_date = (
                team_matches["matchdate"].max() if not team_matches.empty else None
            )
        elif cards_until_suspension == 1:
            status = "WARNING_ONE_AWAY"

        if status:
            alerts.append(
                {
                    "personid": personid,
                    "firstname": firstname,
                    "lastname": lastname,
                    "displayname": displayname,
                    "competition_name": competition_name,
                    "category_name": category_name,
                    "total_accumulated": accumulated_yellows,
                    "next_threshold": next_threshold,
                    "status": status,
                    "suspension_served": suspension_served,
                    "last_sanction_date": (
                        last_match_date if is_suspended else group.iloc[-1]["matchdate"]
                    ),
                    "last_team_match_date": (
                        last_team_match_date if is_suspended else None
                    ),
                }
            )

    return pd.DataFrame(alerts)


def _compute_higher_category_alerts(df_cat: pd.DataFrame) -> pd.DataFrame:
    if df_cat.empty:
        return pd.DataFrame()

    alerts_cat = []
    for _, row in df_cat.iterrows():
        age = row["age"]
        comp_cat = str(row["competition_category"]).upper()
        if pd.isna(age):
            continue

        cat_age_limit = None
        if comp_cat.startswith("U-"):
            try:
                cat_age_limit = int(comp_cat.split("-")[1])
            except ValueError:
                pass
        elif comp_cat in ["SENIORES", "PRIMERA", "ADULTOS", "PRIMER EQUIPO"]:
            cat_age_limit = 19

        if cat_age_limit and cat_age_limit > (age + 1):
            row["category_age_limit"] = cat_age_limit
            row["age_difference"] = int(cat_age_limit - age)
            alerts_cat.append(row)

    if not alerts_cat:
        return pd.DataFrame()
    return pd.DataFrame(alerts_cat)


def _get_yellow_card_alerts_from_supabase(
    supabase_client, season: str | None = None
) -> pd.DataFrame:
    df_actions = _fetch_supabase_table(
        supabase_client,
        table="actuaciones_jugadores",
        columns="personid,singleyellow,secondyellow,clubid,id,matchid",
    )
    if df_actions.empty:
        return pd.DataFrame()

    for col in ["singleyellow", "secondyellow"]:
        if col not in df_actions.columns:
            df_actions[col] = False
        df_actions[col] = _to_bool(df_actions[col])
    df_actions = df_actions[df_actions["singleyellow"] | df_actions["secondyellow"]].copy()
    if df_actions.empty:
        return pd.DataFrame()

    df_actions["personid"] = _to_int64(df_actions["personid"])
    df_actions["id"] = _to_int64(df_actions["id"])
    df_actions["clubid"] = _to_int64(df_actions["clubid"])
    df_actions["matchid"] = _to_int64(df_actions["matchid"])

    df_players = _fetch_supabase_table(
        supabase_client,
        table="jugadores",
        columns="personid,firstname,lastname,displayname",
    )
    if df_players.empty:
        return pd.DataFrame()
    df_players["personid"] = _to_int64(df_players["personid"])

    df_matches = _fetch_supabase_table(
        supabase_client,
        table="partidos",
        columns="matchid,id,hometeam,awayteam,matchdate",
    )
    if df_matches.empty:
        return pd.DataFrame()
    df_matches["matchid"] = _to_int64(df_matches["matchid"])
    df_matches["id"] = _to_int64(df_matches["id"])
    df_matches["hometeam"] = _to_int64(df_matches["hometeam"])
    df_matches["awayteam"] = _to_int64(df_matches["awayteam"])

    df_comp = _fetch_supabase_table(
        supabase_client,
        table="competiciones",
        columns="id,name,category,season",
    )
    if df_comp.empty:
        return pd.DataFrame()
    df_comp["id"] = _to_int64(df_comp["id"])
    df_comp = _filter_competitions_by_season(df_comp, season)
    if df_comp.empty:
        return pd.DataFrame()

    valid_comp_ids = set(df_comp["id"].dropna().astype(int).tolist())
    if not valid_comp_ids:
        return pd.DataFrame()
    df_actions = df_actions[df_actions["id"].isin(valid_comp_ids)].copy()
    df_matches = df_matches[df_matches["id"].isin(valid_comp_ids)].copy()
    if df_actions.empty or df_matches.empty:
        return pd.DataFrame()

    df_events = df_actions.merge(
        df_players[["personid", "firstname", "lastname", "displayname"]],
        on="personid",
        how="inner",
    )
    df_events = df_events.merge(
        df_matches[["matchid", "matchdate"]],
        on="matchid",
        how="inner",
    )
    df_events = df_events.merge(
        df_comp.rename(
            columns={
                "id": "competition_id",
                "name": "competition_name",
                "category": "category_name",
            }
        ),
        left_on="id",
        right_on="competition_id",
        how="left",
    )
    df_events["competition_id"] = _to_int64(df_events["competition_id"])

    df_all_matches = df_matches.rename(columns={"id": "competition_id"})
    return _compute_yellow_card_alerts(df_events, df_all_matches)


def _get_low_minutes_alerts_from_supabase(
    supabase_client, threshold_percentage: float = 20, season: str | None = None
) -> pd.DataFrame:
    df_matches = _fetch_supabase_table(
        supabase_client,
        table="partidos",
        columns="id,hometeam,awayteam,matchstatus",
    )
    df_comp = _fetch_supabase_table(
        supabase_client,
        table="competiciones",
        columns="id,name,category,matchlength,season",
    )
    df_actions = _fetch_supabase_table(
        supabase_client,
        table="actuaciones_jugadores",
        columns="personid,id,clubid,minutesplayed",
    )
    df_players = _fetch_supabase_table(
        supabase_client,
        table="jugadores",
        columns="personid,firstname,lastname,displayname",
    )
    if df_matches.empty or df_comp.empty or df_actions.empty or df_players.empty:
        return pd.DataFrame()

    df_matches["id"] = _to_int64(df_matches["id"])
    df_matches["hometeam"] = _to_int64(df_matches["hometeam"])
    df_matches["awayteam"] = _to_int64(df_matches["awayteam"])
    if "matchstatus" in df_matches.columns:
        status_norm = (
            df_matches["matchstatus"].astype("string").fillna("").str.strip().str.upper()
        )
        df_matches = df_matches[status_norm == "JUGADO"].copy()
    df_comp["id"] = _to_int64(df_comp["id"])
    df_comp["matchlength"] = _to_float(df_comp["matchlength"])
    df_actions["id"] = _to_int64(df_actions["id"])
    df_comp = _filter_competitions_by_season(df_comp, season)
    if df_comp.empty:
        return pd.DataFrame()

    valid_comp_ids = set(df_comp["id"].dropna().astype(int).tolist())
    if not valid_comp_ids:
        return pd.DataFrame()
    df_matches = df_matches[df_matches["id"].isin(valid_comp_ids)].copy()
    df_actions = df_actions[df_actions["id"].isin(valid_comp_ids)].copy()
    if df_matches.empty or df_actions.empty:
        return pd.DataFrame()

    df_actions["personid"] = _to_int64(df_actions["personid"])
    df_actions["clubid"] = _to_int64(df_actions["clubid"])
    df_actions["minutesplayed"] = _to_float(df_actions["minutesplayed"]).fillna(0)
    df_players["personid"] = _to_int64(df_players["personid"])

    df_match_comp = df_matches.merge(
        df_comp[["id", "name", "category", "matchlength"]],
        on="id",
        how="inner",
    ).rename(
        columns={
            "id": "competition_id",
            "name": "competition_name",
            "category": "category_name",
        }
    )
    if df_match_comp.empty:
        return pd.DataFrame()

    home_matches = (
        df_match_comp.groupby(
            ["competition_id", "competition_name", "category_name", "matchlength", "hometeam"],
            dropna=False,
        )
        .size()
        .reset_index(name="matches_played")
        .rename(columns={"hometeam": "team_id"})
    )
    away_matches = (
        df_match_comp.groupby(
            ["competition_id", "competition_name", "category_name", "matchlength", "awayteam"],
            dropna=False,
        )
        .size()
        .reset_index(name="matches_played")
        .rename(columns={"awayteam": "team_id"})
    )
    team_matches = pd.concat([home_matches, away_matches], ignore_index=True)
    team_total_matches = (
        team_matches.groupby(
            ["competition_id", "competition_name", "category_name", "matchlength", "team_id"],
            dropna=False,
        )["matches_played"]
        .sum()
        .reset_index(name="total_matches")
    )

    player_minutes = (
        df_actions.groupby(["personid", "id", "clubid"], dropna=False)["minutesplayed"]
        .sum()
        .reset_index(name="total_minutes")
        .rename(columns={"id": "competition_id", "clubid": "team_id"})
    )

    df_minutes = player_minutes.merge(
        team_total_matches,
        on=["competition_id", "team_id"],
        how="inner",
    )
    df_minutes = df_minutes.merge(
        df_players[["personid", "firstname", "lastname", "displayname"]],
        on="personid",
        how="inner",
    )
    if df_minutes.empty:
        return pd.DataFrame()

    df_minutes["possible_minutes"] = (
        _to_float(df_minutes["total_matches"]) * _to_float(df_minutes["matchlength"])
    )
    df_minutes["percentage"] = (
        _to_float(df_minutes["total_minutes"]) / df_minutes["possible_minutes"].replace(0, pd.NA)
    ) * 100
    df_minutes = df_minutes[df_minutes["total_matches"] > 0].copy()
    df_minutes = df_minutes[
        [
            "firstname",
            "lastname",
            "displayname",
            "competition_name",
            "category_name",
            "total_minutes",
            "possible_minutes",
            "percentage",
        ]
    ].sort_values("percentage", ascending=True, na_position="last")
    return df_minutes[df_minutes["percentage"] < threshold_percentage].copy()


def _calculate_age_from_dob(dob):
    if pd.isna(dob):
        return pd.NA
    if isinstance(dob, pd.Timestamp):
        dob = dob.date()
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _get_higher_category_alerts_from_supabase(
    supabase_client, season: str | None = None
) -> pd.DataFrame:
    df_actions = _fetch_supabase_table(
        supabase_client,
        table="actuaciones_jugadores",
        columns="personid,id,minutesplayed",
    )
    df_players = _fetch_supabase_table(
        supabase_client,
        table="jugadores",
        columns="personid,firstname,lastname,displayname,dateofbirth",
    )
    df_comp = _fetch_supabase_table(
        supabase_client,
        table="competiciones",
        columns="id,name,category,parentcompetitionid,season",
    )
    if df_actions.empty or df_players.empty or df_comp.empty:
        return pd.DataFrame()

    df_actions["personid"] = _to_int64(df_actions["personid"])
    df_actions["id"] = _to_int64(df_actions["id"])
    df_actions["minutesplayed"] = _to_float(df_actions["minutesplayed"]).fillna(0)
    df_players["personid"] = _to_int64(df_players["personid"])
    df_players["dateofbirth"] = _to_datetime(df_players["dateofbirth"])
    df_comp["id"] = _to_int64(df_comp["id"])
    df_comp["parentcompetitionid"] = _to_int64(df_comp["parentcompetitionid"])
    df_comp = _filter_competitions_by_season(df_comp, season)
    if df_comp.empty:
        return pd.DataFrame()

    valid_comp_ids = set(df_comp["id"].dropna().astype(int).tolist())
    if not valid_comp_ids:
        return pd.DataFrame()
    df_actions = df_actions[df_actions["id"].isin(valid_comp_ids)].copy()
    if df_actions.empty:
        return pd.DataFrame()

    player_minutes = (
        df_actions.groupby(["personid", "id"], dropna=False)["minutesplayed"]
        .sum()
        .reset_index(name="total_minutes")
        .rename(columns={"id": "competition_id"})
    )

    df_parent_names = df_comp[["id", "name"]].rename(
        columns={"id": "parentcompetitionid", "name": "parent_name"}
    )
    df_comp_aug = df_comp.merge(df_parent_names, on="parentcompetitionid", how="left")
    df_comp_aug["competition_name"] = df_comp_aug["parent_name"].combine_first(
        df_comp_aug["name"]
    )
    df_comp_aug = df_comp_aug.rename(columns={"category": "competition_category"})

    df_cat = player_minutes.merge(
        df_players[["personid", "firstname", "lastname", "displayname", "dateofbirth"]],
        on="personid",
        how="inner",
    )
    df_cat = df_cat.merge(
        df_comp_aug[["id", "competition_name", "competition_category"]],
        left_on="competition_id",
        right_on="id",
        how="left",
    )
    df_cat["age"] = df_cat["dateofbirth"].apply(_calculate_age_from_dob)

    df_cat = df_cat[
        [
            "firstname",
            "lastname",
            "displayname",
            "dateofbirth",
            "competition_category",
            "competition_name",
            "age",
            "total_minutes",
        ]
    ]
    return _compute_higher_category_alerts(df_cat)


def get_yellow_card_alerts(source, season=None):
    return _get_yellow_card_alerts_from_supabase(source, season=season)

def get_low_minutes_alerts(source, threshold_percentage=20, season=None):
    return _get_low_minutes_alerts_from_supabase(source, threshold_percentage, season)

def get_higher_category_alerts(source, season=None):
    return _get_higher_category_alerts_from_supabase(source, season=season)
