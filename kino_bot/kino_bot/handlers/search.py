"""Kino qidirish + KOD yuborilganda avtomatik kino topish (fallback router)."""
from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from database.queries import search_all
from keyboards.inline import mixed_results_kb
from services.movie_service import send_by_code
from utils.filters import NOT_CMD, menu
from aiogram import F
from utils.helpers import esc
from utils.texts import t

router = Router()          # menyu tugmasi
fallback = Router()        # eng oxirida ulanadi: kod yoki nom


@router.message(menu("search"))
async def search_prompt(message, state: FSMContext, lang):
    await state.clear()
    await message.answer(t(lang, "search_prompt"))


@fallback.message(StateFilter(None), F.text, NOT_CMD)
async def by_code_or_name(message, bot, session, user, lang, staff):
    q = message.text.strip()
    if len(q) <= 24 and await send_by_code(bot, session, message.chat.id, user.id, q, lang, staff):
        return
    if len(q) >= 2:
        movies, series = await search_all(session, q)
        if movies or series:
            await message.answer(t(lang, "search_results", q=esc(q[:60])), reply_markup=mixed_results_kb(movies, series))
            return
    await message.answer(t(lang, "not_found"))
