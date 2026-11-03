"""Kino so'rash va admin bilan bog'lanish (adminlar javobi bilan)."""
from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton as B, InlineKeyboardMarkup as M, Message

from database.models import MovieRequest, SupportMessage, User
from services.notification_service import notify_staff, safe_send
from states.admin_states import ReplyForm
from states.user_states import UserForm
from utils.filters import NOT_CMD, NOT_MENU, menu
from utils.helpers import esc, utcnow
from utils.texts import t

router = Router()


def _who(user) -> str:
    uname = f" @{user.username}" if user.username else ""
    return f"<b>{esc(user.full_name)}</b>{uname} (<code>{user.id}</code>)"


# ---- foydalanuvchi: kino so'rash ----
@router.message(menu("request"))
async def req_start(message: Message, state: FSMContext, lang):
    await state.set_state(UserForm.request)
    await message.answer(t(lang, "req_prompt"))


@router.message(StateFilter(UserForm.request), F.text, NOT_MENU, NOT_CMD)
async def req_save(message: Message, bot: Bot, state: FSMContext, session, user, lang):
    req = MovieRequest(user_id=user.id, title=message.text.strip()[:250])
    session.add(req)
    await session.flush()
    await state.clear()
    await message.answer(t(lang, "req_sent"))
    kb = M(inline_keyboard=[[B(text="✅ Qabul", callback_data=f"rq:ok:{req.id}"), B(text="❌ Rad", callback_data=f"rq:no:{req.id}")]])
    await notify_staff(bot, session, f"✉️ <b>Kino so'rovi #{req.id}</b>\n{_who(user)}\n\n🎬 {esc(req.title)}", kb)


# ---- foydalanuvchi: adminga xabar ----
@router.message(menu("contact"))
async def contact_start(message: Message, state: FSMContext, lang):
    await state.set_state(UserForm.support)
    await message.answer(t(lang, "contact_prompt"))


@router.message(StateFilter(UserForm.support), F.text, NOT_MENU, NOT_CMD)
async def contact_save(message: Message, bot: Bot, state: FSMContext, session, user, lang):
    sm = SupportMessage(user_id=user.id, text=message.text.strip()[:3500])
    session.add(sm)
    await session.flush()
    await state.clear()
    await message.answer(t(lang, "contact_sent"))
    kb = M(inline_keyboard=[[B(text="💬 Javob berish", callback_data=f"sp:{sm.id}")]])
    await notify_staff(bot, session, f"💬 <b>Xabar #{sm.id}</b>\n{_who(user)}\n\n{esc(sm.text)}", kb)


# ---- admin: so'rovni qabul/rad ----
@router.callback_query(F.data.startswith("rq:"))
async def req_decide(cb, bot: Bot, session, role):
    if not role:
        return await cb.answer("⛔", show_alert=True)
    _, action, rid = cb.data.split(":")
    req = await session.get(MovieRequest, int(rid))
    if not req or req.status != "pending":
        return await cb.answer("Allaqachon ko'rib chiqilgan", show_alert=True)
    req.status = "accepted" if action == "ok" else "rejected"
    req.handled_by = cb.from_user.id
    u = await session.get(User, req.user_id)
    if u:
        await safe_send(bot, u.id, t(u.language, "req_ok" if action == "ok" else "req_no", title=esc(req.title)))
    await cb.answer("Bajarildi")
    await cb.message.edit_text(cb.message.html_text + f"\n\n{'✅ Qabul qilindi' if action == 'ok' else '❌ Rad etildi'} — {esc(cb.from_user.full_name)}")


# ---- admin: javob berish ----
@router.callback_query(F.data.startswith("sp:"))
async def reply_start(cb, state: FSMContext, role):
    if not role:
        return await cb.answer("⛔", show_alert=True)
    await state.set_state(ReplyForm.text)
    await state.update_data(sp_id=int(cb.data.split(":")[1]))
    await cb.answer()
    await cb.message.answer("✍️ Javob matnini yozing (/cancel — bekor qilish):")


@router.message(StateFilter(ReplyForm.text), F.text, NOT_CMD)
async def reply_send(message: Message, bot: Bot, state: FSMContext, session, role):
    if not role:
        return
    data = await state.get_data()
    sm = await session.get(SupportMessage, data["sp_id"])
    await state.clear()
    if not sm:
        return await message.answer("Topilmadi.")
    u = await session.get(User, sm.user_id)
    sm.admin_reply, sm.replied_by, sm.replied_at = message.text, message.from_user.id, utcnow()
    ok = await safe_send(bot, sm.user_id, t(u.language if u else "uz", "admin_reply", text=esc(message.text)))
    await message.answer("✅ Javob yuborildi." if ok else "⚠️ Foydalanuvchiga yuborib bo'lmadi (bot bloklangan bo'lishi mumkin).")
