"""Zaxira nusxa: JSON dump (har qanday DB) + SQLite faylining nusxasi."""
import io
import json
import logging
import os
import shutil
import sqlite3
import tempfile
from datetime import date, datetime

from aiogram import Bot
from aiogram.types import BufferedInputFile
from sqlalchemy import select

from config import settings
from database.db import session_maker
from database.models import Base
from database.queries import staff_ids

log = logging.getLogger(__name__)


def _ser(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


async def make_json_dump() -> bytes:
    out = {}
    async with session_maker() as s:
        for table in Base.metadata.sorted_tables:
            rows = (await s.execute(select(table))).mappings().all()
            out[table.name] = [{k: _ser(v) for k, v in r.items()} for r in rows]
    return json.dumps(out, ensure_ascii=False).encode()


def sqlite_copy() -> bytes | None:
    if not settings.is_sqlite:
        return None
    path = settings.database_url.split("///", 1)[-1]
    if not os.path.exists(path):
        return None
    tmp = tempfile.mktemp(suffix=".db")
    src = sqlite3.connect(path)
    dst = sqlite3.connect(tmp)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()
    data = open(tmp, "rb").read()
    os.remove(tmp)
    return data


async def send_backup(bot: Bot, chat_ids) -> None:
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M")
    dump = await make_json_dump()
    db_bytes = sqlite_copy()
    for cid in chat_ids:
        try:
            await bot.send_document(cid, BufferedInputFile(dump, f"kino_backup_{stamp}.json"), caption="💾 JSON zaxira")
            if db_bytes:
                await bot.send_document(cid, BufferedInputFile(db_bytes, f"kino_{stamp}.db"), caption="💾 SQLite zaxira")
        except Exception as e:
            log.warning("Backup %s ga yuborilmadi: %s", cid, e)


async def backup_to_owners(bot: Bot) -> None:
    async with session_maker() as s:
        ids = await staff_ids(s)
    owners = [i for i in ids if i in settings.admin_ids] or ids
    await send_backup(bot, owners)
