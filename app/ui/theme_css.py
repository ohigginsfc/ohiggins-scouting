"""CSS global O'Higgins para Streamlit (sin dependencias de theme.py)."""

from __future__ import annotations


def build_ohiggins_css() -> str:
    """Devuelve el bloque CSS completo envuelto en etiquetas <style>."""
    OHIGGINS_BLUE = "#5091CD"
    OHIGGINS_GREEN = "#49A942"
    OHIGGINS_YELLOW = "#FFDD00"
    OHIGGINS_BLACK = "#000000"
    OHIGGINS_WHITE = "#FFFFFF"
    OHIGGINS_LIGHT_BG = "#F4F8FC"
    OHIGGINS_CARD_BG = "#FFFFFF"
    OHIGGINS_BORDER = "#D7E3EF"
    OHIGGINS_TEXT = "#111827"
    OHIGGINS_MUTED_TEXT = "#64748B"
    OHIGGINS_BLUE_DARK = "#3D7AB5"
    OHIGGINS_BLUE_LIGHT = "#E8F2FA"
    OHIGGINS_GREEN_LIGHT = "#EAF6E9"
    OHIGGINS_YELLOW_LIGHT = "#FFF9CC"
    OHIGGINS_ORANGE = "#F59E0B"
    OHIGGINS_FONT = '"Handel Gothic BT", "Arial", "Helvetica", sans-serif'

    return f"""<style>
    /* ── Global full-width layout ── */
    html, body, .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    section.main {{
        width: 100% !important;
        max-width: none !important;
        box-sizing: border-box !important;
    }}
    html, body,
    [data-testid="stAppViewContainer"],
    .stApp {{
        overflow-x: hidden !important;
        background-color: #F5F7FA !important;
        color-scheme: light !important;
    }}
    .stApp {{
        font-family: {OHIGGINS_FONT};
        color: {OHIGGINS_TEXT};
        --background-color: #eaf2fb !important;
        --secondary-background-color: #ffffff !important;
        --text-color: #111827 !important;
        --primary-color: #ff4b4b !important;
    }}
    [data-testid="stAppViewContainer"] > section.main,
    section.main {{
        margin-left: 0 !important;
        margin-right: 0 !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
    }}
    .block-container,
    .main .block-container,
    [data-testid="stMainBlockContainer"],
    section.main [data-testid="stMainBlockContainer"],
    section.main .block-container,
    .stMainBlockContainer {{
        width: 100% !important;
        max-width: none !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        padding-top: 0.85rem !important;
        padding-bottom: 2rem !important;
        box-sizing: border-box !important;
    }}

    /* ── Typography ── */
    h1 {{
        color: {OHIGGINS_BLACK} !important;
        border-left: 6px solid {OHIGGINS_BLUE};
        padding-left: 12px;
        letter-spacing: -0.03em;
        font-weight: 700 !important;
    }}
    h2, h3 {{
        color: {OHIGGINS_TEXT} !important;
        border-bottom: 1px solid {OHIGGINS_BORDER};
        padding-bottom: 0.35rem;
    }}
    h2 {{
        margin-top: 0.25rem !important;
    }}

    /* ── Sidebar eliminada: ocultar por completo ── */
    section[data-testid="stSidebar"],
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarNav"],
    [data-testid="stSidebarResizeHandle"] {{
        display: none !important;
        width: 0 !important;
        min-width: 0 !important;
        max-width: 0 !important;
        visibility: hidden !important;
        pointer-events: none !important;
    }}

    /* ── Cabecera superior compacta ── */
    .scouting-top-header {{
        width: 100%;
        min-height: 78px;
        max-height: 90px;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        gap: 24px;
        padding: 10px 4px;
        box-sizing: border-box;
    }}
    .scouting-brand {{
        display: flex;
        align-items: center;
        gap: 18px;
        min-width: 0;
    }}
    .scouting-brand-logo {{
        display: block;
        object-fit: contain;
        flex-shrink: 0;
        width: auto;
        height: auto;
    }}
    .scouting-campus-logo {{
        width: 170px;
        max-width: 180px;
        max-height: 54px;
    }}
    .scouting-club-logo {{
        width: 55px;
        max-width: 58px;
        max-height: 62px;
    }}
    .scouting-brand-title {{
        margin-left: 12px;
        white-space: nowrap;
        font-size: 1.05rem;
        font-weight: 700;
        color: #111827;
        line-height: 1.2;
    }}
    .scouting-top-user {{
        margin: 0 !important;
        font-size: 0.86rem !important;
        font-weight: 600 !important;
        color: #64748B !important;
        text-align: right !important;
        line-height: 1.2 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-end !important;
        min-height: 2rem !important;
    }}
    .scouting-top-divider {{
        border: none !important;
        border-top: 1px solid #D7E3EF !important;
        margin: 0.35rem 0 0.55rem 0 !important;
        width: 100% !important;
        max-width: none !important;
    }}
    .scouting-pitch-chip {{
        display: inline-block;
        padding: 0.35rem 0.65rem;
        border-radius: 8px;
        background: #E8F2FA;
        color: #3D7AB5;
        border: 1px solid #5091CD;
        font-size: 0.88rem;
        line-height: 1.3;
    }}
    .stApp .st-key-dashboard_pitch_chart {{
        width: 100%;
        max-width: 1120px;
        margin-left: auto;
        margin-right: auto;
    }}
    .stApp .st-key-dashboard_pitch_chart [data-testid="stPlotlyChart"] {{
        width: 100%;
    }}
    /* Estilos de navegación por key (no usar :has sobre VerticalBlock raíz) */
    .stApp [class*="st-key-nav_"] .stButton > button,
    .stApp [class*="st-key-nav_"] .stButton > button[kind="secondary"],
    .stApp [class*="st-key-nav_"] .stButton > button[data-testid="baseButton-secondary"] {{
        background-color: #ffffff !important;
        color: #111827 !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 999px !important;
        box-shadow: none !important;
        font-size: 0.84rem !important;
        font-weight: 600 !important;
        min-height: 2.15rem !important;
        padding: 0.28rem 0.55rem !important;
        white-space: nowrap !important;
    }}
    .stApp [class*="st-key-nav_"] .stButton > button:hover {{
        background-color: #f8fafc !important;
        color: #111827 !important;
        border-color: #94a3b8 !important;
    }}
    .stApp [class*="st-key-nav_"] .stButton > button[kind="primary"],
    .stApp [class*="st-key-nav_"] .stButton > button[data-testid="baseButton-primary"] {{
        background-color: #ff4b4b !important;
        color: #ffffff !important;
        border: 1px solid #ff4b4b !important;
        border-radius: 999px !important;
        box-shadow: none !important;
        font-weight: 700 !important;
    }}
    .stApp [class*="st-key-nav_"] .stButton > button[kind="primary"]:hover {{
        background-color: #e04343 !important;
        border-color: #e04343 !important;
        color: #ffffff !important;
    }}
    .stApp .st-key-top_header_logout {{
        display: flex !important;
        justify-content: flex-end !important;
        align-items: center !important;
    }}
    .stApp .st-key-top_header_logout .stButton {{
        width: auto !important;
    }}
    .stApp .st-key-top_header_logout .stButton > button {{
        width: auto !important;
        min-width: unset !important;
        font-size: 0.8rem !important;
        min-height: 2rem !important;
        padding: 0.25rem 0.75rem !important;
        border-radius: 8px !important;
        white-space: nowrap !important;
    }}
    @media (max-width: 1100px) {{
        .scouting-top-header {{
            min-height: 72px;
            max-height: none;
            padding: 8px 2px;
        }}
        .scouting-campus-logo {{
            width: 140px;
            max-height: 46px;
        }}
        .scouting-club-logo {{
            width: 48px;
            max-height: 54px;
        }}
        .scouting-brand {{
            gap: 12px;
        }}
        .scouting-brand-title {{
            margin-left: 4px;
            font-size: 0.95rem;
        }}
        .stApp [class*="st-key-nav_"] .stButton > button {{
            font-size: 0.74rem !important;
            padding: 0.22rem 0.2rem !important;
        }}
    }}
    @media (max-width: 720px) {{
        .scouting-brand {{
            flex-wrap: wrap;
            gap: 10px;
        }}
        .scouting-brand-title {{
            margin-left: 0;
            white-space: normal;
        }}
    }}

    /* ── Metrics (main area only; dashboard KPIs) ── */
    section.main div[data-testid="stMetric"],
    .main div[data-testid="stMetric"] {{
        background: {OHIGGINS_CARD_BG};
        border: 1px solid {OHIGGINS_BORDER};
        border-radius: 12px;
        padding: 0.65rem 0.85rem;
        box-shadow: 0 1px 3px rgba(80, 145, 205, 0.06);
        min-height: 4.5rem;
    }}
    section.main div[data-testid="stMetric"] label,
    .main div[data-testid="stMetric"] label {{
        color: {OHIGGINS_BLUE} !important;
        font-weight: 600 !important;
        font-size: 0.78rem !important;
        white-space: normal !important;
    }}
    section.main div[data-testid="stMetric"] [data-testid="stMetricValue"],
    .main div[data-testid="stMetric"] [data-testid="stMetricValue"],
    section.main div[data-testid="stMetric"] [data-testid="stMetricValue"] > div,
    .main div[data-testid="stMetric"] [data-testid="stMetricValue"] > div {{
        color: {OHIGGINS_BLACK} !important;
        font-weight: 700 !important;
        font-size: clamp(1rem, 1.5vw, 1.45rem) !important;
        line-height: 1.15 !important;
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: unset !important;
        word-break: normal !important;
    }}

    /* No estilizar contenedores Streamlit genéricos como cards */

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0.35rem;
        border-bottom: 2px solid {OHIGGINS_BORDER};
    }}
    .stTabs [data-baseweb="tab"] {{
        color: {OHIGGINS_MUTED_TEXT} !important;
        font-weight: 600 !important;
        border-radius: 8px 8px 0 0 !important;
        padding: 0.5rem 1rem !important;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        color: {OHIGGINS_BLUE} !important;
        background: {OHIGGINS_BLUE_LIGHT} !important;
    }}
    .stTabs [aria-selected="true"] {{
        color: {OHIGGINS_WHITE} !important;
        background: {OHIGGINS_BLUE} !important;
    }}
    .stTabs [aria-selected="true"]:hover {{
        color: {OHIGGINS_WHITE} !important;
        background: {OHIGGINS_BLUE_DARK} !important;
    }}

    /* ── Expanders ── */
    details[data-testid="stExpander"] {{
        background: {OHIGGINS_CARD_BG};
        border: 1px solid {OHIGGINS_BORDER} !important;
        border-radius: 12px !important;
        overflow: hidden;
    }}
    details[data-testid="stExpander"] summary {{
        color: {OHIGGINS_BLUE} !important;
        font-weight: 600 !important;
        padding: 0.65rem 1rem !important;
        background: {OHIGGINS_BLUE_LIGHT};
    }}
    details[data-testid="stExpander"] summary:hover {{
        background: {OHIGGINS_BLUE_LIGHT};
        color: {OHIGGINS_BLUE_DARK} !important;
    }}
    details[data-testid="stExpander"] > div {{
        padding: 0.75rem 1rem 1rem 1rem !important;
        border-top: 1px solid {OHIGGINS_BORDER};
    }}

    /* ── Alerts ── */
    div[data-testid="stAlert"] {{
        border-radius: 10px !important;
        border-width: 1px !important;
    }}
    div[data-testid="stAlert"][data-baseweb="notification"] {{
        border-radius: 10px !important;
    }}
    .stAlert[data-baseweb="notification"] div[role="alert"] {{
        border-radius: 10px !important;
    }}
    div[data-testid="stNotificationContentInfo"],
    div[data-testid="stAlert"]:has(svg[data-testid="stIconMaterialInfo"]) {{
        background-color: {OHIGGINS_BLUE_LIGHT} !important;
        border-color: {OHIGGINS_BLUE} !important;
        color: {OHIGGINS_TEXT} !important;
    }}
    div[data-testid="stNotificationContentSuccess"],
    div[data-testid="stAlert"]:has(svg[data-testid="stIconMaterialCheck"]) {{
        background-color: {OHIGGINS_GREEN_LIGHT} !important;
        border-color: {OHIGGINS_GREEN} !important;
        color: {OHIGGINS_TEXT} !important;
    }}
    div[data-testid="stNotificationContentWarning"],
    div[data-testid="stAlert"]:has(svg[data-testid="stIconMaterialWarning"]) {{
        background-color: {OHIGGINS_YELLOW_LIGHT} !important;
        border-color: {OHIGGINS_YELLOW} !important;
        color: {OHIGGINS_BLACK} !important;
    }}

    /* ── Form labels ── */
    .stTextInput label,
    .stNumberInput label,
    .stSelectbox label,
    .stMultiSelect label,
    .stTextArea label,
    .stDateInput label,
    .stTimeInput label,
    .stSlider label,
    .stCheckbox label,
    section.main .stRadio label,
    section.main [data-testid="stWidgetLabel"] {{
        color: {OHIGGINS_TEXT} !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
    }}
    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea,
    .stDateInput input,
    .stSelectbox div[data-baseweb="select"] > div {{
        background-color: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        caret-color: #111827 !important;
        border-color: #cbd5e1 !important;
        border-radius: 8px !important;
    }}
    .stTextInput input::placeholder,
    .stNumberInput input::placeholder,
    .stTextArea textarea::placeholder {{
        color: #6b7280 !important;
        -webkit-text-fill-color: #6b7280 !important;
        opacity: 1 !important;
    }}
    .stTextInput input:focus,
    .stNumberInput input:focus,
    .stTextArea textarea:focus {{
        border-color: {OHIGGINS_BLUE} !important;
        box-shadow: 0 0 0 1px {OHIGGINS_BLUE} !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        caret-color: #111827 !important;
    }}

    /* ── Dataframes / tables ── */
    div[data-testid="stDataFrame"],
    div[data-testid="stDataEditor"] {{
        border: 1px solid {OHIGGINS_BORDER};
        border-radius: 10px;
        overflow: auto;
        background: #ffffff !important;
        color: #111827 !important;
        color-scheme: light !important;
    }}

    /* ── Dividers ── */
    hr.section-hr {{
        margin: 1.5rem 0;
        border: none;
        border-top: 1px solid {OHIGGINS_BORDER};
    }}

    /* ── Reusable O'Higgins card system ── */
    .oh-card {{
        background: {OHIGGINS_CARD_BG};
        border: 1px solid {OHIGGINS_BORDER};
        border-radius: 14px;
        padding: 1rem 1.15rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 4px rgba(80, 145, 205, 0.08);
    }}
    .oh-card-title {{
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: {OHIGGINS_BLUE};
        margin: 0 0 0.35rem 0;
    }}
    .oh-card-value {{
        font-size: clamp(1rem, 1.4vw, 1.35rem);
        font-weight: 700;
        color: {OHIGGINS_BLACK};
        margin: 0;
        line-height: 1.15;
        white-space: normal;
        overflow: visible;
        text-overflow: unset;
        word-break: normal;
    }}
    .oh-ficha-field {{
        background: {OHIGGINS_CARD_BG};
        border: 1px solid {OHIGGINS_BORDER};
        border-radius: 10px;
        padding: 0.45rem 0.6rem;
        margin-bottom: 0.4rem;
        min-height: 3.5rem;
        box-shadow: 0 1px 2px rgba(80, 145, 205, 0.05);
    }}
    .oh-ficha-label {{
        font-size: clamp(0.75rem, 0.85vw, 0.85rem);
        font-weight: 600;
        color: {OHIGGINS_BLUE};
        margin: 0 0 0.2rem 0;
        line-height: 1.2;
    }}
    .oh-ficha-value {{
        font-size: clamp(1.1rem, 1.4vw, 1.8rem);
        font-weight: 700;
        color: {OHIGGINS_BLACK};
        margin: 0;
        line-height: 1.15;
        white-space: normal;
        overflow: visible;
        text-overflow: unset;
        word-break: normal;
    }}
    .oh-ficha-value-long {{
        font-size: clamp(0.95rem, 1.15vw, 1.25rem);
        font-weight: 600;
        line-height: 1.25;
    }}
    .oh-ficha-shell {{
        border: 1px solid {OHIGGINS_BORDER};
        border-radius: 14px;
        padding: 1rem 1.1rem;
        background: {OHIGGINS_CARD_BG};
        box-shadow: 0 1px 4px rgba(80, 145, 205, 0.07);
    }}
    .oh-section {{
        margin: 1.25rem 0;
    }}
    .oh-section-title {{
        font-size: 0.95rem;
        font-weight: 700;
        color: {OHIGGINS_BLUE};
        margin: 0 0 0.65rem 0;
        padding-bottom: 0.35rem;
        border-bottom: 2px solid {OHIGGINS_BORDER};
    }}
    .oh-chip {{
        display: inline-block;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 0.15rem 0.55rem;
        border-radius: 999px;
        line-height: 1.3;
        margin-right: 0.35rem;
    }}
    .oh-chip-blue {{
        background: {OHIGGINS_BLUE_LIGHT};
        color: {OHIGGINS_BLUE_DARK};
        border: 1px solid {OHIGGINS_BLUE};
    }}
    .oh-chip-green {{
        background: {OHIGGINS_GREEN_LIGHT};
        color: #1B5E20;
        border: 1px solid {OHIGGINS_GREEN};
    }}
    .oh-chip-yellow {{
        background: {OHIGGINS_YELLOW_LIGHT};
        color: {OHIGGINS_BLACK};
        border: 1px solid {OHIGGINS_YELLOW};
    }}
    .oh-metric-card {{
        background: {OHIGGINS_CARD_BG};
        border: 1px solid {OHIGGINS_BORDER};
        border-radius: 14px;
        padding: 0.85rem 1rem;
        box-shadow: 0 1px 3px rgba(80, 145, 205, 0.08);
    }}
    .oh-player-header {{
        font-size: 1.5rem;
        font-weight: 700;
        color: {OHIGGINS_TEXT};
        letter-spacing: -0.02em;
        margin: 0 0 0.5rem 0;
    }}
    .oh-report-summary {{
        background: linear-gradient(180deg, {OHIGGINS_LIGHT_BG} 0%, {OHIGGINS_BLUE_LIGHT} 100%);
        border: 1px solid {OHIGGINS_BORDER};
        border-left: 4px solid {OHIGGINS_BLUE};
        border-radius: 14px;
        padding: 1rem 1.15rem;
        margin: 1rem 0;
    }}
    .oh-strength-card {{
        background: {OHIGGINS_GREEN_LIGHT};
        border: 1px solid {OHIGGINS_GREEN};
        border-radius: 12px;
        padding: 0.85rem 1rem;
    }}
    .oh-weakness-card {{
        background: #FEE2E2;
        border: 1px solid #FCA5A5;
        border-radius: 12px;
        padding: 0.85rem 1rem;
    }}

    /* ── Main header block ── */
    .main-header h1 {{
        letter-spacing: -0.04em;
        font-weight: 700;
        font-size: 2rem;
        line-height: 1.15;
        margin-bottom: 0.15rem;
        border-bottom: none;
        border-left: 6px solid {OHIGGINS_BLUE};
        padding-left: 12px;
        color: {OHIGGINS_BLACK};
    }}
    .main-header .main-subtitle {{
        color: {OHIGGINS_MUTED_TEXT};
        font-size: 0.95rem;
        margin: 0 0 0.35rem 0;
        font-weight: 400;
    }}

    /* ── Star ratings ── */
    .star-rating-row {{
        display: flex;
        align-items: center;
        gap: 0.45rem;
        margin: 0.1rem 0 0.4rem 0;
    }}
    .star-rating-wrap {{
        position: relative;
        display: inline-block;
        font-size: 1.08rem;
        line-height: 1;
        letter-spacing: 0.08em;
        font-family: Georgia, "Times New Roman", serif;
    }}
    .star-rating-wrap--four {{
        max-width: 5.2em;
    }}
    .stars-fill {{
        position: absolute;
        left: 0;
        top: 0;
        height: 100%;
        overflow: hidden;
        white-space: nowrap;
        color: {OHIGGINS_BLUE};
        text-shadow: none;
    }}
    .star-rating-num {{
        font-size: 0.72rem;
        color: {OHIGGINS_MUTED_TEXT};
        font-variant-numeric: tabular-nums;
    }}
    .form-star-preview .star-rating-wrap {{ font-size: 1.22rem; }}
    .form-star-preview .star-rating-num {{ font-size: 0.68rem; }}
    .group-summary-stars .star-rating-wrap {{ font-size: 1.42rem; }}
    .group-summary-stars .star-rating-row {{ margin-top: 0.35rem; }}
    .manual-form-big-stars .star-rating-wrap {{ font-size: 1.55rem; letter-spacing: 0.1em; }}
    .manual-form-big-stars .star-rating-row {{ margin: 0.15rem 0 0.4rem 0; justify-content: flex-start; }}
    .manual-form-big-stars .star-rating-num {{ display: none; }}
    .manual-rating-note {{
        font-size: 0.72rem;
        color: {OHIGGINS_MUTED_TEXT};
        text-align: center;
        margin: 0.35rem 0 0 0;
        font-variant-numeric: tabular-nums;
    }}
    .manual-rating-ctrl {{ margin-top: 0.25rem; }}

    /* ── Attribute cards ── */
    .attr-card {{
        border: none;
        border-radius: 10px;
        padding: 0.55rem 0.65rem;
        margin-bottom: 0.45rem;
        background: {OHIGGINS_LIGHT_BG};
        border-left: 3px solid {OHIGGINS_BORDER};
    }}
    .attr-card-title {{
        font-size: 0.82rem;
        font-weight: 600;
        color: {OHIGGINS_TEXT};
        margin-bottom: 0.15rem;
    }}
    .summary-attr-mini {{
        border: 1px solid {OHIGGINS_BORDER};
        border-radius: 8px;
        padding: 0.4rem 0.5rem;
        margin-bottom: 0.35rem;
        background: {OHIGGINS_LIGHT_BG};
    }}
    .summary-rc {{
        font-size: 0.7rem;
        color: {OHIGGINS_MUTED_TEXT};
        margin: 0.2rem 0 0 0;
        font-variant-numeric: tabular-nums;
    }}

    /* ── Player photo placeholder ── */
    .player-photo-placeholder {{
        min-height: 220px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: {OHIGGINS_LIGHT_BG};
        border: 1px dashed {OHIGGINS_BORDER};
        border-radius: 10px;
        color: {OHIGGINS_MUTED_TEXT};
        font-size: 0.95rem;
        font-weight: 500;
    }}

    /* ── Percentile metrics ── */
    .pct-metric-card {{
        background: {OHIGGINS_CARD_BG};
        border: 1px solid {OHIGGINS_BORDER};
        border-radius: 14px;
        padding: 0.65rem 0.85rem 0.6rem 0.85rem;
        margin-bottom: 0.45rem;
        box-shadow: 0 1px 3px rgba(80, 145, 205, 0.08);
    }}
    .pct-metric-title {{
        font-weight: 600;
        font-size: 0.95rem;
        color: {OHIGGINS_TEXT};
        margin: 0 0 0.5rem 0;
        line-height: 1.25;
    }}
    .pct-strip-zone {{
        margin: 0 0 0.55rem 0;
        padding: 0.15rem 0;
        overflow: visible;
    }}
    .pct-interp {{
        display: block;
        font-size: 0.82rem;
        color: {OHIGGINS_MUTED_TEXT};
        margin-top: 0.25rem;
        line-height: 1.35;
    }}
    .pct-strip-wrap {{
        position: relative;
        height: 16px;
        border-radius: 999px;
        overflow: visible;
        margin: 0;
        background: {OHIGGINS_LIGHT_BG};
    }}
    .pct-strip-wrap--single {{
        height: 20px;
    }}
    .pct-strip-wrap--dual {{
        height: 24px;
    }}
    .pct-strip-gradient {{
        position: absolute;
        inset: 0;
        border-radius: 999px;
        overflow: hidden;
        background: linear-gradient(
            90deg,
            #dc2626 0%,
            {OHIGGINS_ORANGE} 25%,
            {OHIGGINS_YELLOW} 50%,
            #7BC96F 75%,
            {OHIGGINS_GREEN} 100%
        );
        opacity: 0.85;
    }}
    .pct-marker {{
        position: absolute;
        top: 50%;
        z-index: 4;
        transform: translate(-50%, -50%);
    }}
    .pct-marker--single {{
        width: 22px;
        height: 22px;
        background: #000000;
        border: 3px solid {OHIGGINS_WHITE};
        border-radius: 50%;
        box-shadow: 0 0 0 1.5px #000000, 0 2px 6px rgba(15, 23, 42, 0.45);
    }}
    .pct-marker--dual {{
        width: 20px;
        height: 20px;
        border: 3px solid {OHIGGINS_WHITE};
        border-radius: 50%;
        box-shadow: 0 0 0 1.5px #000000, 0 2px 5px rgba(15, 23, 42, 0.4);
    }}
    .pct-marker--diamond {{
        width: 18px;
        height: 18px;
        border: 3px solid {OHIGGINS_WHITE};
        border-radius: 3px;
        box-shadow: 0 0 0 1.5px #000000, 0 2px 5px rgba(15, 23, 42, 0.4);
    }}
    .pct-marker-label,
    .pct-marker-label--dual {{
        display: none !important;
    }}
    .cmp-legend-shape {{
        display: inline-block;
        width: 12px;
        height: 12px;
        margin-right: 0.35rem;
        vertical-align: middle;
        border: 2px solid {OHIGGINS_WHITE};
        box-shadow: 0 0 0 1px #000000;
    }}
    .cmp-legend-shape--circle {{
        border-radius: 50%;
    }}
    .cmp-legend-shape--diamond {{
        border-radius: 2px;
        transform: rotate(45deg);
        margin-right: 0.45rem;
    }}
    .pct-badge {{
        display: inline-block;
        font-weight: 700;
        font-size: 0.88rem;
        padding: 0.12rem 0.45rem;
        border-radius: 6px;
        color: {OHIGGINS_WHITE};
        margin-right: 0.35rem;
    }}
    .pct-value-line {{
        font-size: 0.88rem;
        color: {OHIGGINS_MUTED_TEXT};
        margin: 0.15rem 0 0 0;
    }}
    .pct-metric-card--compact {{
        padding: 14px 18px !important;
        margin-bottom: 0.35rem !important;
    }}
    .pct-metric-card--compact .pct-metric-title {{
        margin: 0 0 0.35rem 0 !important;
        font-size: 0.9rem !important;
    }}
    .pct-metric-card--compact .pct-strip-zone {{
        margin: 0 0 0.4rem 0 !important;
    }}
    .pct-summary-line {{
        font-size: 0.88rem;
        font-weight: 600;
        color: {OHIGGINS_TEXT};
        margin: 0.15rem 0 0.1rem 0;
        line-height: 1.3;
    }}
    .pct-summary-line .pct-badge {{
        margin-right: 0.15rem;
    }}
    /* Radares subjetivos */
    .subjective-radar-legend-once {{
        font-size: 0.8rem;
        color: {OHIGGINS_MUTED_TEXT};
        margin: 0 0 0.35rem 0;
        line-height: 1.3;
    }}
    .subjective-radar-legend-swatch {{
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 0.2rem;
        vertical-align: middle;
    }}
    .subjective-radar-legend-swatch--player {{
        background: {OHIGGINS_BLUE};
        margin-left: 0;
    }}
    .subjective-radar-legend-swatch--cohort {{
        background: #475569;
        margin-left: 0.65rem;
    }}
    [data-testid="stVerticalBlock"]:has(.subjective-radar-blocks-marker) [data-testid="stPlotlyChart"] > div {{
        height: 460px !important;
        min-height: 460px !important;
        max-height: 460px !important;
    }}
    [data-testid="stVerticalBlock"]:has(.subjective-radar-blocks-marker) [data-testid="stPlotlyChart"] {{
        margin: 0.15rem 0 0.25rem 0 !important;
    }}
    [data-testid="stVerticalBlock"]:has(.subjective-radar-detail-grid-marker) [data-testid="stPlotlyChart"] > div {{
        height: 400px !important;
        min-height: 400px !important;
        max-height: 400px !important;
    }}
    [data-testid="stVerticalBlock"]:has(.subjective-radar-detail-grid-marker) [data-testid="stPlotlyChart"] {{
        margin: 0 0 0.2rem 0 !important;
    }}
    [data-testid="stVerticalBlock"]:has(.subjective-radars-section-marker) h4,
    [data-testid="stVerticalBlock"]:has(.subjective-radars-section-marker) h5 {{
        margin-top: 0.35rem !important;
        margin-bottom: 0.25rem !important;
    }}
    hr.section-hr--tight {{
        margin: 0.65rem 0 0.5rem 0 !important;
    }}
    .cmp-radar-legend-once {{
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.65rem 1.25rem;
        font-size: 0.88rem;
        color: {OHIGGINS_TEXT};
        margin: 0 0 0.75rem 0;
        padding: 0.45rem 0 0.35rem 0;
        line-height: 1.4;
    }}
    .cmp-radar-legend-once .cmp-legend-item {{
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        font-weight: 600;
    }}
    .cmp-radar-legend-once .cmp-legend-item strong {{
        font-weight: 700;
    }}
    .cmp-radar-legend-note {{
        font-size: 0.8rem;
        font-weight: 500;
        color: {OHIGGINS_MUTED_TEXT};
    }}
    [data-testid="stVerticalBlock"]:has(.cmp-objective-radar-marker) [data-testid="stPlotlyChart"] > div {{
        height: 460px !important;
        min-height: 460px !important;
        max-height: 460px !important;
    }}
    [data-testid="stVerticalBlock"]:has(.cmp-objective-radar-marker) [data-testid="stPlotlyChart"] {{
        margin: 0 0 0.35rem 0 !important;
    }}
    .cmp-pct-card {{
        display: flex;
        flex-direction: column;
        background: {OHIGGINS_CARD_BG};
        border: 1px solid {OHIGGINS_BLACK};
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 0.35rem;
        box-shadow: none;
        overflow: visible;
    }}
    .cmp-pct-card .pct-metric-title {{
        margin: 0;
        flex-shrink: 0;
    }}
    .cmp-pct-strip-block {{
        margin-top: 6px;
        margin-bottom: 10px;
        width: 100%;
        flex-shrink: 0;
        position: relative;
        overflow: visible;
    }}
    .cmp-pct-strip-block .pct-strip-zone {{
        margin: 0;
        padding: 0.15rem 0;
        overflow: visible;
    }}
    .cmp-pct-marker {{
        position: absolute;
        top: 50%;
        transform: translate(-50%, -50%);
        border: 3px solid {OHIGGINS_WHITE} !important;
        box-shadow: 0 0 0 1.5px #000000, 0 2px 4px rgba(15, 23, 42, 0.35);
    }}
    .cmp-pct-marker.pct-marker--diamond {{
        transform: translate(-50%, -50%) rotate(45deg);
    }}
    .cmp-pct-legend {{
        display: flex;
        flex-direction: column;
        gap: 0.45rem;
        margin: 0;
        font-size: 0.84rem;
        color: {OHIGGINS_TEXT};
        line-height: 1.5;
    }}
    .cmp-pct-legend-line {{
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.3rem;
        margin: 0;
        line-height: 1.5;
    }}
    .cmp-pct-legend-line strong {{
        font-weight: 700;
    }}
    .cmp-pct-summary {{
        margin: 12px 0 0 0;
        font-size: 0.82rem;
        font-weight: 600;
        color: {OHIGGINS_MUTED_TEXT};
        line-height: 1.4;
    }}
    .cmp-pct-direction-chip {{
        display: inline-block;
        margin-top: 8px;
        font-size: 0.72rem;
        font-weight: 600;
        color: {OHIGGINS_MUTED_TEXT};
        background: {OHIGGINS_LIGHT_BG};
        border: 1px solid {OHIGGINS_BORDER};
        border-radius: 6px;
        padding: 0.15rem 0.45rem;
        line-height: 1.35;
        align-self: flex-start;
    }}
    .cmp-pct-meta {{
        display: flex;
        flex-direction: column;
        gap: 0.35rem;
        font-size: 0.82rem;
        color: {OHIGGINS_TEXT};
        margin: 0.15rem 0 0.35rem 0;
        line-height: 1.4;
    }}
    .cmp-pct-meta-line {{
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.25rem;
    }}
    .cmp-pct-meta-line strong {{
        font-weight: 700;
    }}
    .cmp-pct-meta-oh {{
        color: {OHIGGINS_BLUE};
    }}
    .cmp-pct-meta-cmp {{
        color: {OHIGGINS_GREEN};
    }}
    .cmp-pct-vs {{
        display: block;
        font-size: 0.8rem;
        font-weight: 600;
        color: {OHIGGINS_MUTED_TEXT};
        margin-top: 0.1rem;
    }}
    .cmp-legend {{
        display: flex;
        gap: 1rem;
        margin: 0.2rem 0 0.8rem 0;
        font-size: 0.9rem;
        color: {OHIGGINS_BLACK};
    }}
    .cmp-legend-item {{
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        font-weight: 700;
    }}
    .cmp-legend-dot {{
        width: 0.75rem;
        height: 0.75rem;
        border-radius: 50%;
        border: 1px solid {OHIGGINS_BLACK};
        display: inline-block;
    }}
    .cmp-identity-card {{
        border: 2px solid {OHIGGINS_BLACK};
        border-radius: 12px;
        overflow: hidden;
        background: {OHIGGINS_WHITE};
        min-height: 11.5rem;
    }}
    .cmp-identity-head {{
        color: {OHIGGINS_WHITE};
        font-weight: 700;
        font-size: 0.85rem;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        padding: 0.45rem 0.7rem;
    }}
    .cmp-identity-body {{
        padding: 0.7rem;
        color: {OHIGGINS_BLACK};
    }}
    .cmp-identity-role {{
        font-size: 0.8rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }}
    .cmp-identity-name {{
        font-size: 1.1rem;
        font-weight: 700;
        line-height: 1.2;
        margin-bottom: 0.25rem;
    }}
    .cmp-identity-line {{
        font-size: 0.9rem;
        line-height: 1.25;
        margin-bottom: 0.15rem;
    }}
    .cmp-vs-wrap {{
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .cmp-vs {{
        font-size: 1rem;
        font-weight: 800;
        border: 1px solid {OHIGGINS_BLACK};
        border-radius: 999px;
        padding: 0.28rem 0.75rem;
    }}
    .cmp-table-wrap table {{
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        background: {OHIGGINS_WHITE};
        border: 1px solid {OHIGGINS_BORDER};
        border-radius: 12px;
        overflow: hidden;
    }}
    .cmp-table-wrap th {{
        text-align: left;
        padding: 0.55rem 0.65rem;
        font-size: 0.83rem;
        font-weight: 700;
        color: {OHIGGINS_BLACK};
        background: {OHIGGINS_LIGHT_BG};
        border-bottom: 1px solid {OHIGGINS_BORDER};
    }}
    .cmp-table-wrap td {{
        padding: 0.5rem 0.65rem;
        border-bottom: 1px solid {OHIGGINS_BORDER};
        vertical-align: middle;
    }}
    .cmp-table-wrap tbody tr:last-child td {{
        border-bottom: none;
    }}
    .cmp-col-metric {{
        font-weight: 600;
        color: {OHIGGINS_BLACK};
        min-width: 12rem;
    }}
    .cmp-table-cell {{
        border: 1px solid {OHIGGINS_BORDER};
        border-radius: 8px;
        padding: 0.35rem 0.45rem;
        background: {OHIGGINS_WHITE};
    }}
    .cmp-owner-oh .cmp-table-value {{
        color: {OHIGGINS_BLUE};
        font-weight: 700;
    }}
    .cmp-owner-cmp .cmp-table-value {{
        color: {OHIGGINS_GREEN};
        font-weight: 700;
    }}
    .cmp-winner-oh {{
        border-color: {OHIGGINS_BLUE} !important;
        box-shadow: inset 0 0 0 1px {OHIGGINS_BLUE};
    }}
    .cmp-winner-cmp {{
        border-color: {OHIGGINS_GREEN} !important;
        box-shadow: inset 0 0 0 1px {OHIGGINS_GREEN};
    }}
    .cmp-table-value-line {{
        display: flex;
        align-items: center;
        gap: 0.35rem;
        font-size: 0.88rem;
        line-height: 1.1;
        margin-bottom: 0.3rem;
    }}
    .cmp-pct-badge {{
        display: inline-block;
        padding: 0.08rem 0.38rem;
        border-radius: 999px;
        color: {OHIGGINS_BLACK};
        font-size: 0.74rem;
        font-weight: 800;
        border: 1px solid rgba(0, 0, 0, 0.18);
    }}
    .cmp-table-pct-track {{
        width: 100%;
        height: 0.38rem;
        border-radius: 999px;
        background: #E5E7EB;
        overflow: hidden;
    }}
    .cmp-table-pct-fill {{
        height: 100%;
        border-radius: 999px;
    }}
    .cmp-col-diff {{
        font-weight: 800;
        white-space: nowrap;
    }}
    .cmp-diff-positive {{
        color: {OHIGGINS_GREEN};
    }}
    .cmp-diff-positive-soft {{
        color: #7BC96F;
    }}
    .cmp-diff-negative {{
        color: #DC2626;
    }}
    .cmp-diff-negative-soft {{
        color: #F87171;
    }}
    .cmp-diff-neutral {{
        color: #64748B;
    }}
    .cmp-diff-arrow {{
        font-size: 0.92rem;
        margin-left: 0.1rem;
    }}

    /* ── Scout / executive ficha ── */
    .scout-section-label {{
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: {OHIGGINS_MUTED_TEXT};
        margin: 0.5rem 0 0.25rem 0;
    }}
    .ficha-report-summary {{
        margin-top: 0.85rem;
        padding-top: 0.85rem;
        border-top: 1px solid {OHIGGINS_BORDER};
    }}
    .ficha-report-summary h5 {{
        margin: 0 0 0.5rem 0;
        font-size: 0.95rem;
        font-weight: 600;
        color: {OHIGGINS_TEXT};
    }}
    .executive-ficha-name {{
        font-size: 1.65rem;
        font-weight: 700;
        color: {OHIGGINS_TEXT};
        letter-spacing: -0.02em;
        margin: 0 0 0.75rem 0;
        line-height: 1.2;
    }}
    .executive-ficha-divider {{
        border: none;
        border-top: 1px solid {OHIGGINS_BORDER};
        margin: 0.85rem 0;
    }}
    .scout-summary-box {{
        background: linear-gradient(180deg, {OHIGGINS_LIGHT_BG} 0%, {OHIGGINS_BLUE_LIGHT} 100%);
        border: 1px solid {OHIGGINS_BORDER};
        border-left: 4px solid {OHIGGINS_BLUE};
        border-radius: 14px;
        padding: 1rem 1.15rem;
        margin: 1rem 0 1.25rem 0;
    }}
    .scout-summary-label {{
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: {OHIGGINS_MUTED_TEXT};
        margin: 0 0 0.5rem 0;
    }}
    .scout-summary-text {{
        font-size: 1rem;
        line-height: 1.55;
        color: {OHIGGINS_TEXT};
        margin: 0;
        white-space: pre-wrap;
    }}
    .sw-column-title {{
        font-size: 0.95rem;
        font-weight: 700;
        color: {OHIGGINS_TEXT};
        margin: 0 0 0.5rem 0;
        padding-bottom: 0.35rem;
        border-bottom: 2px solid {OHIGGINS_BORDER};
    }}
    .sw-column-body {{
        font-size: 0.92rem;
        line-height: 1.55;
        color: {OHIGGINS_TEXT};
    }}
</style>"""


