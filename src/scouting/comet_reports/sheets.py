"""Publicación de reportes con scope Sheets; catálogo de ingestión mantiene solo lectura."""
import base64
import json
import os
import time
import pandas as pd
from .errors import ReportError


class ReportSheets:
    def __init__(self, document_id):
        if not document_id:
            raise ValueError('Falta COMET_REPORT_SHEET_ID')
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            info = json.loads(base64.b64decode(''.join(os.environ.get('GOOGLE_SV_B64', '').split()), validate=True))
            credentials = Credentials.from_service_account_info(info,
                scopes=['https://www.googleapis.com/auth/spreadsheets'])
            self.document = gspread.authorize(credentials).open_by_key(document_id)
        except Exception:
            raise ReportError('No se pudo abrir la hoja de reportes; revisar credencial y permiso de editor') from None

    def replace(self, title, frame):
        import gspread
        title = str(title).replace('/', '-').replace('\\', '-')[:50]
        if not title:
            raise ValueError('Nombre de pestaña vacío')
        values = [[str(column) for column in frame.columns]]
        values.extend([["" if pd.isna(cell) else str(cell) for cell in row]
                       for row in frame.itertuples(index=False, name=None)])
        width = max(1, len(frame.columns))
        try:
            try:
                sheet = self.document.worksheet(title)
            except gspread.WorksheetNotFound:
                sheet = self.document.add_worksheet(title=title, rows=max(100, len(values)), cols=width)
            if sheet.row_count < len(values) or sheet.col_count < width:
                sheet.resize(rows=max(sheet.row_count, len(values)), cols=max(sheet.col_count, width))
            # One atomic Sheets request replaces values and clears omitted old cells. RAW string
            # values cannot turn player names beginning '=' into spreadsheet formulas.
            body = {'requests': [{'updateCells': {
                'range': {'sheetId': sheet.id, 'startRowIndex': 0, 'endRowIndex': sheet.row_count,
                          'startColumnIndex': 0, 'endColumnIndex': sheet.col_count},
                'rows': [{'values': [{'userEnteredValue': {'stringValue': cell}} for cell in row]} for row in values],
                'fields': 'userEnteredValue'}}]}
            for attempt in range(4):
                try:
                    self.document.batch_update(body)
                    return
                except gspread.APIError as exc:
                    if exc.response.status_code not in (429, 500, 502, 503, 504) or attempt == 3:
                        raise
                    time.sleep(min(5 * 2**attempt, 30))
        except Exception:
            raise ReportError('No se pudo publicar una pestaña COMET; revisar permisos y cuota. Publicación posiblemente parcial') from None
