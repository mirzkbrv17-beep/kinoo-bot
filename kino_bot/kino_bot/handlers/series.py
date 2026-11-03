from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from database.models import Episode, Season, Series
from database.queries import watched_episode_ids
from handlers.movies import build_list
from keyboards.inline import episodes_kb
from services.movie_service import send_episode, send_series_card
from utils.filters import menu
from utils.texts import t

router = Router()


@router.message(menu("series"))
async def series_menu(message, session, user, lang, staff, state: FSMContext):
    await state.clear()
    text, kb = await build_list(session, user.id, lang, "s", 0, 0, staff)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("se:"))
async def series_open(cb, bot, session, lang):
    series = await session.get(Series, int(cb.data.split(":")[1]))
    if not series or not series.is_active:
        return await cb.answer(t(lang, "not_found"), show_alert=True)
    await cb.answer()
    await send_series_card(bot, session, cb.message.chat.id, series, lang)


@router.callback_query(F.data.startswith("sn:"))
async def season_open(cb, session, user, lang):
    season = await session.get(Season, int(cb.data.split(":")[1]))
    if not season:
        return await cb.answer()
    eps = (await session.execute(select(Episode).where(Episode.season_id == season.id).order_by(Episode.number))).scalars().all()
    watched = await watched_episode_ids(session, user.id, season.series_id)
    await cb.answer()
    text = f"{t(lang, 'season', n=season.number)}\n{t(lang, 'episodes_title')}" if eps else t(lang, "empty")
    await cb.message.answer(text, reply_markup=episodes_kb(eps, watched, lang, season.series_id))


@router.callback_query(F.data.startswith("ep:"))
async def episode_open(cb, bot, session, user, lang, staff):
    ep = await session.get(Episode, int(cb.data.split(":")[1]))
    if not ep:
        return await cb.answer(t(lang, "not_found"), show_alert=True)
    await cb.answer()
    await send_episode(bot, session, cb.message.chat.id, user.id, ep, lang, staff)
