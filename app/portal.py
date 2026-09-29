"""Single Streamlit entrypoint: personal accounts, COMET admin boundary, scouting."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'app'))
os.environ['PORTAL_MODE'] = '1'
os.environ['DISABLE_SOFASCORE_UPDATE'] = '1'
os.environ['DB_SCHEMA'] = 'scouting'

import streamlit as st
from scouting.portal import accounts
from scouting.portal.security import session_scope, require_admin


def logout():
    st.session_state.clear()
    st.query_params.clear()


def login():
    st.title("O’Higgins · Plataforma deportiva")
    st.caption('Accede con tu cuenta personal del club.')
    with st.form('portal_login'):
        username = st.text_input('Correo electrónico', key='portal_username')
        password = st.text_input('Contraseña', type='password', key='portal_password')
        submit = st.form_submit_button('Entrar', type='primary')
    if submit:
        try:
            token = accounts.authenticate(username, password)
        except Exception:
            st.error('No se pudo iniciar sesión. Revisa la configuración de Supabase Auth con el administrador.')
            return
        if token:
            st.session_state.clear()
            st.session_state['portal_session'] = token
            st.query_params.clear()
            st.rerun()
        st.error('Credenciales incorrectas o cuenta temporalmente bloqueada.')


def manage_accounts():
    require_admin()
    st.header('Usuarios y permisos')
    st.caption('Cada cuenta pertenece a una persona. Los cambios revocan sus sesiones actuales.')
    users = accounts.list_users()
    st.dataframe([{k: u[k] for k in ('username', 'display_name', 'role', 'active')} for u in users], hide_index=True)
    selected = st.selectbox('Cuenta', ['Nueva cuenta'] + [u['username'] for u in users])
    old = next((u for u in users if u['username'] == selected), None)
    with st.form('account_editor'):
        username = st.text_input('Correo electrónico', value=old['username'] if old else '', disabled=bool(old))
        name = st.text_input('Nombre y apellidos', value=old['display_name'] if old else '')
        role = st.selectbox('Rol', ['scout', 'admin'], index=1 if old and old['role'] == 'admin' else 0)
        active = st.checkbox('Cuenta activa', value=bool(old['active']) if old else True)
        password = st.text_input('Nueva contraseña (dejar vacía para conservarla)', type='password')
        verified = st.checkbox('He verificado que este correo pertenece a la persona del club', value=bool(old))
        submit = st.form_submit_button('Guardar cuenta')
    if submit:
        if not verified:
            st.warning('Verifica la identidad antes de crear la cuenta.')
            return
        try:
            accounts.save_user(username=username, name=name, password=password, role=role,
                               user_id=old['id'] if old else None, active=active)
            st.success('Cuenta guardada. Las sesiones anteriores quedan revocadas.')
            st.rerun()
        except (ValueError, PermissionError) as exc:
            st.error(str(exc))
        except Exception:
            st.error('No se pudo guardar la cuenta. Comprueba si el usuario ya existe.')

    with st.expander('Asignar propietario a un informe migrado'):
        from scouting.db import get_connection
        from scouting.services.reports_service import assign_report_owner, fetch_visible_reports
        with get_connection() as conn:
            reports = fetch_visible_reports(conn, limit=1000)
        active_users = {u['id']: u for u in users if u['active']}
        if reports and active_users:
            by_id = {r['id']: r for r in reports}
            report_id = st.selectbox('Informe', list(by_id), format_func=lambda rid:
                f"#{rid} · {by_id[rid].get('player_full_name')} · {by_id[rid].get('scout_name')} · {by_id[rid].get('report_date')}")
            owner_id = st.selectbox('Cuenta propietaria', list(active_users), format_func=lambda uid: active_users[uid]['username'])
            confirm = st.checkbox('He verificado la autoría de este informe')
            if st.button('Asignar propietario', disabled=not confirm):
                with get_connection() as conn:
                    assign_report_owner(conn, report_id, owner_id)
                st.success('Propietario asignado; contenido deportivo conservado.')
        else:
            st.info('No hay informes visibles o cuentas activas para asignar.')


def render_comet():
    require_admin()  # Before import, menus, cache lookup or connection creation.
    import comet_dashboard as comet
    pages = {
        'Resumen ejecutivo': comet.page_executive_summary,
        'Desarrollo juvenil': comet.page_youth_development,
        'Rendimiento competitivo': comet.page_competition_performance,
        'Análisis de jugadores': comet.page_player_analysis,
        'Estructura del plantel': comet.page_squad_structure,
    }
    st.header('COMET · Fútbol formativo')
    st.caption('Datos federados · Acceso exclusivo de administración')
    page = st.selectbox('Sección COMET', list(pages), key='comet_section')
    pages[page]()


def render_scouting(user):
    import streamlit_app as scouting
    from ui.layout import render_top_header, render_page_heading
    from ui.styles import build_full_width_layout_css
    from ui.theme import inject_ohiggins_theme
    inject_ohiggins_theme()
    st.markdown(build_full_width_layout_css(), unsafe_allow_html=True)
    pages = {
        'Dashboard': scouting._render_dashboard,
        'Nuevo informe': scouting._render_new_report,
        'Consultar jugador': scouting._render_player_lookup,
        'Comparación': scouting._render_comparison_tab,
        'Datos objetivos': scouting._render_objective_explorer,
    }
    if user['role'] == 'admin':
        pages['Informes ocultos'] = scouting._render_hidden_reports_page
    st.header('Scouting')
    page = render_top_header(pages=list(pages), username=user['display_name'])
    if page not in pages:
        raise PermissionError('Sección no autorizada.')
    if scouting._handle_page_navigation(page):
        st.rerun()
    render_page_heading(page)
    if page in {'Dashboard', 'Consultar jugador', 'Comparación', 'Datos objetivos'}:
        from scouting.db import get_connection
        from scouting.repositories.sofascore_event_ingestion_repository import list_incomplete_coverage
        with get_connection() as conn:
            incomplete = list_incomplete_coverage(conn)
        for coverage in incomplete:
            st.warning(
                f"Cobertura parcial de Sofascore · {coverage['competition']} {coverage['season']}: "
                f"{coverage['processed']}/{coverage['expected']} partidos registrados con datos importados. "
                'Los totales excluyen los encuentros pendientes; no se cuentan como ceros.'
            )
    pages[page]()


def main():
    st.set_page_config(page_title="O’Higgins · Plataforma deportiva", page_icon='⚽', layout='wide')
    token = st.session_state.get('portal_session')
    try:
        user = accounts.resolve_session(token)
    except Exception:
        st.error('No se pudo verificar la sesión. Revisa la configuración de Supabase con el administrador.')
        return
    if not user:
        if token:
            logout()
        login()
        return
    with session_scope(token, verified_user=user):
        st.title("O’Higgins FC")
        st.caption(f"{user['display_name']} · {user['role']}")
        modules = ['Inicio', 'COMET', 'Scouting', 'Administración'] if user['role'] == 'admin' else ['Scouting']
        if st.session_state.get('portal_module') not in modules:
            st.session_state['portal_module'] = modules[0]
        module = st.radio('Módulo', modules, key='portal_module', horizontal=True)
        if st.session_state.get('_portal_previous_module') != module:
            for key in list(st.session_state):
                if key not in {'portal_session', 'portal_module'}:
                    del st.session_state[key]
            st.query_params.clear()
            st.session_state['_portal_previous_module'] = module
        if st.button('Cerrar sesión'):
            logout()
            st.rerun()
        try:
            if module == 'COMET':
                render_comet()
            elif module == 'Administración':
                manage_accounts()
            elif module == 'Scouting':
                render_scouting(user)
            else:
                require_admin()
                st.title('Plataforma deportiva')
                st.write('Un acceso para los datos federados y el trabajo de scouting del club.')
                left, right = st.columns(2)
                with left:
                    st.subheader('COMET · Fútbol formativo')
                    st.write('Planteles, minutos, resultados y desarrollo de divisiones menores.')
                with right:
                    st.subheader('Scouting')
                    st.write('Informes, estadísticas y comparación de jugadores.')
        except PermissionError:
            st.error('No tienes permiso para realizar esta operación. Inicia sesión de nuevo si tu cuenta cambió.')
        except Exception:
            # Never expose DSNs, SQL containing sensitive values, or provider bodies.
            st.error('No se pudo cargar esta sección. El administrador debe revisar la configuración y conectividad.')


if __name__ == '__main__':
    main()
