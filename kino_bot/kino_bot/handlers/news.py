from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton as B, InlineKeyboardMarkup as M

from database.queries import get_setting
from utils.filters import menu
from utils.validators import is_url
from utils.texts import t

router = Router()


@router.message(menu("news"))
async def news(message, session, lang, state: FSMContext):
    await state.clear()
    text = (await get_setting(session, "news_text", "")).strip()
    url = (await get_setting(session, "news_url", "")).strip()
    kb = M(inline_keyboard=[[B(text=t(lang, "news_btn"), url=url)]]) if is_url(url) else None
    if not text and not kb:
        return await message.answer(t(lang, "news_empty"))
    await message.answer(text or t(lang, "menu_news"), reply_markup=kb)
