from datetime import timedelta

from aiogram import Bot, Router
from sqlalchemy import func, select

from database.models import Referral, User
from database.queries import get_setting, grant_vip, referral_stats
from services.notification_service import safe_send
from utils.filters import menu
from utils.helpers import utcnow
from utils.texts import t

router = Router()


async def confirm_referral(bot: Bot, s, user) -> None:
    """Taklif qilingan foydalanuvchi obunadan o'tgach (asosiy menyuga kirgach) tasdiqlanadi."""
    ref = (await s.execute(select(Referral).where(
        Referral.referred_id == user.id, Referral.confirmed.is_(False)))).scalars().first()
    if not ref:
        return
    day = utcnow() - timedelta(days=1)
    today = (await s.execute(select(func.count()).select_from(Referral).where(
        Referral.referrer_id == ref.referrer_id, Referral.confirmed.is_(True), Referral.created_at >= day))).scalar_one()
    if today >= int(await get_setting(s, "ref_daily_limit", "30")):
        return
    ref.confirmed = True
    await s.flush()
    referrer = await s.get(User, ref.referrer_id)
    if not referrer:
        return
    rl = referrer.language
    await safe_send(bot, referrer.id, t(rl, "ref_joined"))
    every, days = int(await get_setting(s, "ref_every", "5")), int(await get_setting(s, "ref_days", "3"))
    ok, _ = await referral_stats(s, referrer.id)
    if every > 0 and days > 0 and ok % every == 0:
        await grant_vip(s, referrer.id, days, "referral")
        await safe_send(bot, referrer.id, t(rl, "ref_reward", days=days))


@router.message(menu("invite"))
async def invite(message, bot, session, user, lang, state):
    await state.clear()
    me = await bot.me()
    ok, wait = await referral_stats(session, user.id)
    await message.answer(t(lang, "invite_text", link=f"https://t.me/{me.username}?start=ref_{user.id}", ok=ok, wait=wait,
                           every=await get_setting(session, "ref_every", "5"), days=await get_setting(session, "ref_days", "3")),
                         disable_web_page_preview=True)
