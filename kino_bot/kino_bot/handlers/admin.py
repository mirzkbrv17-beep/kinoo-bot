"""Admin paneli: kontent qo'shish (FSM), tahrirlash, o'chirish, janr, foydalanuvchi, VIP, reklama, promo, xodimlar."""
import asyncio
import logging
import re
from datetime import timedelta

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton as B, InlineKeyboardMarkup as M, Message
from sqlalchemy import select

from database.models import Admin, Episode, Genre, Movie, PromoCode, Season, Series, User
from database.queries import (all_genres, code_taken, expire_vips, find_by_code, grant_vip, next_code, role_of,
                              set_vip_days, vip_list)
from keyboards.admin import (admin_menu, back_kb, cancel_kb, confirm_kb, edit_kb, genre_pick_kb, series_menu_kb,
                             step_kb, user_card_kb)
from middlewares.admin import AdminMiddleware
from services.backup_service import send_backup
from services.notification_service import run_broadcast, safe_send
from services.statistics_service import admin_stats_text
from states.admin_states import (BroadcastForm, ContentForm, DelForm, EditForm, GenreForm, PromoForm, StaffForm,
                                 UserMgmt)
from utils.filters import NOT_CMD
from utils.helpers import esc, fmt_dt, norm_code, search_key, utcnow
from utils.validators import (is_url, parse_duration, parse_imdb, parse_year, valid_code)

log = logging.getLogger(__name__)
router = Router()
router.message.middleware(AdminMiddleware())
router.callback_query.middleware(AdminMiddleware())
_tasks: set = set()

# ======================= umumiy =======================
async def edit(cb, text, kb=None):
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        await cb.message.answer(text, reply_markup=kb)


async def open_menu(target, role, edit_msg=False):
    text = "🛠 <b>Admin panel</b>\n\nKerakli bo'limni tanlang:"
    if edit_msg:
        await edit(target, text, admin_menu(role))
    else:
        await target.answer(text, reply_markup=admin_menu(role))


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext, role):
    await state.clear()
    await open_menu(message, role)


@router.callback_query(F.data == "adm:menu")
async def cb_menu(cb, state: FSMContext, role):
    await state.clear()
    await cb.answer()
    await open_menu(cb, role, edit_msg=True)


@router.callback_query(F.data == "adm:close")
async def cb_close(cb, state: FSMContext):
    await state.clear()
    await cb.answer()
    try:
        await cb.message.delete()
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "af:cancel", StateFilter("*"))
async def cb_cancel(cb, state: FSMContext, role):
    await state.clear()
    await cb.answer("Bekor qilindi")
    await open_menu(cb, role, edit_msg=True)


@router.callback_query(F.data == "adm:stats")
async def cb_stats(cb, session):
    await cb.answer()
    await edit(cb, await admin_stats_text(session), back_kb())


@router.callback_query(F.data == "adm:backup")
async def cb_backup(cb, bot: Bot):
    await cb.answer("Tayyorlanmoqda…")
    await send_backup(bot, [cb.from_user.id])


# ======================= kontent qo'shish (FSM) =======================
PROMPTS = {
    "title": "🎬 Nomini yuboring:",
    "media": "📹 Video (yoki fayl) yuboring, yoki tomosha havolasini (https://…) yozing:",
    "poster": "🖼 Poster (rasm) yuboring:",
    "code": "🔑 Kodni yozing (harf/raqam/-/_). O'tkazib yuborsangiz avtomatik beriladi:",
    "original_title": "🔤 Original nomi:",
    "year": "📅 Chiqqan yili (masalan 2023):",
    "country": "🌍 Davlati:",
    "genre": "🎭 Janrni tanlang:",
    "duration": "⏱ Davomiyligi (daqiqa: 105 yoki 1:45):",
    "age_limit": "🔞 Yosh cheklovi (masalan 16+):",
    "imdb": "⭐ IMDb reytingi (0–10):",
    "description": "📝 Tavsif:",
    "trailer_url": "🎞 Treyler havolasi (https://…):",
    "is_vip": "👑 Bu VIP kontentmi?",
    "series_code": "🔑 Serial kodini yuboring:",
    "season_no": "📋 Fasl raqami:",
    "ep_no": "▶️ Qism raqami:",
}
MOVIE_STEPS = ["title", "media", "poster", "code", "original_title", "year", "country", "genre", "duration",
               "age_limit", "imdb", "description", "trailer_url"]
