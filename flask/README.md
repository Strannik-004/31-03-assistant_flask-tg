# Flask чат-виджет для лендинга

Минималистичное Flask-приложение с чат-виджетом для сайта.  
Виджет собирает заявку (имя, контакт, описание запроса) и сохраняет ее в Google Sheets `Заявки с сайта`.

## Структура

```text
.
├─ app.py
├─ sheets_client.py
├─ requirements.txt
├─ .env.example
├─ templates/
│  └─ index.html
└─ static/
   ├─ css/
   │  └─ style.css
   └─ js/
      └─ chat.js
```

## 1) Установка

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 2) Настройка Google Sheets API

1. Создайте проект в Google Cloud.
2. Включите **Google Sheets API**.
3. Создайте **Service Account**.
4. Сгенерируйте JSON-ключ и сохраните его в корне проекта (например, `my-project-service-account.json`).
5. Создайте Google-таблицу с названием **`Заявки с сайта`**.
6. Нажмите "Поделиться" у таблицы и добавьте email сервисного аккаунта (из JSON) с правами редактора.

При первом сохранении заявки приложение автоматически выставит заголовки:
- Дата и время
- Имя
- Телефон
- Email
- Описание запроса
- Источник

## 3) Переменные окружения

Скопируйте `.env.example` в `.env` и заполните:

```env
FLASK_SECRET_KEY=replace_with_random_secret
FLASK_DEBUG=1
PORT=5000
GOOGLE_SERVICE_ACCOUNT_FILE=./my-project-service-account.json
GOOGLE_SPREADSHEET_NAME=Заявки с сайта
```

## 4) Запуск

```bash
python app.py
```

Откройте в браузере: [http://localhost:5000](http://localhost:5000)

## Логика диалога

1. Приветствие.
2. Запрос имени (если неизвестно).
3. Запрос контакта (телефон или email).
4. Запрос описания запроса.
5. После получения минимального набора данных заявка сохраняется в Google Sheets.
6. Пользователь получает финальное подтверждение.

## Примечания

- Реализовано без Telegram-библиотек и без Telegram-логики.
- Состояние диалога хранится в Flask session.
- Если указан только телефон или только email, второй контакт остается пустым.
- В поле "Источник" всегда записывается `Сайт`.
