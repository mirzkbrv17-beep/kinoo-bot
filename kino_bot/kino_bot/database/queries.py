"""Ma'lumotlar bazasi so'rovlari (parametrlashtirilgan — SQL injection xavfi yo'q)."""
import random
from datetime import timedelta
from typing import Optional

from sqlalchemy import and_, delete, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import (Admin, BotSetting, Episode, Favorite, Genre, MandatoryChannel, Movie,
                             MovieView, PromoCode, PromoUsage, Referral, Season, Series, User,
                             VipSubscription, WatchHistory)
from utils.helpers import norm_code, utcnow


# ---------- sozlamalar ----------
async def get_setting(s: AsyncSession, key: str, default: str = "") -> str:
    row = await s.get(BotSetting, key)
    return row.value if row else default


async def set_setting(s: AsyncSession, key: str, value) -> None:
    row = await s.get(BotSetting, key)
    if row:
        row.value = str(value)
    else:
        s.add(BotSetting(key=key, value=str(value)))
    await s.flush()


# ---------- rollar ----------
async def role_of(s: AsyncSession, uid: int) -> Optional[str]:
    if uid in settings.admin_ids:
        return "owner"
    return (await s.execute(select(Admin.role).where(Admin.user_id == uid))).scalar_one_or_none()


async def staff_ids(s: AsyncSession) -> list:
    ids = set(settings.admin_ids)
    ids.update((await s.execute(select(Admin.user_id))).scalars().all())
    return list(ids)


# ---------- VIP ----------
async def vip_until(s: AsyncSession, uid: int):
    q = select(func.max(VipSubscription.expires_at)).where(
        VipSubscription.user_id == uid, VipSubscription.is_active.is_(True),
        VipSubscription.expires_at > utcnow())
    return (await s.execute(q)).scalar_one_or_none()


async def is_vip(s: AsyncSession, uid: int) -> bool:
    return (await vip_until(s, uid)) is not None


async def _deactivate(s: AsyncSession, uid: int):
    await s.execute(update(VipSubscription).where(
        VipSubscription.user_id == uid, VipSubscription.is_active.is_(True)).values(is_active=False))


async def grant_vip(s: AsyncSession, uid: int, days: int, source: str = "admin"):
    """Mavjud VIP ustiga kun qo'shadi."""
    now = utcnow()
    cur = await vip_until(s, uid)
    exp = (cur if cur and cur > now else now) + timedelta(days=days)
    await _deactivate(s, uid)
    s.add(VipSubscription(user_id=uid, starts_at=now, expires_at=exp, is_active=True, source=source))
    await s.flush()
    return exp


async def set_vip_days(s: AsyncSession, uid: int, days: int):
    """VIP muddatini bugundan boshlab aniq belgilaydi; 0 = bekor qilish."""
    await _deactivate(s, uid)
    if days <= 0:
        await s.flush()
        return None
    now = utcnow()
    exp = now + timedelta(days=days)
    s.add(VipSubscription(user_id=uid, starts_at=now, expires_at=exp, is_active=True, source="admin"))
    await s.flush()
    return exp


async def expire_vips(s: AsyncSession) -> list:
    """Muddati tugagan VIP'larni oddiy holatga qaytaradi; tugaganlar ID ro'yxatini qaytaradi."""
    now = utcnow()
    rows = (await s.execute(select(VipSubscription.user_id).where(
        VipSubscription.is_active.is_(True), VipSubscription.expires_at <= now))).scalars().all()
    if rows:
        await s.execute(update(VipSubscription).where(
            VipSubscription.is_active.is_(True), VipSubscription.expires_at <= now).values(is_active=False))
        still = set((await s.execute(select(VipSubscription.user_id).where(
            VipSubscription.is_active.is_(True), VipSubscription.expires_at > now))).scalars().all())
        rows = [u for u in set(rows) if u not in still]
    return list(rows)


