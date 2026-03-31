# Telegram-бот: ИИ-ассистент и заявки в Google Sheets

Бот ведёт диалог через OpenAI, собирает **имя**, **контакт** (телефон или Telegram username) и **суть запроса**, затем добавляет строку в Google Таблицу.

## Требования

- Python **3.12**
- Токен Telegram-бота ([@BotFather](https://t.me/BotFather))
- Ключ [OpenAI API](https://platform.openai.com/)
- Проект Google Cloud с включёнными API **Google Sheets** и **Google Drive**
- Сервисный аккаунт и JSON-ключ; таблица расшарена на email сервисного аккаунта (права **Редактор**)

## Установка

```bash
cd bot
python -m venv .venv
```

Windows (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Linux / macOS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Переменные окружения

Создайте файл `.env` в папке `bot` (или в родительской папке проекта). Значения из `.env` **перекрывают** одноимённые переменные среды Windows — иначе старый `OPENAI_API_KEY` из системы может мешать обновлению ключа в файле.

| Переменная | Описание |
|------------|----------|
| `TELEGRAM_BOT_TOKEN` | Токен бота (допустимо имя `BOT_TOKEN`). Файл `.env` лучше сохранять в UTF-8 без BOM-проблем — при чтении используется `utf-8-sig` |
| `OPENAI_API_KEY` | Ключ OpenAI |
| `GOOGLE_SHEETS_CREDENTIALS_PATH` | Путь к JSON сервисного аккаунта: абсолютный или относительный — ищется от папки `bot`, корня проекта (родитель `bot`) и текущего каталога |
| `SPREADSHEET_ID` | ID таблицы из URL: `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/...` |
| `SHEET_NAME` | Имя вкладки (по умолчанию `Заявки`) |
| `OPENAI_MODEL` | Необязательно, по умолчанию `gpt-4o-mini` |

Пример `.env`:

```env
TELEGRAM_BOT_TOKEN=123456:ABC...
OPENAI_API_KEY=sk-...
GOOGLE_SHEETS_CREDENTIALS_PATH=C:\path\to\service-account.json
SPREADSHEET_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SHEET_NAME=Заявки
```

## Запуск

```bash
python bot.py
```

Должно появиться сообщение в логе: `Бот запущен (long polling)`. В Telegram откройте бота и отправьте `/start`.

## Структура проекта

| Файл | Назначение |
|------|------------|
| `bot.py` | Запуск бота, обработчики Telegram |
| `ai_logic.py` | OpenAI, промпт, сессии диалога |
| `sheets.py` | Запись в Google Sheets (gspread) |
| `config.py` | Загрузка переменных окружения |

## Примечания

- История диалога хранится **в памяти** процесса; после перезапуска бота пользователю нужно снова нажать `/start`.
- Если лист с именем из `SHEET_NAME` отсутствует, он будет создан; при пустой таблице добавится строка заголовков.
