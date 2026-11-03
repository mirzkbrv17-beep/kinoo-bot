"""Foydalanuvchini ro'yxatga olish, DB sessiya, rol, ban tekshiruvi, referal."""
import logging
import re

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from config import settings
from database.db import session_maker
from database.models import Referral, User
from database.queries import role_of
from utils.helpers import utcnow
from utils.texts import t

log = logging.getLogger(__name__)
REF_RE = re.compile(r"^/start\s+ref_(\d+)$")


class UserMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        tg = data.get("event_from_user")
        if tg is None or tg.is_bot:
            return await handler(event, data)
        async with session_maker() as s:
            user = await s.get(User, tg.id)
            is_new = user is None
            name = (tg.full_name or "")[:250]
            if is_new:
                lang = "ru" if (tg.language_code or "").startswith("ru") else settings.default_lang
                user = User(id=tg.id, username=tg.username, full_name=name, language=lang)
                s.add(user)
                await s.flush()
                await self._referral(s, event, user)
            else:
                user.username, user.full_name = tg.username, name
                user.last_active_at = utcnow()
                user.is_active = True
            role = await role_of(s, tg.id)
            data.update(session=s, user=user, lang=user.language, is_new=is_new,
                        role=role, staff=role is not None)
            if user.is_banned and not role:
                await self._say(event, t(user.language, "banned"))
                await s.commit()
                return None
            try:
                result = await handler(event, data)
                await s.commit()
                return result
            except Exception:
                await s.rollback()
                raise

    @staticmethod
    async def _referral(s, event, user):
        """Soxta referalga qarshi: o'zini taklif qilib bo'lmaydi, faqat yangi foydalanuvchi, bir marta."""
        if not isinstance(event, Message) or not event.text:
            return
        m = REF_RE.match(event.text.strip())
        if not m:
            return
        ref_id = int(m.group(1))
        if ref_id == user.id:
            return
        referrer = await s.get(User, ref_id)
        if not referrer or referrer.is_banned:
            return
        user.referrer_id = ref_id
        s.add(Referral(referrer_id=ref_id, referred_id=user.id, confirmed=False))
        await s.flush()

    @staticmethod
    async def _say(event, text):
        if isinstance(event, Message):
            await event.answer(text)
        elif isinstance(event, CallbackQuery):
            await event.answer(text, show_alert=True)
