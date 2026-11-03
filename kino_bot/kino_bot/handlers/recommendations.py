from aiogram import Router
from aiogram.fsm.context import FSMContext

from database.queries import recommend
from keyboards.inline import movie_list_kb
from utils.filters import menu
from utils.helpers import esc
from utils.texts import t

router = Router()


@router.message(menu("recs"))
async def recs(message, session, user, lang, staff, state: FSMContext):
    await state.clear()
    data = await recommend(session, user.id)
    lines, allm, seen = [t(lang, "recs_title")], [], set()
    for key, head in (("pref", "rec_pref"), ("hist", "rec_hist"), ("rand", "rec_rand")):
        items = [m for m in data[key] if m.id not in seen]
        if not items:
            continue
        lines += ["", f"<b>{t(lang, head)}</b>"] + [f"• {esc(m.title)}" + (f" ({m.year})" if m.year else "") for m in items]
        for m in items:
            seen.add(m.id)
            allm.append(m)
    if not allm:
        return await message.answer(t(lang, "recs_title") + "\n\n" + t(lang, "empty"))
    await message.answer("\n".join(lines), reply_markup=movie_list_kb(allm, lang, vip_ok=True))
