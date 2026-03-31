"""
Загрузка настроек из переменных окружения (.env или система).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# .env рядом с проектом (папка bot) или в корне родителя
_env_dir = Path(__file__).resolve().parent
_project_root = _env_dir.parent
# utf-8-sig убирает BOM в начале файла — иначе первая переменная может не прочитаться
_env_encoding = "utf-8-sig"
# override=True: значения из .env перекрывают переменные среды Windows — иначе старый OPENAI_API_KEY из системы мешает обновлению в файле
load_dotenv(_env_dir / ".env", encoding=_env_encoding, override=True)
load_dotenv(_project_root / ".env", encoding=_env_encoding, override=True)


def _strip_env_value(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().strip('"').strip("'")


def _resolve_existing_file(raw: str) -> str:
    """
    Ищет файл по пути raw: абсолютный путь, затем относительно bot/, корня проекта и cwd.
    Нужно, чтобы ./keys.json из .env в корне проекта находился при запуске из папки bot/.
    """
    path_str = _strip_env_value(raw)
    if not path_str:
        return ""

    p = Path(path_str)
    if p.is_absolute() and p.is_file():
        return str(p.resolve())

    rel = path_str.lstrip("./").replace("\\", "/")
    for base in (_env_dir, _project_root, Path.cwd()):
        candidate = (base / path_str).resolve()
        if candidate.is_file():
            return str(candidate)
        candidate2 = (base / rel).resolve()
        if candidate2.is_file():
            return str(candidate2)

    return path_str


# Токен: основное имя + запасное BOT_TOKEN (частая опечатка в .env)
TELEGRAM_BOT_TOKEN: str = _strip_env_value(
    os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or ""
)
OPENAI_API_KEY: str = _strip_env_value(os.getenv("OPENAI_API_KEY"))
OPENAI_MODEL: str = _strip_env_value(os.getenv("OPENAI_MODEL")) or "gpt-4o-mini"

# Путь к JSON ключу сервисного аккаунта Google (после разрешения относительных путей)
_GOOGLE_CREDS_RAW: str = _strip_env_value(
    os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", "")
)
GOOGLE_SHEETS_CREDENTIALS_PATH: str = (
    _resolve_existing_file(_GOOGLE_CREDS_RAW) if _GOOGLE_CREDS_RAW else ""
)

SPREADSHEET_ID: str = os.getenv("SPREADSHEET_ID", "").strip()
# Имя листа в таблице (вкладка)
SHEET_NAME: str = os.getenv("SHEET_NAME", "Заявки").strip()


def validate_config() -> list[str]:
    """Возвращает список отсутствующих или неверных настроек."""
    errors: list[str] = []
    if not TELEGRAM_BOT_TOKEN:
        errors.append(
            "TELEGRAM_BOT_TOKEN не задан — в .env укажите TELEGRAM_BOT_TOKEN=число:строка "
            "(или BOT_TOKEN=...) без пробелов вокруг =; сохраните .env в UTF-8"
        )
    elif ":" not in TELEGRAM_BOT_TOKEN:
        errors.append(
            "TELEGRAM_BOT_TOKEN неверного формата: нужен вид 123456789:AAH... "
            "(обязательно двоеточие, без кавычек и пробелов вокруг)"
        )
    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY не задан")
    elif not OPENAI_API_KEY.startswith("sk-"):
        errors.append(
            "OPENAI_API_KEY должен быть ключом OpenAI и начинаться с sk- (или sk-proj-...). "
            "Похоже, в .env попал не тот секрет. Проверьте https://platform.openai.com/account/api-keys "
            "и при необходимости удалите дубликат OPENAI_API_KEY из «Переменные среды» Windows."
        )
    if not GOOGLE_SHEETS_CREDENTIALS_PATH:
        errors.append("GOOGLE_SHEETS_CREDENTIALS_PATH не задан")
    elif not Path(GOOGLE_SHEETS_CREDENTIALS_PATH).is_file():
        errors.append(
            f"Файл учётных данных не найден: {_GOOGLE_CREDS_RAW or GOOGLE_SHEETS_CREDENTIALS_PATH} "
            f"(искали также относительно {_project_root} и {_env_dir})"
        )
    if not SPREADSHEET_ID:
        errors.append("SPREADSHEET_ID не задан")
    return errors
