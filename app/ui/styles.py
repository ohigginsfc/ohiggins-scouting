"""
Sistema visual moderno (2026) — capa de diseño SaaS.

Selectores internos de Streamlit documentados:
- [data-testid="stAppViewContainer"]  fondo app
- [data-testid="stMainBlockContainer"] / .block-container  layout full-width
- [data-testid="stSidebar"] (+ variantes)  ocultar sidebar
- [data-testid="stMetric"]  KPIs nativos (si se usan)
- [data-testid="stDataFrame"]  tablas
- [data-testid="baseButton-primary|secondary"]  botones
- [data-testid="stExpander"]  expanders
- .stTabs [data-baseweb="tab"]  pestañas
- .st-key-*  widgets por key (nav_, top_header_logout, dashboard_pitch_chart, …)

No se usan :has() sobre stVerticalBlock genéricos para layout.
"""

from __future__ import annotations


def build_design_system_css() -> str:
    """CSS del sistema de diseño: tokens, chrome, botones, tablas, componentes."""
    return """
<style>
:root {
    --app-bg: #E8F0F8;
    --surface: #FFFFFF;
    --surface-alt: #F5F9FC;
    --surface-subtle: #F5F9FC;
    --surface-hover: #E4EEF7;

    --text-primary: #101828;
    --text-secondary: #667085;
    --text-muted: #98A2B3;

    --border-soft: #E4E7EC;
    --border-strong: #D0D5DD;

    /* Identidad O'Higgins / Sports Data Campus */
    --brand-blue: #4F8FCC;
    --brand-blue-strong: #2F6FAE;
    --brand-blue-soft: #EAF3FB;
    --brand-green: #49A942;
    --brand-green-soft: #EDF8EC;
    --brand-yellow: #F2D335;
    --brand-yellow-soft: #FFF8DB;

    --primary: var(--brand-blue);
    --primary-hover: var(--brand-blue-strong);
    --primary-soft: var(--brand-blue-soft);
    --primary-ink: #1E4F7A;

    --success: var(--brand-green);
    --success-soft: var(--brand-green-soft);
    --warning: #B54708;
    --warning-soft: var(--brand-yellow-soft);
    --danger: #D92D20;
    --danger-soft: #FEF3F2;
    --info-soft: #EEF4FF;

    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;

    --shadow-sm: 0 1px 3px rgba(16, 24, 40, 0.08);
    --shadow-md: 0 8px 24px rgba(16, 24, 40, 0.08);

    --space-xs: 4px;
    --space-sm: 8px;
    --space-md: 16px;
    --space-lg: 24px;
    --space-xl: 32px;
    --space-2xl: 48px;

    --font-sans: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif;
    --btn-height: 40px;
}

/* ── Layout full-width ── */
html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
section.main {
    width: 100% !important;
    max-width: none !important;
    box-sizing: border-box !important;
}
html, body,
[data-testid="stAppViewContainer"],
.stApp {
    overflow-x: hidden !important;
    background: var(--app-bg) !important;
    color-scheme: light !important;
}
.stApp {
    /* Tokens nativos Streamlit: anclar tema claro (no heredar SO oscuro). */
    --background-color: #eaf2fb !important;
    --secondary-background-color: #ffffff !important;
    --text-color: #111827 !important;
    --primary-color: #ff4b4b !important;
}
.stApp, .stApp p, .stApp label, .stApp span,
.stApp [data-testid="stMarkdownContainer"] {
    font-family: var(--font-sans) !important;
    color: var(--text-primary);
}
[data-testid="stAppViewContainer"] > section.main,
section.main {
    margin-left: 0 !important;
    margin-right: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
}
[data-testid="stMainBlockContainer"],
.stMainBlockContainer,
.main .block-container,
.block-container,
section.main .block-container {
    width: 100% !important;
    max-width: none !important;
    margin: 0 !important;
    padding: 1.25rem 2rem 3rem !important;
    box-sizing: border-box !important;
}

/* Sidebar oculto */
section[data-testid="stSidebar"],
[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarNav"],
[data-testid="stSidebarResizeHandle"] {
    display: none !important;
    width: 0 !important;
    min-width: 0 !important;
    max-width: 0 !important;
    visibility: hidden !important;
    pointer-events: none !important;
}

/* Tipografía de página: sin barra lateral ni subrayados pesados */
.stApp h1, .stApp h2, .stApp h3 {
    border: none !important;
    border-left: none !important;
    border-bottom: none !important;
    padding-left: 0 !important;
    color: var(--text-primary) !important;
    letter-spacing: -0.02em;
    font-family: var(--font-sans) !important;
}
.stApp h2 { font-size: 1.45rem !important; font-weight: 700 !important; margin: 0 0 0.15rem 0 !important; }
.stApp h3 { font-size: 1.1rem !important; font-weight: 650 !important; }
.stApp h4, .stApp h5 { color: var(--text-primary) !important; font-weight: 600 !important; }

/* ── Cabecera superior (banda única) ── */
.scouting-chrome-brand {
    display: flex;
    align-items: center;
    min-height: 64px;
    padding: 0.35rem 0;
}
.scouting-brand {
    display: flex;
    align-items: center;
    gap: 14px;
    min-width: 0;
}
.scouting-brand-logo {
    display: block;
    object-fit: contain;
    flex-shrink: 0;
    width: auto;
    height: auto;
}
.scouting-campus-logo {
    width: 150px;
    max-width: 160px;
    max-height: 42px;
}
.scouting-club-logo {
    width: 44px;
    max-width: 48px;
    max-height: 48px;
}
.scouting-brand-copy {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    min-width: 0;
}
.scouting-brand-title {
    white-space: nowrap;
    font-size: 1.08rem;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.2;
    letter-spacing: -0.02em;
}
.scouting-brand-title::after {
    content: "";
    display: inline-block;
    width: 7px;
    height: 7px;
    margin-left: 0.4rem;
    border-radius: 50%;
    background: var(--brand-yellow);
    vertical-align: middle;
}
.scouting-brand-subtitle {
    font-size: 0.75rem;
    color: var(--text-secondary);
    font-weight: 500;
    letter-spacing: 0.01em;
}
.scouting-chrome-session {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    min-height: 1.6rem;
    margin-bottom: 0.25rem;
}
.scouting-user-chip {
    display: inline-flex;
    align-items: center;
    padding: 0.22rem 0.7rem;
    border-radius: 999px;
    background: var(--brand-blue-soft);
    color: var(--brand-blue-strong);
    font-size: 0.8rem;
    font-weight: 650;
    line-height: 1.2;
    border: none;
}
.scouting-top-header,
.scouting-top-user,
.scouting-top-divider,
.scouting-nav-row {
    display: none !important;
}
.scouting-nav-strip {
    height: 0;
    margin: 0.55rem 0 0.15rem 0;
    border: none;
    border-top: 1px solid rgba(79, 143, 204, 0.18);
}

/* Navegación: colores explícitos (no heredar tema oscuro de Streamlit) */
.stApp [class*="st-key-nav_"] .stButton > button,
.stApp [class*="st-key-nav_"] .stButton > button[kind="secondary"],
.stApp [class*="st-key-nav_"] .stButton > button[data-testid="baseButton-secondary"] {
    background-color: #ffffff !important;
    background-image: none !important;
    color: #111827 !important;
    border: 1px solid #cbd5e1 !important;
    border-color: #cbd5e1 !important;
    border-radius: 999px !important;
    box-shadow: none !important;
    font-size: 0.82rem !important;
    font-weight: 550 !important;
    min-height: 2.15rem !important;
    height: auto !important;
    padding: 0.4rem 0.65rem !important;
    white-space: nowrap !important;
    line-height: 1.2 !important;
}
.stApp [class*="st-key-nav_"] .stButton > button:hover,
.stApp [class*="st-key-nav_"] .stButton > button:focus {
    background-color: #f8fafc !important;
    color: #111827 !important;
    border-color: #94a3b8 !important;
}
.stApp [class*="st-key-nav_"] .stButton > button:focus-visible {
    outline: 2px solid #4f9bd8 !important;
    outline-offset: 2px !important;
}
.stApp [class*="st-key-nav_"] .stButton > button:active {
    background-color: #eaf2fb !important;
    color: #111827 !important;
    border-color: #94a3b8 !important;
}
.stApp [class*="st-key-nav_"] .stButton > button:disabled,
.stApp [class*="st-key-nav_"] .stButton > button[disabled] {
    background-color: #f1f5f9 !important;
    color: #94a3b8 !important;
    border-color: #e2e8f0 !important;
    opacity: 1 !important;
}
/* Pestaña activa: coral/rojo de la app (nunca negro) */
.stApp [class*="st-key-nav_"] .stButton > button[kind="primary"],
.stApp [class*="st-key-nav_"] .stButton > button[data-testid="baseButton-primary"] {
    background-color: #ff4b4b !important;
    background-image: none !important;
    color: #ffffff !important;
    border: 1px solid #ff4b4b !important;
    border-color: #ff4b4b !important;
    border-radius: 999px !important;
    box-shadow: none !important;
    font-size: 0.82rem !important;
    font-weight: 650 !important;
    min-height: 2.15rem !important;
    height: auto !important;
    padding: 0.4rem 0.65rem !important;
    white-space: nowrap !important;
    line-height: 1.2 !important;
}
.stApp [class*="st-key-nav_"] .stButton > button[kind="primary"]:hover,
.stApp [class*="st-key-nav_"] .stButton > button[data-testid="baseButton-primary"]:hover,
.stApp [class*="st-key-nav_"] .stButton > button[kind="primary"]:focus,
.stApp [class*="st-key-nav_"] .stButton > button[data-testid="baseButton-primary"]:focus,
.stApp [class*="st-key-nav_"] .stButton > button[kind="primary"]:active,
.stApp [class*="st-key-nav_"] .stButton > button[data-testid="baseButton-primary"]:active {
    background-color: #e04343 !important;
    color: #ffffff !important;
    border-color: #e04343 !important;
}
.stApp .st-key-top_header_logout {
    display: flex !important;
    justify-content: flex-end !important;
}
.stApp .st-key-top_header_logout .stButton {
    width: auto !important;
    margin-left: auto !important;
}
.stApp .st-key-top_header_logout .stButton > button {
    width: auto !important;
    min-width: unset !important;
    background: transparent !important;
    color: var(--text-secondary) !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 0.78rem !important;
    font-weight: 550 !important;
    min-height: 2rem !important;
    padding: 0.28rem 0.55rem !important;
    white-space: nowrap !important;
    box-shadow: none !important;
}
.stApp .st-key-top_header_logout .stButton > button:hover {
    background: var(--brand-blue-soft) !important;
    color: var(--brand-blue-strong) !important;
}

/* ── Botones globales (jerarquía) ── */
.stApp section.main .stButton > button,
.stApp section.main [data-testid="baseButton-secondary"],
.stApp section.main [data-testid="baseButton-primary"] {
    border-radius: 10px !important;
    min-height: var(--btn-height) !important;
    padding: 0.4rem 1rem !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    box-shadow: none !important;
    transition: background 0.12s ease, border-color 0.12s ease, color 0.12s ease;
}
.stApp section.main [data-testid="baseButton-primary"],
.stApp section.main .stButton > button[kind="primary"] {
    background: var(--primary) !important;
    color: #FFFFFF !important;
    border: 1px solid var(--primary) !important;
}
.stApp section.main [data-testid="baseButton-primary"]:hover,
.stApp section.main .stButton > button[kind="primary"]:hover {
    background: var(--primary-hover) !important;
    border-color: var(--primary-hover) !important;
}
/* Descarga de datos: siempre primario azul (nunca peligro) */
.stApp [class*="st-key-dashboard_sports_primary"] .stButton > button,
.stApp [class*="st-key-admin_sports_primary"] .stButton > button {
    background: var(--primary) !important;
    color: #FFFFFF !important;
    border: 1px solid var(--primary) !important;
}
.stApp [class*="st-key-dashboard_sports_primary"] .stButton > button:hover,
.stApp [class*="st-key-admin_sports_primary"] .stButton > button:hover {
    background: var(--primary-hover) !important;
    border-color: var(--primary-hover) !important;
}
.scouting-sports-summary {
    font-size: 0.86rem;
    color: var(--text-secondary);
    margin: 0.2rem 0 0.15rem;
    font-weight: 500;
}
.stApp section.main [data-testid="baseButton-secondary"],
.stApp section.main .stButton > button[kind="secondary"] {
    background: var(--surface) !important;
    color: var(--text-primary) !important;
    border: none !important;
    box-shadow: 0 0 0 1px var(--border-soft) !important;
}
.stApp section.main [data-testid="baseButton-secondary"]:hover,
.stApp section.main .stButton > button[kind="secondary"]:hover {
    background: var(--surface-hover) !important;
    box-shadow: 0 0 0 1px var(--border-strong) !important;
}
.stApp section.main .stButton > button:focus-visible {
    outline: 2px solid var(--primary) !important;
    outline-offset: 2px !important;
}
/* Peligro: solo keys explícitas de eliminación */
.stApp [class*="st-key-dashboard_delete_permanent"] .stButton > button,
.stApp [class*="st-key-hidden_delete_permanent"] .stButton > button {
    background: var(--danger-soft) !important;
    color: var(--danger) !important;
    border: 1px solid #FECDCA !important;
}
.stApp [class*="st-key-dashboard_delete_permanent"] .stButton > button:hover,
.stApp [class*="st-key-hidden_delete_permanent"] .stButton > button:hover {
    background: #FEE4E2 !important;
    border-color: var(--danger) !important;
}
.stApp [class*="st-key-hidden_restore"] .stButton > button,
.stApp [class*="st-key-pitch_clear"] .stButton > button {
    background: transparent !important;
    color: var(--primary-ink) !important;
    border: 1px solid transparent !important;
    box-shadow: none !important;
}
.stApp [class*="st-key-hidden_restore"] .stButton > button:hover,
.stApp [class*="st-key-pitch_clear"] .stButton > button:hover {
    background: var(--primary-soft) !important;
}

/* ── Page / section headers ── */
.scouting-icon {
    display: inline-block;
    vertical-align: middle;
    flex-shrink: 0;
    color: var(--brand-blue);
}
.scouting-icon-wrap {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    line-height: 0;
}
.scouting-icon-glyph {
    font-size: 0.95rem;
    color: var(--brand-blue);
}
.scouting-page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-md);
    margin: 0.35rem 0 var(--space-lg) 0;
    padding: 0 0 0.65rem 0;
    border-bottom: none;
}
.scouting-page-title-row {
    display: flex;
    align-items: center;
    gap: 0.55rem;
}
.scouting-page-title-row .scouting-icon-wrap {
    width: 2.1rem;
    height: 2.1rem;
    border-radius: 10px;
    background: var(--brand-blue-soft);
    color: var(--brand-blue-strong);
}
.scouting-page-title {
    margin: 0 !important;
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    letter-spacing: -0.025em;
    border: none !important;
}
.scouting-page-subtitle {
    margin: 0.35rem 0 0 2.65rem !important;
    font-size: 0.92rem !important;
    color: var(--text-secondary) !important;
    line-height: 1.4;
    font-weight: 450 !important;
}
.scouting-section-header {
    margin: 1.35rem 0 0.75rem 0;
    padding-left: 0.65rem;
    border-left: 3px solid var(--brand-blue);
}
.scouting-section-title-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
}
.scouting-section-title {
    margin: 0 !important;
    font-size: 1.05rem !important;
    font-weight: 650 !important;
    color: var(--text-primary) !important;
    border: none !important;
}
.scouting-section-subtitle {
    margin: 0.2rem 0 0 0 !important;
    font-size: 0.84rem !important;
    color: var(--text-secondary) !important;
}

/* ── Metric cards (sin borde doble: solo franja + superficie) ── */
.scouting-metric-card {
    position: relative;
    background: var(--surface);
    border: none;
    border-radius: var(--radius-md);
    padding: 1rem 1.1rem 1rem 1.15rem;
    min-height: 5.8rem;
    box-shadow: var(--shadow-sm);
    box-sizing: border-box;
    overflow: hidden;
}
.scouting-metric-card::before {
    content: "";
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 4px;
    background: var(--brand-blue);
}
.scouting-metric-card--blue::before { background: var(--brand-blue); }
.scouting-metric-card--green::before { background: var(--brand-green); }
.scouting-metric-card--yellow::before { background: var(--brand-yellow); }
.scouting-metric-card--slate::before { background: #64748B; }
.scouting-metric-card--info::before { background: #6B9BD1; }
.scouting-metric-card--blue { background: linear-gradient(180deg, #FFFFFF 0%, #F7FBFE 100%); }
.scouting-metric-card--green { background: linear-gradient(180deg, #FFFFFF 0%, #F7FCF6 100%); }
.scouting-metric-card--yellow { background: linear-gradient(180deg, #FFFFFF 0%, #FFFCF0 100%); }
.scouting-metric-card--slate { background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%); }
.scouting-metric-card--info { background: linear-gradient(180deg, #FFFFFF 0%, #F5F8FC 100%); }
.scouting-metric-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin-bottom: 0.45rem;
}
.scouting-metric-label {
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--text-secondary);
    letter-spacing: 0.01em;
}
.scouting-metric-card .scouting-icon-wrap {
    width: 1.7rem;
    height: 1.7rem;
    border-radius: 8px;
    background: var(--brand-blue-soft);
    color: var(--brand-blue-strong);
}
.scouting-metric-card--green .scouting-icon-wrap {
    background: var(--brand-green-soft);
    color: var(--brand-green);
}
.scouting-metric-card--yellow .scouting-icon-wrap {
    background: var(--brand-yellow-soft);
    color: #9A7B00;
}
.scouting-metric-value {
    font-size: 1.65rem;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.15;
    letter-spacing: -0.03em;
    font-variant-numeric: tabular-nums;
}
.scouting-metric-helper {
    margin: 0.35rem 0 0 0;
    font-size: 0.75rem;
    color: var(--text-muted);
}
.scouting-metric-trend {
    margin-left: 0.35rem;
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--brand-green);
}

/* Badges */
.scouting-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.28rem;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 650;
    line-height: 1.25;
    margin-right: 0.35rem;
    white-space: nowrap;
}
.scouting-badge .scouting-icon { color: currentColor; }
.scouting-badge--neutral { background: #F2F4F7; color: #344054; }
.scouting-badge--info { background: var(--brand-blue-soft); color: var(--brand-blue-strong); }
.scouting-badge--success { background: var(--brand-green-soft); color: #2F7A2C; }
.scouting-badge--warning { background: var(--brand-yellow-soft); color: #9A7B00; }
.scouting-badge--danger { background: var(--danger-soft); color: #B42318; }
.scouting-badge--violet { background: var(--info-soft); color: #3B6BB5; }

/* Empty state */
.scouting-empty-state {
    background: linear-gradient(180deg, #FFFFFF 0%, #F0F6FB 100%);
    border: none;
    border-radius: var(--radius-md);
    padding: 1.75rem 1.25rem;
    text-align: center;
    margin: 0.5rem 0 1rem 0;
    box-shadow: var(--shadow-sm);
}
.scouting-empty-icon {
    margin: 0 auto 0.55rem auto;
    width: 2.6rem;
    height: 2.6rem;
    border-radius: 12px;
    background: var(--brand-blue-soft);
    color: var(--brand-blue-strong);
    display: flex;
    align-items: center;
    justify-content: center;
}
.scouting-empty-title {
    margin: 0;
    font-size: 0.98rem;
    font-weight: 650;
    color: var(--text-primary);
}
.scouting-empty-desc {
    margin: 0.35rem auto 0;
    max-width: 34rem;
    font-size: 0.86rem;
    color: var(--text-secondary);
    line-height: 1.45;
}
.scouting-empty-action-hint {
    margin: 0.55rem 0 0 0;
    font-size: 0.8rem;
    color: var(--brand-blue-strong);
    font-weight: 600;
}

/* Player header */
.scouting-player-header {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    background: linear-gradient(135deg, #FFFFFF 0%, #F0F6FB 100%);
    border: none;
    border-left: 4px solid var(--brand-blue);
    border-radius: var(--radius-md);
    padding: 1rem 1.15rem;
    margin: 0 0 1rem 0;
    box-shadow: var(--shadow-sm);
}
.scouting-player-title-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.35rem;
}
.scouting-player-title-row .scouting-icon-wrap {
    width: 2rem;
    height: 2rem;
    border-radius: 10px;
    background: var(--brand-blue-soft);
    color: var(--brand-blue-strong);
}
.scouting-player-name {
    margin: 0 !important;
    font-size: 1.35rem !important;
    font-weight: 700 !important;
    border: none !important;
}
.scouting-player-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem 1rem;
}
.scouting-player-meta-item {
    font-size: 0.84rem;
    color: var(--text-primary);
}
.scouting-player-meta-label {
    color: var(--text-muted);
    font-weight: 550;
    margin-right: 0.15rem;
}
.scouting-player-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    align-items: center;
}

.scouting-info-item {
    background: var(--surface-subtle);
    border: 1px solid var(--border-soft);
    border-radius: var(--radius-sm);
    padding: 0.55rem 0.7rem;
    margin-bottom: 0.45rem;
}
.scouting-info-label {
    display: block;
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--text-secondary);
    margin-bottom: 0.15rem;
}
.scouting-info-value {
    display: block;
    font-size: 0.95rem;
    font-weight: 650;
    color: var(--text-primary);
}

.scouting-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem 0.75rem;
    margin: 0.35rem 0 0.75rem 0;
}
.scouting-flash {
    border-radius: var(--radius-sm);
    padding: 0.7rem 0.9rem;
    margin: 0 0 0.85rem 0;
    font-size: 0.88rem;
    font-weight: 550;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}
.scouting-flash--success {
    background: var(--brand-green-soft);
    color: #2F7A2C;
    border: 1px solid #B7E4B3;
}
.scouting-flash--warning {
    background: var(--brand-yellow-soft);
    color: #9A7B00;
    border: 1px solid #F0E08A;
}

/* Sofascore compact panel */
.scouting-sofascore-panel {
    position: relative;
    display: flex;
    gap: 0;
    background: linear-gradient(180deg, #FFFFFF 0%, #F0F6FB 100%);
    border: none;
    border-radius: var(--radius-md);
    padding: 0;
    box-shadow: var(--shadow-sm);
    margin-bottom: 0.35rem;
    overflow: hidden;
}
.scouting-sofascore-accent {
    width: 4px;
    flex-shrink: 0;
    background: linear-gradient(180deg, var(--brand-blue) 0%, var(--brand-green) 100%);
}
.scouting-sofascore-main {
    padding: 0.85rem 1rem;
    flex: 1;
}
.scouting-sofascore-title {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.92rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 0.25rem;
}
.scouting-sofascore-title .scouting-icon { color: var(--brand-blue-strong); }
.scouting-sofascore-meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.35rem 0.45rem;
    font-size: 0.84rem;
    color: var(--text-secondary);
}
.scouting-sofascore-date {
    margin-top: 0.35rem;
    font-size: 0.78rem;
    color: var(--text-muted);
}
.scouting-dot { color: var(--text-muted); }
.scouting-muted { color: var(--text-secondary); }
.scouting-sports-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    flex-wrap: wrap;
    margin-bottom: 0.35rem;
}
.scouting-sports-header .scouting-sofascore-title {
    margin-bottom: 0;
}
.scouting-sports-message {
    font-size: 0.9rem;
    color: var(--text-secondary);
    line-height: 1.45;
    margin: 0.35rem 0 0.55rem;
}
.scouting-sports-help {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin: 0.45rem 0 0.2rem;
    line-height: 1.4;
}
.scouting-sports-rows {
    display: grid;
    gap: 0.28rem;
    margin: 0.55rem 0 0.35rem;
}
.scouting-sports-row {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    font-size: 0.84rem;
    color: var(--text-secondary);
}
.scouting-sports-row strong {
    color: var(--text-primary);
    font-weight: 650;
    text-align: right;
}
.scouting-sports-progress {
    margin: 0.45rem 0 0.55rem;
}
.scouting-sports-step {
    font-size: 0.78rem;
    font-weight: 650;
    color: var(--brand-blue-strong);
    text-transform: uppercase;
    letter-spacing: 0.02em;
}
.scouting-sports-step-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-top: 0.15rem;
}
.scouting-sports-next {
    font-size: 0.82rem;
    color: var(--text-muted);
    margin-top: 0.35rem;
}
.scouting-sports-phases {
    margin: 0.55rem 0 0;
    padding-left: 1.1rem;
    font-size: 0.8rem;
    color: var(--text-muted);
}
.scouting-sports-phases li.is-active {
    color: var(--text-primary);
    font-weight: 650;
}

.scouting-filter-chip,
.scouting-pitch-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.35rem 0.75rem;
    border-radius: 999px;
    background: var(--brand-blue-soft);
    color: var(--brand-blue-strong);
    border: 1px solid #B7D4EE;
    font-size: 0.84rem;
    line-height: 1.3;
}
.scouting-filter-chip-label { color: var(--text-secondary); font-weight: 550; }

.stApp .st-key-dashboard_pitch_chart {
    width: 100%;
    max-width: 1120px;
    margin-left: auto;
    margin-right: auto;
}
.stApp .st-key-dashboard_pitch_chart [data-testid="stPlotlyChart"] {
    width: 100%;
}

/* Tablas / dataframes (tema claro forzado) */
div[data-testid="stDataFrame"],
div[data-testid="stDataEditor"] {
    border: 1px solid #D7E6F3 !important;
    border-radius: var(--radius-md) !important;
    overflow: auto;
    box-shadow: var(--shadow-sm);
    background: #ffffff !important;
    color: #111827 !important;
    color-scheme: light !important;
}
div[data-testid="stDataFrame"] [data-testid="stDataFrameResizable"],
div[data-testid="stDataEditor"] [data-testid="stDataFrameResizable"] {
    background: #ffffff !important;
    color: #111827 !important;
}
div[data-testid="stDataFrame"] thead tr th,
div[data-testid="stDataFrame"] [role="columnheader"],
div[data-testid="stDataEditor"] thead tr th,
div[data-testid="stDataEditor"] [role="columnheader"] {
    background: #EEF4FA !important;
    color: #1E4F7A !important;
    font-weight: 650 !important;
    border-color: #D7E6F3 !important;
}
div[data-testid="stDataFrame"] tbody tr td,
div[data-testid="stDataFrame"] [role="gridcell"],
div[data-testid="stDataEditor"] tbody tr td,
div[data-testid="stDataEditor"] [role="gridcell"] {
    background: #ffffff !important;
    color: #111827 !important;
    border-color: #E4E7EC !important;
}
div[data-testid="stDataFrame"] tbody tr:nth-child(even) td,
div[data-testid="stDataFrame"] tbody tr:nth-child(even) [role="gridcell"] {
    background: #F8FBFE !important;
}
div[data-testid="stDataFrame"] [aria-selected="true"],
div[data-testid="stDataEditor"] [aria-selected="true"] {
    background: #EAF3FB !important;
    color: #111827 !important;
}

/* Inputs: fondo blanco + texto oscuro (evita blanco sobre blanco con OS oscuro) */
.stApp .stTextInput input,
.stApp .stNumberInput input,
.stApp .stTextArea textarea,
.stApp .stDateInput input,
.stApp .stTimeInput input,
.stApp .stSelectbox div[data-baseweb="select"] > div,
.stApp .stMultiSelect div[data-baseweb="select"] > div,
.stApp [data-baseweb="input"] input,
.stApp [data-baseweb="textarea"] textarea,
.stApp [data-baseweb="select"] > div {
    background-color: #ffffff !important;
    color: #111827 !important;
    -webkit-text-fill-color: #111827 !important;
    caret-color: #111827 !important;
    border-color: #cbd5e1 !important;
    border-radius: var(--radius-sm) !important;
}
.stApp .stTextInput input::placeholder,
.stApp .stNumberInput input::placeholder,
.stApp .stTextArea textarea::placeholder,
.stApp .stDateInput input::placeholder,
.stApp [data-baseweb="input"] input::placeholder,
.stApp [data-baseweb="textarea"] textarea::placeholder {
    color: #6b7280 !important;
    -webkit-text-fill-color: #6b7280 !important;
    opacity: 1 !important;
}
.stApp .stTextInput input:hover,
.stApp .stNumberInput input:hover,
.stApp .stTextArea textarea:hover,
.stApp .stDateInput input:hover,
.stApp [data-baseweb="input"] input:hover,
.stApp [data-baseweb="textarea"] textarea:hover {
    border-color: #94a3b8 !important;
}
.stApp .stTextInput input:focus,
.stApp .stNumberInput input:focus,
.stApp .stTextArea textarea:focus,
.stApp .stDateInput input:focus,
.stApp [data-baseweb="input"] input:focus,
.stApp [data-baseweb="textarea"] textarea:focus {
    border-color: #4f9bd8 !important;
    box-shadow: 0 0 0 1px #4f9bd8 !important;
    color: #111827 !important;
    -webkit-text-fill-color: #111827 !important;
    caret-color: #111827 !important;
}
.stApp .stTextInput input:disabled,
.stApp .stNumberInput input:disabled,
.stApp .stTextArea textarea:disabled,
.stApp [data-baseweb="input"] input:disabled,
.stApp [data-baseweb="textarea"] textarea:disabled {
    background-color: #f1f5f9 !important;
    color: #667085 !important;
    -webkit-text-fill-color: #667085 !important;
    border-color: #e2e8f0 !important;
}
.stApp .stTextInput input:-webkit-autofill,
.stApp .stTextInput input:-webkit-autofill:hover,
.stApp .stTextInput input:-webkit-autofill:focus,
.stApp .stTextInput input:-webkit-autofill:active,
.stApp [data-baseweb="input"] input:-webkit-autofill,
.stApp [data-baseweb="input"] input:-webkit-autofill:hover,
.stApp [data-baseweb="input"] input:-webkit-autofill:focus,
.stApp [data-baseweb="input"] input:-webkit-autofill:active {
    -webkit-text-fill-color: #111827 !important;
    caret-color: #111827 !important;
    box-shadow: 0 0 0 1000px #ffffff inset !important;
    -webkit-box-shadow: 0 0 0 1000px #ffffff inset !important;
    transition: background-color 99999s ease-in-out 0s;
}
section.main [data-testid="stWidgetLabel"],
.stTextInput label, .stNumberInput label, .stSelectbox label,
.stMultiSelect label, .stTextArea label, .stDateInput label, .stSlider label {
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    font-size: 0.84rem !important;
}
/* BaseWeb popovers / menús */
.stApp [data-baseweb="popover"],
.stApp [data-baseweb="menu"],
.stApp [data-baseweb="popover"] ul,
.stApp [data-baseweb="menu"] ul,
.stApp [data-baseweb="popover"] li,
.stApp [data-baseweb="menu"] li {
    background-color: #ffffff !important;
    color: #111827 !important;
}
.stApp [data-baseweb="menu"] li:hover,
.stApp [data-baseweb="menu"] li[aria-selected="true"] {
    background-color: #eaf3fb !important;
    color: #111827 !important;
}
.stApp [data-baseweb="select"] svg,
.stApp [data-baseweb="input"] svg {
    fill: #475569 !important;
    color: #475569 !important;
}

/* Tabs suaves */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.25rem;
    border-bottom: 1px solid var(--border-soft);
}
.stTabs [data-baseweb="tab"] {
    color: var(--text-secondary) !important;
    font-weight: 550 !important;
    border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--brand-blue-strong) !important;
    background: var(--brand-blue-soft) !important;
}
.stTabs [aria-selected="true"] {
    color: var(--brand-blue-strong) !important;
    background: var(--brand-blue-soft) !important;
    border-bottom: 2px solid var(--brand-blue) !important;
}

/* Expanders más ligeros */
details[data-testid="stExpander"] {
    background: var(--surface) !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: var(--radius-md) !important;
}
details[data-testid="stExpander"] summary {
    color: var(--brand-blue-strong) !important;
    font-weight: 600 !important;
    background: #F5FAFE !important;
}

/* Form surfaces: sin borde (evita cajas anidadas de Streamlit) */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border: none !important;
    border-radius: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
    padding: 0 !important;
}

/* Separadores suaves */
hr.section-hr {
    margin: 1.1rem 0 !important;
    border: none !important;
    border-top: 1px solid rgba(79, 143, 204, 0.16) !important;
}
hr.section-hr--tight {
    margin: 0.55rem 0 0.45rem 0 !important;
}

/* Metrics nativos (fallback) */
section.main div[data-testid="stMetric"] {
    background: var(--surface);
    border: none;
    border-left: 4px solid var(--brand-blue);
    border-radius: var(--radius-md);
    padding: 0.75rem 0.9rem;
    box-shadow: var(--shadow-sm);
    min-height: 5.5rem;
}
section.main div[data-testid="stMetric"] label {
    color: var(--text-secondary) !important;
    font-weight: 600 !important;
}
section.main div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: var(--text-primary) !important;
    font-weight: 700 !important;
}

/* Formularios: secciones por tipografía + acento */
.scouting-form-section {
    margin: 1.35rem 0 0.55rem 0;
    padding: 0.1rem 0 0.1rem 0.75rem;
    border-left: 3px solid var(--brand-blue);
    background: transparent;
}
.scouting-form-section-title-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
}
.scouting-form-section-title {
    margin: 0 !important;
    font-size: 1.02rem !important;
    font-weight: 650 !important;
    color: var(--text-primary) !important;
    border: none !important;
}
.scouting-form-section-sub {
    margin: 0.2rem 0 0.35rem 0 !important;
    font-size: 0.82rem !important;
    color: var(--text-secondary) !important;
}

/* Escala subjetiva 1–4 */
.rating-attr-row {
    margin: 0.85rem 0 0.1rem 0;
    padding: 0.55rem 0.65rem 0.35rem;
    border-radius: var(--radius-sm);
    border-left: 3px solid var(--border-soft);
}
.rating-attr-row--low { border-left-color: #E57373; background: #FFF8F8; }
.rating-attr-row--mid { border-left-color: #F59E0B; background: #FFFBF3; }
.rating-attr-row--good { border-left-color: var(--brand-blue); background: #F5FAFE; }
.rating-attr-row--high { border-left-color: var(--brand-green); background: #F6FBF5; }
.rating-attr-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
}
.rating-attr-label {
    font-weight: 650;
    font-size: 0.95rem;
    color: var(--text-primary);
}
.star-rating-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 2.4rem;
    padding: 0.18rem 0.55rem;
    border-radius: 999px;
    font-size: 0.82rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
}
.star-rating-pill--low { background: #FEE2E2; color: #B42318; }
.star-rating-pill--mid { background: #FEF0C7; color: #B54708; }
.star-rating-pill--good { background: var(--brand-blue-soft); color: var(--brand-blue-strong); }
.star-rating-pill--high { background: var(--brand-green-soft); color: #2F7A2C; }
.star-rating-row .stars-bg { color: #D0D5DD; }
.star-rating-row--low .stars-fill { color: #E57373 !important; }
.star-rating-row--mid .stars-fill { color: #F59E0B !important; }
.star-rating-row--good .stars-fill { color: var(--brand-blue) !important; }
.star-rating-row--high .stars-fill { color: var(--brand-green) !important; }
.manual-form-big-stars .star-rating-wrap { font-size: 1.55rem; letter-spacing: 0.1em; }
.manual-form-big-stars .star-rating-row {
    margin: 0.15rem 0 0.4rem 0;
    justify-content: flex-start;
}
.manual-form-big-stars .star-rating-num { display: none; }
.stApp [class*="__q0"] .stButton > button[kind="secondary"] {
    background: #FEE2E2 !important; color: #B42318 !important; border: none !important;
}
.stApp [class*="__q1"] .stButton > button[kind="secondary"] {
    background: #FEF0C7 !important; color: #B54708 !important; border: none !important;
}
.stApp [class*="__q2"] .stButton > button[kind="secondary"] {
    background: var(--brand-blue-soft) !important; color: var(--brand-blue-strong) !important; border: none !important;
}
.stApp [class*="__q3"] .stButton > button[kind="secondary"] {
    background: var(--brand-green-soft) !important; color: #2F7A2C !important; border: none !important;
}
.stApp [class*="__q0"] .stButton > button[kind="primary"] {
    background: #E57373 !important; color: #FFF !important; border: none !important;
}
.stApp [class*="__q1"] .stButton > button[kind="primary"] {
    background: #F59E0B !important; color: #FFF !important; border: none !important;
}
.stApp [class*="__q2"] .stButton > button[kind="primary"] {
    background: var(--brand-blue) !important; color: #FFF !important; border: none !important;
}
.stApp [class*="__q3"] .stButton > button[kind="primary"] {
    background: var(--brand-green) !important; color: #FFF !important; border: none !important;
}
.stApp [class*="__dec"] .stButton > button,
.stApp [class*="__inc"] .stButton > button {
    background: var(--surface-alt) !important;
    color: var(--text-secondary) !important;
    border: none !important;
    font-size: 0.8rem !important;
    min-height: 2.2rem !important;
}

details[data-testid="stExpander"] {
    background: var(--surface) !important;
    border: none !important;
    border-radius: var(--radius-md) !important;
    box-shadow: var(--shadow-sm);
}
details[data-testid="stExpander"] summary {
    color: var(--brand-blue-strong) !important;
    font-weight: 600 !important;
    background: #F0F6FB !important;
}

div[data-testid="stDataFrame"],
div[data-testid="stDataEditor"] {
    border: none !important;
    border-radius: var(--radius-md) !important;
    overflow: auto;
    box-shadow: var(--shadow-sm);
    background: #ffffff !important;
    color: #111827 !important;
    color-scheme: light !important;
}

.scouting-empty-state {
    background: linear-gradient(180deg, #FFFFFF 0%, #F0F6FB 100%);
    border: none;
    border-radius: var(--radius-md);
    padding: 1.75rem 1.25rem;
    text-align: center;
    margin: 0.5rem 0 1rem 0;
    box-shadow: var(--shadow-sm);
}
.scouting-filter-chip,
.scouting-pitch-chip {
    border: none;
}

@media (max-width: 1100px) {
    [data-testid="stMainBlockContainer"],
    .main .block-container {
        padding-left: 1.1rem !important;
        padding-right: 1.1rem !important;
    }
    .scouting-campus-logo { width: 130px; max-height: 38px; }
    .scouting-club-logo { width: 40px; max-height: 42px; }
    .scouting-brand-title { font-size: 0.95rem; }
    .stApp [class*="st-key-nav_"] .stButton > button {
        font-size: 0.72rem !important;
        padding: 0.3rem 0.4rem !important;
    }
    .scouting-page-subtitle { margin-left: 0 !important; }
}
@media (max-width: 720px) {
    .scouting-brand { flex-wrap: wrap; }
    .scouting-brand-title { white-space: normal; }
    .scouting-player-header { flex-direction: column; }
}
</style>
"""


def build_full_width_layout_css() -> str:
    """Compat: refuerzo de ancho completo + sistema visual moderno."""
    return build_design_system_css()


def build_forced_light_theme_css() -> str:
    """Capa final: ancla tema claro frente a SO/navegador en modo oscuro."""
    return """
<style>
/* color-scheme light: evita controles nativos oscuros del navegador */
html, body, .stApp, [data-testid="stAppViewContainer"] {
    color-scheme: light !important;
}
</style>
"""
