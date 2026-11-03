"""Sozlamalar: foydalanuvchi sozlamalari + admin: premium emoji, bot sozlamalari."""
import logging

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton as B, InlineKeyboardMarkup as M, Message

from database.queries import all_genres, get_setting, redeem_promo, set_setting
from handlers.movies import show
from handlers.vip import status_text
from keyboards.admin import back_kb
from keyboards.inline import lang_kb, pref_genres_kb, settings_kb
from middlewares.admin import AdminMiddleware
from services.emoji_service import emoji_service
from services.menu_service import send_menu
from states.admin_states import EmojiForm, SettingForm
from states.user_states import UserForm
from utils.filters import NOT_CMD, NOT_MENU, menu
from utils.helpers import chunk, esc
from utils.texts import MENU, menu_label, t

log = logging.getLogger(__name__)
router = Router()
admin_router = Router()
admin_router.message.middleware(AdminMiddleware())
admin_router.callback_query.middleware(AdminMiddleware())


# ================= foydalanuvchi sozlamalari =================
@router.message(menu("settings"))
async def settings_menu(message: Message, state: FSMContext, lang, staff):
    await state.clear()
    await message.answer(t(lang, "settings_title"), reply_markup=settings_kb(lang, staff))


@router.callback_query(F.data.startswith("us:"))
async def user_settings(cb, session, user, lang, state: FSMContext):
    act = cb.data.split(":")[1]
    await cb.answer()
    if act == "lang":
        await cb.message.answer(t(lang, "choose_lang"), reply_markup=lang_kb())
    elif act == "genres":
        sel = {int(x) for x in user.pref_genres.split(",") if x.isdigit()}
        await cb.message.answer(t(lang, "genres_pick"), reply_markup=pref_genres_kb(await all_genres(session), sel, lang))
    elif act == "promo":
        await state.set_state(UserForm.promo)
        await cb.message.answer(t(lang, "promo_prompt"))
    elif act == "vip":
        await cb.message.answer(await status_text(session, user.id, lang))


@router.callback_query(F.data.startswith("pg:"))
async def toggle_pref(cb, session, user, lang):
    gid = int(cb.data.split(":")[1])
    sel = {int(x) for x in user.pref_genres.split(",") if x.isdigit()}
    sel ^= {gid}
    user.pref_genres = ",".join(str(x) for x in sorted(sel))
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=pref_genres_kb(await all_genres(session), sel, lang))


@router.message(StateFilter(UserForm.promo), F.text, NOT_MENU, NOT_CMD)
async def promo_use(message: Message, state: FSMContext, session, user, lang):
    days, err = await redeem_promo(session, user.id, message.text)
    await state.clear()
    await message.answer(t(lang, "promo_ok", days=days) if days else t(lang, "promo_bad"))


# ================= admin: premium emoji =================
async def emoji_view(lang="uz"):
    rows = []
    for pair in chunk(MENU, 2):
        rows.append([B(text=f"{'✅' if emoji_service.ids.get(k) else '➖'} {fb} {menu_label('uz', k)}"[:40], callback_data=f"em:{k}") for k, fb in pair])
    rows.append([B(text="🧪 Menyuni sinash", callback_data="em:test"), B(text="🔄 Ikonkalarni yoqish" if emoji_service.disabled else "♻️ Hammasini tozalash",
                                                                   callback_data="em:enable" if emoji_service.disabled else "em:clear")])
    rows.append([B(text="⬅️ Admin menyu", callback_data="adm:menu")])
    status = "⛔ Telegram rad etdi — oddiy emoji fallback ishlayapti" if emoji_service.disabled else (
        "✅ Premium ikonkalar yoqilgan" if emoji_service.ids else "ℹ️ ID kiritilmagan — oddiy emoji ishlatiladi")
    text = ("😀 <b>Premium emoji sozlamalari</b>\n\n" + status +
            "\n\nTugmani tanlang, so'ng <b>premium emoji</b> yuboring (ID avtomatik olinadi) yoki ID raqamini yozing. "
            "ID o'chirish uchun <code>0</code> yuboring.")
    return text, M(inline_keyboard=rows)


@admin_router.callback_query(F.data == "adm:emoji")
async def adm_emoji(cb, state: FSMContext):
    await state.clear()
    text, kb = await emoji_view()
    await cb.answer()
    await cb.message.edit_text(text, reply_markup=kb)


