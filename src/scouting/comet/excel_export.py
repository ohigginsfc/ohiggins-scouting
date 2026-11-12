"""Archivo Excel (.xlsx) con una tabla del seguimiento COMET.

Es lógica pura, sin Streamlit: recibe la tabla tal como se ve en pantalla (columnas ya renombradas y ordenadas) y devuelve
los bytes del libro. Reglas de la exportación:

* Un dato ausente queda como celda vacía, nunca como 0 ni como texto: en la pantalla se ve «—», pero en Excel las columnas
  numéricas deben seguir siendo números que se pueden ordenar, sumar y graficar sin que un «—» cuente como 0.
* Un texto jamás se interpreta como fórmula ni como error de Excel (un rival llamado «=1+1» o «#N/A» se guarda como texto).
* La hoja «Información» dice qué tabla es, cuándo y con qué versión del portal se generó, y repite los criterios
  provisionales que la pantalla mostraba, para que una cifra supuesta no circule como si el club la hubiera aprobado.
"""
from __future__ import annotations

import io
import math
import re
import unicodedata
from datetime import date, datetime, time
from decimal import Decimal
from typing import Callable, Mapping, Optional, Sequence, Union

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .facts import LOCAL_TZ

XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
INFO_SHEET = 'Información'
ORIGIN = 'Portal O’Higgins · COMET'
EMPTY_CELLS_NOTE = 'Las celdas vacías son datos ausentes (en la pantalla se ven como «—»); no significan 0.'

HEADER_COLOR = '1B537B'      # azul del club (el mismo de los gráficos)
MAX_SHEET_TITLE = 31         # límite de Excel para el nombre de una hoja
MAX_CELL_TEXT = 32767        # límite de Excel por celda
MAX_SLUG = 80                # largo máximo de la parte descriptiva del nombre del archivo
MIN_WIDTH, MAX_WIDTH = 8, 60
HEADER_WRAP_FROM = 18        # los títulos de columna más largos se parten en varias líneas
DATE_FORMAT = 'dd-mm-yyyy'
DATETIME_FORMAT = 'dd-mm-yyyy hh:mm'

Formatter = Union[str, Callable, None]

_ILLEGAL_XML = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f]')
_SHEET_FORBIDDEN = re.compile(r'[\[\]:*?/\\]')
_PY_NUMBER_FORMAT = re.compile(r'^(?P<pre>[^{}]*)\{:\.(?P<digits>\d+)f\}(?P<post>[^{}]*)$')
_HEX_COLOR = re.compile(r'^[0-9A-Fa-f]{6}$')


def local_today() -> date:
    """Fecha de hoy en Chile (el servidor puede estar en otra zona horaria)."""
    return pd.Timestamp.now(tz=LOCAL_TZ).date()


def slug(text: str, limit: int = MAX_SLUG) -> str:
    """Texto en minúsculas, sin tildes y con guiones bajos: apto para el nombre de un archivo."""
    folded = unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii')
    words = re.sub(r'[^a-z0-9]+', '_', folded.lower()).strip('_')
    return words[:limit].strip('_') or 'tabla'


def export_filename(name: str, today: Optional[date] = None) -> str:
    """comet_<tabla>_<aaaa-mm-dd>.xlsx, con la fecha de hoy en Chile."""
    return f'comet_{slug(name)}_{(today or local_today()):%Y-%m-%d}.xlsx'


def sheet_title(name: str) -> str:
    """Nombre de hoja válido en Excel: lo que va antes de « · », sin []:*?/\\ y con hasta 31 caracteres."""
    head = _SHEET_FORBIDDEN.sub(' ', str(name).split(' · ')[0])
    head = _ILLEGAL_XML.sub('', head)
    head = re.sub(r'\s+', ' ', head).strip(" '")  # Excel no admite apóstrofes al inicio ni al final
    return head[:MAX_SHEET_TITLE].strip(" '") or 'Tabla'


def excel_number_format(formatter: Formatter) -> Optional[str]:
    """Formato de número de Excel equivalente a uno de Python como '{:.1f} %'; None si no se puede traducir.

    Las funciones de formato propias (por ejemplo, de fechas) no se traducen: la celda conserva el valor real.
    """
    if not isinstance(formatter, str):
        return None
    match = _PY_NUMBER_FORMAT.match(formatter)
    if match is None:
        return None
    digits = int(match['digits'])
    core = '0' if digits == 0 else '0.' + '0' * digits
    pre = f'"{match["pre"]}"' if match['pre'] else ''
    post = f'"{match["post"]}"' if match['post'] else ''
    return f'{pre}{core}{post}'


def _clean(text: str) -> str:
    return _ILLEGAL_XML.sub('', text)[:MAX_CELL_TEXT]


def cell_value(value):
    """Valor listo para una celda de Excel; None (celda vacía) si el dato falta. Un dato ausente nunca pasa a ser 0."""
    if value is None or value is pd.NaT or value is pd.NA:
        return None
    if isinstance(value, str):
        return _clean(value)
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating, Decimal)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, (datetime, np.datetime64)):
        stamp = pd.Timestamp(value)
        if pd.isna(stamp):
            return None
        if stamp.tzinfo is not None:
            stamp = stamp.tz_localize(None)  # hora local tal como se ve en pantalla; Excel no guarda zonas
        return stamp.to_pydatetime()
    if isinstance(value, date):
        return value
    return _clean(str(value))


