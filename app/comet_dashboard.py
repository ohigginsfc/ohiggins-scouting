import os
from datetime import datetime
from typing import Optional, Dict

import pandas as pd
import psycopg
from urllib.parse import quote_plus
from dotenv import load_dotenv
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go



OHIGGINS_CLUB_ID = 40010

OH_BLUE = "#4A7BA7"
OH_DARK = "#111827"
OH_GREEN = "#2D5016"
OH_GOLD = "#D4AF37"
OH_LIGHT = "#F9FAFB"
OH_RED = "#E11D48"
OH_GRAY = "#6B7280"

LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "OHigginsFC.png")

ALL_CATEGORIES_ORDERED = [
    "Primer Equipo",
    "U-19",
    "U-16",
    "U-15",
    "U-14",
    "U-13",
    "U-12",
    "U-11",
]

YOUTH_CATEGORIES = [
    "U-19",
    "U-16",
    "U-15",
    "U-14",
    "U-13",
    "U-12",
    "U-11",
]

from scouting.portal.security import admin_only, require_admin

@admin_only
def get_db_connection():
    dsn = os.environ.get('COMET_DATABASE_URL', '').strip()
    if not dsn:
        raise RuntimeError('Falta la conexión de lectura de COMET.')
    return psycopg.connect(dsn, connect_timeout=10, autocommit=True,
        options='-c default_transaction_read_only=on -c search_path=public -c statement_timeout=30000')

@admin_only
def load_data(query: str, params: Optional[Dict] = None) -> pd.DataFrame:
    with get_db_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


@admin_only
@st.cache_data(ttl=600)
def get_categories_overview() -> pd.DataFrame:
    query = f"""
        SELECT
            c.category,
            COUNT(DISTINCT c.id) AS total_competitions,
            COUNT(DISTINCT p.matchid) AS total_matches,
            MAX(c.season) AS season
        FROM competiciones c
        LEFT JOIN partidos p
            ON c.id = p.id
           AND (p.hometeam = {OHIGGINS_CLUB_ID} OR p.awayteam = {OHIGGINS_CLUB_ID})
        WHERE c.id IN (
            SELECT DISTINCT id FROM competidores WHERE clubid = {OHIGGINS_CLUB_ID}
        )
        GROUP BY c.category
        ORDER BY c.category;
    """
    return load_data(query)


@admin_only
@st.cache_data(ttl=600)
def get_standings_by_category(category: Optional[str] = None) -> pd.DataFrame:
    query = f"""
        SELECT
            c.category,
            c.name AS competition_name,
            c.season,
            p.position,
            p.matches,
            p.wins,
            p.draws,
            p.losses,
            p.points,
            p.goalsfor,
            p.goalsagainst,
            p.goaldifference
        FROM posiciones p
        JOIN competiciones c ON p.id = c.id
        WHERE p.clubid = {OHIGGINS_CLUB_ID}
          AND p.status = 'ACTIVO'
    """
    params = None
    if category:
        query += " AND c.category = %(cat)s"
        params = {"cat": category}
    query += " ORDER BY c.category, p.points DESC;"
    df = load_data(query, params)
    if not df.empty:
        df["efectividad"] = ((df["points"] / (df["matches"] * 3)) * 100).round(1)
        df["pts_per_match"] = (df["points"] / df["matches"]).round(2)
    return df


@admin_only
@st.cache_data(ttl=600)
def get_player_stats_by_category(category: Optional[str] = None) -> pd.DataFrame:
    query = f"""
        SELECT
            j.personid,
            j.displayname,
            EXTRACT(YEAR FROM AGE(j.dateofbirth)) AS age,
            j.nationality,
            j.level,
            c.category,
            COUNT(DISTINCT a.matchid) AS matches,
            SUM(a.minutesplayed) AS minutes,
            SUM(CASE WHEN a.startinglineup THEN 1 ELSE 0 END) AS starts,
            SUM(a.goals) AS goals,
            SUM(a.singleyellow::int) AS yellow_cards,
            SUM(a.redcards::int) AS red_cards,
            ROUND(
                CAST(SUM(a.minutesplayed) AS NUMERIC)
                / NULLIF(COUNT(DISTINCT a.matchid), 0),
                0
            ) AS avg_minutes,
            ROUND(
                CAST(SUM(a.goals) AS NUMERIC) * 90.0
                / NULLIF(SUM(a.minutesplayed), 0),
                2
            ) AS goals_per90
        FROM actuaciones_jugadores a
        JOIN jugadores j ON a.personid = j.personid
        JOIN competiciones c ON a.id = c.id
        WHERE a.clubid = {OHIGGINS_CLUB_ID}
          AND a.played = TRUE
          AND (a.goalkeeper IS NULL OR a.goalkeeper = FALSE)
    """
    params = None
    if category:
        query += " AND c.category = %(cat)s"
        params = {"cat": category}
    query += """
        GROUP BY
            j.personid, j.displayname, j.dateofbirth,
            j.nationality, j.level, c.category
        HAVING SUM(a.minutesplayed) > 0
        ORDER BY SUM(a.minutesplayed) DESC;
    """
    return load_data(query, params)