FLOWS = {
    "movie": dict(steps=MOVIE_STEPS + ["is_vip"], required={"title", "media"}, preset={"kind": "movie"}),
    "vip": dict(steps=MOVIE_STEPS, required={"title", "media"}, preset={"kind": "movie", "is_vip": True}),
    "cartoon": dict(steps=MOVIE_STEPS + ["is_vip"], required={"title", "media"}, preset={"kind": "cartoon"}),
    "series": dict(steps=["title", "poster", "code", "original_title", "year", "country", "genre", "description",
                          "trailer_url", "is_vip"], required={"title"}, preset={}),
    "season": dict(steps=["series_code", "season_no"], required={"series_code", "season_no"}, preset={}),
    "episode": dict(steps=["series_code", "season_no", "ep_no", "media", "code"],
                    required={"series_code", "season_no", "ep_no", "media"}, preset={}),
}
ENTRY = {"add_movie": "movie", "add_vip": "vip", "add_cartoon": "cartoon", "add_series": "series",
         "add_season": "season", "add_episode": "episode"}
TEXT_LIMITS = {"title": 250, "original_title": 250, "country": 120, "age_limit": 15, "description": 3500}


async def parse_value(field: str, message: Message, s):
    """(yangilanishlar dict, xato matni) qaytaradi."""
    txt = (message.text or "").strip()
    if field in TEXT_LIMITS:
        return ({field: txt[:TEXT_LIMITS[field]]}, None) if txt else (None, "❌ Matn yuboring.")
    if field == "poster":
        if message.photo:
            return {"poster_file_id": message.photo[-1].file_id}, None
        return None, "❌ Rasm (foto) yuboring."
    if field == "media":
        if message.video:
            return {"video_file_id": message.video.file_id, "video_type": "video"}, None
        if message.document:
            return {"video_file_id": message.document.file_id, "video_type": "document"}, None
        if is_url(txt):
            return {"watch_url": txt}, None
        return None, "❌ Video, fayl yoki https:// havola yuboring."
    if field == "code":
        if not valid_code(txt):
            return None, "❌ Kod faqat harf, raqam, - va _ dan iborat bo'lsin (1–24 belgi)."
        if await code_taken(s, txt):
            return None, "❌ Bu kod band. Boshqasini yozing."
        return {"code": norm_code(txt)}, None
    if field == "year":
        y = parse_year(txt)
        return ({"year": y}, None) if y else (None, "❌ Yil 1888–2100 oralig'ida bo'lsin.")
    if field == "duration":
        d = parse_duration(txt)
        return ({"duration": d}, None) if d else (None, "❌ Masalan: 105 yoki 1:45")
    if field == "imdb":
        v = parse_imdb(txt)
        return ({"imdb": v}, None) if v is not None else (None, "❌ 0 dan 10 gacha son yuboring.")
    if field == "trailer_url":
        return ({"trailer_url": txt}, None) if is_url(txt) else (None, "❌ To'g'ri https:// havola yuboring.")
    if field == "series_code":
        sr = (await s.execute(select(Series).where(Series.code == norm_code(txt)))).scalars().first()
        return ({"series_id": sr.id, "series_title": sr.title}, None) if sr else (None, "❌ Bunday serial topilmadi.")
    if field in ("season_no", "ep_no"):
        return ({field: int(txt)}, None) if txt.isdigit() and 0 < int(txt) < 1000 else (None, "❌ Musbat butun son yuboring.")
    return None, "❌ Tugmalardan foydalaning."


async def start_flow(cb, state: FSMContext, session, flow: str):
    cfg = FLOWS[flow]
    await state.set_state(ContentForm.fill)
    await state.update_data(flow=flow, i=0, fields=dict(cfg["preset"]), admin_id=cb.from_user.id)
    await cb.answer()
    await ask(cb.message, state, session)


async def ask(target: Message, state: FSMContext, session):
    d = await state.get_data()
    cfg = FLOWS[d["flow"]]
    steps, i = cfg["steps"], d["i"]
    if i >= len(steps):
        return await finish(target, state, session)
    f = steps[i]
    req = f in cfg["required"]
    genres = await all_genres(session) if f == "genre" else None
    await target.answer(f"<b>{i + 1}/{len(steps)}</b> · {PROMPTS[f]}  <i>({'majburiy' if req else 'ixtiyoriy'})</i>",
                        reply_markup=step_kb(f, req, genres))


async def _advance(target, state, session, updates=None):
    d = await state.get_data()
    fields = d["fields"]
    if updates:
        fields.update(updates)
    await state.update_data(fields=fields, i=d["i"] + 1)
    await ask(target, state, session)


@router.callback_query(F.data.startswith("adm:"), F.data.func(lambda x: x.split(":")[1] in ENTRY))
async def cb_add(cb, state: FSMContext, session):
    await start_flow(cb, state, session, ENTRY[cb.data.split(":")[1]])


