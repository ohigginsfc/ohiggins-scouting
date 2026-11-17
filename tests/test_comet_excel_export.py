"""Excel de las tablas COMET: valores, formatos y protecciones, sin Streamlit y con datos ficticios."""
import io
import zipfile
from datetime import date, datetime, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest
from openpyxl import load_workbook

from scouting.comet import excel_export as ex


def book(frame, name='Tabla de prueba', **kwargs):
    return load_workbook(io.BytesIO(ex.build_workbook(frame, name, **kwargs)))


def sheet(frame, name='Tabla de prueba', **kwargs):
    workbook = book(frame, name, **kwargs)
    ws = workbook[workbook.sheetnames[0]]
    ws.expected_rows = len(frame)  # las celdas vacías del final no cuentan en max_row
    return ws


def column(ws, number):
    return [ws.cell(row=row, column=number).value for row in range(2, ws.expected_rows + 2)]


# --- datos ausentes: celda vacía, jamás 0 ni texto -------------------------------------------------------------------

def test_missing_values_are_empty_cells_and_real_zeros_stay_zero():
    frame = pd.DataFrame({'Jugador': ['A', 'B', 'C', 'D'], 'Minutos': [90.0, np.nan, 0.0, None],
                          'Goles': pd.array([1, None, 0, 2], dtype='Int64')})
    ws = sheet(frame)
    assert column(ws, 2) == [90, None, 0, None]
    assert column(ws, 3) == [1, None, 0, 2]


def test_a_numeric_column_with_gaps_stays_numeric_so_excel_can_sum_it():
    ws = sheet(pd.DataFrame({'Minutos': [90.0, np.nan, 45.0]}))
    assert [c.data_type for c in ws['A'][1:] if c.value is not None] == ['n', 'n']
    assert ws['A3'].value is None


def test_infinite_values_and_nat_are_empty_cells():
    frame = pd.DataFrame({'x': [np.inf, -np.inf, 1.5], 'fecha': [pd.NaT, pd.Timestamp('2026-01-02'), pd.NaT]})
    ws = sheet(frame)
    assert column(ws, 1) == [None, None, 1.5]
    assert column(ws, 2) == [None, datetime(2026, 1, 2), None]


def test_pandas_na_and_none_in_text_columns_are_empty_cells():
    ws = sheet(pd.DataFrame({'Nota': pd.array(['a', pd.NA, None], dtype='object')}))
    assert column(ws, 1) == ['a', None, None]


# --- texto: nunca fórmula ni error de Excel --------------------------------------------------------------------------

@pytest.mark.parametrize('text', ['=1+1', '=HYPERLINK("http://example.test","clic")', '+34 600 000 000', '-1', '@SUM(A1)',
                                  '#N/A', '#REF!', '=cmd|"/c calc"!A0'])
def test_text_is_never_stored_as_a_formula_or_an_error(text):
    stream = io.BytesIO(ex.build_workbook(pd.DataFrame({'Rival': [text]}), 'Rivales'))
    cell = load_workbook(stream)['Rivales']['A2']
    assert cell.value == text and cell.data_type == 's'
    xml = zipfile.ZipFile(stream).read('xl/worksheets/sheet1.xml').decode('utf-8')
    assert '<f>' not in xml and 't="e"' not in xml


def test_formula_like_headers_and_info_text_are_plain_text():
    workbook = book(pd.DataFrame({'=A1': [1]}), '=nombre', notes=['=1+1'])
    assert workbook.worksheets[0]['A1'].data_type == 's'
    assert all(cell.data_type != 'f' for sheet_ in workbook.worksheets for row in sheet_.iter_rows() for cell in row)


def test_control_characters_are_removed_and_text_is_cut_at_excel_limit():
    ws = sheet(pd.DataFrame({'Nota': ['hola\x00\x07 mundo', 'x' * 40000, 'Ñandú · ü']}))
    assert ws['A2'].value == 'hola mundo'
    assert len(ws['A3'].value) == 32767
    assert ws['A4'].value == 'Ñandú · ü'


# --- tipos, formatos y fechas ----------------------------------------------------------------------------------------

@pytest.mark.parametrize('python_format,excel_format', [
    ('{:.0f}', '0'), ('{:.1f}', '0.0'), ('{:.2f}', '0.00'), ('{:.1f} %', '0.0" %"'), ('{:.0f} min', '0" min"'),
    ('Pos. {:.0f}', '"Pos. "0'), ('{:+d}', None), ('texto', None), (None, None), (lambda value: str(value), None)])
def test_python_formats_become_excel_formats(python_format, excel_format):
    assert ex.excel_number_format(python_format) == excel_format