async def vip_list(s: AsyncSession, limit: int = 60):
    q = (select(User, func.max(VipSubscription.expires_at).label("exp"))
         .join(VipSubscription, VipSubscription.user_id == User.id)
         .where(VipSubscription.is_active.is_(True), VipSubscription.expires_at > utcnow())
         .group_by(User.id).order_by(desc("exp")).limit(limit))
    return (await s.execute(q)).all()


# ---------- kodlar ----------
async def code_taken(s: AsyncSession, code: str) -> bool:
    code = norm_code(code)
    for model in (Movie, Series, Episode):
        if (await s.execute(select(model.id).where(model.code == code))).first():
            return True
    return False


async def next_code(s: AsyncSession) -> str:
    while True:
        n = int(await get_setting(s, "next_code", "101"))
        await set_setting(s, "next_code", n + 1)
        if not await code_taken(s, str(n)):
            return str(n)


async def find_by_code(s: AsyncSession, code: str):
    code = norm_code(code)
    m = (await s.execute(select(Movie).where(Movie.code == code, Movie.is_active.is_(True)))).scalars().first()
    if m:
        return "movie", m
    e = (await s.execute(select(Episode).where(Episode.code == code))).scalars().first()
    if e:
        return "episode", e
    sr = (await s.execute(select(Series).where(Series.code == code, Series.is_active.is_(True)))).scalars().first()
    if sr:
        return "series", sr
    return None


# ---------- janrlar ----------
async def all_genres(s: AsyncSession):
    return (await s.execute(select(Genre).order_by(Genre.id))).scalars().all()


def genre_label(g: Genre, lang: str) -> str:
    return (g.name_ru if lang == "ru" and g.name_ru else g.name_uz) if g else ""


async def genre_name(s: AsyncSession, genre_id, lang: str) -> str:
    if not genre_id:
        return ""
    return genre_label(await s.get(Genre, genre_id), lang)


# ---------- ro'yxatlar ----------
async def list_movies(s: AsyncSession, *, kind=None, genre_id=None, vip=None, page=0, per=8):
    cond = [Movie.is_active.is_(True)]
    if kind:
        cond.append(Movie.kind == kind)
    if genre_id:
        cond.append(Movie.genre_id == genre_id)
    if vip is not None:
        cond.append(Movie.is_vip.is_(vip))
    total = (await s.execute(select(func.count()).select_from(Movie).where(*cond))).scalar_one()
    rows = (await s.execute(select(Movie).where(*cond).order_by(Movie.id.desc())
                            .limit(per).offset(page * per))).scalars().all()
    return rows, total


async def list_series(s: AsyncSession, page=0, per=8):
    cond = [Series.is_active.is_(True)]
    total = (await s.execute(select(func.count()).select_from(Series).where(*cond))).scalar_one()
    rows = (await s.execute(select(Series).where(*cond).order_by(Series.id.desc())
                            .limit(per).offset(page * per))).scalars().all()
    return rows, total


async def search_all(s: AsyncSession, q: str, limit: int = 15):
    like = f"%{q.lower().strip()}%"
    movies = (await s.execute(select(Movie).where(Movie.is_active.is_(True), or_(
        Movie.search_key.like(like), Movie.code == norm_code(q))).order_by(Movie.views.desc()).limit(limit))).scalars().all()
    series = (await s.execute(select(Series).where(Series.is_active.is_(True), Series.search_key.like(like))
                              .order_by(Series.views.desc()).limit(limit))).scalars().all()
    return movies, series


async def random_movie(s: AsyncSession, allow_vip: bool = True):
    cond = [Movie.is_active.is_(True)]
    if not allow_vip:
        cond.append(Movie.is_vip.is_(False))
    return (await s.execute(select(Movie).where(*cond).order_by(func.random()).limit(1))).scalars().first()


# ---------- sevimlilar ----------
async def is_fav(s: AsyncSession, uid: int, movie_id: int) -> bool:
    return (await s.execute(select(Favorite.id).where(
        Favorite.user_id == uid, Favorite.movie_id == movie_id))).first() is not None


