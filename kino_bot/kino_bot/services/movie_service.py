"""Kino / qism yuborish va caption yasash."""
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardButton as B, InlineKeyboardMarkup as M
from sqlalchemy import select

from database.models import Episode, Season, Series
from database.queries import genre_name, get_setting, is_fav, is_vip, log_view
from keyboards.inline import episode_kb, movie_kb, seasons_kb
from utils.helpers import esc, fmt_duration
from utils.texts import t

log = logging.getLogger(__name__)


def build_caption(m, genre: str, lang: str, limit: int = 1000) -> str:
    icon = "🎬" if getattr(m, "kind", "movie") != "cartoon" else "🧸"
    lines = [f"{icon} <b>{esc(m.title)}</b>" + (f" ({m.year})" if m.year else "")]
    if m.original_title:
        lines.append(f"<i>{esc(m.original_title)}</i>")
    lines.append("")
    lines.append(f"🔑 {t(lang, 'f_code')}: <code>{esc(m.code)}</code>")
    if m.country:
        lines.append(f"🌍 {t(lang, 'f_country')}: {esc(m.country)}")
    if genre:
        lines.append(f"🎭 {t(lang, 'f_genre')}: {esc(genre)}")
    if getattr(m, "duration", None):
        lines.append(f"⏱ {t(lang, 'f_duration')}: {fmt_duration(m.duration)}")
    if getattr(m, "age_limit", None):
        lines.append(f"🔞 {t(lang, 'f_age')}: {esc(m.age_limit)}")
    if getattr(m, "imdb", None):
        lines.append(f"⭐ {t(lang, 'f_imdb')}: {m.imdb}")
    lines.append(f"👁 {t(lang, 'f_views')}: {m.views}")
    if m.is_vip:
        lines.append(f"👑 {t(lang, 'f_vip')}")
    head = "\n".join(lines)
    if m.description:
        room = limit - len(head) - 8
        if room > 40:
            d = m.description if len(m.description) <= room else m.description[:room - 1].rstrip() + "…"
            head += f"\n\n📝 {esc(d)}"
    return head


async def _send_file(bot: Bot, chat_id: int, ftype: str, file_id: str, **kw):
    if ftype == "document":
        return await bot.send_document(chat_id, file_id, **kw)
    return await bot.send_video(chat_id, file_id, **kw)


async def send_movie(bot: Bot, s, chat_id: int, uid: int, movie, lang: str, staff: bool = False) -> None:
    genre = await genre_name(s, movie.genre_id, lang)
    cap = build_caption(movie, genre, lang)
    allowed = (not movie.is_vip) or staff or await is_vip(s, uid)
    kb = movie_kb(movie, lang, await is_fav(s, uid, movie.id), locked=not allowed)
    protect = (await get_setting(s, "protect_content", "0")) == "1" and not staff
    if not allowed:
        text = cap + "\n\n" + t(lang, "vip_locked")
        if movie.poster_file_id:
            await bot.send_photo(chat_id, movie.poster_file_id, caption=text, reply_markup=kb)
        else:
            await bot.send_message(chat_id, text, reply_markup=kb)
        return
    if movie.video_file_id:
        if movie.poster_file_id:
            await bot.send_photo(chat_id, movie.poster_file_id, caption=cap, reply_markup=kb)
            await _send_file(bot, chat_id, movie.video_type, movie.video_file_id,
                             caption=f"🎬 <b>{esc(movie.title)}</b>", protect_content=protect)
        else:
            await _send_file(bot, chat_id, movie.video_type, movie.video_file_id, caption=cap,
                             reply_markup=kb, protect_content=protect)
    elif movie.poster_file_id:
        await bot.send_photo(chat_id, movie.poster_file_id, caption=cap, reply_markup=kb, protect_content=protect)
    else:
        await bot.send_message(chat_id, cap, reply_markup=kb)
    await log_view(s, uid, movie=movie)


async def send_series_card(bot: Bot, s, chat_id: int, series, lang: str) -> None:
    seasons = (await s.execute(select(Season).where(Season.series_id == series.id).order_by(Season.number))).scalars().all()
    genre = await genre_name(s, series.genre_id, lang)
    cap = build_caption(series, genre, lang)
    if not seasons:
        cap += "\n\n" + t(lang, "empty")
    else:
        cap += "\n\n" + t(lang, "seasons_title")
    kb = seasons_kb(seasons, lang) if seasons else None
    if series.poster_file_id:
        await bot.send_photo(chat_id, series.poster_file_id, caption=cap, reply_markup=kb)
    else:
        await bot.send_message(chat_id, cap, reply_markup=kb)


async def send_episode(bot: Bot, s, chat_id: int, uid: int, ep, lang: str, staff: bool = False) -> None:
    series = await s.get(Series, ep.series_id)
    season = await s.get(Season, ep.season_id)
    siblings = (await s.execute(select(Episode).where(Episode.season_id == ep.season_id).order_by(Episode.number))).scalars().all()
    kb = episode_kb(ep, siblings, lang)
    title = f"📺 <b>{esc(series.title)}</b>\n{t(lang, 'season', n=season.number)} · {t(lang, 'episode', n=ep.number)}\n🔑 <code>{esc(ep.code)}</code>"
    if series.is_vip and not (staff or await is_vip(s, uid)):
        await bot.send_message(chat_id, title + "\n\n" + t(lang, "vip_locked"),
                               reply_markup=M(inline_keyboard=[[B(text=t(lang, "buy_vip"), callback_data="vip:plans")]]))
        return
    protect = (await get_setting(s, "protect_content", "0")) == "1" and not staff
    if ep.video_file_id:
        await _send_file(bot, chat_id, ep.video_type, ep.video_file_id, caption=title, reply_markup=kb, protect_content=protect)
    else:
        await bot.send_message(chat_id, title, reply_markup=kb)
    await log_view(s, uid, episode=ep)


async def send_by_code(bot: Bot, s, chat_id: int, uid: int, code: str, lang: str, staff: bool = False) -> bool:
    from database.queries import find_by_code
    found = await find_by_code(s, code)
    if not found:
        return False
    kind, obj = found
    if kind == "movie":
        await send_movie(bot, s, chat_id, uid, obj, lang, staff)
    elif kind == "episode":
        await send_episode(bot, s, chat_id, uid, obj, lang, staff)
    else:
        await send_series_card(bot, s, chat_id, obj, lang)
    return True