def test_numbers_keep_their_precision_and_take_the_on_screen_format():
    ws = sheet(pd.DataFrame({'Participación': [55.5555, 100.0], 'Edad': [17.0, 15.0], 'Sin formato': [1.5, 2.0]}),
               number_formats={'Participación': '{:.1f} %', 'Edad': '{:.0f}'})
    assert ws['A2'].value == 55.5555 and ws['A2'].number_format == '0.0" %"'
    assert ws['B2'].number_format == '0'
    assert ws['C2'].number_format == 'General'


def test_text_cells_ignore_numeric_formats():
    ws = sheet(pd.DataFrame({'Edad': ['—', 'n/d']}), number_formats={'Edad': '{:.0f}'})
    assert column(ws, 1) == ['—', 'n/d'] and ws['A2'].number_format == 'General'


def test_dates_are_real_dates_in_chilean_order():
    ws = sheet(pd.DataFrame({'Fecha': [pd.Timestamp('2026-11-01'), pd.Timestamp('2026-11-02 15:30'), date(2026, 11, 3)]}))
    assert ws['A2'].value == datetime(2026, 11, 1) and ws['A2'].number_format == 'dd-mm-yyyy'
    assert ws['A3'].value == datetime(2026, 11, 2, 15, 30) and ws['A3'].number_format == 'dd-mm-yyyy hh:mm'
    assert ws['A4'].number_format == 'dd-mm-yyyy'


def test_timezone_aware_times_keep_the_wall_clock_time_of_the_screen():
    stamp = pd.Timestamp('2026-11-01 10:00', tz='America/Santiago')
    assert sheet(pd.DataFrame({'Hora': [stamp]}))['A2'].value == datetime(2026, 11, 1, 10, 0)


def test_booleans_numpy_types_and_decimals_are_written_as_numbers():
    frame = pd.DataFrame({'Cumple': [True, False], 'n': np.array([3, 4], dtype=np.int64),
                          'x': [np.float32(1.5), np.float64(2.25)], 'd': [Decimal('1.5'), Decimal('NaN')]})
    ws = sheet(frame)
    assert column(ws, 1) == [True, False] and ws['A2'].data_type == 'b'
    assert column(ws, 2) == [3, 4] and column(ws, 3) == [1.5, 2.25] and column(ws, 4) == [1.5, None]


def test_lists_and_other_objects_are_written_as_text():
    ws = sheet(pd.DataFrame({'Valor': pd.Series([[1, 2], {'a': 1}, (3, 4)], dtype='object')}))
    assert column(ws, 1) == ['[1, 2]', "{'a': 1}", '(3, 4)']
    assert ex.cell_value(timedelta(minutes=5)) == '0:05:00'


# --- hoja lista para trabajar -----------------------------------------------------------------------------------------

def test_header_is_styled_frozen_and_filterable():
    ws = sheet(pd.DataFrame({'a': [1, 2], 'b': [3, 4]}))
    assert ws.freeze_panes == 'A2' and ws.auto_filter.ref == 'A1:B3'
    assert ws['A1'].font.bold and ws['A1'].fill.fill_type == 'solid'


def test_filter_covers_every_row_even_when_the_last_ones_have_no_data():
    ws = sheet(pd.DataFrame({'a': [1.0, np.nan, np.nan], 'b': [None, None, None]}))
    assert ws.auto_filter.ref == 'A1:B4'


def test_column_widths_fit_the_content_within_limits():
    frame = pd.DataFrame({'Jugador': ['Nombre muy largo de un jugador con tres apellidos'], 'Edad': [15],
                          'Título de columna larguísimo que se parte en varias líneas': [1]})
    widths = {k: v.width for k, v in sheet(frame).column_dimensions.items()}
    assert widths['A'] > widths['B'] >= ex.MIN_WIDTH
    assert widths['C'] <= ex.HEADER_WRAP_FROM + 2 + 1 and ex.MAX_WIDTH >= widths['A']


def test_empty_table_still_produces_a_valid_book_with_only_the_header():
    workbook = book(pd.DataFrame({'a': pd.Series(dtype='float64')}))
    ws = workbook.worksheets[0]
    assert ws.max_row == 1 and ws['A1'].value == 'a' and ws.auto_filter.ref is None
    assert book(pd.DataFrame()).sheetnames[-1] == ex.INFO_SHEET


def test_repeated_column_titles_are_kept():
    ws = sheet(pd.DataFrame([[1, 2]], columns=['Goles', 'Goles']))
    assert [ws['A1'].value, ws['B1'].value] == ['Goles', 'Goles'] and column(ws, 2) == [2]


