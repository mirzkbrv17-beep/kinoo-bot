"""Majburiy obuna: /start emas, BARCHA xabar va callback'larda tekshiradi."""
import logging

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from keyboards.inline import subscribe_kb
from services.subscription_service import missing_channels
from utils.texts import t

log = logging.getLogger(__name__)
PASS_CALLBACKS = ("chk_sub", "noop")


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user, s, bot = data.get("user"), data.get("session"), data.get("bot")
        if user is None or s is None or data.get("staff"):
            return await handler(event, data)
        if isinstance(event, CallbackQuery) and (event.data or "") in PASS_CALLBACKS:
            return await handler(event, data)
        missing = await missing_channels(bot, s, user.id)
        if not missing:
            return await handler(event, data)
        lang = data.get("lang", "uz")
        kb = subscribe_kb(missing, lang)
        if isinstance(event, Message):
            await event.answer(t(lang, "sub_required"), reply_markup=kb)
        elif isinstance(event, CallbackQuery):
            await event.answer()
            if event.message:
                await event.message.answer(t(lang, "sub_required"), reply_markup=kb)
        return None
