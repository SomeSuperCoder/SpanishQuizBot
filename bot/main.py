import asyncio
import logging
import socket
from urllib.parse import urlparse

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from bot.config import settings
from bot.database.connection import init_db
from bot.middleware.whitelist import WhitelistMiddleware
from bot.handlers import start_router, survey_router, callbacks_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _check_proxy(url: str) -> bool:
    """Check if proxy is reachable via TCP connect."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        with socket.create_connection((host, port), timeout=2):
            return True
    except (OSError, TypeError):
        return False


async def _async_main():
    await init_db()
    logger.info("Database initialized")

    # Proxy detection — only used if reachable
    proxy_url = settings.proxy_url
    proxy_available = _check_proxy(proxy_url)
    if proxy_available:
        logger.info("🔌 Proxy detected at %s — using proxy for Telegram API", proxy_url)
        session = AiohttpSession(proxy=proxy_url)
    else:
        logger.warning("⚠️  Proxy at %s unreachable — connecting directly (will fail if Telegram is blocked)", proxy_url)
        session = None

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )
    dp = Dispatcher()

    dp.message.middleware(WhitelistMiddleware())
    dp.callback_query.middleware(WhitelistMiddleware())

    dp.include_router(start_router)
    dp.include_router(survey_router)
    dp.include_router(callbacks_router)

    logger.info("Bot starting...")
    await dp.start_polling(
        bot,
        allowed_updates=["message", "callback_query", "my_chat_member", "channel_post"],
    )


def main():
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()