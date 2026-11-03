from aiogram import F, Router
from aiogram.fsm.context import FSMContext

from keyboards.inline import lang_kb
from services.menu_service import send_menu
from utils.filters import menu
from utils.helpers import esc
from utils.texts import LANGS, t

router = Router()


@router.message(menu("language"))
async def ask_lang(message, state: FSMContext, lang):
    await state.clear()
    await message.answer(t(lang, "choose_lang"), reply_markup=lang_kb())


@router.callback_query(F.data.startswith("lang:"))
async def set_lang(cb, bot, user, state: FSMContext):
    code = cb.data.split(":")[1]
    if code not in LANGS:
        return await cb.answer()
    user.language = code
    await state.clear()
    await cb.answer(t(code, "lang_set"))
    try:
        await cb.message.delete()
    except Exception:
        pass
    await send_menu(bot, cb.message.chat.id, code, t(code, "welcome", name=esc(user.full_name or "")))
