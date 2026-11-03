"""Engine, sessiya va boshlang'ich ma'lumotlar (seed)."""
import logging
import os

from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from config import settings
from database.models import Base, BotSetting, CustomEmoji, Genre
from utils.texts import MENU

log = logging.getLogger(__name__)

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
session_maker = async_sessionmaker(engine, expire_on_commit=False)

if settings.is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.close()

DEFAULT_SETTINGS = {
    "forced_sub": "1", "protect_content": "0", "next_code": "101",
    "vip_plans": "30:100,90:250,365:800",  # kun:Stars
    "ref_every": "5", "ref_days": "3", "ref_daily_limit": "30",
    "news_text": "", "news_url": "",
}
DEFAULT_GENRES = [("Jangari", "Боевик"), ("Komediya", "Комедия"), ("Drama", "Драма"), ("Qo'rqinchli", "Ужасы"),
                  ("Fantastika", "Фантастика"), ("Melodrama", "Мелодрама"), ("Triller", "Триллер"),
                  ("Detektiv", "Детектив"), ("Sarguzasht", "Приключения"), ("Hujjatli", "Документальный")]


async def init_db() -> None:
    if settings.is_sqlite:
        path = settings.database_url.split("///", 1)[-1]
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_maker() as s:
        for k, v in DEFAULT_SETTINGS.items():
            if await s.get(BotSetting, k) is None:
                s.add(BotSetting(key=k, value=v))
        for key, fb in MENU:
            if await s.get(CustomEmoji, key) is None:
                s.add(CustomEmoji(key=key, emoji_id=None, fallback=fb))
        if (await s.execute(select(Genre.id).limit(1))).first() is None:
            for uz, ru in DEFAULT_GENRES:
                s.add(Genre(name_uz=uz, name_ru=ru))
        await s.commit()
    log.info("Database tayyor: %s", settings.database_url.split("@")[-1])
