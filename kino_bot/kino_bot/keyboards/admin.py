"""Admin paneli klaviaturalari."""
from aiogram.types import InlineKeyboardButton as B, InlineKeyboardMarkup as M

from database.queries import genre_label
from utils.helpers import chunk

# moderator uchun ruxsat etilgan amallar
MOD_ACTIONS = {"menu", "add_movie", "add_cartoon", "series", "add_series", "add_season", "add_episode",
               "edit", "stats", "close"}

ADMIN_BUTTONS = [
    ("🎬 Kino qo'shish", "add_movie"), ("👑 VIP kino qo'shish", "add_vip"),
    ("✏️ Kino tahrirlash", "edit"), ("🗑 Kino o'chirish", "del"),
    ("📺 Serial qo'shish", "series"), ("🧸 Multfilm qo'shish", "add_cartoon"),
    ("🎭 Janrlarni boshqarish", "genres"), ("👥 Foydalanuvchilar", "users"),
    ("🚫 Ban", "ban"), ("✅ Unban", "unban"),
    ("👑 VIP berish", "vipgive"), ("⏳ VIP muddatini o'zgartirish", "vipterm"),
    ("📢 Majburiy obuna", "channels"), ("😀 Premium emoji", "emoji"),
    ("📣 Reklama yuborish", "bcast"), ("🎁 Promo-kodlar", "promo"),
    ("🛡 Admin qo'shish", "add_admin"), ("🧑‍💼 Moderator qo'shish", "add_mod"),
    ("📊 Statistika", "stats"), ("🤖 Bot sozlamalari", "botset"),
    ("💾 Zaxira nusxa", "backup"),
]


def admin_menu(role: str) -> M:
    items = ADMIN_BUTTONS if role in ("owner", "admin") else [b for b in ADMIN_BUTTONS if b[1] in MOD_ACTIONS]
    rows = list(chunk([B(text=n, callback_data=f"adm:{a}") for n, a in items], 2))
    rows.append([B(text="❌ Yopish", callback_data="adm:close")])
    return M(inline_keyboard=rows)


def back_kb(extra=None) -> M:
    rows = (extra or []) + [[B(text="⬅️ Admin menyu", callback_data="adm:menu")]]
    return M(inline_keyboard=rows)


def cancel_kb() -> M:
    return M(inline_keyboard=[[B(text="❌ Bekor qilish", callback_data="af:cancel")]])


def step_kb(field: str, required: bool, genres=None) -> M:
    rows = []
    if field == "genre" and genres:
        rows += list(chunk([B(text=g.name_uz, callback_data=f"af:g:{g.id}") for g in genres], 3))
    if field == "is_vip":
        rows.append([B(text="👑 Ha, VIP", callback_data="af:v:1"), B(text="Oddiy", callback_data="af:v:0")])
    tail = []
    if not required and field != "is_vip":
        tail.append(B(text="⏭ O'tkazib yuborish", callback_data="af:skip"))
    tail.append(B(text="❌ Bekor qilish", callback_data="af:cancel"))
    rows.append(tail)
    return M(inline_keyboard=rows)


def series_menu_kb() -> M:
    return M(inline_keyboard=[
        [B(text="📺 Serial yaratish", callback_data="adm:add_series")],
        [B(text="📋 Fasl qo'shish", callback_data="adm:add_season")],
        [B(text="▶️ Qism qo'shish", callback_data="adm:add_episode")],
        [B(text="⬅️ Admin menyu", callback_data="adm:menu")]])


def edit_kb(movie_id: int, movie) -> M:
    fields = [("Nomi", "title"), ("Original", "original_title"), ("Yili", "year"), ("Davlat", "country"),
              ("Davomiyligi", "duration"), ("Yosh", "age_limit"), ("IMDb", "imdb"), ("Tavsif", "description"),
              ("Treyler", "trailer_url"), ("Poster", "poster"), ("Video/havola", "media"), ("Janr", "genre"),
              ("Kod", "code")]
    rows = list(chunk([B(text=n, callback_data=f"ed:{f}") for n, f in fields], 3))
    rows.append([B(text="👑 VIP: " + ("ha" if movie.is_vip else "yo'q"), callback_data="ed:t_vip"),
                 B(text="👁 Faol: " + ("ha" if movie.is_active else "yo'q"), callback_data="ed:t_active")])
    rows.append([B(text="⬅️ Admin menyu", callback_data="adm:menu")])
    return M(inline_keyboard=rows)


def genre_pick_kb(genres, prefix: str) -> M:
    return M(inline_keyboard=list(chunk([B(text=g.name_uz, callback_data=f"{prefix}:{g.id}") for g in genres], 3)))


def confirm_kb(yes: str, no: str = "adm:menu") -> M:
    return M(inline_keyboard=[[B(text="✅ Ha", callback_data=yes), B(text="❌ Yo'q", callback_data=no)]])


def user_card_kb(uid: int, banned: bool) -> M:
    return M(inline_keyboard=[
        [B(text="✅ Unban" if banned else "🚫 Ban", callback_data=f"uk:{'unban' if banned else 'ban'}:{uid}")],
        [B(text="👑 +30 kun", callback_data=f"uk:vip:{uid}:30"), B(text="👑 +365 kun", callback_data=f"uk:vip:{uid}:365")],
        [B(text="❎ VIP bekor", callback_data=f"uk:vip0:{uid}")],
        [B(text="⬅️ Admin menyu", callback_data="adm:menu")]])
