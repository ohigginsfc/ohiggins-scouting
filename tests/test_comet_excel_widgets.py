"""Botón «Descargar Excel» de las tablas COMET: qué baja, que no rompa la pantalla y que no quede ninguna tabla sin él."""
import ast
import io
import re
from pathlib import Path

import pandas as pd
import pytest
import streamlit as st
from openpyxl import load_workbook
from streamlit.testing.v1 import AppTest

from scouting.comet import excel_export
from tests.test_comet_goals_by_year import screen  # noqa: F401  (fixture: pantallas SQL con datos ficticios)
from tests.test_comet_pages import ADMIN, PAGES, SCRIPT, comet_env, raw  # noqa: F401  (fixtures)
from tests.test_comet_plantel_bajas import render as render_dashboard

APP = Path('app')


@pytest.fixture
def downloads(monkeypatch):
    """Cada botón de descarga que dibuja una pantalla, con los bytes que ofrece."""
    sent = []
    real = st.download_button

    def spy(label, data, *args, **kwargs):
        sent.append(dict(label=label, data=data, **kwargs))
        return real(label, data, *args, **kwargs)

    monkeypatch.setattr(st, 'download_button', spy)
    return sent


@pytest.fixture(autouse=True)
def app_on_path(monkeypatch):
    monkeypatch.syspath_prepend(str(APP.resolve()))


def opened(download):
    return load_workbook(io.BytesIO(download['data']))


def run(script) -> AppTest:
    """Los scripts de prueba solo llevan ASCII (las tildes con chr()): en Windows AppTest descarta en silencio un script con tildes."""
    app = AppTest.from_function(script, default_timeout=60).run()
    assert not app.exception, [e.value for e in app.exception]
    return app


# --- las tablas de los componentes compartidos ----------------------------------------------------------------------------

def one_table():
    import pandas as pd
    from ui.comet_widgets import show_table
    frame = pd.DataFrame({'displayname': ['Ana', 'Beto'], 'age': [15.0, None], 'minutes': [90, 0], 'oculta': [1, 2]})
    show_table(frame, {'displayname': ('Jugador', None), 'age': ('Edad', '{:.0f}'), 'minutes': ('Minutos', '{:.0f}')},
               name='Prueba ' + chr(183) + ' U-15 2026')


def test_a_named_table_offers_the_excel_of_exactly_the_visible_columns(downloads):
    app = run(one_table)

    assert len(app.dataframe) == 1 and len(downloads) == 1
    sent = downloads[0]
    assert sent['label'] == 'Descargar Excel' and sent['mime'] == excel_export.XLSX_MIME
    assert re.fullmatch(r'comet_prueba_u_15_2026_\d{4}-\d{2}-\d{2}\.xlsx', sent['file_name'])
    book = opened(sent)
    assert book.sheetnames == ['Prueba', 'Información']
    assert [c.value for c in book['Prueba'][1]] == ['Jugador', 'Edad', 'Minutos']  # sin la columna que no se muestra


def test_missing_values_are_a_dash_on_screen_and_an_empty_cell_in_excel_never_zero(downloads):
    app = run(one_table)

    assert app.dataframe[0].value['Edad'].tolist() == ['15', '—']
    ws = opened(downloads[0])['Prueba']
    assert [ws['B2'].value, ws['B3'].value] == [15, None]
    assert [ws['C2'].value, ws['C3'].value] == [90, 0], 'un 0 verdadero se conserva'
    assert ws['B2'].number_format == '0'


def without_name():
    import pandas as pd
    from ui.comet_widgets import show_table, show_static_table
    frame = pd.DataFrame({'a': [1]})
    show_table(frame, {'a': ('A', None)})
    show_static_table(frame, {'a': ('A', None)})


def test_tables_without_a_name_keep_working_without_a_button(downloads):
    app = run(without_name)
    assert len(app.dataframe) == 1 and len(app.table) == 1 and not downloads


