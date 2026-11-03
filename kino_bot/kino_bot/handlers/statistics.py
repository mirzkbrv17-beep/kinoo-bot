from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext

from keyboards.inline import stats_kb
from services.statistics_service import top_text
from utils.filters import menu

router = Router()


@router.message(menu("stats"))
async def stats(message, session, lang, state: FSMContext):
    await state.clear()
    await message.answer(await top_text(session, lang, "all"), reply_markup=stats_kb(lang))


@router.callback_query(F.data.startswith("st:"))
async def stats_period(cb, session, lang):
    period = cb.data.split(":")[1]
    if period not in ("all", "today", "week", "month", "vip"):
        return await cb.answer()
    await cb.answer()
    try:
        await cb.message.edit_text(await top_text(session, lang, period), reply_markup=stats_kb(lang))
    except TelegramBadRequest:
        pass  # xabar o'zgarmagan
