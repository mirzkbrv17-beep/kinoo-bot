"""Admin routerlari uchun: faqat ADMIN_ID / admins jadvalidagi rollar."""
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from keyboards.admin import MOD_ACTIONS


class AdminMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        role = data.get("role")
        if role is None:
            if isinstance(event, CallbackQuery):
                await event.answer("⛔ Ruxsat yo'q", show_alert=True)
            elif isinstance(event, Message):
                await event.answer("⛔ Ruxsat yo'q")
            return None
        if role == "moderator" and isinstance(event, CallbackQuery):
            cb = event.data or ""
            if cb.startswith("adm:") and cb.split(":")[1] not in MOD_ACTIONS:
                await event.answer("⛔ Bu amal faqat adminlar uchun", show_alert=True)
                return None
        return await handler(event, data)
