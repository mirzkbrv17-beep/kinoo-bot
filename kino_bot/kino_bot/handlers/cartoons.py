from aiogram import Router
from aiogram.fsm.context import FSMContext

from handlers.movies import build_list
from utils.filters import menu

router = Router()


@router.message(menu("cartoons"))
async def cartoons(message, session, user, lang, staff, state: FSMContext):
    await state.clear()
    text, kb = await build_list(session, user.id, lang, "c", 0, 0, staff)
    await message.answer(text, reply_markup=kb)
