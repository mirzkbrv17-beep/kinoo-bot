import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ChatMemberUpdated, Message
from sqlalchemy import update

from database.db import session_maker
from database.models import User
from handlers.referrals import confirm_referral
from keyboards.inline import lang_kb
from services.menu_service import send_menu
from services.movie_service import send_by_code
from utils.filters import menu
from utils.helpers import esc
from utils.texts import t

log = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart(), StateFilter("*"))
async def cmd_start(message: Message, command: CommandObject, state: FSMContext, bot: Bot, session, user, lang, is_new, staff):
    await state.clear()
    await confirm_referral(bot, session, user)
    args = command.args or ""
    if is_new and not args.startswith("m_"):
        await message.answer(t(lang, "choose_lang"), reply_markup=lang_kb())
        return
    await send_menu(bot, message.chat.id, lang, t(lang, "welcome", name=esc(user.full_name or "do'st")))
    if args.startswith("m_"):
        if not await send_by_code(bot, session, message.chat.id, user.id, args[2:], lang, staff):
            await message.answer(t(lang, "not_found"))


@router.message(Command("cancel"), StateFilter("*"))
async def cmd_cancel(message: Message, state: FSMContext, bot: Bot, lang):
    await state.clear()
    await send_menu(bot, message.chat.id, lang, t(lang, "cancelled"))


@router.message(Command("help"))
async def cmd_help(message: Message, lang):
    await message.answer(t(lang, "help_text"))


@router.message(menu("help"))
async def menu_help(message: Message, state: FSMContext, lang):
    await state.clear()
    await message.answer(t(lang, "help_text"))


@router.my_chat_member()
async def on_block(event: ChatMemberUpdated):
    """Foydalanuvchi botni bloklasa/qayta yoqsa — is_active yangilanadi."""
    if event.chat.type != "private":
        return
    active = event.new_chat_member.status not in ("kicked", "left")
    async with session_maker() as s:
        await s.execute(update(User).where(User.id == event.chat.id).values(is_active=active))
        await s.commit()