@router.callback_query(F.data == "adm:series")
async def cb_series_menu(cb):
    await cb.answer()
    await edit(cb, "📺 <b>Serial bo'limi</b>", series_menu_kb())


@router.message(StateFilter(ContentForm.fill))
async def flow_message(message: Message, state: FSMContext, session):
    d = await state.get_data()
    field = FLOWS[d["flow"]]["steps"][d["i"]]
    updates, err = await parse_value(field, message, session)
    if err:
        return await message.answer(err)
    await _advance(message, state, session, updates)


@router.callback_query(F.data == "af:skip", StateFilter(ContentForm.fill))
async def flow_skip(cb, state: FSMContext, session):
    d = await state.get_data()
    cfg = FLOWS[d["flow"]]
    if cfg["steps"][d["i"]] in cfg["required"]:
        return await cb.answer("Bu maydon majburiy", show_alert=True)
    await cb.answer()
    await _advance(cb.message, state, session)


@router.callback_query(F.data.startswith("af:g:"), StateFilter(ContentForm.fill))
async def flow_genre(cb, state: FSMContext, session):
    d = await state.get_data()
    if FLOWS[d["flow"]]["steps"][d["i"]] != "genre":
        return await cb.answer()
    await cb.answer()
    await _advance(cb.message, state, session, {"genre_id": int(cb.data.split(":")[2])})


@router.callback_query(F.data.startswith("af:v:"), StateFilter(ContentForm.fill))
async def flow_vip(cb, state: FSMContext, session):
    d = await state.get_data()
    if FLOWS[d["flow"]]["steps"][d["i"]] != "is_vip":
        return await cb.answer()
    await cb.answer()
    await _advance(cb.message, state, session, {"is_vip": cb.data.endswith("1")})


def _link_kb(rows):
    return M(inline_keyboard=rows + [[B(text="⬅️ Admin menyu", callback_data="adm:menu")]])


async def finish(target: Message, state: FSMContext, session):
    d = await state.get_data()
    flow, f, admin_id = d["flow"], d["fields"], d.get("admin_id")
    await state.clear()
    try:
        if flow in ("movie", "vip", "cartoon"):
            if not f.get("title") or not (f.get("video_file_id") or f.get("watch_url")):
                return await target.answer("❌ Nom va video/havola majburiy. Qaytadan boshlang.", reply_markup=back_kb())
            code = f.get("code") or await next_code(session)
            m = Movie(code=code, kind=f.get("kind", "movie"), title=f["title"], original_title=f.get("original_title"),
                      search_key=search_key(f["title"], f.get("original_title")), poster_file_id=f.get("poster_file_id"),
                      year=f.get("year"), country=f.get("country"), genre_id=f.get("genre_id"), duration=f.get("duration"),
                      age_limit=f.get("age_limit"), imdb=f.get("imdb"), description=f.get("description"),
                      video_file_id=f.get("video_file_id"), video_type=f.get("video_type", "video"),
                      watch_url=f.get("watch_url"), trailer_url=f.get("trailer_url"), is_vip=bool(f.get("is_vip")),
                      added_by=admin_id)
            session.add(m)
            await session.flush()
            return await target.answer(f"✅ Qo'shildi: <b>{esc(m.title)}</b>\n🔑 Kod: <code>{m.code}</code>",
                                       reply_markup=_link_kb([[B(text="▶️ Ko'rish", callback_data=f"mv:{m.id}")],
                                                              [B(text="➕ Yana qo'shish", callback_data=f"adm:add_{'vip' if f.get('is_vip') else ('cartoon' if m.kind == 'cartoon' else 'movie')}")]]))
        if flow == "series":
            if not f.get("title"):
                return await target.answer("❌ Nom majburiy.", reply_markup=back_kb())
            code = f.get("code") or await next_code(session)
            sr = Series(code=code, title=f["title"], original_title=f.get("original_title"),
                        search_key=search_key(f["title"], f.get("original_title")), poster_file_id=f.get("poster_file_id"),
                        year=f.get("year"), country=f.get("country"), genre_id=f.get("genre_id"),
                        description=f.get("description"), trailer_url=f.get("trailer_url"), is_vip=bool(f.get("is_vip")))
            session.add(sr)
            await session.flush()
            return await target.answer(f"✅ Serial yaratildi: <b>{esc(sr.title)}</b>\n🔑 Kod: <code>{sr.code}</code>\n\nEndi fasl va qismlarni qo'shing.",
                                       reply_markup=series_menu_kb())
        season = (await session.execute(select(Season).where(Season.series_id == f["series_id"], Season.number == f["season_no"]))).scalars().first()
        if flow == "season":
            if season:
                return await target.answer("ℹ️ Bu fasl allaqachon mavjud.", reply_markup=series_menu_kb())
            session.add(Season(series_id=f["series_id"], number=f["season_no"]))
            await session.flush()
            return await target.answer(f"✅ {f['season_no']}-fasl qo'shildi ({esc(f['series_title'])}).", reply_markup=series_menu_kb())
        # episode
        if not season:
            season = Season(series_id=f["series_id"], number=f["season_no"])
            session.add(season)
            await session.flush()
        if (await session.execute(select(Episode.id).where(Episode.season_id == season.id, Episode.number == f["ep_no"]))).first():
            return await target.answer("❌ Bu qism raqami allaqachon mavjud.", reply_markup=series_menu_kb())
        code = f.get("code") or await next_code(session)
        ep = Episode(series_id=f["series_id"], season_id=season.id, number=f["ep_no"], code=code,
                     video_file_id=f.get("video_file_id"), video_type=f.get("video_type", "video"), watch_url=f.get("watch_url"))
        session.add(ep)
        await session.flush()
        await target.answer(f"✅ Qism qo'shildi: {esc(f['series_title'])} · {f['season_no']}-fasl {f['ep_no']}-qism\n🔑 Kod: <code>{ep.code}</code>",
                            reply_markup=series_menu_kb())
    except Exception:
        log.exception("finish xato")
        await session.rollback()
        await target.answer("⚠️ Saqlashda xatolik. Loglarni tekshiring.", reply_markup=back_kb())