def build_login_css() -> str:
    """CSS aislado para pantalla de login (sidebar oculto, tarjeta = st.form)."""
    return """<style>
    .stApp:has(.scouting-login-page) {
        background: var(--app-bg, #F4F7FB) !important;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .stApp:has(.scouting-login-page) section[data-testid="stSidebar"],
    .stApp:has(.scouting-login-page) [data-testid="collapsedControl"] {
        display: none !important;
    }
    .stApp:has(.scouting-login-page) [data-testid="stAppViewContainer"] > section.main {
        margin-left: 0 !important;
        width: 100% !important;
        max-width: none !important;
    }
    .stApp:has(.scouting-login-page) .main .block-container {
        max-width: none !important;
        padding-top: 7vh !important;
        padding-bottom: 4vh !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    .scouting-login-page { display: none !important; }
    /* Tarjeta única: key estable login_form (evita div HTML vacío) */
    .stApp:has(.scouting-login-page) .st-key-login_form {
        width: 100% !important;
        max-width: 480px !important;
        margin: 0 auto !important;
        background: #FFFFFF !important;
        border: 1px solid #E4E7EC !important;
        border-radius: 16px !important;
        box-shadow: 0 8px 24px rgba(16, 24, 40, 0.08) !important;
        padding: 2rem 2.15rem 1.75rem !important;
        box-sizing: border-box !important;
    }
    /* Si stForm queda anidado dentro del wrapper con key, no duplicar la tarjeta */
    .stApp:has(.scouting-login-page) .st-key-login_form [data-testid="stForm"] {
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
        max-width: none !important;
    }
    /* Fallback si la key está en el propio stForm */
    .stApp:has(.scouting-login-page) [data-testid="stForm"].st-key-login_form,
    .stApp:has(.scouting-login-page) .st-key-login_form[data-testid="stForm"] {
        border: 1px solid #E4E7EC !important;
        background: #FFFFFF !important;
        box-shadow: 0 8px 24px rgba(16, 24, 40, 0.08) !important;
        padding: 2rem 2.15rem 1.75rem !important;
    }
    .stApp:has(.scouting-login-page) [data-testid="stHorizontalBlock"] > div:nth-child(2) {
        min-width: 0 !important;
    }
    .scouting-login-header { text-align: center; margin: 0 0 1rem 0; }
    .scouting-login-logos {
        display: flex; align-items: center; justify-content: center;
        gap: 0.9rem; margin-bottom: 0.85rem;
    }
    .scouting-login-sport-logo {
        max-height: 2.5rem; max-width: 160px; width: auto; object-fit: contain;
    }
    .scouting-login-crest {
        max-height: 3rem; max-width: 52px; width: auto; object-fit: contain;
    }
    .stApp:has(.scouting-login-page) .scouting-login-title {
        color: #101828 !important; border: none !important; padding-left: 0 !important;
        margin: 0 0 0.3rem 0 !important; font-size: clamp(1.35rem, 4vw, 1.65rem) !important;
        font-weight: 700 !important; line-height: 1.25 !important; white-space: nowrap;
        letter-spacing: -0.02em; text-align: center;
    }
    .stApp:has(.scouting-login-page) .scouting-login-subtitle {
        color: #667085; font-size: 0.92rem; margin: 0; text-align: center;
    }
    .stApp:has(.scouting-login-page) [data-testid="stFormSubmitButton"] button {
        background: #4F8FCC !important; color: #FFFFFF !important;
        border: 1px solid #4F8FCC !important; border-radius: 10px !important;
        min-height: 42px !important; font-weight: 650 !important; width: 100% !important;
    }
    .stApp:has(.scouting-login-page) [data-testid="stFormSubmitButton"] button:hover {
        background: #2F6FAE !important; border-color: #2F6FAE !important;
    }
    /* Inputs login: siempre legibles con SO en modo oscuro */
    .stApp:has(.scouting-login-page) .stTextInput input,
    .stApp:has(.scouting-login-page) [data-baseweb="input"] input {
        background-color: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        caret-color: #111827 !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
    }
    .stApp:has(.scouting-login-page) .stTextInput input::placeholder,
    .stApp:has(.scouting-login-page) [data-baseweb="input"] input::placeholder {
        color: #6b7280 !important;
        -webkit-text-fill-color: #6b7280 !important;
        opacity: 1 !important;
    }
    .stApp:has(.scouting-login-page) .stTextInput input:focus,
    .stApp:has(.scouting-login-page) [data-baseweb="input"] input:focus {
        border-color: #4F8FCC !important;
        box-shadow: 0 0 0 1px #4F8FCC !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        caret-color: #111827 !important;
    }
    .stApp:has(.scouting-login-page) .stTextInput input:-webkit-autofill,
    .stApp:has(.scouting-login-page) .stTextInput input:-webkit-autofill:hover,
    .stApp:has(.scouting-login-page) .stTextInput input:-webkit-autofill:focus,
    .stApp:has(.scouting-login-page) .stTextInput input:-webkit-autofill:active,
    .stApp:has(.scouting-login-page) [data-baseweb="input"] input:-webkit-autofill,
    .stApp:has(.scouting-login-page) [data-baseweb="input"] input:-webkit-autofill:hover,
    .stApp:has(.scouting-login-page) [data-baseweb="input"] input:-webkit-autofill:focus,
    .stApp:has(.scouting-login-page) [data-baseweb="input"] input:-webkit-autofill:active {
        -webkit-text-fill-color: #111827 !important;
        caret-color: #111827 !important;
        box-shadow: 0 0 0 1000px #ffffff inset !important;
        -webkit-box-shadow: 0 0 0 1000px #ffffff inset !important;
        transition: background-color 99999s ease-in-out 0s;
    }
    .stApp:has(.scouting-login-page) .scouting-login-error {
        margin: 0 0 0.85rem 0; padding: 0.65rem 0.8rem; border-radius: 8px;
        background: #FEF3F2; color: #B42318; border: 1px solid #FECDCA;
        font-size: 0.88rem; font-weight: 550; text-align: center;
    }
    @media (max-width: 720px) {
        .stApp:has(.scouting-login-page) .main .block-container { padding-top: 3vh !important; }
        .stApp:has(.scouting-login-page) .st-key-login_form {
            max-width: 100% !important;
            padding: 1.35rem 1.15rem 1.2rem !important;
        }
        .stApp:has(.scouting-login-page) [data-testid="stHorizontalBlock"] > div:nth-child(1),
        .stApp:has(.scouting-login-page) [data-testid="stHorizontalBlock"] > div:nth-child(3) {
            display: none !important;
        }
    }
</style>
"""
