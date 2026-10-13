"""Lectura del catálogo de endpoints; sin operaciones de escritura ni scope Drive."""
import base64
import json
import os

import pandas as pd


class GoogleSheets:
    def __init__(self):
        value = os.environ.get('GOOGLE_SV_B64', '')
        if not value:
            raise ValueError('Falta GOOGLE_SV_B64 para leer el catálogo COMET')
        try:
            info = json.loads(base64.b64decode(''.join(value.split()), validate=True))
            import gspread
            from google.oauth2.service_account import Credentials
            credentials = Credentials.from_service_account_info(
                info, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
            self.client = gspread.authorize(credentials)
        except Exception:
            raise ValueError('GOOGLE_SV_B64 no contiene una credencial válida') from None

    def download_as_df(self, sheet_id, worksheet_name=None):
        try:
            document = self.client.open_by_key(sheet_id)
            sheet = document.worksheet(worksheet_name) if worksheet_name else document.sheet1
            return pd.DataFrame(sheet.get_all_records())
        except Exception:
            raise RuntimeError('No se pudo leer el catálogo COMET de Google Sheets; revisar acceso y configuración') from None