@admin_only
@st.cache_data(ttl=600)
def get_goalkeeper_stats_by_category(category: Optional[str] = None) -> pd.DataFrame:
    query = f"""
        SELECT
            j.personid,
            j.displayname,
            EXTRACT(YEAR FROM AGE(j.dateofbirth)) AS age,
            c.category,
            COUNT(DISTINCT a.matchid) AS matches,
            SUM(a.minutesplayed) AS minutes,
            SUM(a.goalsconceded) AS goals_conceded,
            SUM(
                CASE WHEN a.goalsconceded = 0 AND a.played THEN 1 ELSE 0 END
            ) AS clean_sheets,
            ROUND(
                CAST(SUM(a.goalsconceded) AS NUMERIC) * 90.0
                / NULLIF(SUM(a.minutesplayed), 0),
                2
            ) AS gc_per90,
            ROUND(
                CAST(
                    SUM(CASE WHEN a.goalsconceded = 0 THEN 1 ELSE 0 END)
                    AS NUMERIC
                ) * 100.0 / NULLIF(COUNT(DISTINCT a.matchid), 0),
                1
            ) AS clean_sheet_pct
        FROM actuaciones_arqueros a
        JOIN jugadores j ON a.personid = j.personid
        JOIN competiciones c ON a.id = c.id
        WHERE a.clubid = {OHIGGINS_CLUB_ID}
          AND a.played = TRUE
    """
    params = None
    if category:
        query += " AND c.category = %(cat)s"
        params = {"cat": category}
    query += """
        GROUP BY j.personid, j.displayname, j.dateofbirth, c.category
        HAVING SUM(a.minutesplayed) > 0
        ORDER BY SUM(a.minutesplayed) DESC;
    """
    return load_data(query, params)


@admin_only
@st.cache_data(ttl=600)
def get_match_results_by_category(category: Optional[str] = None) -> pd.DataFrame:
    query = f"""
        WITH scores AS (
            SELECT
                pf.matchid,
                MAX(
                    CASE WHEN pf.phase = 'Segundo tiempo'
                         THEN pf.homeresult END
                ) AS final_home,
                MAX(
                    CASE WHEN pf.phase = 'Segundo tiempo'
                         THEN pf.awayresult END
                ) AS final_away
            FROM partidos_fases pf
            GROUP BY pf.matchid
        )
        SELECT
            p.matchid,
            p.matchdate,
            c.category,
            c.name AS competition,
            e_home.club AS home_team,
            e_away.club AS away_team,
            s.final_home,
            s.final_away,
            CASE
                WHEN p.hometeam = {OHIGGINS_CLUB_ID} THEN 'Local'
                ELSE 'Visita'
            END AS venue,
            CASE
                WHEN s.final_home IS NULL OR s.final_away IS NULL THEN NULL
                WHEN p.hometeam = {OHIGGINS_CLUB_ID}
                     AND s.final_home > s.final_away THEN 'Victoria'
                WHEN p.awayteam = {OHIGGINS_CLUB_ID}
                     AND s.final_away > s.final_home THEN 'Victoria'
                WHEN s.final_home = s.final_away THEN 'Empate'
                ELSE 'Derrota'
            END AS result,
            CASE
                WHEN p.hometeam = {OHIGGINS_CLUB_ID} THEN s.final_home
                ELSE s.final_away
            END AS goals_for,
            CASE
                WHEN p.hometeam = {OHIGGINS_CLUB_ID} THEN s.final_away
                ELSE s.final_home
            END AS goals_against
        FROM partidos p
        JOIN competiciones c ON p.id = c.id
        JOIN equipos e_home ON p.hometeam = e_home.clubid
        JOIN equipos e_away ON p.awayteam = e_away.clubid
        LEFT JOIN scores s ON p.matchid = s.matchid
        WHERE (p.hometeam = {OHIGGINS_CLUB_ID} OR p.awayteam = {OHIGGINS_CLUB_ID})
          AND p.matchdate IS NOT NULL
          AND p.matchdate < NOW()
    """
    params = None
    if category:
        query += " AND c.category = %(cat)s"
        params = {"cat": category}
    query += " ORDER BY p.matchdate DESC;"
    df = load_data(query, params)
    if not df.empty:
        df["matchdate"] = pd.to_datetime(df["matchdate"])
    return df


