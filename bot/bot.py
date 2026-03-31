"""
Точка входа: Telegram-бот на pyTelegramBotAPI (telebot).
Принимает сообщения, передаёт их в ИИ, при готовности пишет строку в Google Sheets.
"""
from __future__ import annotations

import logging
import sys
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Сначала проверяем .env — иначе telebot падает с «Token must contain a colon»
from config import TELEGRAM_BOT_TOKEN, validate_config

_startup_errors = validate_config()
if _startup_errors:
    for err in _startup_errors:
        logger.error("%s", err)
    sys.exit(1)

import telebot
from openai import AuthenticationError
from telebot import types

from ai_logic import process_message, reset_session
from sheets import append_application

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode=None)
# Черновики заявок, ожидающих подтверждение пользователем перед записью.
_pending_confirmations: dict[int, dict[str, Any]] = {}


def _command_base(text: str | None) -> str:
    """/start или /start@BotName → /start"""
    if not text:
        return ""
    part = text.split()[0]
    return part.split("@", 1)[0].lower()


def _normalize_confirmation(text: str) -> str:
    return text.strip().lower()


def _is_confirm_yes(text: str) -> bool:
    normalized = _normalize_confirmation(text)
    return normalized in {"да", "д", "yes", "y", "ok", "ок", "подтверждаю"}


def _is_confirm_no(text: str) -> bool:
    normalized = _normalize_confirmation(text)
    return normalized in {"нет", "н", "no", "n", "отмена", "cancel"}


def _confirmation_preview(application: dict[str, str]) -> str:
    lines = [
        "Проверьте заявку перед сохранением:",
        f"Имя: {application.get('name', '')}",
        f"Телефон: {application.get('phone', '')}",
        f"Категория: {application.get('product_category', '')}",
        f"Запрос: {application.get('request_summary', '')}",
    ]
    if application.get("budget"):
        lines.append(f"Бюджет: {application['budget']}")
    if application.get("brand_preferences"):
        lines.append(f"Бренд/предпочтения: {application['brand_preferences']}")
    if application.get("key_requirements"):
        lines.append(f"Ключевые параметры: {application['key_requirements']}")
    if application.get("city_or_delivery"):
        lines.append(f"Город/доставка: {application['city_or_delivery']}")
    if application.get("contact_time"):
        lines.append(f"Удобное время связи: {application['contact_time']}")
    lines.append("")
    lines.append("Сохранить в таблицу? Ответьте: Да или Нет.")
    return "\n".join(lines)


def _welcome_message() -> str:
    return (
        "Здравствуйте! Я ИИ-консультант по бытовой технике.\n\n"
        "Чем могу помочь:\n"
        "- подсказать по выбору техники под ваши задачи;\n"
        "- объяснить отличия моделей и важные характеристики;\n"
        "- помочь с подбором по бюджету;\n"
        "- оформить заявку для менеджера.\n\n"
        "Напишите, пожалуйста, что именно подбираем."
    )


@bot.message_handler(commands=["start", "help"])
def cmd_start(message: types.Message) -> None:
    chat_id = message.chat.id
    base = _command_base(message.text)

    if base == "/help":
        bot.reply_to(
            message,
            "Я помогу оформить заявку: имя, контакт и суть запроса. "
            "Команда /start — начать заново. Просто отвечайте на вопросы сообщениями.",
        )
        return

    reset_session(chat_id)
    _pending_confirmations.pop(chat_id, None)
    logger.info("/start от user_id=%s", message.from_user.id if message.from_user else None)
    bot.reply_to(message, _welcome_message())

    try:
        result = process_message(chat_id, user_text=None)
    except AuthenticationError:
        logger.exception("OpenAI: неверный или просроченный API-ключ")
        bot.reply_to(
            message,
            "Не удаётся подключиться к ИИ: неверный ключ OpenAI на сервере. "
            "Администратору: проверьте OPENAI_API_KEY в .env (должен начинаться с sk-) "
            "и перезапустите бота.",
        )
        return
    except Exception:
        logger.exception("Ошибка при старте диалога")
        bot.reply_to(
            message,
            "Сервис временно недоступен. Попробуйте позже или напишите /start снова.",
        )
        return

    bot.reply_to(message, result["reply"])


