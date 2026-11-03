"""Majburiy obunani tekshirish (bot va Mini App uchun umumiy)."""
import logging
import time

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from database.queries import get_setting, list_channels

log = logging.getLogger(__name__)
_ok_cache: dict = {}  # user_id -> vaqt (muvaffaqiyatli tekshiruv keshi)
CACHE_TTL = 45


def forget(uid: int) -> None:
    _ok_cache.pop(uid, None)


async def missing_channels(bot: Bot, s, uid: int, use_cache: bool = True) -> list:
    if (await get_setting(s, "forced_sub", "1")) != "1":
        return []
    if use_cache and time.time() - _ok_cache.get(uid, 0) < CACHE_TTL:
        return []
    missing = []
    for ch in await list_channels(s, active_only=True):
        try:
            m = await bot.get_chat_member(ch.chat_id, uid)
            ok = m.status in ("member", "administrator", "creator") or (
                m.status == "restricted" and getattr(m, "is_member", False))
        except TelegramAPIError as e:  # bot kanalda admin emas / kanal o'chgan — foydalanuvchini bloklamaymiz
            log.warning("Kanal %s tekshirilmadi: %s", ch.chat_id, e)
            continue
        if not ok:
            missing.append(ch)
    if not missing:
        _ok_cache[uid] = time.time()
    return missing


def channel_url(ch):
    if ch.invite_link:
        return ch.invite_link
    if ch.username:
        return f"https://t.me/{ch.username.lstrip('@')}"
    return None