@admin_router.callback_query(F.data.startswith("em:"))
async def em_actions(cb, bot: Bot, session, state: FSMContext, lang):
    act = cb.data.split(":")[1]
    if act == "test":
        await cb.answer()
        return await send_menu(bot, cb.message.chat.id, lang, "🧪 Test menyu")
    if act == "enable":
        emoji_service.disabled = False
    elif act == "clear":
        for k, _ in MENU:
            await emoji_service.set_id(session, k, None)
    else:
        await state.set_state(EmojiForm.wait)
        await state.update_data(key=act)
        await cb.answer()
        return await cb.message.answer(f"«{menu_label('uz', act)}» uchun premium emoji yuboring (yoki ID raqam). Bekor: /cancel")
    await cb.answer()
    text, kb = await emoji_view()
    await cb.message.edit_text(text, reply_markup=kb)


@admin_router.message(StateFilter(EmojiForm.wait))
async def em_receive(message: Message, state: FSMContext, session):
    data = await state.get_data()
    key = data["key"]
    emoji_id = None
    for ent in (message.entities or []):
        if ent.type == "custom_emoji":
            emoji_id = ent.custom_emoji_id
            break
    if emoji_id is None and message.text:
        txt = message.text.strip()
        if txt == "0":
            await emoji_service.set_id(session, key, None)
            await state.clear()
            text, kb = await emoji_view()
            return await message.answer("🗑 ID o'chirildi.\n\n" + text, reply_markup=kb)
        if txt.isdigit() and 10 <= len(txt) <= 30:
            emoji_id = txt
    if not emoji_id:
        return await message.answer("❌ Premium emoji yoki raqamli ID yuboring.")
    await emoji_service.set_id(session, key, emoji_id)
    emoji_service.disabled = False
    await state.clear()
    text, kb = await emoji_view()
    await message.answer(f"✅ Saqlandi: <code>{emoji_id}</code>\n\n" + text, reply_markup=kb)


# ================= admin: bot sozlamalari =================
SETTING_INFO = {
    "protect_content": ("🔒 Kontentni saqlash/ulashishdan himoya", "toggle"),
    "vip_plans": ("💳 VIP tariflar (kun:Stars,...)", "text"),
    "ref_every": ("👥 Har nechta referal uchun mukofot", "text"),
    "ref_days": ("🎁 Mukofot VIP kunlari", "text"),
    "ref_daily_limit": ("🛑 Kunlik referal limiti", "text"),
    "news_text": ("📰 Yangiliklar matni", "text"),
    "news_url": ("📢 Yangiliklar kanali havolasi", "text"),
}


async def botset_view(s):
    rows, lines = [], ["🤖 <b>Bot sozlamalari</b>", ""]
    for key, (title, kind) in SETTING_INFO.items():
        val = await get_setting(s, key, "")
        shown = ("✅" if val == "1" else "⛔") if kind == "toggle" else (esc(val[:40]) or "—")
        lines.append(f"{title}: <b>{shown}</b>")
        rows.append([B(text=title[:38], callback_data=f"bs:{key}")])
    rows.append([B(text="⬅️ Admin menyu", callback_data="adm:menu")])
    return "\n".join(lines), M(inline_keyboard=rows)


@admin_router.callback_query(F.data == "adm:botset")
async def adm_botset(cb, session, state: FSMContext):
    await state.clear()
    text, kb = await botset_view(session)
    await cb.answer()
    await cb.message.edit_text(text, reply_markup=kb)


@admin_router.callback_query(F.data.startswith("bs:"))
async def bs_pick(cb, session, state: FSMContext):
    key = cb.data.split(":")[1]
    if key not in SETTING_INFO:
        return await cb.answer()
    if SETTING_INFO[key][1] == "toggle":
        cur = await get_setting(session, key, "0")
        await set_setting(session, key, "0" if cur == "1" else "1")
        text, kb = await botset_view(session)
        await cb.answer()
        return await cb.message.edit_text(text, reply_markup=kb)
    await state.set_state(SettingForm.value)
    await state.update_data(key=key)
    await cb.answer()
    cur = await get_setting(session, key, "")
    await cb.message.answer(f"{SETTING_INFO[key][0]}\nHozirgi: <code>{esc(cur) or '—'}</code>\n\nYangi qiymatni yuboring (tozalash uchun <code>-</code>):")


@admin_router.message(StateFilter(SettingForm.value), F.text, NOT_CMD)
async def bs_save(message: Message, state: FSMContext, session):
    key = (await state.get_data())["key"]
    val = "" if message.text.strip() == "-" else message.text.strip()
    if key in ("ref_every", "ref_days", "ref_daily_limit") and not val.isdigit():
        return await message.answer("❌ Raqam yuboring.")
    if key == "vip_plans":
        from handlers.vip import parse_plans
        if val and not parse_plans(val):
            return await message.answer("❌ Format: <code>30:100,90:250</code>")
    await set_setting(session, key, val)
    await state.clear()
    text, kb = await botset_view(session)
    await message.answer("✅ Saqlandi.\n\n" + text, reply_markup=kb)