# ======================= tahrirlash =======================
def yn(v) -> str:
    return "ha" if v else "yo'q"


def card_text(m: Movie) -> str:
    media = "video" if m.video_file_id else ("havola" if m.watch_url else "yo'q")
    return (f"✏️ <b>{esc(m.title)}</b> ({m.year or '—'})\n🔑 <code>{m.code}</code> · {m.kind}\n"
            f"👑 VIP: {yn(m.is_vip)} · 👁 {m.views} · faol: {yn(m.is_active)}\n"
            f"⭐ {m.imdb or '—'} · ⏱ {m.duration or '—'} · media: {media}\n\nQaysi maydonni o'zgartiramiz?")


@router.callback_query(F.data == "adm:edit")
async def edit_start(cb, state: FSMContext):
    await state.set_state(EditForm.code)
    await cb.answer()
    await cb.message.answer("✏️ Tahrirlanadigan kino kodini yuboring:", reply_markup=cancel_kb())


@router.message(StateFilter(EditForm.code), F.text, NOT_CMD)
async def edit_find(message: Message, state: FSMContext, session):
    m = (await session.execute(select(Movie).where(Movie.code == norm_code(message.text)))).scalars().first()
    if not m:
        return await message.answer("❌ Bunday kodli kino topilmadi. Qayta yuboring:", reply_markup=cancel_kb())
    await state.set_state(EditForm.value)
    await state.update_data(movie_id=m.id, field=None)
    await message.answer(card_text(m), reply_markup=edit_kb(m.id, m))


@router.callback_query(F.data.startswith("ed:"), StateFilter(EditForm.value))
async def edit_field(cb, state: FSMContext, session):
    d = await state.get_data()
    m = await session.get(Movie, d["movie_id"])
    if not m:
        return await cb.answer("Topilmadi", show_alert=True)
    f = cb.data.split(":")[1]
    if f in ("t_vip", "t_active"):
        if f == "t_vip":
            m.is_vip = not m.is_vip
        else:
            m.is_active = not m.is_active
        await cb.answer("✅")
        return await edit(cb, card_text(m), edit_kb(m.id, m))
    if f == "genre":
        await cb.answer()
        return await cb.message.answer("🎭 Yangi janr:", reply_markup=genre_pick_kb(await all_genres(session), "eg"))
    await state.update_data(field=f)
    await cb.answer()
    await cb.message.answer(PROMPTS.get(f, "Yangi qiymat:") if f != "poster" else PROMPTS["poster"], reply_markup=cancel_kb())


@router.callback_query(F.data.startswith("eg:"), StateFilter(EditForm.value))
async def edit_genre(cb, state: FSMContext, session):
    m = await session.get(Movie, (await state.get_data())["movie_id"])
    m.genre_id = int(cb.data.split(":")[1])
    await cb.answer("✅ Janr o'zgardi")
    await cb.message.answer(card_text(m), reply_markup=edit_kb(m.id, m))


