"""Demostración local del seguimiento COMET con DATOS FICTICIOS. No es parte del portal.

    streamlit run scripts/demo_comet_followup.py --server.address=127.0.0.1

No usa cuentas, Supabase ni COMET: sustituye la carga de datos por un generador ficticio y el
almacén de configuración por uno en memoria, y no lee ninguna variable de conexión. Se niega a
arrancar si detecta credenciales de conexión en el entorno o si no escucha solo en el equipo local.
Sirve para revisar las pantallas y tomar capturas antes de tener acceso autorizado a los datos reales.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / 'src', ROOT / 'app', ROOT):
    sys.path.insert(0, str(path))
os.environ['PORTAL_MODE'] = '1'
os.environ['DISABLE_SOFASCORE_UPDATE'] = '1'

import streamlit as st

CREDENTIALS = ('COMET_DATABASE_URL', 'PORTAL_AUTH_DATABASE_URL', 'SCOUTING_DATABASE_URL',
               'PORTAL_SUPABASE_SECRET_KEY', 'DB_PASSWORD')

st.set_page_config(page_title='Demostración COMET (datos ficticios)', layout='wide')
if any(os.environ.get(name) for name in CREDENTIALS):
    st.error('La demostración no arranca con credenciales de conexión en el entorno. Ejecútala en una '
             'terminal sin las variables de COMET, Supabase o la base de scouting.')
    st.stop()
if st.get_option('server.address') not in ('127.0.0.1', 'localhost', '::1'):
    st.error('La demostración solo puede escuchar en el equipo local: usa --server.address=127.0.0.1.')
    st.stop()

import comet_context
import comet_followup
import comet_insights
from scouting.portal.security import session_scope
from scripts import comet_demo_data, comet_demo_store
from ui.portal_brand import inject_portal_brand, masthead

DEMO_ADMIN = dict(id='00000000-0000-0000-0000-00000000d3a0', role='admin', active=True, revision=1,
                  display_name='Administración (demostración)', username='demo@example.test')


@st.cache_resource
def _prepare():
    """Datos ficticios y almacén en memoria; se crean una sola vez por proceso."""
    from datetime import date
    from scouting.comet import adelantados
    from scouting.comet.facts import build_dataset
    raw = comet_demo_data.build_raw()
    comet_demo_store.install()
    ds = build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers'])
    featured = adelantados.ahead_players(ds, 2026).iloc[0]['personid']  # un adelantado con muchos minutos
    with session_scope({}, verified_user=DEMO_ADMIN):
        comet_demo_store.set_mark(featured, 'proyectado', True, 'Ficticio: seguimiento de demostración')
        comet_demo_store.set_mark(featured, 'seleccion', True, 'Ficticio: convocado a la selección')
        comet_demo_store.add_period(featured, 'sudamericano', date(2026, 4, 10), date(2026, 4, 24), 'Ficticio: concentración')
        for other in adelantados.ahead_players(ds, 2026)['personid'].iloc[1:4]:
            comet_demo_store.set_mark(other, 'proyectado', True, 'Ficticio')
    return raw, featured


RAW, FEATURED_PLAYER = _prepare()
comet_context.load_raw = lambda: RAW
comet_context.now = lambda: comet_demo_data.TODAY
st.session_state.setdefault('cp_player', FEATURED_PLAYER)  # la ficha abre con un jugador ilustrativo

PAGES = {
    'Partido semanal': comet_followup.page_weekly_match,
    'Rankings por categoría': comet_followup.page_rankings,
    'Ficha del jugador': comet_followup.page_player,
    'Indicadores': comet_insights.page_indicators,
    'Alertas': comet_insights.page_alerts,
    'Jugadores adelantados': comet_insights.page_adelantados,
    'Seguimiento y configuración': comet_insights.page_tracking,
}

inject_portal_brand()
masthead(DEMO_ADMIN)
st.warning('DEMOSTRACIÓN CON DATOS FICTICIOS: los jugadores, partidos y resultados no existen. '
           'No hay conexión con COMET ni con Supabase.')
requested = st.query_params.get('page', list(PAGES)[0])
page = st.selectbox('Sección COMET', list(PAGES), index=list(PAGES).index(requested) if requested in PAGES else 0,
                    key='demo_section')
with session_scope({}, verified_user=DEMO_ADMIN):
    PAGES[page]()
