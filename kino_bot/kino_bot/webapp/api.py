"""Mini App uchun aiohttp server: statik fayllar + xavfsiz API (initData HMAC tekshiruvi)."""
import io
import logging
from collections import OrderedDict
from pathlib import Path

from aiohttp import web
from sqlalchemy import select, func

from config import settings
from database.db import session_maker
from database.models import Episode, Genre, Movie, Season, Series, User
from database.queries import genre_label, is_fav, is_vip, role_of, toggle_fav
from services.subscription_service import channel_url, missing_channels
from utils.validators import sign_poster, validate_init_data

log = logging.getLogger(__name__)
BASE = Path(__file__).parent
PAGE = 18
_poster_cache: "OrderedDict[str, bytes]" = OrderedDict()


def api(handler):
    """initData, ban va majburiy obunani tekshiradigan dekorator."""
    async def wrapper(request: web.Request):
        tg = validate_init_data(request.headers.get("X-Init-Data", ""), settings.bot_token)
        if not tg:
            return web.json_response({"error": "auth"}, status=401)
        async with session_maker() as s:
            user = await s.get(User, tg["id"])
            if not user:
                return web.json_response({"error": "start_bot"}, status=403)
            if user.is_banned:
                return web.json_response({"error": "banned"}, status=403)
            role = await role_of(s, user.id)
            if not role:
                missing = await missing_channels(request.app["bot"], s, user.id)
                if missing:
                    return web.json_response({"error": "subscribe", "channels": [
                        {"title": c.title, "url": channel_url(c)} for c in missing]}, status=403)
            vip = bool(role) or await is_vip(s, user.id)
            resp = await handler(request, s, user, vip)
            await s.commit()
            return resp
    return wrapper


def _poster(kind: str, obj) -> str | None:
    if not obj.poster_file_id:
        return None
    return f"/poster/{kind}/{obj.id}?s={sign_poster(kind, obj.id, settings.bot_token)}"


def _item(kind: str, o, vip: bool) -> dict:
    return {"type": kind, "id": o.id, "code": o.code, "title": o.title, "year": o.year,
            "imdb": getattr(o, "imdb", None), "vip": o.is_vip, "locked": o.is_vip and not vip,
            "poster": _poster(kind, o)}


@api
async def me(request, s, user, vip):
    bot_me = await request.app["bot"].me()
    return web.json_response({"bot": bot_me.username, "vip": vip, "lang": user.language, "name": user.full_name})


@api
async def genres(request, s, user, vip):
    rows = (await s.execute(select(Genre).order_by(Genre.id))).scalars().all()
    return web.json_response([{"id": g.id, "name": genre_label(g, user.language)} for g in rows])


@api
async def catalog(request, s, user, vip):
    q = request.query
    kind = q.get("kind", "all")
    page = max(0, int(q.get("page", "0") or 0)) if (q.get("page", "0") or "0").isdigit() else 0
    text = (q.get("q") or "").strip().lower()[:60]
    genre = int(q["genre"]) if (q.get("genre") or "").isdigit() else None
    if kind == "series":
        cond = [Series.is_active.is_(True)]
        if text:
            cond.append(Series.search_key.like(f"%{text}%"))
        if genre:
            cond.append(Series.genre_id == genre)
        rows = (await s.execute(select(Series).where(*cond).order_by(Series.id.desc()).limit(PAGE + 1).offset(page * PAGE))).scalars().all()
        items = [_item("series", o, vip) for o in rows[:PAGE]]
    else:
        cond = [Movie.is_active.is_(True)]
        if kind == "cartoon":
            cond.append(Movie.kind == "cartoon")
        elif kind == "movie":
            cond.append(Movie.kind == "movie")
        elif kind == "vip":
            cond.append(Movie.is_vip.is_(True))
        if text:
            cond.append(Movie.search_key.like(f"%{text}%"))
        if genre:
            cond.append(Movie.genre_id == genre)
        rows = (await s.execute(select(Movie).where(*cond).order_by(Movie.id.desc()).limit(PAGE + 1).offset(page * PAGE))).scalars().all()
        items = [_item("movie", o, vip) for o in rows[:PAGE]]
    return web.json_response({"items": items, "more": len(rows) > PAGE})


@api
async def item(request, s, user, vip):
    kind, oid = request.match_info["kind"], int(request.match_info["id"])
    model = Series if kind == "series" else Movie
    o = await s.get(model, oid)
    if not o or not o.is_active:
        return web.json_response({"error": "not_found"}, status=404)
    g = await s.get(Genre, o.genre_id) if o.genre_id else None
    data = _item(kind, o, vip) | {
        "original": o.original_title, "country": o.country, "genre": genre_label(g, user.language) if g else None,
        "description": o.description, "trailer": o.trailer_url, "views": o.views,
        "duration": getattr(o, "duration", None), "age": getattr(o, "age_limit", None), "fav": False}
    if kind == "movie":
        data["fav"] = await is_fav(s, user.id, o.id)
    else:
        data["seasons"] = (await s.execute(select(func.count()).select_from(Season).where(Season.series_id == o.id))).scalar_one()
        data["episodes"] = (await s.execute(select(func.count()).select_from(Episode).where(Episode.series_id == o.id))).scalar_one()
    return web.json_response(data)


@api
async def fav(request, s, user, vip):
    oid = int(request.match_info["id"])
    if not await s.get(Movie, oid):
        return web.json_response({"error": "not_found"}, status=404)
    return web.json_response({"fav": await toggle_fav(s, user.id, oid)})


async def poster(request: web.Request):
    kind, oid = request.match_info["kind"], int(request.match_info["id"])
    if request.query.get("s") != sign_poster(kind, oid, settings.bot_token):
        raise web.HTTPForbidden()
    async with session_maker() as s:
        o = await s.get(Series if kind == "series" else Movie, oid)
        file_id = o.poster_file_id if o else None
    if not file_id:
        raise web.HTTPNotFound()
    data = _poster_cache.get(file_id)
    if data is None:
        bot = request.app["bot"]
        f = await bot.get_file(file_id)
        buf = io.BytesIO()
        await bot.download_file(f.file_path, buf)
        data = buf.getvalue()
        _poster_cache[file_id] = data
        while len(_poster_cache) > 200:
            _poster_cache.popitem(last=False)
    return web.Response(body=data, content_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})


async def index(request):
    return web.FileResponse(BASE / "index.html")


async def css(request):
    return web.FileResponse(BASE / "style.css")


async def js(request):
    return web.FileResponse(BASE / "app.js")


async def health(request):
    return web.Response(text="ok")


def make_app(bot) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app.router.add_get("/", index)
    app.router.add_get("/health", health)
    app.router.add_get("/style.css", css)
    app.router.add_get("/app.js", js)
    app.router.add_get("/api/me", me)
    app.router.add_get("/api/genres", genres)
    app.router.add_get("/api/catalog", catalog)
    app.router.add_get("/api/item/{kind:movie|series}/{id:\\d+}", item)
    app.router.add_post("/api/fav/{id:\\d+}", fav)
    app.router.add_get("/poster/{kind:movie|series}/{id:\\d+}", poster)
    return app