@router.message(StateFilter(EditForm.value))
async def edit_value(message: Message, state: FSMContext, session):
    d = await state.get_data()
    field = d.get("field")
    if not field:
        return await message.answer("Avval yuqoridagi tugmalardan maydonni tanlang.")
    updates, err = await parse_value(field, message, session)
    if err:
        return await message.answer(err)
    m = await session.get(Movie, d["movie_id"])
    for k, v in updates.items():
        setattr(m, k, v)
    if "watch_url" in updates:
        m.video_file_id = None
    if "video_file_id" in updates:
        m.watch_url = None
    m.search_key = search_key(m.title, m.original_title)
    await state.update_data(field=None)
    await message.answer("✅ Yangilandi.\n\n" + card_text(m), reply_markup=edit_kb(m.id, m))


# ======================= o'chirish =======================
@router.callback_query(F.data == "adm:del")
async def del_start(cb, state: FSMContext):
    await state.set_state(DelForm.code)
    await cb.answer()
    await cb.message.answer("🗑 O'chiriladigan kino / serial / qism kodini yuboring:", reply_markup=cancel_kb())


@router.message(StateFilter(DelForm.code), F.text, NOT_CMD)
async def del_find(message: Message, state: FSMContext, session):
    code = norm_code(message.text)
    obj = None
    for kind, model in (("movie", Movie), ("series", Series), ("episode", Episode)):
        row = (await session.execute(select(model).where(model.code == code))).scalars().first()
        if row:
            obj = (kind, row)
            break
    if not obj:
        return await message.answer("❌ Bunday kod topilmadi.", reply_markup=cancel_kb())
    kind, row = obj
    await state.update_data(kind=kind, oid=row.id)
    await message.answer(f"⚠️ <b>{kind}</b> o'chiriladi: <b>{esc(getattr(row, 'title', code))}</b> (kod <code>{code}</code>).\nBog'liq ma'lumotlar ham o'chadi. Davom etamizmi?",
                         reply_markup=confirm_kb("dl:yes"))


@router.callback_query(F.data == "dl:yes", StateFilter(DelForm.code))
async def del_confirm(cb, state: FSMContext, session, role):
    d = await state.get_data()
    model = {"movie": Movie, "series": Series, "episode": Episode}.get(d.get("kind"))
    row = await session.get(model, d["oid"]) if model else None
    if row:
        await session.delete(row)
        await session.flush()
    await state.clear()
    await cb.answer("O'chirildi")
    await edit(cb, "✅ O'chirildi.", back_kb())


# ======================= janrlar =======================
async def genres_view(s):
    gs = await all_genres(s)
    rows = [[B(text=f"🗑 {g.name_uz} / {g.name_ru}", callback_data=f"gd:{g.id}")] for g in gs]
    rows.append([B(text="➕ Janr qo'shish", callback_data="ga")])
    rows.append([B(text="⬅️ Admin menyu", callback_data="adm:menu")])
    return "🎭 <b>Janrlar</b> (o'chirish uchun bosing)", M(inline_keyboard=rows)


@router.callback_query(F.data == "adm:genres")
async def genres_menu(cb, session, state: FSMContext):
    await state.clear()
    text, kb = await genres_view(session)
    await cb.answer()
    await edit(cb, text, kb)


@router.callback_query(F.data == "ga")
async def genre_add_start(cb, state: FSMContext):
    await state.set_state(GenreForm.add)
    await cb.answer()
    await cb.message.answer("Janr nomini yuboring: <code>O'zbekcha | Русский</code>\nMasalan: <code>Tarixiy | Исторический</code>", reply_markup=cancel_kb())


@router.message(StateFilter(GenreForm.add), F.text, NOT_CMD)
async def genre_add(message: Message, state: FSMContext, session):
    uz, _, ru = (p.strip() for p in message.text.partition("|"))
    if not uz:
        return await message.answer("❌ Nom bo'sh.")
    if (await session.execute(select(Genre.id).where(Genre.name_uz == uz[:60]))).first():
        return await message.answer("❌ Bunday janr bor.")
    session.add(Genre(name_uz=uz[:60], name_ru=(ru or uz)[:60]))
    await session.flush()
    await state.clear()
    text, kb = await genres_view(session)
    await message.answer("✅ Qo'shildi.\n\n" + text, reply_markup=kb)


@router.callback_query(F.data.startswith("gd:"))
async def genre_del(cb, session):
    g = await session.get(Genre, int(cb.data.split(":")[1]))
    if g:
        await session.delete(g)
        await session.flush()
    await cb.answer("O'chirildi")
    text, kb = await genres_view(session)
    await edit(cb, text, kb)


