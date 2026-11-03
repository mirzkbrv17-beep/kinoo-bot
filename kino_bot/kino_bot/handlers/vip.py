"""VIP: katalog, holat, Telegram Stars (XTR) orqali to'lov."""
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import LabeledPrice, Message, PreCheckoutQuery

from database.queries import get_setting, grant_vip, vip_until
from handlers.movies import build_list
from keyboards.inline import vip_plans_kb
from services.notification_service import notify_staff
from utils.filters import menu
from utils.helpers import esc, fmt_date, utcnow
from utils.texts import t

log = logging.getLogger(__name__)
router = Router()


def parse_plans(raw: str) -> list:
    plans = []
    for part in (raw or "").split(","):
        if ":" in part:
            d, st = part.split(":", 1)
            if d.strip().isdigit() and st.strip().isdigit() and int(d) > 0 and int(st) > 0:
                plans.append((int(d), int(st)))
    return plans


async def status_text(s, uid: int, lang: str) -> str:
    until = await vip_until(s, uid)
    if until:
        return t(lang, "vip_on", date=fmt_date(until), days=max(0, (until - utcnow()).days))
    return t(lang, "vip_off")


async def _vip_home(message: Message, session, user, lang, staff):
    text, kb = await build_list(session, user.id, lang, "v", 0, 0, staff)
    await message.answer(await status_text(session, user.id, lang) + "\n\n" + text, reply_markup=kb)


@router.message(menu("vip"))
async def menu_vip(message: Message, session, user, lang, staff, state: FSMContext):
    await state.clear()
    await _vip_home(message, session, user, lang, staff)


@router.message(Command("vip"))
async def cmd_vip(message: Message, session, user, lang, staff):
    await _vip_home(message, session, user, lang, staff)


@router.callback_query(F.data == "vip:plans")
async def cb_plans(cb, session, lang):
    plans = parse_plans(await get_setting(session, "vip_plans", ""))
    await cb.answer()
    if not plans:
        return await cb.message.answer(t(lang, "vip_no_plans"))
    await cb.message.answer(t(lang, "vip_title"), reply_markup=vip_plans_kb(plans, lang))


@router.callback_query(F.data.startswith("vip:buy:"))
async def cb_buy(cb, bot: Bot, session, lang):
    days = int(cb.data.split(":")[2])
    plans = dict(parse_plans(await get_setting(session, "vip_plans", "")))
    if days not in plans:
        return await cb.answer(t(lang, "error"), show_alert=True)
    await cb.answer()
    await bot.send_invoice(
        cb.message.chat.id, title=f"VIP — {days}", description=f"VIP obuna: {days} kun",
        payload=f"vip:{days}", currency="XTR", provider_token="",
        prices=[LabeledPrice(label=f"VIP {days}", amount=plans[days])])


@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await q.answer(ok=q.invoice_payload.startswith("vip:"), error_message="Noto'g'ri to'lov")


@router.message(F.successful_payment)
async def paid(message: Message, bot: Bot, session, user, lang):
    pay = message.successful_payment
    try:
        days = int(pay.invoice_payload.split(":")[1])
    except (IndexError, ValueError):
        return
    plans = dict(parse_plans(await get_setting(session, "vip_plans", "")))
    if plans.get(days) != pay.total_amount:
        log.error("To'lov summasi mos emas: %s %s", pay.invoice_payload, pay.total_amount)
        await notify_staff(bot, session, f"⚠️ Mos kelmaydigan to'lov: user {user.id}, {pay.invoice_payload}, {pay.total_amount} XTR, charge <code>{esc(pay.telegram_payment_charge_id)}</code>")
        return
    exp = await grant_vip(session, user.id, days, "stars")
    log.info("Stars to'lov: user=%s days=%s charge=%s", user.id, days, pay.telegram_payment_charge_id)
    await message.answer(t(lang, "vip_thanks", date=fmt_date(exp)))
    await notify_staff(bot, session, f"💰 Yangi VIP: <b>{esc(user.full_name)}</b> (<code>{user.id}</code>) — {days} kun, {pay.total_amount} ⭐")
