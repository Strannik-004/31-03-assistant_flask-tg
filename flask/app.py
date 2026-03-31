import os
import re
from datetime import datetime
from typing import Dict, Optional

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session

from sheets_client import GoogleSheetsClient

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "change-me-in-production")

SHEETS_CLIENT = GoogleSheetsClient(
    service_account_file=os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", ""),
    spreadsheet_name=os.getenv("GOOGLE_SPREADSHEET_NAME", "Заявки с сайта"),
)

EMAIL_RE = re.compile(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")
PHONE_RE = re.compile(r"(\+?\d[\d\-\s\(\)]{8,}\d)")


def _default_state() -> Dict[str, object]:
    return {
        "lead": {"name": "", "phone": "", "email": "", "request": ""},
        "completed": False,
    }


def _get_state() -> Dict[str, object]:
    if "chat_state" not in session:
        session["chat_state"] = _default_state()
    return session["chat_state"]


def _save_state(state: Dict[str, object]) -> None:
    session["chat_state"] = state


def _extract_email(text: str) -> Optional[str]:
    match = EMAIL_RE.search(text)
    return match.group(1).strip() if match else None


def _extract_phone(text: str) -> Optional[str]:
    match = PHONE_RE.search(text)
    if not match:
        return None
    raw_phone = match.group(1)
    digits_count = len(re.sub(r"\D", "", raw_phone))
    return raw_phone.strip() if digits_count >= 10 else None


def _extract_name(text: str) -> Optional[str]:
    lowered = text.lower().strip()

    patterns = [
        r"(?:меня зовут|мо[её] имя|я)\s+([a-zA-Zа-яА-ЯёЁ\-]{2,30})",
        r"^([a-zA-Zа-яА-ЯёЁ\-]{2,30})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, lowered, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip(" .,!?:;")
            if candidate:
                return candidate.capitalize()
    return None


def _looks_like_request(text: str) -> bool:
    cleaned = text.strip()
    if len(cleaned) < 5:
        return False
    if _extract_email(cleaned) or _extract_phone(cleaned):
        return False
    if len(cleaned.split()) < 2:
        return False
    return True


def _next_prompt(lead: Dict[str, str]) -> str:
    if not lead["name"]:
        return "Подскажите, пожалуйста, как к вам обращаться?"
    if not (lead["phone"] or lead["email"]):
        return "Оставьте, пожалуйста, телефон или email для связи."
    if not lead["request"]:
        return "Кратко опишите, пожалуйста, ваш запрос."
    return ""


def _apply_message_to_lead(lead: Dict[str, str], text: str) -> None:
    email = _extract_email(text)
    phone = _extract_phone(text)
    name = _extract_name(text)

    if email and not lead["email"]:
        lead["email"] = email
    if phone and not lead["phone"]:
        lead["phone"] = phone
    if name and not lead["name"]:
        lead["name"] = name

    if not lead["request"] and _looks_like_request(text):
        lead["request"] = text.strip()

    if not lead["name"] and len(text.split()) <= 3 and not email and not phone:
        lead["name"] = text.strip().split()[0].capitalize()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat/start", methods=["POST"])
def chat_start():
    state = _get_state()
    if state.get("completed"):
        state = _default_state()
        _save_state(state)

    lead = state["lead"]
    greeting = (
        "Здравствуйте! Я помогу оформить заявку. "
        "Подскажите, пожалуйста, как к вам обращаться?"
        if not lead["name"]
        else "Здравствуйте! Продолжим оформление заявки."
    )
    return jsonify({"reply": greeting})


@app.route("/api/chat/message", methods=["POST"])
def chat_message():
    payload = request.get_json(silent=True) or {}
    user_text = str(payload.get("message", "")).strip()
    if not user_text:
        return jsonify({"reply": "Напишите, пожалуйста, сообщение."}), 400

    state = _get_state()
    if state.get("completed"):
        return jsonify(
            {
                "reply": "Спасибо! Ваша заявка уже принята. Если нужно, можно отправить новую после обновления страницы."
            }
        )

    lead = state["lead"]
    _apply_message_to_lead(lead, user_text)

    missing_prompt = _next_prompt(lead)
    if missing_prompt:
        _save_state(state)
        return jsonify({"reply": missing_prompt})

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    saved = SHEETS_CLIENT.save_lead(
        created_at=now,
        name=lead["name"],
        phone=lead["phone"],
        email=lead["email"],
        request_text=lead["request"],
        source="Сайт",
    )
    if not saved:
        _save_state(state)
        return jsonify(
            {
                "reply": "Не удалось сохранить заявку из-за технической ошибки. Пожалуйста, отправьте сообщение еще раз через минуту."
            }
        ), 500

    state["completed"] = True
    _save_state(state)
    return jsonify(
        {
            "reply": "Спасибо! Я передал вашу заявку. С вами свяжутся в ближайшее время."
        }
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )
