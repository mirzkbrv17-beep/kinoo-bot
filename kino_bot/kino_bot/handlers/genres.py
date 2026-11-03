from aiogram import F, Router
from aiogram.fsm.context import FSMContext

from database.queries import all_genres
from handlers.movies import build_list, show
from keyboards.inline import genres_kb
from utils.filters import menu
from utils.texts import t

router = Router()


@router.message(menu("genres"))
async def genres(message, session, lang, state: FSMContext):
    await state.clear()
    items = await all_genres(session)
    if not items:
        return await message.answer(t(lang, "empty"))
    await message.answer(t(lang, "genres_title"), reply_markup=genres_kb(items, lang))


@router.callback_query(F.data.startswith("gen:"))
async def genre_open(cb, session, user, lang, staff):
    await cb.answer()
    text, kb = await build_list(session, user.id, lang, "g", int(cb.data.split(":")[1]), 0, staff)
    await show(cb, text, kb)
