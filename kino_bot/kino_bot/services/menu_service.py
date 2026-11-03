"""Asosiy menyuni yuborish (premium ikonka rad etilsa — oddiy emoji fallback)."""
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from keyboards.user import main_menu
from services.emoji_service import emoji_service

log = logging.getLogger(__name__)


async def send_menu(bot: Bot, chat_id: int, lang: str, text: str):
    try:
        return await bot.send_message(chat_id, text, reply_markup=main_menu(lang))
    except TelegramBadRequest as e:
        low = str(e).lower()
        if emoji_service.has_any() and any(w in low for w in ("emoji", "icon", "button", "document_invalid")):
            log.warning("Premium emoji tugma ikonkalari rad etildi (%s). Oddiy emoji fallback yoqildi.", e)
            emoji_service.disabled = True
            return await bot.send_message(chat_id, text, reply_markup=main_menu(lang))
        raise