@bot.message_handler(content_types=["text"])
def on_text(message: types.Message) -> None:
    chat_id = message.chat.id
    text = (message.text or "").strip()
    if not text:
        return

    logger.debug("Сообщение от chat_id=%s: %s...", chat_id, text[:80])

    if chat_id in _pending_confirmations:
        if _is_confirm_yes(text):
            pending = _pending_confirmations.pop(chat_id)
            uid = message.from_user.id if message.from_user else None
            uname = message.from_user.username if message.from_user else None
            try:
                append_application(
                    name=pending["name"],
                    phone=pending["phone"],
                    product_category=pending["product_category"],
                    request_summary=pending["request_summary"],
                    budget=pending.get("budget", ""),
                    brand_preferences=pending.get("brand_preferences", ""),
                    key_requirements=pending.get("key_requirements", ""),
                    city_or_delivery=pending.get("city_or_delivery", ""),
                    contact_time=pending.get("contact_time", ""),
                    comment=pending.get("comment", ""),
                    dialog_summary=pending.get("dialog_summary", ""),
                    manager_call_needed=pending.get("manager_call_needed", "Да"),
                    telegram_user_id=uid,
                    telegram_username=uname,
                )
            except Exception:
                logger.exception("Ошибка записи в Google Sheets")
                bot.reply_to(
                    message,
                    "⚠️ Подтверждение получено, но запись в таблицу не удалась. "
                    "Попробуйте ещё раз чуть позже.",
                )
                return

            reset_session(chat_id)
            bot.reply_to(
                message,
                "✅ Заявка сохранена. Спасибо! Для новой заявки нажмите /start.",
            )
            return

        if _is_confirm_no(text):
            _pending_confirmations.pop(chat_id, None)
            reset_session(chat_id)
            bot.reply_to(
                message,
                "Хорошо, не сохраняю. Давайте оформим заново — нажмите /start.",
            )
            return

        bot.reply_to(
            message,
            "Нужно подтверждение: ответьте «Да», чтобы сохранить, или «Нет», чтобы отменить.",
        )
        return

    try:
        result = process_message(chat_id, user_text=text)
    except AuthenticationError:
        logger.exception("OpenAI: неверный или просроченный API-ключ")
        bot.reply_to(
            message,
            "Ошибка настройки ключа OpenAI. Обратитесь к администратору.",
        )
        return
    except Exception:
        logger.exception("Ошибка обработки сообщения")
        bot.reply_to(
            message,
            "Не удалось обработать сообщение. Попробуйте ещё раз или /start.",
        )
        return

    reply = result["reply"]

    if result["ready_to_submit"]:
        application = {
            "name": result["name"] or "",
            "phone": result["phone"] or "",
            "product_category": result["product_category"] or "",
            "request_summary": result["request_summary"] or "",
            "budget": result["budget"] or "",
            "brand_preferences": result["brand_preferences"] or "",
            "key_requirements": result["key_requirements"] or "",
            "city_or_delivery": result["city_or_delivery"] or "",
            "contact_time": result["contact_time"] or "",
            "comment": result["comment"] or "",
            "dialog_summary": result["dialog_summary"] or "",
            "manager_call_needed": result["manager_call_needed"] or "Да",
        }
        _pending_confirmations[chat_id] = {
            **application,
        }
        bot.reply_to(
            message,
            reply + "\n\n" + _confirmation_preview(application),
        )
        return

    bot.reply_to(message, reply)


def main() -> None:
    logger.info("Бот запущен (long polling)")
    bot.infinity_polling(skip_pending=True, logger_level=logging.WARNING)


if __name__ == "__main__":
    main()
