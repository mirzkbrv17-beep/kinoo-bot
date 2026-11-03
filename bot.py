"""Kino bot — kirish nuqtasi: polling + Mini App web server (Render Web Service)."""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, MenuButtonWebApp, WebAppInfo
from aiohttp import web

from config import settings
from database.db import init_db, session_maker
from database.queries import expire_vips
from handlers import (admin, cartoons, favorites, genres, history, language, movies, news, recommendations,
                      referrals, search, series, settings as settings_h, start, statistics, subscription, support, vip)
from middlewares.subscription import SubscriptionMiddleware
from middlewares.user import UserMiddleware
from services.backup_service import backup_to_owners
from services.emoji_service import emoji_service
from services.notification_service import safe_send
from utils.texts import t
from webapp.api import make_app

log = logging.getLogger("kino_bot")


async def vip_watcher(bot: Bot):
    """Har soatda: muddati tugagan VIP'larni oddiy holatga qaytaradi va xabar beradi."""
    while True:
        try:
            async with session_maker() as s:
                expired = await expire_vips(s)
                users = {}
                if expired:
                    from database.models import User
                    from sqlalchemy import select
                    users = {u.id: u.language for u in (await s.execute(select(User).where(User.id.in_(expired)))).scalars()}
                await s.commit()
            for uid, lang in users.items():
                await safe_send(bot, uid, t(lang, "vip_expired"))
        except Exception:
            log.exception("vip_watcher")
        await asyncio.sleep(3600)


async def backup_loop(bot: Bot):
    hours = max(1, settings.backup_every_hours)
    await asyncio.sleep(300)
    while True:
        try:
            await backup_to_owners(bot)
        except Exception:
            log.exception("backup_loop")
        await asyncio.sleep(hours * 3600)


async def main():
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not settings.bot_token:
        sys.exit("BOT_TOKEN topilmadi (.env faylini tekshiring)")
    if not settings.admin_ids:
        log.warning("ADMIN_ID berilmagan — admin paneliga hech kim kira olmaydi!")

    await init_db()
    async with session_maker() as s:
        await emoji_service.load(s)

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # middleware tartibi: avval foydalanuvchi/sessiya, keyin majburiy obuna
    for obs in (dp.message, dp.callback_query):
        obs.outer_middleware(UserMiddleware())
        obs.outer_middleware(SubscriptionMiddleware())

    # routerlar tartibi muhim: start/cancel -> menyular -> admin -> (eng oxirida) kod/nom fallback
    for r in (start.router, language.router, referrals.router, search.router, favorites.router, vip.router,
              genres.router, series.router, cartoons.router, statistics.router, history.router,
              recommendations.router, news.router, support.router, settings_h.router, subscription.router,
              movies.router, admin.router, subscription.admin_router, settings_h.admin_router, search.fallback):
        dp.include_router(r)

    me = await bot.me()
    log.info("Bot ishga tushdi: @%s", me.username)
    await bot.delete_webhook(drop_pending_updates=False)
    await bot.set_my_commands([BotCommand(command="start", description="Bosh menyu"),
                               BotCommand(command="vip", description="VIP"),
                               BotCommand(command="help", description="Yordam"),
                               BotCommand(command="cancel", description="Bekor qilish")])
    if settings.webapp_url.startswith("https://"):
        try:
            await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="🎬 Kino", web_app=WebAppInfo(url=settings.webapp_url)))
        except Exception as e:
            log.warning("Menu button o'rnatilmadi: %s", e)

    runner = web.AppRunner(make_app(bot))
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", settings.port).start()
    log.info("Web server: 0.0.0.0:%s (Mini App: %s)", settings.port, settings.webapp_url or "WEBAPP_URL yo'q")

    bg = [asyncio.create_task(vip_watcher(bot)), asyncio.create_task(backup_loop(bot))]
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        for task in bg:
            task.cancel()
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
