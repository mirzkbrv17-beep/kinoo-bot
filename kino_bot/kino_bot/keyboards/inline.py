"""Inline klaviaturalar."""
from math import ceil
from typing import Optional

from aiogram.types import InlineKeyboardButton as B, InlineKeyboardMarkup as M, WebAppInfo

from config import settings
from database.queries import genre_label
from services.subscription_service import channel_url
from utils.helpers import chunk
from utils.texts import LANGS, t
from utils.validators import is_url


def _m(rows) -> M:
    return M(inline_keyboard=rows)


def lang_kb() -> M:
    return _m([[B(text=name, callback_data=f"lang:{code}") for code, name in LANGS.items()]])


def subscribe_kb(channels, lang: str) -> M:
    rows = [[B(text=f"📢 {c.title or c.username or c.chat_id}", url=channel_url(c))] for c in channels if channel_url(c)]
    rows.append([B(text=t(lang, "sub_check"), callback_data="chk_sub")])
    return _m(rows)


def pager_row(prefix: str, page: int, total: int, per: int) -> list:
    pages = max(1, ceil(total / per))
    if pages <= 1:
        return []
    row = []
    if page > 0:
        row.append(B(text="⬅️", callback_data=f"{prefix}:{page - 1}"))
    row.append(B(text=f"{page + 1}/{pages}", callback_data="noop"))
    if page < pages - 1:
        row.append(B(text="➡️", callback_data=f"{prefix}:{page + 1}"))
    return row


def movie_list_kb(movies, lang: str, prefix: Optional[str] = None, page: int = 0, total: int = 0,
                  per: int = 8, vip_ok: bool = True, extra_rows=None) -> M:
    rows = []
    for m in movies:
        lock = "🔒 " if (m.is_vip and not vip_ok) else ("👑 " if m.is_vip else "")
        year = f" ({m.year})" if m.year else ""
        rows.append([B(text=f"{lock}{m.title}{year}"[:60], callback_data=f"mv:{m.id}")])
    if prefix:
        nav = pager_row(prefix, page, total, per)
        if nav:
            rows.append(nav)
    rows += extra_rows or []
    return _m(rows)


def series_list_kb(series, prefix: str, page: int, total: int, per: int = 8) -> M:
    rows = [[B(text=f"📺 {s.title}"[:60], callback_data=f"se:{s.id}")] for s in series]
    nav = pager_row(prefix, page, total, per)
    if nav:
        rows.append(nav)
    return _m(rows)


def mixed_results_kb(movies, series) -> M:
    rows = [[B(text=f"🎬 {m.title}{f' ({m.year})' if m.year else ''}"[:60], callback_data=f"mv:{m.id}")] for m in movies]
    rows += [[B(text=f"📺 {s.title}"[:60], callback_data=f"se:{s.id}")] for s in series]
    return _m(rows)


def webapp_button(lang: str) -> Optional[B]:
    if settings.webapp_url.startswith("https://"):
        return B(text=t(lang, "open_app"), web_app=WebAppInfo(url=settings.webapp_url))
    return None


def movie_kb(movie, lang: str, fav: bool, locked: bool) -> M:
    rows = []
    if locked:
        rows.append([B(text=t(lang, "buy_vip"), callback_data="vip:plans")])
    else:
        rows.append([B(text=t(lang, "rem_fav" if fav else "add_fav"), callback_data=f"fav:{movie.id}")])
        if movie.watch_url and is_url(movie.watch_url):
            rows.append([B(text=t(lang, "watch"), url=movie.watch_url)])
    if movie.trailer_url and is_url(movie.trailer_url):
        rows.append([B(text=t(lang, "trailer"), url=movie.trailer_url)])
    return _m(rows)


def episode_kb(ep, siblings, lang: str) -> M:
    rows = []
    if ep.watch_url and is_url(ep.watch_url):
        rows.append([B(text=t(lang, "watch"), url=ep.watch_url)])
    nav = []
    idx = next((i for i, e in enumerate(siblings) if e.id == ep.id), 0)
    if idx > 0:
        nav.append(B(text=f"⬅️ {t(lang, 'episode', n=siblings[idx - 1].number)}", callback_data=f"ep:{siblings[idx - 1].id}"))
    if idx < len(siblings) - 1:
        nav.append(B(text=f"{t(lang, 'episode', n=siblings[idx + 1].number)} ➡️", callback_data=f"ep:{siblings[idx + 1].id}"))
    if nav:
        rows.append(nav)
    rows.append([B(text=t(lang, "seasons"), callback_data=f"sn:{ep.season_id}")])
    return _m(rows)


def seasons_kb(seasons, lang: str) -> M:
    return _m([[B(text=t(lang, "season", n=s.number), callback_data=f"sn:{s.id}")] for s in seasons])


def episodes_kb(eps, watched: set, lang: str, series_id: int) -> M:
    btns = [B(text=f"{'✅ ' if e.id in watched else ''}{e.number}", callback_data=f"ep:{e.id}") for e in eps]
    rows = list(chunk(btns, 5))
    rows.append([B(text="⬅️", callback_data=f"se:{series_id}")])
    return _m(rows)


def genres_kb(genres, lang: str) -> M:
    btns = [B(text=genre_label(g, lang), callback_data=f"gen:{g.id}") for g in genres]
    return _m(list(chunk(btns, 2)))


def pref_genres_kb(genres, selected: set, lang: str) -> M:
    btns = [B(text=("✅ " if g.id in selected else "▫️ ") + genre_label(g, lang), callback_data=f"pg:{g.id}") for g in genres]
    return _m(list(chunk(btns, 2)))


def stats_kb(lang: str) -> M:
    keys = [("all", "st_all"), ("today", "st_today"), ("week", "st_week"), ("month", "st_month"), ("vip", "st_vip")]
    btns = [B(text=t(lang, k), callback_data=f"st:{p}") for p, k in keys]
    return _m(list(chunk(btns, 3)))


def vip_plans_kb(plans, lang: str) -> M:
    return _m([[B(text=t(lang, "vip_buy", days=d, stars=st), callback_data=f"vip:buy:{d}")] for d, st in plans])


def settings_kb(lang: str, staff: bool) -> M:
    rows = [[B(text=t(lang, "set_lang"), callback_data="us:lang"), B(text=t(lang, "set_genres"), callback_data="us:genres")],
            [B(text=t(lang, "set_promo"), callback_data="us:promo"), B(text=t(lang, "set_vip"), callback_data="us:vip")]]
    app = webapp_button(lang)
    if app:
        rows.append([app])
    if staff:
        rows.append([B(text=t(lang, "set_admin"), callback_data="adm:menu")])
    return _m(rows)


def again_random_kb(lang: str) -> M:
    return _m([[B(text=t(lang, "again"), callback_data="rnd")]])