def _write(cell, value) -> None:
    cell.value = value
    if isinstance(value, str):
        cell.data_type = 's'  # «=1+1» o «#N/A» se guardan como texto, no como fórmula ni como error
        if value[:1] in ('=', '+', '-', '@'):
            cell.quotePrefix = True  # y editar la celda en Excel tampoco la convierte en fórmula


def _hex(color) -> Optional[str]:
    text = str(color).lstrip('#')
    return text.upper() if _HEX_COLOR.match(text) else None


def _shown_length(value, number_format: Optional[str]) -> int:
    if isinstance(value, datetime):
        return len(DATE_FORMAT) if value.time() == time.min else len(DATETIME_FORMAT)
    if isinstance(value, date):
        return len(DATE_FORMAT)
    if isinstance(value, float):
        decimals = number_format.count('0') - 1 if number_format and '.' in number_format else 0
        return len(f'{value:.{max(decimals, 0)}f}') + (2 if number_format and '"' in number_format else 0)
    return len(str(value))


def build_workbook(frame: pd.DataFrame, name: str, *, number_formats: Optional[Mapping[str, Formatter]] = None,
                   fills: Optional[Mapping[str, Mapping[str, tuple]]] = None, notes: Sequence[str] = (),
                   generated_at: Optional[datetime] = None, portal_version: Optional[str] = None) -> bytes:
    """Libro .xlsx con la tabla en la primera hoja y la hoja «Información».

    `number_formats`: {título de columna: formato de Python como '{:.1f} %'} para que Excel muestre lo mismo que la pantalla.
    `fills`: {título de columna: {valor de la celda: (color del texto, color de fondo)}} para repetir los colores de la tabla.
    `notes`: criterios provisionales que se vieron en pantalla; se copian a la hoja «Información».
    """
    workbook = Workbook()
    sheet = workbook.active
    title = sheet_title(name)
    sheet.title = 'Tabla' if title.casefold() == INFO_SHEET.casefold() else title

    columns = list(frame.columns)
    formats = [excel_number_format((number_formats or {}).get(column)) for column in columns]
    palettes = [(fills or {}).get(column) or {} for column in columns]
    widths = [min(len(str(column)), HEADER_WRAP_FROM) for column in columns]

    header_font = Font(bold=True, color='FFFFFF')
    header_fill = PatternFill('solid', start_color=HEADER_COLOR, end_color=HEADER_COLOR)
    header_align = Alignment(vertical='center', wrap_text=True)
    for index, column in enumerate(columns, start=1):
        cell = sheet.cell(row=1, column=index)
        _write(cell, _clean(str(column)))
        cell.font, cell.fill, cell.alignment = header_font, header_fill, header_align

    painted: dict = {}
    for row_number, row in enumerate(frame.itertuples(index=False, name=None), start=2):
        for index, raw in enumerate(row, start=1):
            value = cell_value(raw)
            if value is None:
                continue  # celda vacía
            cell = sheet.cell(row=row_number, column=index)
            _write(cell, value)
            number_format = formats[index - 1]
            if isinstance(value, datetime):
                cell.number_format = DATE_FORMAT if value.time() == time.min else DATETIME_FORMAT
            elif isinstance(value, date):
                cell.number_format = DATE_FORMAT
            elif number_format and isinstance(value, (int, float)) and not isinstance(value, bool):
                cell.number_format = number_format
            widths[index - 1] = max(widths[index - 1], _shown_length(value, number_format))
            colors = palettes[index - 1].get(value) if isinstance(value, str) else None
            if colors:
                ink, paper = _hex(colors[0]), _hex(colors[1])
                if ink and paper:
                    if (ink, paper) not in painted:
                        painted[(ink, paper)] = (Font(bold=True, color=ink),
                                                 PatternFill('solid', start_color=paper, end_color=paper))
                    cell.font, cell.fill = painted[(ink, paper)]

    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = max(MIN_WIDTH, min(width + 2, MAX_WIDTH))
    if columns:
        sheet.freeze_panes = 'A2'
        if len(frame):  # del frame, no de las celdas escritas: una fila sin ningún dato también es parte de la tabla
            sheet.auto_filter.ref = f'A1:{get_column_letter(len(columns))}{len(frame) + 1}'

    _write_info(workbook, name, len(frame), notes, generated_at, portal_version)
    workbook.properties.creator = ORIGIN
    workbook.properties.title = _clean(str(name))[:255]
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _write_info(workbook: Workbook, name: str, rows: int, notes: Sequence[str], generated_at: Optional[datetime],
                portal_version: Optional[str]) -> None:
    stamp = generated_at or pd.Timestamp.now(tz=LOCAL_TZ).tz_localize(None)
    lines = [('Tabla', str(name)), ('Filas', rows), ('Generado el', f'{stamp:%d-%m-%Y %H:%M} (hora de Chile)'),
             ('Origen', ORIGIN)]
    if portal_version:
        lines.append(('Versión del portal', f'v{portal_version}'))
    lines.append(('Datos ausentes', EMPTY_CELLS_NOTE))
    lines += [('Criterio provisional', str(note)) for note in notes]
    info = workbook.create_sheet(INFO_SHEET)
    for number, (label, value) in enumerate(lines, start=1):
        label_cell, value_cell = info.cell(row=number, column=1), info.cell(row=number, column=2)
        _write(label_cell, label)
        _write(value_cell, _clean(value) if isinstance(value, str) else value)
        label_cell.font = Font(bold=True, color=HEADER_COLOR)
        label_cell.alignment = Alignment(vertical='top')
        value_cell.alignment = Alignment(vertical='top', wrap_text=True, horizontal='left')
    info.column_dimensions['A'].width = 24
    info.column_dimensions['B'].width = 100
