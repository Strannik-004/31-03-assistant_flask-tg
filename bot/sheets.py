"""
Запись заявок в Google Таблицу через gspread и сервисный аккаунт.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

from config import (
    GOOGLE_SHEETS_CREDENTIALS_PATH,
    SHEET_NAME,
    SPREADSHEET_ID,
)

logger = logging.getLogger(__name__)

# Области для Google Sheets API
_SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
)

EXPECTED_HEADERS = [
    "Дата и время (UTC)",
    "Источник",
    "Имя",
    "Телефон",
    "Telegram @username",
    "Категория товара",
    "Запрос клиента",
    "Бюджет",
    "Бренд / предпочтения",
    "Ключевые характеристики",
    "Город / доставка",
    "Удобное время связи",
    "Статус",
    "Комментарий",
    "История диалога (краткое резюме)",
    "Нужен звонок менеджера",
]


def _get_client() -> gspread.Client:
    path = Path(GOOGLE_SHEETS_CREDENTIALS_PATH)
    creds = Credentials.from_service_account_file(str(path), scopes=_SCOPES)
    return gspread.authorize(creds)


def ensure_header_row() -> None:
    """
    Создаёт лист при необходимости и гарантирует корректную строку заголовков.
    Если лист не пустой, но заголовки отличаются от ожидаемых — первая строка будет обновлена.
    """
    client = _get_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    try:
        worksheet = spreadsheet.worksheet(SHEET_NAME)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows=1000, cols=20)
        logger.info("Создан новый лист: %s", SHEET_NAME)

    header_row = worksheet.row_values(1)
    if not header_row:
        worksheet.update("A1:P1", [EXPECTED_HEADERS], value_input_option="USER_ENTERED")
        logger.info("Добавлена строка заголовков на лист «%s»", SHEET_NAME)
        return

    normalized = [cell.strip() for cell in header_row[: len(EXPECTED_HEADERS)]]
    if normalized != EXPECTED_HEADERS:
        worksheet.update("A1:P1", [EXPECTED_HEADERS], value_input_option="USER_ENTERED")
        logger.info("Заголовки листа «%s» обновлены до актуальной структуры", SHEET_NAME)


def append_application(
    name: str,
    phone: str,
    product_category: str,
    request_summary: str,
    budget: str = "",
    brand_preferences: str = "",
    key_requirements: str = "",
    city_or_delivery: str = "",
    contact_time: str = "",
    comment: str = "",
    dialog_summary: str = "",
    manager_call_needed: str = "Да",
    telegram_user_id: int | None = None,
    telegram_username: str | None = None,
) -> None:
    """
    Добавляет одну заявку в конец листа.
    """
    ensure_header_row()
    client = _get_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    worksheet = spreadsheet.worksheet(SHEET_NAME)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    username_cell = f"@{telegram_username}" if telegram_username else ""

    worksheet.append_row(
        [
            ts,
            "Telegram bot",
            name.strip(),
            phone.strip(),
            username_cell,
            product_category.strip(),
            request_summary.strip(),
            budget.strip(),
            brand_preferences.strip(),
            key_requirements.strip(),
            city_or_delivery.strip(),
            contact_time.strip(),
            "Новая заявка",
            comment.strip(),
            dialog_summary.strip(),
            manager_call_needed.strip() or "Да",
        ],
        value_input_option="USER_ENTERED",
    )
    logger.info(
        "Заявка записана в таблицу: user_id=%s",
        telegram_user_id,
    )