@admin_only
@st.cache_data(ttl=600)
def get_squad_by_age_category() -> pd.DataFrame:
    query = """
        SELECT
            j.personid,
            j.displayname,
            j.dateofbirth,
            EXTRACT(YEAR FROM AGE(j.dateofbirth)) AS age,
            j.nationality,
            j.level,
            j.status,
            CASE
                WHEN EXTRACT(YEAR FROM AGE(j.dateofbirth)) >= 20 THEN 'Primer Equipo'
                WHEN EXTRACT(YEAR FROM AGE(j.dateofbirth)) = 19 THEN 'U-19'
                WHEN EXTRACT(YEAR FROM AGE(j.dateofbirth)) IN (17, 18) THEN 'U-19'
                WHEN EXTRACT(YEAR FROM AGE(j.dateofbirth)) IN (15, 16) THEN 'U-16'
                WHEN EXTRACT(YEAR FROM AGE(j.dateofbirth)) IN (14, 15) THEN 'U-15'
                WHEN EXTRACT(YEAR FROM AGE(j.dateofbirth)) IN (13, 14) THEN 'U-13'
                WHEN EXTRACT(YEAR FROM AGE(j.dateofbirth)) IN (12, 13) THEN 'U-12'
                WHEN EXTRACT(YEAR FROM AGE(j.dateofbirth)) <= 11 THEN 'U-11'
                ELSE 'Primer Equipo'
            END AS age_category
        FROM jugadores j
        WHERE LOWER(j.orgname) LIKE '%higgins%'
          AND j.status = 'ACTIVO'
        ORDER BY age DESC;
    """
    return load_data(query)


def category_badge(category: str) -> str:
    mapping = {
        "Primer Equipo": "primer",
        "U-19": "u19",
        "U-16": "u16",
        "U-15": "u15",
        "U-14": "u14",
        "U-13": "u13",
        "U-12": "u12",
        "U-11": "u11",
    }
    cls = mapping.get(category, "u19")
    return f'<span class="category-badge badge-{cls}">{category}</span>'


def render_result_icon(result: str) -> str:
    icons = {"Victoria": "🟢", "Empate": "🟡", "Derrota": "🔴"}
    return icons.get(result, "⚪")


def create_performance_chart(df: pd.DataFrame, category: str):
    if df.empty or "matchdate" not in df.columns or "result" not in df.columns:
        return None
    df_sorted = df.sort_values("matchdate").reset_index(drop=True)
    pts = (df_sorted["result"] == "Victoria").astype(int) * 3 + (
        df_sorted["result"] == "Empate"
    ).astype(int)
    df_sorted["efectividad_acum"] = pts.cumsum() / ((df_sorted.index + 1) * 3) * 100
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_sorted["matchdate"],
            y=df_sorted["efectividad_acum"],
            mode="lines+markers",
            line=dict(color=OH_BLUE, width=3),
            marker=dict(size=8, color=OH_GOLD),
        )
    )
    fig.update_layout(
        title=f"Evolución de Efectividad - {category}",
        xaxis_title="Fecha",
        yaxis_title="Efectividad (%)",
        yaxis=dict(range=[0, 100]),
        height=400,
        hovermode="x unified",
        showlegend=False,
        plot_bgcolor="white",
    )
    return fig