def empty_table():
    import pandas as pd
    from ui.comet_widgets import show_table, show_static_table
    empty = pd.DataFrame({'a': pd.Series(dtype='float64')})
    show_table(empty, {'a': ('A', None)}, name='Vacia')
    show_static_table(empty, {'a': ('A', None)}, name='Vacia estatica')


def test_an_empty_table_says_so_and_offers_no_download(downloads):
    app = run(empty_table)
    assert [c.value for c in app.caption] == ['Sin registros.', 'Sin registros.'] and not downloads


def same_name_three_times():
    import pandas as pd
    from ui.comet_widgets import show_table
    frame = pd.DataFrame({'a': [1]})
    for _ in range(3):
        show_table(frame, {'a': ('A', None)}, name='Igual')


def test_tables_with_the_same_name_each_get_their_own_button(downloads):
    app = run(same_name_three_times)

    assert len(app.dataframe) == 3 and len(app.get('download_button')) == 3
    assert len({d['key'] for d in downloads}) == 3, 'una clave repetida haría fallar la pantalla'
    assert {d['file_name'] for d in downloads} == {downloads[0]['file_name']}


def static_table():
    import pandas as pd
    from ui.comet_widgets import show_static_table
    attention = 'Atenci' + chr(243) + 'n'
    frame = pd.DataFrame({'control': ['a', 'b'], 'nivel': [attention, 'Correcto'], 'cantidad': [1, None]})
    show_static_table(frame, {'control': ('Control', None), 'nivel': ('Estado', None), 'cantidad': ('Cantidad', None)},
                      colors=('nivel', {attention: 'Naranja'}), name='Calidad de datos')


def test_static_table_exports_its_first_column_too_and_repeats_the_colors(downloads):
    app = run(static_table)

    assert len(app.table) == 1 and len(downloads) == 1
    ws = opened(downloads[0])['Calidad de datos']
    assert [c.value for c in ws[1]] == ['Control', 'Estado', 'Cantidad']
    assert [ws['A2'].value, ws['A3'].value] == ['a', 'b']
    assert ws['B2'].fill.start_color.rgb.endswith('FEF0C7') and ws['B3'].fill.fill_type is None
    assert [ws['C2'].value, ws['C3'].value] == [1, None]


def colored_table():
    import pandas as pd
    from ui.comet_widgets import show_table
    frame = pd.DataFrame({'result': ['Victoria', 'Derrota', None], 'goals': [2, 0, 1]})
    show_table(frame, {'result': ('Resultado', None), 'goals': ('Goles', '{:.0f}')},
               colors=('result', {'Victoria': 'Verde', 'Derrota': 'Rojo'}), name='Resultados')


def test_colored_columns_keep_their_colors_in_excel(downloads):
    run(colored_table)
    ws = opened(downloads[0])['Resultados']
    assert ws['A2'].fill.start_color.rgb.endswith('DCFCE7') and ws['A3'].fill.start_color.rgb.endswith('FEE4E2')
    assert ws['A4'].value is None and ws['A4'].fill.fill_type is None