async def toggle_fav(s: AsyncSession, uid: int, movie_id: int) -> bool:
    """True = qo'shildi, False = o'chirildi."""
    row = (await s.execute(select(Favorite).where(Favorite.user_id == uid, Favorite.movie_id == movie_id))).scalars().first()
    if row:
        await s.delete(row)
        await s.flush()
        return False
    s.add(Favorite(user_id=uid, movie_id=movie_id))
    await s.flush()
    return True


async def list_favs(s: AsyncSession, uid: int, page=0, per=8):
    base = select(Movie).join(Favorite, Favorite.movie_id == Movie.id).where(
        Favorite.user_id == uid, Movie.is_active.is_(True))
    total = (await s.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (await s.execute(base.order_by(Favorite.id.desc()).limit(per).offset(page * per))).scalars().all()
    return rows, total


# ---------- ko'rishlar ----------
async def log_view(s: AsyncSession, uid: int, movie: Movie = None, episode: Episode = None) -> None:
    now = utcnow()
    hist_cond = [WatchHistory.user_id == uid]
    view_cond = [MovieView.user_id == uid, MovieView.viewed_at > now - timedelta(minutes=30)]
    if movie is not None:
        hist_cond.append(WatchHistory.movie_id == movie.id)
        view_cond.append(MovieView.movie_id == movie.id)
    else:
        hist_cond.append(WatchHistory.episode_id == episode.id)
        view_cond.append(MovieView.episode_id == episode.id)
    h = (await s.execute(select(WatchHistory).where(*hist_cond))).scalars().first()
    if h:
        h.times += 1
        h.last_at = now
    else:
        s.add(WatchHistory(user_id=uid, movie_id=movie.id if movie else None,
                           episode_id=episode.id if episode else None))
    recent = (await s.execute(select(MovieView.id).where(*view_cond).limit(1))).first()
    if recent is None:  # faqat haqiqiy (takrorlanmagan) ko'rish sanaladi
        s.add(MovieView(user_id=uid, movie_id=movie.id if movie else None,
                        episode_id=episode.id if episode else None))
        if movie is not None:
            await s.execute(update(Movie).where(Movie.id == movie.id).values(views=Movie.views + 1))
        else:
            await s.execute(update(Episode).where(Episode.id == episode.id).values(views=Episode.views + 1))
            await s.execute(update(Series).where(Series.id == episode.series_id).values(views=Series.views + 1))
    await s.flush()


async def user_history(s: AsyncSession, uid: int, limit: int = 15):
    return (await s.execute(select(WatchHistory).where(WatchHistory.user_id == uid)
                            .order_by(WatchHistory.last_at.desc()).limit(limit))).scalars().all()


async def watched_episode_ids(s: AsyncSession, uid: int, series_id: int) -> set:
    q = (select(WatchHistory.episode_id).join(Episode, Episode.id == WatchHistory.episode_id)
         .where(WatchHistory.user_id == uid, Episode.series_id == series_id))
    return set((await s.execute(q)).scalars().all())


async def top_movies(s: AsyncSession, since=None, vip_only=False, limit=10):
    c = func.count(MovieView.id).label("c")
    q = (select(Movie, c).join(MovieView, MovieView.movie_id == Movie.id).where(Movie.is_active.is_(True)))
    if since:
        q = q.where(MovieView.viewed_at >= since)
    if vip_only:
        q = q.where(Movie.is_vip.is_(True))
    q = q.group_by(Movie.id).order_by(desc("c")).limit(limit)
    return (await s.execute(q)).all()


# ---------- tavsiyalar ----------
async def recommend(s: AsyncSession, uid: int, per: int = 5) -> dict:
    user = await s.get(User, uid)
    watched = select(WatchHistory.movie_id).where(WatchHistory.user_id == uid, WatchHistory.movie_id.isnot(None))
    base = [Movie.is_active.is_(True), Movie.id.not_in(watched)]
    out = {"pref": [], "hist": [], "rand": []}
    pref = [int(x) for x in (user.pref_genres or "").split(",") if x.strip().isdigit()] if user else []
    if pref:
        out["pref"] = (await s.execute(select(Movie).where(*base, Movie.genre_id.in_(pref))
                                       .order_by(func.coalesce(Movie.imdb, 0).desc(), Movie.views.desc()).limit(per))).scalars().all()
    top = (await s.execute(
        select(Movie.genre_id, func.count().label("c")).join(WatchHistory, WatchHistory.movie_id == Movie.id)
        .where(WatchHistory.user_id == uid, Movie.genre_id.isnot(None)).group_by(Movie.genre_id)
        .order_by(desc("c")).limit(3))).all()
    if top:
        gids = [g for g, _ in top]
        out["hist"] = (await s.execute(select(Movie).where(*base, Movie.genre_id.in_(gids))
                                       .order_by(Movie.views.desc()).limit(per))).scalars().all()
    taken = {m.id for m in out["pref"] + out["hist"]}
    rand_cond = list(base) + ([Movie.id.not_in(taken)] if taken else [])
    out["rand"] = (await s.execute(select(Movie).where(*rand_cond).order_by(func.random()).limit(per))).scalars().all()
    return out


# ---------- kanallar ----------
async def list_channels(s: AsyncSession, active_only: bool = False):
    q = select(MandatoryChannel).order_by(MandatoryChannel.id)
    if active_only:
        q = q.where(MandatoryChannel.is_active.is_(True))
    return (await s.execute(q)).scalars().all()


# ---------- promo ----------
async def redeem_promo(s: AsyncSession, uid: int, code: str):
    """(kun, None) yoki (None, xato) qaytaradi."""
    p = (await s.execute(select(PromoCode).where(PromoCode.code == norm_code(code)))).scalars().first()
    if not p or not p.is_active or p.used_count >= p.max_uses or (p.expires_at and p.expires_at < utcnow()):
        return None, "bad"
    if (await s.execute(select(PromoUsage.id).where(PromoUsage.promo_id == p.id, PromoUsage.user_id == uid))).first():
        return None, "used"
    s.add(PromoUsage(promo_id=p.id, user_id=uid))
    p.used_count += 1
    await grant_vip(s, uid, p.vip_days, "promo")
    return p.vip_days, None


# ---------- referal ----------
async def referral_stats(s: AsyncSession, uid: int):
    ok = (await s.execute(select(func.count()).select_from(Referral).where(
        Referral.referrer_id == uid, Referral.confirmed.is_(True)))).scalar_one()
    wait = (await s.execute(select(func.count()).select_from(Referral).where(
        Referral.referrer_id == uid, Referral.confirmed.is_(False)))).scalar_one()
    return ok, wait


# ---------- statistika ----------
async def count(s: AsyncSession, model, *cond) -> int:
    return (await s.execute(select(func.count()).select_from(model).where(*cond))).scalar_one()


async def admin_counts(s: AsyncSession) -> dict:
    now = utcnow()
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    vip_users = (await s.execute(select(func.count(func.distinct(VipSubscription.user_id))).where(
        VipSubscription.is_active.is_(True), VipSubscription.expires_at > now))).scalar_one()
    return {
        "users": await count(s, User),
        "new_today": await count(s, User, User.created_at >= day),
        "active": await count(s, User, User.last_active_at >= now - timedelta(days=7)),
        "movies": await count(s, Movie, Movie.is_active.is_(True)),
        "series": await count(s, Series, Series.is_active.is_(True)),
        "views": await count(s, MovieView),
        "vip": vip_users,
        "banned": await count(s, User, User.is_banned.is_(True)),
        "blocked": await count(s, User, User.is_active.is_(False)),
    }