# ======================= foydalanuvchilar / ban / VIP =======================
async def find_user(s, raw: str):
    raw = raw.strip()
    if re.fullmatch(r"\d{4,15}", raw):
        return await s.get(User, int(raw))
    if re.fullmatch(r"@?\w{3,}", raw):
        return (await s.execute(select(User).where(User.username == raw.lstrip("@")))).scalars().first()
    return None


async def user_card(s, u: User) -> str:
    from database.queries import vip_until
    until = await vip_until(s, u.id)
    vip_txt = fmt_dt(until) if until else "yo'q"
    return (f"👤 <b>{esc(u.full_name)}</b> {('@' + u.username) if u.username else ''}\n🆔 <code>{u.id}</code>\n"
            f"🌐 {u.language} · 📅 {fmt_dt(u.created_at)}\n🕒 Oxirgi faollik: {fmt_dt(u.last_active_at)}\n"
            f"🚫 Ban: {yn(u.is_banned)}\n👑 VIP: {vip_txt}")


USER_PROMPTS = {"info": "👥 Foydalanuvchi ID yoki @username yuboring:", "ban": "🚫 Ban qilinadigan foydalanuvchi ID/@username:",
                "unban": "✅ Unban qilinadigan ID/@username:", "vipgive": "👑 VIP beriladigan ID/@username:",
                "vipterm": "⏳ VIP muddati o'zgartiriladigan ID/@username:"}


@router.callback_query(F.data == "adm:users")
async def users_menu(cb, state: FSMContext):
    await state.set_state(UserMgmt.wait_id)
    await state.update_data(action="info")
    await cb.answer()
    await cb.message.answer(USER_PROMPTS["info"], reply_markup=M(inline_keyboard=[
        [B(text="📋 VIP ro'yxati", callback_data="adm:viplist")], [B(text="❌ Bekor qilish", callback_data="af:cancel")]]))


@router.callback_query(F.data.func(lambda x: x.startswith("adm:") and x.split(":")[1] in ("ban", "unban", "vipgive", "vipterm")))
async def users_action_start(cb, state: FSMContext):
    action = cb.data.split(":")[1]
    await state.set_state(UserMgmt.wait_id)
    await state.update_data(action=action)
    await cb.answer()
    await cb.message.answer(USER_PROMPTS[action], reply_markup=cancel_kb())


@router.callback_query(F.data == "adm:viplist")
async def vip_list_cb(cb, session):
    rows = await vip_list(session)
    await cb.answer()
    lines = ["👑 <b>VIP foydalanuvchilar</b>", ""] + [f"• {esc(u.full_name)} (<code>{u.id}</code>) — {fmt_dt(exp)} gacha" for u, exp in rows]
    if not rows:
        lines.append("Hozircha yo'q.")
    await cb.message.answer("\n".join(lines)[:4000], reply_markup=back_kb())


@router.message(StateFilter(UserMgmt.wait_id), F.text, NOT_CMD)
async def user_resolve(message: Message, bot: Bot, state: FSMContext, session, role):
    u = await find_user(session, message.text)
    if not u:
        return await message.answer("❌ Foydalanuvchi topilmadi (u botga /start bosgan bo'lishi kerak).", reply_markup=cancel_kb())
    d = await state.get_data()
    action = d["action"]
    if action in ("ban",) and await role_of(session, u.id):
        return await message.answer("⛔ Xodimni ban qilib bo'lmaydi.")
    if action == "info":
        await state.clear()
        return await message.answer(await user_card(session, u), reply_markup=user_card_kb(u.id, u.is_banned))
    if action in ("ban", "unban"):
        u.is_banned = action == "ban"
        await state.clear()
        return await message.answer(f"{'🚫 Ban qilindi' if u.is_banned else '✅ Unban qilindi'}: <b>{esc(u.full_name)}</b>", reply_markup=back_kb())
    await state.set_state(UserMgmt.wait_days)
    await state.update_data(uid=u.id)
    await message.answer(f"{esc(u.full_name)} uchun kunlar soni:" + ("\n(0 = VIP ni bekor qilish)" if action == "vipterm" else ""), reply_markup=cancel_kb())


