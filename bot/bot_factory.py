"""
Shared Bot + Dispatcher factory.

Used by both:
  - bot/main.py (long-polling mode, local dev)
  - api/webhook.py (webhook mode, Vercel)
"""
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from bot.config import settings, active_proxy_url
from bot.database.connection import init_db
from bot.middleware.whitelist import WhitelistMiddleware
from bot.handlers import start_router, survey_router, callbacks_router

logger = logging.getLogger(__name__)


def _build_session() -> AiohttpSession | None:
    """Build aiohttp session with proxy if available."""
    if active_proxy_url:
        return AiohttpSession(proxy=active_proxy_url)
    return None


def create_bot() -> Bot:
    """Create a Bot instance with the configured token and optional proxy."""
    session = _build_session()
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )


def create_dispatcher() -> Dispatcher:
    """Create and configure a Dispatcher with all handlers and middleware."""
    dp = Dispatcher()

    dp.message.middleware(WhitelistMiddleware())
    dp.callback_query.middleware(WhitelistMiddleware())

    dp.include_router(start_router)
    dp.include_router(survey_router)
    dp.include_router(callbacks_router)

    return dp
