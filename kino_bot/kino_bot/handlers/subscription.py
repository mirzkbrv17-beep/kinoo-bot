"""Majburiy obuna: foydalanuvchi tekshiruvi ("chk_sub") + admin kanal boshqaruvi."""
import logging
import re

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton as B, InlineKeyboardMarkup as M, Message

from database.models import MandatoryChannel
from database.queries import get_setting, list_channels, set_setting
from handlers.referrals import confirm_referral
from keyboards.admin import back_kb
from keyboards.inline import subscribe_kb
from middlewares.admin import AdminMiddleware
from services.menu_service import send_menu
from services.subscription_service import channel_url, forget, missing_channels
from states.admin_states import ChannelForm
from utils.helpers import esc
from utils.texts import t

log = logging.getLogger(__name__)
router = Router()          # foydalanuvchi
admin_router = Router()    # admin (kanal boshqaruvi)
admin_router.message.middleware(AdminMiddleware())
admin_router.callback_query.middleware(AdminMiddleware())


@router.callback_query(F.data == "chk_sub")
async def check_sub(cb, bot: Bot, session, user, lang):
    forget(user.id)
    missing = await missing_channels(bot, session, user.id, use_cache=False)
    if missing:
        await cb.answer(t(lang, "sub_not_yet"), show_alert=True)
        try:
            await cb.message.edit_reply_markup(reply_markup=subscribe_kb(missing, lang))
        except Exception:
            pass
        return
    await cb.answer(t(lang, "sub_ok"))
    try:
        await cb.message.delete()
    except Exception:
        pass
    await confirm_referral(bot, session, user)
    await send_menu(bot, cb.message.chat.id, lang, t(lang, "sub_ok") + "\n\n" + t(lang, "menu_hint"))


# ---------------- admin ----------------
async def channels_view(s):
    chans = await list_channels(s)
    on = (await get_setting(s, "forced_sub", "1")) == "1"
    lines = [f"📢 <b>Majburiy obuna</b>: {'✅ yoqilgan' if on else '⛔ o‘chirilgan'}", ""]
    rows = []
    if not chans:
        lines.append("Kanallar yo'q.")
    for c in chans:
        lines.append(f"{'🟢' if c.is_active else '⚪️'} {esc(c.title)} — <code>{c.chat_id}</code>")
        rows.append([B(text=f"{'⏸' if c.is_active else '▶️'} {c.title[:20]}", callback_data=f"ch:t:{c.id}"),
                     B(text="🗑 O'chirish", callback_data=f"ch:d:{c.id}")])
    rows.append([B(text="➕ Kanal qo'shish", callback_data="ch:add")])
    rows.append([B(text="⛔ Obunani o'chirish" if on else "✅ Obunani yoqish", callback_data="ch:f")])
    rows.append([B(text="⬅️ Admin menyu", callback_data="adm:menu")])
    return "\n".join(lines), M(inline_keyboard=rows)


@admin_router.callback_query(F.data == "adm:channels")
async def adm_channels(cb, session, state: FSMContext):
    await state.clear()
    text, kb = await channels_view(session)
    await cb.answer()
    await cb.message.edit_text(text, reply_markup=kb)


@admin_router.callback_query(F.data.startswith("ch:"))
async def ch_actions(cb, session, state: FSMContext):
    parts = cb.data.split(":")
    act = parts[1]
    if act == "add":
        await state.set_state(ChannelForm.add)
        await cb.answer()
        return await cb.message.answer(
            "➕ Kanalni qo'shish uchun:\n• <code>@kanal_username</code> yoki <code>-100...</code> ID yuboring\n• yoki kanaldan biror postni forward qiling\n\n"
            "⚠️ Bot kanalda <b>administrator</b> bo'lishi shart.", reply_markup=back_kb())
    if act == "f":
        cur = await get_setting(session, "forced_sub", "1")
        await set_setting(session, "forced_sub", "0" if cur == "1" else "1")
    elif act in ("t", "d"):
        ch = await session.get(MandatoryChannel, int(parts[2]))
        if ch:
            if act == "t":
                ch.is_active = not ch.is_active
            else:
                await session.delete(ch)
        await session.flush()
    await cb.answer()
    text, kb = await channels_view(session)
    await cb.message.edit_text(text, reply_markup=kb)


@admin_router.message(StateFilter(ChannelForm.add))
async def ch_add(message: Message, bot: Bot, state: FSMContext, session):
    chat_ref = None
    origin = getattr(message, "forward_origin", None)
    if origin is not None and getattr(origin, "chat", None) is not None:
        chat_ref = origin.chat.id
    elif message.text:
        txt = message.text.strip()
        if re.fullmatch(r"-?\d{5,}", txt):
            chat_ref = int(txt)
        elif re.fullmatch(r"@?[A-Za-z0-9_]{4,}", txt):
            chat_ref = "@" + txt.lstrip("@")
    if chat_ref is None:
        return await message.answer("❌ Format noto'g'ri. @username, -100… ID yoki forward yuboring.")
    try:
        chat = await bot.get_chat(chat_ref)
        me = await bot.me()
        member = await bot.get_chat_member(chat.id, me.id)
    except TelegramAPIError as e:
        return await message.answer(f"❌ Kanal topilmadi yoki bot kanalda yo'q: {esc(e)}")
    if member.status not in ("administrator", "creator"):
        return await message.answer("❌ Bot bu kanalda administrator emas. Avval botni admin qiling.")
    if chat.type not in ("channel", "supergroup", "group"):
        return await message.answer("❌ Bu kanal/guruh emas.")
    link = f"https://t.me/{chat.username}" if chat.username else None
    if not link:
        try:
            link = (await bot.create_chat_invite_link(chat.id, name="kino_bot")).invite_link
        except TelegramAPIError:
            link = getattr(chat, "invite_link", None)
    if not link:
        return await message.answer("❌ Taklif havolasi olinmadi: botga «Taklif havolalari» huquqini bering.")
    existing = [c for c in await list_channels(session) if c.chat_id == chat.id]
    if existing:
        existing[0].title, existing[0].username, existing[0].invite_link, existing[0].is_active = chat.title, chat.username, link, True
    else:
        session.add(MandatoryChannel(chat_id=chat.id, title=chat.title or "", username=chat.username, invite_link=link))
    await state.clear()
    await session.flush()
    text, kb = await channels_view(session)
    await message.answer("✅ Kanal qo'shildi.\n\n" + text, reply_markup=kb)
