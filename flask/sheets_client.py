from __future__ import annotations

from typing import List

import gspread


class GoogleSheetsClient:
    HEADERS: List[str] = [
        "Дата и время",
        "Имя",
        "Телефон",
        "Email",
        "Описание запроса",
        "Источник",
    ]

    def __init__(self, service_account_file: str, spreadsheet_name: str):
        self.service_account_file = service_account_file
        self.spreadsheet_name = spreadsheet_name

    def _get_worksheet(self):
        if not self.service_account_file:
            return None
        try:
            gc = gspread.service_account(filename=self.service_account_file)
            spreadsheet = gc.open(self.spreadsheet_name)
            worksheet = spreadsheet.sheet1

            current_headers = worksheet.row_values(1)
            if current_headers != self.HEADERS:
                worksheet.update("A1:F1", [self.HEADERS])

            return worksheet
        except Exception:
            return None

    def save_lead(
        self,
        created_at: str,
        name: str,
        phone: str,
        email: str,
        request_text: str,
        source: str,
    ) -> bool:
        worksheet = self._get_worksheet()
        if worksheet is None:
            return False
        try:
            worksheet.append_row(
                [created_at, name, phone, email, request_text, source],
                value_input_option="USER_ENTERED",
            )
            return True
        except Exception:
            return False
