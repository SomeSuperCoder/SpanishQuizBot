from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from bot.config import settings

class WhitelistMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user = event.from_user
        if not user or not user.username:
            if isinstance(event, Message):
                await event.answer("❌ No tienes permiso para usar este bot.")
            elif isinstance(event, CallbackQuery):
                await event.answer("❌ No tienes permiso.", show_alert=True)
            return None
        
        if user.username.lower() not in [u.lower() for u in settings.whitelist_usernames]:
            if isinstance(event, Message):
                await event.answer("❌ No estás en la lista de usuarios permitidos.")
            elif isinstance(event, CallbackQuery):
                await event.answer("❌ No estás en la lista de usuarios permitidos.", show_alert=True)
            return None
        
        return await handler(event, data)