import asyncio
import logging
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiogram_dialog import setup_dialogs
from aiohttp import web
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from dialogs import include_dialogs
from middlewares.db import DbSessionMiddleware
from handlers import setup_routers
from config import settings
# from middlewares.throttling import ThrottlingMiddleware

from redis.asyncio.client import Redis

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%d.%m.%Y %H:%M:%S',
)

rotating_handler = RotatingFileHandler(
    'logs/bot.log',
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding='utf-8'
)
rotating_handler.setLevel(logging.INFO)
rotating_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
))


async def main():
    logger = logging.getLogger()
    logger.addHandler(rotating_handler)

    module_logger = logging.getLogger(__name__)

    session = AiohttpSession()

    bot_settings = {"session": session, "default": DefaultBotProperties(parse_mode="HTML")}

    engine = create_async_engine(
        settings.POSTGRES_DSN,
        future=True,
        echo=False,
        pool_size=15,
        max_overflow=10,
        pool_timeout=30,
        pool_pre_ping=True,
    )

    db_pool = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    bot = Bot(token=settings.BOT_TOKEN, **bot_settings)

    if settings.FSM_STORAGE == "memory":
        dp = Dispatcher(storage=MemoryStorage())
    else:
        dp = Dispatcher(storage=RedisStorage(
            redis=Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, password=settings.REDIS_PASSWORD),
            key_builder=DefaultKeyBuilder(with_destiny=True)))

    dp.message.middleware(DbSessionMiddleware(db_pool))
    # dp.message.middleware(ThrottlingMiddleware(1.0))

    dp.callback_query.middleware(DbSessionMiddleware(db_pool))
    # dp.callback_query.middleware(ThrottlingMiddleware(1.0))

    dp.update.outer_middleware(DbSessionMiddleware(db_pool))

    routers = setup_routers()
    dp.include_router(routers)

    dp.include_routers(*include_dialogs())

    setup_dialogs(dp)

    try:
        module_logger.info("Trying to start bot...")
        if settings.WEBHOOK_DOMAIN:
            await bot.set_webhook(
                url=settings.WEBHOOK_DOMAIN + settings.WEBHOOK_PATH,
                drop_pending_updates=True,
                allowed_updates=dp.resolve_used_update_types()
            )

            app = web.Application()

            SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=settings.WEBHOOK_PATH)

            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, host=settings.WEBHOOK_HOST, port=settings.WEBHOOK_PORT)
            await site.start()

            print(f"🌐 Webhook listening: {settings.WEBHOOK_DOMAIN + settings.WEBHOOK_PATH}")

            await asyncio.Event().wait()
        else:
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        module_logger.info(f"Failed to startup bot: {e}")
    finally:
        module_logger.info("Bot stopped")
        await bot.session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
