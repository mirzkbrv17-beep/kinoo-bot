from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton as B, InlineKeyboardMarkup as M
from sqlalchemy import func, select

from database.models import Episode, Movie, Series, WatchHistory
from database.queries import user_history
from utils.filters import menu
from utils.helpers import esc, fmt_dt
from utils.texts import t

router = Router()


@router.message(menu("history"))
async def history(message, session, user, lang, state: FSMContext):
    await state.clear()
    rows = await user_history(session, user.id)
    if not rows:
        return await message.answer(t(lang, "hist_title") + "\n\n" + t(lang, "empty"))
    lines, kb = [t(lang, "hist_title"), ""], []
    for h in rows:
        if h.movie_id:
            m = await session.get(Movie, h.movie_id)
            if not m:
                continue
            title, cb = m.title, f"mv:{m.id}"
        else:
            ep = await session.get(Episode, h.episode_id)
            sr = await session.get(Series, ep.series_id) if ep else None
            if not ep or not sr:
                continue
            title, cb = f"{sr.title} · {t(lang, 'episode', n=ep.number)}", f"ep:{ep.id}"
        lines.append("• " + t(lang, "hist_line", title=esc(title), date=fmt_dt(h.last_at), n=h.times))
        kb.append([B(text=title[:55], callback_data=cb)])
    total = (await session.execute(select(func.count()).select_from(WatchHistory).where(WatchHistory.user_id == user.id))).scalar_one()
    rep = (await session.execute(select(func.count()).select_from(WatchHistory).where(
        WatchHistory.user_id == user.id, WatchHistory.times > 1))).scalar_one()
    lines += ["", f"📈 {total} • 🔁 {rep}"]
    await message.answer("\n".join(lines), reply_markup=M(inline_keyboard=kb))
