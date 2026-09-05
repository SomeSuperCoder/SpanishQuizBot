"""
Vercel serverless entry point — webhook mode.

Handles Telegram updates via HTTP POST instead of long-polling.
Set WEBHOOK_URL env var to enable webhook mode.

Usage (Vercel):
  POST https://your-project.vercel.app/api/webhook
  Body: Telegram Update JSON

Usage (local test):
  uvicorn api.webhook:app --port 8000
  curl -X POST http://localhost:8000/api/webhook -H "Content-Type: application/json" -d '{}'
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from bot.bot_factory import create_bot, create_dispatcher
from bot.config import settings
from bot.database.connection import init_db

logger = logging.getLogger(__name__)

bot = None
dp = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize bot and dispatcher on cold start."""
    global bot, dp
    await init_db()
    bot = create_bot()
    dp = create_dispatcher()
    logger.info("Webhook bot initialized")
    yield
    logger.info("Webhook bot shutting down")


app = FastAPI(title="BotDeEncuestas Webhook", lifespan=lifespan)


@app.post("/api/webhook")
async def handle_webhook(request: Request):
    """Receive Telegram update and process it."""
    try:
        update = await request.json()
        from aiogram import types
        telegram_update = types.Update(**update)
        await dp.feed_update(bot, telegram_update)
        return JSONResponse({"status": "ok"})
    except Exception as e:
        logger.error("Webhook error: %s", e, exc_info=True)
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)


@app.get("/api/webhook")
async def webhook_health():
    """Health check endpoint."""
    return {"status": "running", "mode": "webhook"}


async def set_webhook():
    """Set the Telegram webhook URL. Call once after deployment."""
    webhook_url = settings.webhook_url
    if not webhook_url:
        raise ValueError("WEBHOOK_URL env var not set")
    await bot.set_webhook(
        url=f"{webhook_url}/api/webhook",
        allowed_updates=["message", "callback_query", "my_chat_member", "channel_post"],
    )
    logger.info("Webhook set to %s/api/webhook", webhook_url)