@admin_only
def page_executive_summary():
    st.markdown(
        '<p class="section-header">📊 Resumen Ejecutivo</p>',
        unsafe_allow_html=True,
    )

    categories_overview = get_categories_overview()
    squad = get_squad_by_age_category()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            "Categorías Activas",
            len(categories_overview) if not categories_overview.empty else 0,
        )
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Jugadores Activos", len(squad) if not squad.empty else 0)
        st.markdown("</div>", unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        total_matches = (
            int(categories_overview["total_matches"].sum())
            if not categories_overview.empty
            else 0
        )
        st.metric("Partidos Disputados", total_matches)
        st.markdown("</div>", unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        professionals = (
            int((squad["level"] == "Profesional").sum())
            if not squad.empty and "level" in squad.columns
            else 0
        )
        st.metric("Jugadores Profesionales", professionals)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🏆 Vista General por Categoría")

    if not categories_overview.empty:
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("### Actividad Competitiva")
            for _, row in categories_overview.iterrows():
                cat = str(row["category"])
                comps = int(row["total_competitions"])
                matches = int(row["total_matches"])
                st.markdown(category_badge(cat), unsafe_allow_html=True)
                st.markdown(f"**{comps}** competiciones • **{matches}** partidos")
                st.markdown("")

        with col2:
            fig = px.bar(
                categories_overview,
                x="category",
                y="total_matches",
                title="Distribución de Partidos por Categoría",
                labels={"category": "Categoría", "total_matches": "Partidos"},
                color="total_matches",
                color_continuous_scale=[OH_GOLD, OH_BLUE],
            )
            fig.update_layout(
                showlegend=False,
                height=350,
                plot_bgcolor="white",
                xaxis_title="Categoría",
                yaxis_title="Partidos",
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("👥 Distribución del Plantel por Categoría")

    if not squad.empty and "age_category" in squad.columns:
        age_dist = (
            squad["age_category"]
            .value_counts()
            .reindex(ALL_CATEGORIES_ORDERED)
            .dropna()
            .astype(int)
            .reset_index()
        )
        age_dist.columns = ["Categoría", "Jugadores"]

        col1, col2 = st.columns([1, 2])
        with col1:
            st.dataframe(
                age_dist,
                hide_index=True,
                use_container_width=True,
            )
        with col2:
            fig = px.bar(
                age_dist,
                x="Categoría",
                y="Jugadores",
                title="Jugadores por Categoría",
                color="Jugadores",
                color_continuous_scale=[OH_GOLD, OH_BLUE],
            )
            fig.update_layout(
                showlegend=False,
                height=400,
                xaxis_tickangle=-45,
                plot_bgcolor="white",
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay información de categorías de edad del plantel.")


@admin_only
def page_youth_development():
    st.markdown(
        '<p class="section-header">🌱 Desarrollo Juvenil</p>',
        unsafe_allow_html=True,
    )

    squad = get_squad_by_age_category()
    selected_cat = st.selectbox(
        "Selecciona Categoría",
        YOUTH_CATEGORIES,
        key="youth_cat",
    )

    if squad.empty or "age_category" not in squad.columns:
        st.warning("No hay datos de plantel juvenil disponibles.")
        return

    squad_filtered = squad[squad["age_category"] == selected_cat]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Jugadores en Categoría", int(len(squad_filtered)))
    with col2:
        if not squad_filtered.empty and "age" in squad_filtered.columns:
            st.metric("Edad Promedio", f"{squad_filtered['age'].mean():.1f}")
        else:
            st.metric("Edad Promedio", "—")
    with col3:
        if not squad_filtered.empty and "nationality" in squad_filtered.columns:
            chilenos = (squad_filtered["nationality"] == "Chile").sum()
            pct = (chilenos / len(squad_filtered) * 100) if len(squad_filtered) else 0
            st.metric("% Chilenos", f"{pct:.0f}%")
        else:
            st.metric("% Chilenos", "—")

    st.markdown("---")

    player_stats = get_player_stats_by_category(selected_cat)
    if player_stats.empty:
        st.info(f"No hay estadísticas disponibles para {selected_cat}.")
        return

    st.subheader(f"⭐ Mejores Jugadores - {selected_cat}")

    tab1, tab2, tab3 = st.tabs(
        ["🎯 Goleadores", "⏱️ Más Utilizados", "📊 Rendimiento Global"]
    )

    with tab1:
        top_scorers = player_stats.nlargest(10, "goals")
        if top_scorers.empty:
            st.info("Sin goles registrados.")
        else:
            col1, col2 = st.columns([2, 1])
            with col1:
                fig = px.bar(
                    top_scorers,
                    x="displayname",
                    y="goals",
                    title="Top 10 Goleadores",
                    labels={"displayname": "Jugador", "goals": "Goles"},
                    color="goals",
                    color_continuous_scale=[OH_GOLD, OH_BLUE],
                )
                fig.update_layout(
                    showlegend=False,
                    xaxis_tickangle=-45,
                    plot_bgcolor="white",
                )
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.dataframe(
                    top_scorers[["displayname", "age", "goals", "matches"]].rename(
                        columns={
                            "displayname": "Jugador",
                            "age": "Edad",
                            "goals": "Goles",
                            "matches": "Partidos",
                        }
                    ),
                    hide_index=True,
                    use_container_width=True,
                )

    with tab2:
        top_minutes = player_stats.nlargest(15, "minutes")
        if top_minutes.empty:
            st.info("No hay minutos registrados.")
        else:
            top_minutes = top_minutes.copy()
            top_minutes["horas"] = (top_minutes["minutes"] / 60).round(1)
            fig = px.bar(
                top_minutes,
                x="displayname",
                y="horas",
                title="Jugadores con Más Minutos",
                labels={"displayname": "Jugador", "horas": "Horas jugadas"},
                color="matches",
                color_continuous_scale=[OH_GOLD, OH_BLUE],
            )
            fig.update_layout(xaxis_tickangle=-45, plot_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        min_matches = st.slider(
            "Mínimo de partidos",
            0,
            int(player_stats["matches"].max()),
            3,
        )
        filtered_stats = player_stats[player_stats["matches"] >= min_matches].copy()
        if filtered_stats.empty:
            st.info("Ningún jugador cumple el filtro.")
            return
        display_df = filtered_stats[
            [
                "displayname",
                "age",
                "matches",
                "minutes",
                "starts",
                "goals",
                "goals_per90",
                "yellow_cards",
                "red_cards",
            ]
        ].rename(
            columns={
                "displayname": "Jugador",
                "age": "Edad",
                "matches": "Partidos",
                "minutes": "Minutos",
                "starts": "Partidos como titular",
                "goals": "Goles",
                "goals_per90": "Goles/90",
                "yellow_cards": "Tarjetas amarillas",
                "red_cards": "Tarjetas rojas",
            }
        )
        st.dataframe(
            display_df,
            hide_index=True,
            use_container_width=True,
        )


@admin_only
def page_competition_performance():
    st.markdown(
        '<p class="section-header">🏆 Rendimiento por Categoría</p>',
        unsafe_allow_html=True,
    )

    categories_df = get_categories_overview()
    all_cats = sorted(
        set(ALL_CATEGORIES_ORDERED)
        | set(categories_df["category"].dropna().astype(str).tolist())
    )
    if not all_cats:
        st.warning("No hay datos de competiciones disponibles.")
        return

    selected_cat = st.selectbox("Selecciona Categoría", all_cats, key="comp_cat")

    standings = get_standings_by_category(selected_cat)
    matches = get_match_results_by_category(selected_cat)

    if standings.empty:
        st.info(f"No hay posiciones registradas para {selected_cat}.")
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Competiciones", int(standings["competition_name"].nunique()))
    with col2:
        avg_ef = (
            standings["efectividad"].mean() if "efectividad" in standings.columns else 0
        )
        st.metric("Efectividad promedio", f"{avg_ef:.1f}%")
    with col3:
        st.metric("Goles a favor (totales)", int(standings["goalsfor"].sum()))
    with col4:
        st.metric(
            "Diferencia de gol (total)",
            f"{int(standings['goaldifference'].sum()):+d}",
        )

    st.markdown("---")
    st.subheader("📋 Tabla de posiciones por competición")

    display_standings = standings[
        [
            "competition_name",
            "position",
            "matches",
            "wins",
            "draws",
            "losses",
            "points",
            "efectividad",
            "goalsfor",
            "goalsagainst",
            "goaldifference",
        ]
    ].rename(
        columns={
            "competition_name": "Competición",
            "position": "Posición",
            "matches": "Partidos jugados",
            "wins": "Partidos ganados",
            "draws": "Empates",
            "losses": "Derrotas",
            "points": "Puntos",
            "efectividad": "Efectividad (%)",
            "goalsfor": "Goles a favor",
            "goalsagainst": "Goles en contra",
            "goaldifference": "Diferencia de gol",
        }
    )

    st.dataframe(
        display_standings,
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("---")

    if matches.empty:
        st.info("No hay partidos registrados para esta categoría.")
        return

    st.subheader("📈 Análisis de partidos")

    matches_valid = matches.dropna(subset=["result"])
    if matches_valid.empty:
        st.info("No hay resultados completos para analizar.")
        return

    col1, col2 = st.columns([2, 1])

    with col1:
        last_10 = matches_valid.head(10)
        st.markdown("#### Últimos 10 partidos")
        cols = st.columns(len(last_10))
        for i, (_, match) in enumerate(last_10.iterrows()):
            with cols[i]:
                icon = render_result_icon(match["result"])
                gf = int(match["goals_for"])
                ga = int(match["goals_against"])
                st.markdown(
                    f"<div style='text-align:center; font-size:1.5rem'>{icon}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div style='text-align:center; font-size:0.7rem'>{gf}-{ga}</div>",
                    unsafe_allow_html=True,
                )

    with col2:
        st.markdown("#### Resumen")
        results_count = matches_valid["result"].value_counts()
        total = len(matches_valid)
        for result, count in results_count.items():
            pct = (count / total) * 100
            icon = render_result_icon(result)
            st.markdown(f"{icon} **{result}**: {count} ({pct:.1f}%)")

    perf_chart = create_performance_chart(matches_valid, selected_cat)
    if perf_chart:
        st.plotly_chart(perf_chart, use_container_width=True)


@admin_only
def page_player_analysis():
    st.markdown(
        '<p class="section-header">👤 Análisis Individual de Jugadores</p>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1, 1])
    categories_df = get_categories_overview()
    all_cats = sorted(
        set(ALL_CATEGORIES_ORDERED)
        | set(categories_df["category"].dropna().astype(str).tolist())
    )

    with col1:
        selected_cat = st.selectbox(
            "Categoría",
            ["Todas"] + all_cats,
            key="player_cat",
        )
    with col2:
        position_type = st.selectbox(
            "Tipo",
            ["Jugadores de Campo", "Arqueros"],
            key="pos_type",
        )

    if position_type == "Jugadores de Campo":
        cat_filter = None if selected_cat == "Todas" else selected_cat
        stats = get_player_stats_by_category(cat_filter)
        if stats.empty:
            st.info("No hay datos disponibles.")
            return

        col1, col2, col3 = st.columns(3)
        with col1:
            min_matches = st.slider(
                "Mínimo de partidos jugados",
                0,
                int(stats["matches"].max()),
                5,
            )
        with col2:
            nacionalidades = ["Todas"] + sorted(
                stats["nationality"].dropna().unique().tolist()
            )
            nat_filter = st.selectbox(
                "Nacionalidad",
                nacionalidades,
            )
        with col3:
            sort_by = st.selectbox(
                "Ordenar por",
                ["Minutos", "Goles", "Goles/90", "Partidos"],
            )

        filtered = stats[stats["matches"] >= min_matches].copy()
        if nat_filter != "Todas":
            filtered = filtered[filtered["nationality"] == nat_filter]

        sort_map = {
            "Minutos": "minutes",
            "Goles": "goals",
            "Goles/90": "goals_per90",
            "Partidos": "matches",
        }
        filtered = filtered.sort_values(
            sort_map[sort_by],
            ascending=False,
        )

        if filtered.empty:
            st.info("Ningún jugador cumple los filtros.")
            return

        st.subheader(f"📊 Jugadores de Campo ({len(filtered)} jugadores)")

        display_df = filtered[
            [
                "displayname",
                "age",
                "category",
                "nationality",
                "matches",
                "minutes",
                "starts",
                "goals",
                "goals_per90",
                "yellow_cards",
                "red_cards",
            ]
        ].rename(
            columns={
                "displayname": "Jugador",
                "age": "Edad",
                "category": "Categoría",
                "nationality": "País",
                "matches": "Partidos jugados",
                "minutes": "Minutos jugados",
                "starts": "Partidos como titular",
                "goals": "Goles",
                "goals_per90": "Goles/90",
                "yellow_cards": "Tarjetas amarillas",
                "red_cards": "Tarjetas rojas",
            }
        )

        st.dataframe(
            display_df,
            hide_index=True,
            use_container_width=True,
        )

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            top_10 = filtered.head(10)
            fig = px.scatter(
                top_10,
                x="minutes",
                y="goals_per90",
                size="goals",
                hover_name="displayname",
                title="Eficiencia goleadora (Top 10)",
                labels={
                    "minutes": "Minutos jugados",
                    "goals_per90": "Goles/90",
                },
                color="goals",
                color_continuous_scale=[OH_GOLD, OH_BLUE],
            )
            fig.update_layout(plot_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            if selected_cat != "Todas":
                fig2 = px.bar(
                    filtered.head(10),
                    x="displayname",
                    y="minutes",
                    title=f"Top 10 minutos jugados - {selected_cat}",
                    labels={
                        "displayname": "Jugador",
                        "minutes": "Minutos jugados",
                    },
                    color="starts",
                    color_continuous_scale=[OH_GOLD, OH_BLUE],
                )
                fig2.update_layout(
                    xaxis_tickangle=-45,
                    showlegend=False,
                    plot_bgcolor="white",
                )
                st.plotly_chart(fig2, use_container_width=True)

    else:
        cat_filter = None if selected_cat == "Todas" else selected_cat
        gk_stats = get_goalkeeper_stats_by_category(cat_filter)
        if gk_stats.empty:
            st.info("No hay datos de arqueros disponibles.")
            return

        st.subheader(f"🥅 Arqueros ({len(gk_stats)} arqueros)")

        display_df = gk_stats[
            [
                "displayname",
                "age",
                "category",
                "matches",
                "minutes",
                "goals_conceded",
                "gc_per90",
                "clean_sheets",
                "clean_sheet_pct",
            ]
        ].rename(
            columns={
                "displayname": "Arquero",
                "age": "Edad",
                "category": "Categoría",
                "matches": "Partidos jugados",
                "minutes": "Minutos jugados",
                "goals_conceded": "Goles recibidos",
                "gc_per90": "Goles recibidos/90",
                "clean_sheets": "Vallas invictas",
                "clean_sheet_pct": "% vallas invictas",
            }
        )

        st.dataframe(
            display_df,
            hide_index=True,
            use_container_width=True,
        )

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            fig = px.bar(
                gk_stats,
                x="displayname",
                y="gc_per90",
                title="Goles recibidos por 90 minutos",
                labels={"displayname": "Arquero", "gc_per90": "Goles/90"},
                color="gc_per90",
                color_continuous_scale=[OH_GREEN, OH_RED],
            )
            fig.update_layout(
                xaxis_tickangle=-45,
                showlegend=False,
                plot_bgcolor="white",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.bar(
                gk_stats,
                x="displayname",
                y="clean_sheet_pct",
                title="Porcentaje de vallas invictas",
                labels={
                    "displayname": "Arquero",
                    "clean_sheet_pct": "% vallas invictas",
                },
                color="clean_sheet_pct",
                color_continuous_scale=[OH_GOLD, OH_BLUE],
            )
            fig.update_layout(
                xaxis_tickangle=-45,
                showlegend=False,
                plot_bgcolor="white",
            )
            st.plotly_chart(fig, use_container_width=True)


@admin_only
def page_squad_structure():
    st.markdown(
        '<p class="section-header">🏗️ Estructura del Plantel</p>',
        unsafe_allow_html=True,
    )

    squad = get_squad_by_age_category()
    if squad.empty:
        st.warning("No hay datos del plantel.")
        return

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total jugadores", int(len(squad)))
    with col2:
        if "age" in squad.columns:
            st.metric("Edad promedio", f"{squad['age'].mean():.1f}")
        else:
            st.metric("Edad promedio", "—")
    with col3:
        pros = (
            int((squad["level"] == "Profesional").sum())
            if "level" in squad.columns
            else 0
        )
        st.metric("Profesionales", pros)
    with col4:
        if "age" in squad.columns:
            u21 = int((squad["age"] <= 21).sum())
            st.metric("Sub-21", u21)
        else:
            st.metric("Sub-21", "—")
    with col5:
        if "nationality" in squad.columns:
            ch = int((squad["nationality"] == "Chile").sum())
            pct = (ch / len(squad) * 100) if len(squad) else 0
            st.metric("% Chilenos", f"{pct:.0f}%")
        else:
            st.metric("% Chilenos", "—")

    st.markdown("---")
    st.subheader("📊 Distribución del plantel")

    col1, col2 = st.columns([2, 1])

    with col1:
        if "age" in squad.columns:
            squad_age = squad.copy()
            age_bins = [0, 12, 14, 16, 19, 25, 35, 100]
            age_labels = ["<12", "12-14", "15-16", "17-19", "20-25", "26-35", "35+"]
            squad_age["age_group"] = pd.cut(
                squad_age["age"],
                bins=age_bins,
                labels=age_labels,
                right=False,
            )
            age_dist = squad_age["age_group"].value_counts().sort_index().reset_index()
            age_dist.columns = ["Grupo de edad", "Jugadores"]
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    y=age_dist["Grupo de edad"].astype(str),
                    x=age_dist["Jugadores"],
                    orientation="h",
                    marker=dict(
                        color=age_dist["Jugadores"],
                        colorscale=[[0, OH_GOLD], [0.5, OH_BLUE], [1, OH_DARK]],
                    ),
                )
            )
            fig.update_layout(
                xaxis_title="Cantidad de jugadores",
                yaxis_title="Grupo de edad",
                height=400,
                showlegend=False,
                plot_bgcolor="white",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos de edad para construir la pirámide.")

    with col2:
        if "age_category" in squad.columns:
            cat_dist = (
                squad["age_category"]
                .value_counts()
                .reindex(ALL_CATEGORIES_ORDERED)
                .dropna()
                .astype(int)
                .reset_index()
            )
            cat_dist.columns = ["Categoría", "Jugadores"]
            for _, row in cat_dist.iterrows():
                st.markdown(
                    category_badge(row["Categoría"]),
                    unsafe_allow_html=True,
                )
                st.markdown(f"**{row['Jugadores']}** jugadores")
                st.markdown("")
        else:
            st.info("No hay datos de categoría de edad.")

    st.markdown("---")
    st.subheader("📋 Plantel completo")

    col1, col2, col3 = st.columns(3)
    with col1:
        cat_options = ["Todas"] + ALL_CATEGORIES_ORDERED
        cat_filter = st.selectbox("Categoría", cat_options, key="squad_cat")
    with col2:
        if "nationality" in squad.columns:
            nat_options = ["Todas"] + sorted(
                squad["nationality"].dropna().unique().tolist()
            )
        else:
            nat_options = ["Todas"]
        nat_filter = st.selectbox("Nacionalidad", nat_options, key="squad_nat")
    with col3:
        if "level" in squad.columns:
            level_options = ["Todas"] + sorted(
                squad["level"].dropna().unique().tolist()
            )
        else:
            level_options = ["Todas"]
        level_filter = st.selectbox("Nivel", level_options, key="squad_level")

    filtered_squad = squad.copy()
    if cat_filter != "Todas" and "age_category" in filtered_squad.columns:
        filtered_squad = filtered_squad[filtered_squad["age_category"] == cat_filter]
    if nat_filter != "Todas" and "nationality" in filtered_squad.columns:
        filtered_squad = filtered_squad[filtered_squad["nationality"] == nat_filter]
    if level_filter != "Todas" and "level" in filtered_squad.columns:
        filtered_squad = filtered_squad[filtered_squad["level"] == level_filter]

    cols = []
    rename = {}
    if "displayname" in filtered_squad.columns:
        cols.append("displayname")
        rename["displayname"] = "Jugador"
    if "age" in filtered_squad.columns:
        cols.append("age")
        rename["age"] = "Edad"
    if "age_category" in filtered_squad.columns:
        cols.append("age_category")
        rename["age_category"] = "Categoría"
    if "nationality" in filtered_squad.columns:
        cols.append("nationality")
        rename["nationality"] = "Nacionalidad"
    if "level" in filtered_squad.columns:
        cols.append("level")
        rename["level"] = "Nivel"

    if cols:
        display_squad = filtered_squad[cols].rename(columns=rename)
        st.dataframe(
            display_squad,
            hide_index=True,
            use_container_width=True,
        )
        st.caption(f"Mostrando {len(filtered_squad)} de {len(squad)} jugadores.")
    else:
        st.info("No hay columnas suficientes para mostrar el plantel.")
