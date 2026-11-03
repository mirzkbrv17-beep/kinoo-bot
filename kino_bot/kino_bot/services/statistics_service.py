"""Statistika matnlari."""
from database.queries import admin_counts, count, top_movies
from database.models import Movie
from utils.helpers import esc, period_start
from utils.texts import t


async def top_text(s, lang: str, period: str) -> str:
    vip_only = period == "vip"
    since = None if period in ("all", "vip") else period_start(period)
    rows = await top_movies(s, since=since, vip_only=vip_only, limit=10)
    title = {"all": "st_all", "today": "st_today", "week": "st_week", "month": "st_month", "vip": "st_vip"}[period]
    lines = [t(lang, "stats_title"), f"<b>{t(lang, title)}</b>", ""]
    if not rows:
        lines.append(t(lang, "empty"))
    medals = ["🥇", "🥈", "🥉"]
    for i, (m, c) in enumerate(rows):
        mark = medals[i] if i < 3 else f"{i + 1}."
        lines.append(f"{mark} <b>{esc(m.title)}</b> — 👁 {c}")
    total = await count(s, Movie, Movie.is_active.is_(True))
    lines += ["", t(lang, "total_movies", n=total)]
    return "\n".join(lines)


async def admin_stats_text(s) -> str:
    c = await admin_counts(s)
    return (
        "📊 <b>Admin statistikasi</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{c['users']}</b>\n"
        f"🆕 Bugungi yangilar: <b>{c['new_today']}</b>\n"
        f"🔥 Faol (7 kun): <b>{c['active']}</b>\n"
        f"🎞 Jami kinolar: <b>{c['movies']}</b>\n"
        f"📺 Jami seriallar: <b>{c['series']}</b>\n"
        f"👁 Umumiy ko'rishlar: <b>{c['views']}</b>\n"
        f"👑 VIP foydalanuvchilar: <b>{c['vip']}</b>\n"
        f"🚫 Bloklanganlar (ban): <b>{c['banned']}</b>\n"
        f"📴 Botni to'xtatganlar: <b>{c['blocked']}</b>"
    )