def test_a_failed_export_never_hides_the_table(downloads, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError('boom')
    monkeypatch.setattr(excel_export, 'build_workbook', broken)

    app = run(one_table)

    assert len(app.dataframe) == 1 and not downloads
    assert [c.value for c in app.caption] == ['No se pudo preparar la descarga en Excel de esta tabla.']


# --- criterios provisionales: la cifra supuesta no sale del portal sin su aviso -----------------------------------------------

def provisional_then_other_section():
    import pandas as pd
    import streamlit as st
    from scouting.comet.rules import STATUS_PENDING
    from ui.comet_widgets import rule_note, show_table

    class PendingRules:
        def status(self, key):
            return STATUS_PENDING

    frame = pd.DataFrame({'a': [1]})
    st.session_state['comet_section'] = 'Alertas'
    rule_note(PendingRules(), ['age_cutoff'])
    show_table(frame, {'a': ('A', None)}, name='Con aviso')
    st.session_state['comet_section'] = 'Otra pantalla'  # otra pantalla que no llama a rule_note
    show_table(frame, {'a': ('A', None)}, name='Sin aviso')


def provisional_rows(download):
    rows = list(opened(download)['Información'].iter_rows(values_only=True))
    return [r[1] for r in rows if r[0] == 'Criterio provisional']


def test_excel_repeats_the_provisional_criteria_of_the_screen_only(downloads):
    run(provisional_then_other_section)

    with_notice, without_notice = downloads
    notes = provisional_rows(with_notice)
    assert len(notes) == 1 and notes[0].startswith('Supuesto: pendiente de confirmar · ')
    assert 'aprobad' not in notes[0].lower()
    assert provisional_rows(without_notice) == []


# --- las pantallas de COMET con datos ficticios -----------------------------------------------------------------------------

def render(page: str) -> AppTest:
    module, function = PAGES[page]
    app = AppTest.from_string(SCRIPT.format(module=module, function=function, admin=ADMIN), default_timeout=90).run()
    assert not app.exception, [e.value for e in app.exception]
    return app


@pytest.mark.parametrize('page', list(PAGES))
def test_every_table_of_every_comet_screen_has_its_excel(comet_env, downloads, page):
    app = render(page)

    tables = len(app.dataframe) + len(app.table)
    assert tables > 0 and len(downloads) == tables, 'una tabla sin botón de Excel'
    for sent in downloads:
        book = opened(sent)
        assert book.sheetnames[-1] == excel_export.INFO_SHEET and book.worksheets[0].max_row >= 1
        assert sent['file_name'].startswith('comet_') and sent['file_name'].endswith('.xlsx')
    assert len({d['key'] for d in downloads}) == len(downloads)


def test_alerts_excel_carries_the_provisional_criteria_and_the_portal_version(comet_env, downloads):
    from ui.portal_brand import PORTAL_VERSION
    render('Alertas')

    table = next(d for d in downloads if d['file_name'].startswith('comet_alertas_temporada_'))
    assert any('pendiente de confirmar' in note for note in provisional_rows(table))
    info = {r[0]: r[1] for r in opened(table)['Información'].iter_rows(values_only=True)}
    assert info['Versión del portal'] == f'v{PORTAL_VERSION}' and info['Origen'] == excel_export.ORIGIN


def test_weekly_match_excel_names_every_sheet_block_with_its_match(comet_env, downloads):
    render('Partido semanal')

    names = [opened(d).properties.title for d in downloads]
    for block in ('Titulares', 'Suplentes que no ingresaron', 'No citados que no participaron', 'Goles recibidos por arquero'):
        assert any(n.startswith(f'{block} · ') for n in names), block  # los bloques sin filas dicen «Sin registros» y no llevan botón
    assert all(' vs ' in n for n in names if not n.startswith('Partidos de la semana'))


def test_ranking_excel_matches_the_ranking_on_screen(comet_env, downloads):
    app = render('Rankings por categoría')

    goals = next(d for d in downloads if opened(d).properties.title.startswith('Ranking Goles · '))
    ws = opened(goals).worksheets[0]
    assert [c.value for c in ws[1]][:3] == ['Pos.', 'Jugador', 'Edad']
    assert ws.max_row >= 2 and len(app.dataframe) >= 4


@pytest.mark.parametrize('function', ['page_executive_summary', 'page_youth_development', 'page_player_analysis',
                                      'page_competition_performance', 'page_squad_structure'])
def test_every_table_of_the_sql_screens_has_its_excel(screen, downloads, function):
    app = render_dashboard(function)
    if function == 'page_youth_development':
        app.selectbox(key='youth_cat').select('U-15').run()
    downloads.clear()
    app.run()  # una pasada más con la pantalla ya en su estado final: así se cuentan solo sus botones
    assert not app.exception, [e.value for e in app.exception]

    tables = len(app.dataframe) + len(app.table)
    assert tables > 0 and len(downloads) == tables, 'una tabla sin botón de Excel'
    assert all(opened(d).sheetnames[-1] == excel_export.INFO_SHEET for d in downloads)


def test_top_scorers_excel_is_the_table_on_screen_with_real_numbers(screen, downloads):
    app = render_dashboard('page_youth_development')
    app.selectbox(key='youth_cat').select('U-15').run()
    app.selectbox(key='youth_year_U-15').select(2026).run()
    downloads.clear()
    app.run()

    scorers = next(d for d in downloads if opened(d).properties.title == 'Goleadores · U-15 2026')
    ws = opened(scorers).worksheets[0]
    on_screen = app.dataframe[0].value
    assert [c.value for c in ws[1]] == list(on_screen.columns) == ['Jugador', 'Edad', 'Goles', 'Partidos']
    assert {ws.cell(row=r, column=1).value: ws.cell(row=r, column=3).value for r in range(2, ws.max_row + 1)} == \
        dict(zip(on_screen['Jugador'], on_screen['Goles'])) == {'Sub Quince Uno': 5, 'Sub Quince Dos': 1}
    assert scorers['file_name'].startswith('comet_goleadores_u_15_2026_')


def test_goals_by_year_excel_leaves_a_year_without_matches_empty_not_zero(screen, downloads):
    app = render_dashboard('page_youth_development')
    app.selectbox(key='youth_cat').select('U-15').run()
    app.selectbox(key='youth_year_U-15').select(2026).run()
    downloads.clear()
    app.run()

    by_year = next(d for d in downloads if opened(d).properties.title == 'Goles por año de los goleadores · U-15')
    ws = opened(by_year).worksheets[0]
    rows = {ws.cell(row=r, column=1).value: [ws.cell(row=r, column=c).value for c in (2, 3, 4)] for r in range(2, ws.max_row + 1)}
    assert [c.value for c in ws[1]] == ['Jugador', '2025', '2026', 'Total']
    assert rows['Sub Quince Uno'] == [2, 5, 7]
    assert rows['Sub Quince Dos'] == [None, 1, 1], 'sin partidos en 2025: celda vacía; la pantalla muestra «—», nunca 0'


# --- ninguna tabla de COMET queda sin Excel, y el Excel no sale de COMET ----------------------------------------------------

def comet_modules():
    return sorted(APP.glob('comet_*.py'))


def test_every_comet_table_call_passes_a_name_so_it_gets_a_download():
    missing, total = [], 0
    for path in comet_modules():
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ('show_table', 'show_static_table'):
                total += 1
                name = next((k.value for k in node.keywords if k.arg == 'name'), None)
                if name is None or (isinstance(name, ast.Constant) and not name.value):
                    missing.append(f'{path.name}:{node.lineno}')
    assert total >= 40 and not missing, missing


def test_comet_screens_do_not_draw_tables_that_skip_the_shared_widgets():
    direct = []
    for path in comet_modules():
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == 'st' and node.func.attr in ('dataframe', 'table', 'data_editor')):
                direct.append(f'{path.name}:{node.lineno}')
    assert not direct, f'usa show_table o show_static_table para que la tabla se pueda descargar: {direct}'


def test_excel_export_stays_inside_comet():
    """Scouting y las cuentas no ofrecen estas descargas: solo las pantallas de COMET (de administración) las usan."""
    allowed = {'comet_widgets.py'}
    offenders = [p.as_posix() for p in APP.rglob('*.py')
                 if p.name not in allowed and not p.name.startswith('comet_') and not p.name.startswith('test_')
                 and re.search(r'excel_export|download_excel|comet_widgets', p.read_text(encoding='utf-8'))]
    assert offenders == [], offenders


# --- versión del portal ---------------------------------------------------------------------------------------------------

def footer():
    from ui.portal_brand import version_footer
    version_footer()


def test_portal_version_is_semantic_and_shown_in_the_footer():
    from ui.portal_brand import PORTAL_VERSION
    assert re.fullmatch(r'\d+\.\d+\.\d+', PORTAL_VERSION)
    app = run(footer)
    assert f'>v{PORTAL_VERSION}<' in app.markdown[0].value
