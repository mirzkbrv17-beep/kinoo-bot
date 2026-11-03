"""Kino ro'yxatlari, kino ochish, sevimlilarga qo'shish, tasodifiy kino."""
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton as B

from database.models import Movie
from database.queries import (genre_name, is_vip, list_favs, list_movies, list_series, random_movie, toggle_fav)
from keyboards.inline import again_random_kb, movie_kb, movie_list_kb, series_list_kb
from services.movie_service import send_movie
from utils.texts import t

log = logging.getLogger(__name__)
router = Router()
PER = 8


async def build_list(s, uid: int, lang: str, kind: str, arg: int, page: int, staff: bool = False):
    vip_ok = staff or await is_vip(s, uid)
    prefix = f"lst:{kind}:{arg}"
    if kind == "s":
        rows, total = await list_series(s, page, PER)
        text = t(lang, "series_title")
        kb = series_list_kb(rows, prefix, page, total, PER)
        return (text if rows else text + "\n\n" + t(lang, "empty")), kb
    extra = []
    if kind == "g":
        rows, total = await list_movies(s, genre_id=arg, page=page, per=PER)
        text = t(lang, "genre_list", name=await genre_name(s, arg, lang))
    elif kind == "c":
        rows, total = await list_movies(s, kind="cartoon", page=page, per=PER)
        text = t(lang, "cartoons_title")
    elif kind == "v":
        rows, total = await list_movies(s, vip=True, page=page, per=PER)
        text = t(lang, "vip_title")
        if not vip_ok:
            extra = [[B(text=t(lang, "buy_vip"), callback_data="vip:plans")]]
    else:  # "f"
        rows, total = await list_favs(s, uid, page, PER)
        text = t(lang, "fav_title")
    if not rows:
        text += "\n\n" + t(lang, "empty")
    return text, movie_list_kb(rows, lang, prefix, page, total, PER, vip_ok, extra)


async def show(cb_or_msg, text: str, kb):
    """Callback bo'lsa xabarni tahrirlaydi (rasmli bo'lsa yangisini yuboradi), aks holda yuboradi."""
    msg = getattr(cb_or_msg, "message", None)
    if msg is None:
        return await cb_or_msg.answer(text, reply_markup=kb)
    try:
        if msg.text:
            return await msg.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
    return await msg.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("lst:"))
async def cb_list(cb, session, user, lang, staff):
    _, kind, arg, page = cb.data.split(":")
    text, kb = await build_list(session, user.id, lang, kind, int(arg), int(page), staff)
    await cb.answer()
    await show(cb, text, kb)


@router.callback_query(F.data.startswith("mv:"))
async def cb_movie(cb, bot, session, user, lang, staff):
    movie = await session.get(Movie, int(cb.data.split(":")[1]))
    if not movie or not movie.is_active:
        return await cb.answer(t(lang, "not_found"), show_alert=True)
    await cb.answer()
    await send_movie(bot, session, cb.message.chat.id, user.id, movie, lang, staff)


@router.callback_query(F.data.startswith("fav:"))
async def cb_fav(cb, session, user, lang):
    movie = await session.get(Movie, int(cb.data.split(":")[1]))
    if not movie:
        return await cb.answer()
    added = await toggle_fav(session, user.id, movie.id)
    await cb.answer(t(lang, "fav_added" if added else "fav_removed"))
    try:
        await cb.message.edit_reply_markup(reply_markup=movie_kb(movie, lang, added, locked=False))
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "noop")
async def cb_noop(cb):
    await cb.answer()


async def _random(bot, session, chat_id, user, lang, staff):
    allow_vip = staff or await is_vip(session, user.id)
    movie = await random_movie(session, allow_vip)
    if not movie:
        return await bot.send_message(chat_id, t(lang, "empty"))
    await send_movie(bot, session, chat_id, user.id, movie, lang, staff)
    await bot.send_message(chat_id, t(lang, "random_title"), reply_markup=again_random_kb(lang))


from utils.filters import menu  # noqa: E402


@router.message(menu("random"))
async def menu_random(message, bot, session, user, lang, staff, state: FSMContext):
    await state.clear()
    await _random(bot, session, message.chat.id, user, lang, staff)


@router.callback_query(F.data == "rnd")
async def cb_random(cb, bot, session, user, lang, staff):
    await cb.answer()
    await _random(bot, session, cb.message.chat.id, user, lang, staff)