@router.message(StateFilter(UserMgmt.wait_days), F.text, NOT_CMD)
async def user_days(message: Message, bot: Bot, state: FSMContext, session):
    t = message.text.strip()
    if not t.isdigit() or int(t) > 3650:
        return await message.answer("❌ 0–3650 oralig'ida son yuboring.")
    d = await state.get_data()
    days, uid = int(t), d["uid"]
    await state.clear()
    u = await session.get(User, uid)
    if d["action"] == "vipgive":
        if days == 0:
            return await message.answer("❌ Kun musbat bo'lishi kerak.", reply_markup=back_kb())
        exp = await grant_vip(session, uid, days, "admin")
    else:
        exp = await set_vip_days(session, uid, days)
    if exp:
        await safe_send(bot, uid, f"👑 VIP {fmt_dt(exp)} gacha faol!")
    await message.answer(f"✅ Bajarildi. VIP: {fmt_dt(exp) if exp else 'bekor qilindi'}", reply_markup=back_kb())


@router.callback_query(F.data.startswith("uk:"))
async def user_quick(cb, bot: Bot, session, role):
    if role not in ("owner", "admin"):
        return await cb.answer("⛔", show_alert=True)
    parts = cb.data.split(":")
    act, uid = parts[1], int(parts[2])
    u = await session.get(User, uid)
    if not u:
        return await cb.answer("Topilmadi", show_alert=True)
    if act in ("ban", "unban"):
        if act == "ban" and await role_of(session, uid):
            return await cb.answer("⛔ Xodimni ban qilib bo'lmaydi", show_alert=True)
        u.is_banned = act == "ban"
    elif act == "vip":
        exp = await grant_vip(session, uid, int(parts[3]), "admin")
        await safe_send(bot, uid, f"👑 VIP {fmt_dt(exp)} gacha faol!")
    elif act == "vip0":
        await set_vip_days(session, uid, 0)
    await cb.answer("✅")
    await edit(cb, await user_card(session, u), user_card_kb(u.id, u.is_banned))


# ======================= reklama =======================
@router.callback_query(F.data == "adm:bcast")
async def bc_start(cb, state: FSMContext):
    await state.set_state(BroadcastForm.content)
    await cb.answer()
    await cb.message.answer("📣 Reklama xabarini yuboring (matn, rasm, video — nima bo'lsa shu holda tarqatiladi):", reply_markup=cancel_kb())


@router.message(StateFilter(BroadcastForm.content))
async def bc_preview(message: Message, bot: Bot, state: FSMContext, session):
    from sqlalchemy import func
    n = (await session.execute(select(func.count()).select_from(User).where(User.is_active.is_(True), User.is_banned.is_(False)))).scalar_one()
    await state.update_data(chat_id=message.chat.id, mid=message.message_id)
    await state.set_state(BroadcastForm.confirm)
    await bot.copy_message(message.chat.id, message.chat.id, message.message_id)
    await message.answer(f"👆 Shu xabar <b>{n}</b> ta foydalanuvchiga yuboriladi. Tasdiqlaysizmi?", reply_markup=confirm_kb("bc:go", "af:cancel"))


@router.callback_query(F.data == "bc:go", StateFilter(BroadcastForm.confirm))
async def bc_go(cb, bot: Bot, state: FSMContext):
    d = await state.get_data()
    await state.clear()
    await cb.answer("Boshlandi")
    task = asyncio.create_task(run_broadcast(bot, cb.message.chat.id, d["chat_id"], d["mid"]))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    await edit(cb, "📣 Reklama yuborish boshlandi. Tugagach hisobot keladi.", back_kb())


# ======================= promo-kodlar =======================
async def promo_view(s):
    promos = (await s.execute(select(PromoCode).order_by(PromoCode.id.desc()).limit(30))).scalars().all()
    lines = ["🎁 <b>Promo-kodlar</b>", ""]
    rows = []
    for p in promos:
        exp = f" · {p.expires_at:%d.%m.%Y}" if p.expires_at else ""
        lines.append(f"<code>{p.code}</code> — {p.vip_days} kun VIP · {p.used_count}/{p.max_uses}{exp}")
        rows.append([B(text=f"🗑 {p.code}", callback_data=f"pd:{p.id}")])
    if not promos:
        lines.append("Hozircha yo'q.")
    rows.append([B(text="➕ Yangi promo-kod", callback_data="pa")])
    rows.append([B(text="⬅️ Admin menyu", callback_data="adm:menu")])
    return "\n".join(lines), M(inline_keyboard=rows)


@router.callback_query(F.data == "adm:promo")
async def promo_menu(cb, session, state: FSMContext):
    await state.clear()
    text, kb = await promo_view(session)
    await cb.answer()
    await edit(cb, text, kb)


@router.callback_query(F.data == "pa")
async def promo_add_start(cb, state: FSMContext):
    await state.set_state(PromoForm.create)
    await cb.answer()
    await cb.message.answer("Format: <code>KOD KUN LIMIT [AMAL_QILISH_KUNI]</code>\nMasalan: <code>YANGIYIL 7 100 30</code>", reply_markup=cancel_kb())


