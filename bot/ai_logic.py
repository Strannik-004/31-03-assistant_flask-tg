"""
Диалог с OpenAI: консультация по бытовой технике и сбор расширенной заявки в JSON.
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Any

from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL

logger = logging.getLogger(__name__)

client = OpenAI(api_key=OPENAI_API_KEY)

# История сообщений по chat_id (в памяти процесса)
_sessions: dict[int, list[dict[str, str]]] = defaultdict(list)

SYSTEM_PROMPT = """Ты — ИИ-консультант магазина бытовой техники в Telegram.

Роль:
- помогать выбрать технику;
- отвечать кратко и понятно по сценариям использования и важным параметрам;
- мягко подводить к оформлению заявки;
- собирать структурированные данные для передачи менеджеру.

Стиль:
- дружелюбно, вежливо, профессионально;
- без давления и без агрессивных продаж;
- без выдумывания характеристик, цен, наличия и сроков;
- если точных данных нет — честно говори, что лучше уточнить у менеджера.

Обязательные поля ПОЛНОЙ заявки:
1) name (имя клиента),
2) phone (телефон),
3) product_category (категория товара),
4) request_summary (краткое описание запроса).

Желательные поля:
- budget,
- brand_preferences,
- key_requirements,
- city_or_delivery,
- contact_time,
- comment.

Дополнительно:
- dialog_summary: короткое резюме диалога для менеджера (1-2 предложения),
- manager_call_needed: "Да" или "Нет".

Правила сбора:
- сначала помогай по вопросу клиента, потом предлагай оформить заявку;
- задавай уточняющие вопросы по 1-3 за сообщение;
- не переспрашивай то, что уже известно;
- если клиент не готов давать телефон, не дави и продолжай консультацию;
- ready_to_submit=true только когда обязательные поля уже явно получены от клиента;
- если пользователь исправил данные, используй последние данные.

Если сообщение пользователя не по теме — мягко верни к подбору техники или оформлению заявки.

Ответ ВСЕГДА строго одним JSON без markdown и без текста вокруг:
{
  "reply": "текст ответа клиенту",
  "name": "..." или null,
  "phone": "..." или null,
  "product_category": "..." или null,
  "request_summary": "..." или null,
  "budget": "..." или null,
  "brand_preferences": "..." или null,
  "key_requirements": "..." или null,
  "city_or_delivery": "..." или null,
  "contact_time": "..." или null,
  "comment": "..." или null,
  "dialog_summary": "..." или null,
  "manager_call_needed": "Да" или "Нет" или null,
  "ready_to_submit": true/false
}
"""

JSON_INSTRUCTION = (
    "Ответь строго одним JSON-объектом с ключами: "
    "reply, name, phone, product_category, request_summary, budget, "
    "brand_preferences, key_requirements, city_or_delivery, contact_time, "
    "comment, dialog_summary, manager_call_needed, ready_to_submit."
)


def reset_session(chat_id: int) -> None:
    """Очищает историю диалога для чата (новая заявка)."""
    if chat_id in _sessions:
        del _sessions[chat_id]
        logger.debug("Сессия сброшена: chat_id=%s", chat_id)


def _parse_assistant_json(content: str) -> dict[str, Any]:
    """Достаёт JSON из ответа модели."""
    text = content.strip()
    # Иногда модель оборачивает в ```json
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        text = text.strip()
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
    return json.loads(text)


def process_message(chat_id: int, user_text: str | None) -> dict[str, Any]:
    """
    Один ход диалога.

    user_text=None используется после /start: модель сама поприветствует и начнёт сбор.

    Возвращает словарь с текстом ответа, флагом готовности и полями заявки.
    """
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + JSON_INSTRUCTION},
    ]
    messages.extend(_sessions[chat_id])

    if user_text is None:
        user_payload = (
            "[Служебное событие: пользователь только что нажал /start — "
            "поприветствуй и начни сбор заявки с первого шага.]"
        )
    else:
        user_payload = user_text

    messages.append({"role": "user", "content": user_payload})

    try:
        completion = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.5,
            response_format={"type": "json_object"},
        )
    except Exception:
        logger.exception("Ошибка запроса к OpenAI")
        raise

    raw = completion.choices[0].message.content or "{}"
    try:
        data = _parse_assistant_json(raw)
    except json.JSONDecodeError:
        logger.warning("Невалидный JSON от модели: %s", raw[:500])
        data = {
            "reply": "Произошла техническая ошибка. Напишите, пожалуйста, ещё раз.",
            "name": None,
            "phone": None,
            "product_category": None,
            "request_summary": None,
            "budget": None,
            "brand_preferences": None,
            "key_requirements": None,
            "city_or_delivery": None,
            "contact_time": None,
            "comment": None,
            "dialog_summary": None,
            "manager_call_needed": None,
            "ready_to_submit": False,
        }

    reply = str(data.get("reply") or "Продолжим оформление заявки?").strip()
    name = data.get("name")
    phone = data.get("phone")
    product_category = data.get("product_category")
    request_summary = data.get("request_summary")
    budget = data.get("budget")
    brand_preferences = data.get("brand_preferences")
    key_requirements = data.get("key_requirements")
    city_or_delivery = data.get("city_or_delivery")
    contact_time = data.get("contact_time")
    comment = data.get("comment")
    dialog_summary = data.get("dialog_summary")
    manager_call_needed = data.get("manager_call_needed")
    ready = bool(data.get("ready_to_submit"))

    def _clean_str(v: Any) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    name = _clean_str(name)
    phone = _clean_str(phone)
    product_category = _clean_str(product_category)
    request_summary = _clean_str(request_summary)
    budget = _clean_str(budget)
    brand_preferences = _clean_str(brand_preferences)
    key_requirements = _clean_str(key_requirements)
    city_or_delivery = _clean_str(city_or_delivery)
    contact_time = _clean_str(contact_time)
    comment = _clean_str(comment)
    dialog_summary = _clean_str(dialog_summary)
    manager_call_needed = _clean_str(manager_call_needed)
    if manager_call_needed not in {"Да", "Нет"}:
        manager_call_needed = None

    # Жёсткая проверка: не отправляем в таблицу с пустыми полями
    if ready and not (name and phone and product_category and request_summary):
        logger.warning(
            "Модель вернула ready_to_submit=true при неполных полях: "
            "name=%r phone=%r category=%r request=%r",
            name,
            phone,
            product_category,
            request_summary,
        )
        ready = False

    # Сохраняем в историю только «реальные» реплики пользователя и ответы ассистента
    if user_text is not None:
        _sessions[chat_id].append({"role": "user", "content": user_text})
    _sessions[chat_id].append({"role": "assistant", "content": reply})

    # Ограничение длины истории (защита от переполнения контекста)
    max_pairs = 40
    if len(_sessions[chat_id]) > max_pairs * 2:
        _sessions[chat_id] = _sessions[chat_id][-max_pairs * 2 :]

    return {
        "reply": reply,
        "ready_to_submit": ready,
        "name": name,
        "phone": phone,
        "product_category": product_category,
        "request_summary": request_summary,
        "budget": budget,
        "brand_preferences": brand_preferences,
        "key_requirements": key_requirements,
        "city_or_delivery": city_or_delivery,
        "contact_time": contact_time,
        "comment": comment,
        "dialog_summary": dialog_summary,
        "manager_call_needed": manager_call_needed,
    }
