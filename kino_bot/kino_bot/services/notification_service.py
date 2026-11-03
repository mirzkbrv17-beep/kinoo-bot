"""Adminlarga xabar va ommaviy reklama (Telegram limitlariga rioya bilan)."""
import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramRetryAfter
from sqlalchemy import select, update

from database.db import session_maker
from database.models import User
from database.queries import staff_ids

log = logging.getLogger(__name__)


async def notify_staff(bot: Bot, s, text: str, reply_markup=None) -> int:
    sent = 0
    for uid in await staff_ids(s):
        try:
            await bot.send_message(uid, text, reply_markup=reply_markup)
            sent += 1
        except TelegramAPIError as e:
            log.warning("Staff %s ga yuborilmadi: %s", uid, e)
    return sent


async def safe_send(bot: Bot, chat_id: int, text: str, **kw) -> bool:
    try:
        await bot.send_message(chat_id, text, **kw)
        return True
    except TelegramAPIError as e:
        log.info("send_message %s: %s", chat_id, e)
        return False


async def run_broadcast(bot: Bot, admin_chat: int, from_chat: int, message_id: int) -> None:
    """~20 xabar/soniya (Telegram limiti 30/s dan past). Xatolar qayd etiladi."""
    async with session_maker() as s:
        ids = (await s.execute(select(User.id).where(User.is_active.is_(True), User.is_banned.is_(False)))).scalars().all()
    ok = fail = blocked = 0
    dead = []
    for uid in ids:
        for attempt in range(3):
            try:
                await bot.copy_message(uid, from_chat, message_id)
                ok += 1
                break
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
            except TelegramForbiddenError:
                blocked += 1
                dead.append(uid)
                break
            except TelegramAPIError as e:
                log.warning("broadcast %s: %s", uid, e)
                fail += 1
                break
        await asyncio.sleep(0.05)
    if dead:
        async with session_maker() as s:
            await s.execute(update(User).where(User.id.in_(dead)).values(is_active=False))
            await s.commit()
    log.info("Broadcast: ok=%s blocked=%s fail=%s", ok, blocked, fail)
    await safe_send(bot, admin_chat, f"📣 <b>Reklama yakunlandi</b>\n\n✅ Yuborildi: {ok}\n🚫 Bloklagan: {blocked}\n⚠️ Xato: {fail}\n👥 Jami: {len(ids)}")