@router.message(StateFilter(PromoForm.create), F.text, NOT_CMD)
async def promo_add(message: Message, state: FSMContext, session):
    parts = message.text.split()
    if len(parts) not in (3, 4) or not valid_code(parts[0]) or not all(x.isdigit() and int(x) > 0 for x in parts[1:]):
        return await message.answer("❌ Format noto'g'ri. Masalan: <code>YANGIYIL 7 100 30</code>")
    code = norm_code(parts[0])
    if (await session.execute(select(PromoCode.id).where(PromoCode.code == code))).first():
        return await message.answer("❌ Bunday promo-kod bor.")
    session.add(PromoCode(code=code, vip_days=int(parts[1]), max_uses=int(parts[2]),
                          expires_at=utcnow() + timedelta(days=int(parts[3])) if len(parts) == 4 else None))
    await session.flush()
    await state.clear()
    text, kb = await promo_view(session)
    await message.answer("✅ Yaratildi.\n\n" + text, reply_markup=kb)


@router.callback_query(F.data.startswith("pd:"))
async def promo_del(cb, session):
    p = await session.get(PromoCode, int(cb.data.split(":")[1]))
    if p:
        await session.delete(p)
        await session.flush()
    await cb.answer("O'chirildi")
    text, kb = await promo_view(session)
    await edit(cb, text, kb)


# ======================= admin / moderator =======================
async def staff_view(s, role):
    rows_db = (await s.execute(select(Admin).order_by(Admin.id))).scalars().all()
    lines = ["🛡 <b>Xodimlar</b>", ""]
    rows = []
    from config import settings
    for aid in settings.admin_ids:
        lines.append(f"👑 owner — <code>{aid}</code>")
    for a in rows_db:
        lines.append(f"{'🛡' if a.role == 'admin' else '🧑‍💼'} {a.role} — <code>{a.user_id}</code>")
        if role == "owner" or a.role == "moderator":
            rows.append([B(text=f"🗑 {a.role} {a.user_id}", callback_data=f"sr:{a.id}")])
    return "\n".join(lines), rows


@router.callback_query(F.data.func(lambda x: x in ("adm:add_admin", "adm:add_mod")))
async def staff_add_start(cb, state: FSMContext, session, role):
    new_role = "admin" if cb.data.endswith("admin") else "moderator"
    if new_role == "admin" and role != "owner":
        return await cb.answer("⛔ Admin qo'shish faqat egasi uchun", show_alert=True)
    await state.set_state(StaffForm.wait_id)
    await state.update_data(new_role=new_role)
    await cb.answer()
    text, rows = await staff_view(session, role)
    await cb.message.answer(f"{text}\n\n{'🛡 Admin' if new_role == 'admin' else '🧑‍💼 Moderator'} qo'shish: foydalanuvchi ID yoki @username yuboring:",
                            reply_markup=M(inline_keyboard=rows + [[B(text="❌ Bekor qilish", callback_data="af:cancel")]]))


@router.message(StateFilter(StaffForm.wait_id), F.text, NOT_CMD)
async def staff_add(message: Message, bot: Bot, state: FSMContext, session, role):
    u = await find_user(session, message.text)
    if not u:
        return await message.answer("❌ Foydalanuvchi topilmadi (u botga /start bosgan bo'lishi kerak).")
    new_role = (await state.get_data())["new_role"]
    if await role_of(session, u.id) == "owner":
        return await message.answer("ℹ️ Bu foydalanuvchi allaqachon egasi.")
    row = (await session.execute(select(Admin).where(Admin.user_id == u.id))).scalars().first()
    if row:
        row.role = new_role
    else:
        session.add(Admin(user_id=u.id, role=new_role, added_by=message.from_user.id))
    await state.clear()
    await safe_send(bot, u.id, f"🛠 Sizga <b>{new_role}</b> huquqi berildi. /admin")
    await message.answer(f"✅ {esc(u.full_name)} — {new_role}.", reply_markup=back_kb())


@router.callback_query(F.data.startswith("sr:"))
async def staff_remove(cb, session, role):
    a = await session.get(Admin, int(cb.data.split(":")[1]))
    if not a or (role != "owner" and a.role != "moderator"):
        return await cb.answer("⛔", show_alert=True)
    await session.delete(a)
    await session.flush()
    await cb.answer("O'chirildi")
    text, rows = await staff_view(session, role)
    await edit(cb, text, M(inline_keyboard=rows + [[B(text="⬅️ Admin menyu", callback_data="adm:menu")]]))