def test_colors_repeat_the_screen_colors_for_known_values_only():
    frame = pd.DataFrame({'Resultado': ['Victoria', 'Otro', None]})
    ws = sheet(frame, fills={'Resultado': {'Victoria': ('#1B6B34', '#DCFCE7')}})
    assert ws['A2'].fill.start_color.rgb.endswith('DCFCE7') and ws['A2'].font.color.rgb.endswith('1B6B34')
    assert ws['A3'].fill.fill_type is None and ws['A4'].value is None


def test_invalid_colors_are_ignored_instead_of_breaking_the_download():
    ws = sheet(pd.DataFrame({'R': ['x']}), fills={'R': {'x': ('rojo', 'azul')}})
    assert ws['A2'].value == 'x' and ws['A2'].fill.fill_type is None


# --- nombre de hoja y de archivo ---------------------------------------------------------------------------------------

@pytest.mark.parametrize('name,expected', [
    ('Alertas · temporada 2026', 'Alertas'),
    ('Ranking: goles/minutos [U-15]', 'Ranking goles minutos U-15'),
    ('x' * 50, 'x' * 31),
    ("'Con apóstrofes'", 'Con apóstrofes'),
    ('   ', 'Tabla'), ('', 'Tabla'), ('\\/?*[]:', 'Tabla'),
])
def test_sheet_titles_are_valid_for_excel(name, expected):
    assert ex.sheet_title(name) == expected
    assert sheet(pd.DataFrame({'a': [1]}), name).title == expected


def test_a_table_named_like_the_info_sheet_does_not_clash_with_it():
    assert book(pd.DataFrame({'a': [1]}), 'Información').sheetnames == ['Tabla', ex.INFO_SHEET]


def test_filename_is_plain_ascii_dated_and_bounded():
    assert ex.export_filename('Alertas · temporada 2026', date(2026, 11, 12)) == 'comet_alertas_temporada_2026_2026-11-12.xlsx'
    assert ex.export_filename('Ñandú: Ranking de goles · U-15', date(2026, 1, 2)) == 'comet_nandu_ranking_de_goles_u_15_2026-01-02.xlsx'
    assert ex.export_filename('···', date(2026, 1, 2)) == 'comet_tabla_2026-01-02.xlsx'
    assert len(ex.slug('a b ' * 100)) <= ex.MAX_SLUG and not ex.slug('a b ' * 100).endswith('_')


def test_default_filename_date_is_chiles_today(monkeypatch):
    monkeypatch.setattr(ex, 'local_today', lambda: date(2026, 12, 31))
    assert ex.export_filename('Tabla').endswith('_2026-12-31.xlsx')


# --- hoja «Información» -----------------------------------------------------------------------------------------------

def test_information_sheet_documents_the_table_and_the_provisional_criteria():
    data = ex.build_workbook(pd.DataFrame({'a': [1, 2]}), 'Alertas · temporada 2026',
                             notes=['Supuesto: pendiente de confirmar · Regla A', 'Supuesto: pendiente de confirmar · Regla B'],
                             generated_at=datetime(2026, 11, 12, 9, 5), portal_version='1.2.0')
    rows = list(load_workbook(io.BytesIO(data))[ex.INFO_SHEET].iter_rows(values_only=True))
    assert ('Tabla', 'Alertas · temporada 2026') in rows
    assert ('Filas', 2) in rows
    assert ('Generado el', '12-11-2026 09:05 (hora de Chile)') in rows
    assert ('Versión del portal', 'v1.2.0') in rows
    assert ('Datos ausentes', ex.EMPTY_CELLS_NOTE) in rows
    assert [r[1] for r in rows if r[0] == 'Criterio provisional'] == [
        'Supuesto: pendiente de confirmar · Regla A', 'Supuesto: pendiente de confirmar · Regla B']


def test_information_sheet_without_notes_or_version_has_no_empty_rows():
    data = ex.build_workbook(pd.DataFrame({'a': [1]}), 'T', generated_at=datetime(2026, 1, 2, 3, 4))
    labels = [r[0] for r in load_workbook(io.BytesIO(data))[ex.INFO_SHEET].iter_rows(values_only=True)]
    assert labels == ['Tabla', 'Filas', 'Generado el', 'Origen', 'Datos ausentes']


def test_the_empty_cells_note_says_blank_is_not_zero():
    assert 'no significan 0' in ex.EMPTY_CELLS_NOTE and '«—»' in ex.EMPTY_CELLS_NOTE


def test_book_properties_identify_the_origin():
    workbook = book(pd.DataFrame({'a': [1]}), 'Alertas · temporada 2026')
    assert workbook.properties.creator == ex.ORIGIN and workbook.properties.title == 'Alertas · temporada 2026'
