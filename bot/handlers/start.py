from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated
from aiogram.filters import Command, CommandStart, ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER
from aiogram.fsm.context import FSMContext

from bot.database.repository import UserRepository, BotConfigRepository
from bot.keyboards.inline import get_start_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command - register user and show welcome message."""
    await state.clear()

    user = await UserRepository.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or ""
    )

    welcome_text = (
        f"¡Hola {user['first_name']}! 👋 Soy el bot de encuestas para tu canal de español.\n\n"
        "¿Qué quieres hacer?"
    )

    await message.answer(welcome_text, reply_markup=get_start_keyboard())


@router.channel_post(Command("link"))
async def cmd_link(message: Message):
    """Handle /link command in a channel — relink the channel and auto-delete."""
    chat = message.chat
    if chat.type != "channel":
        await message.delete()
        return

    await BotConfigRepository.set("channel_id", str(chat.id))
    await BotConfigRepository.set("channel_title", chat.title or chat.username or str(chat.id))

    await message.delete()

    await message.answer(
        f"✅ Canal vinculado: {chat.title}\n\n"
        "Este canal ahora tiene encuestas automatizadas.\n\n"
        "🤖 Creado por @somesupercoder"
    )


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> IS_MEMBER))
async def handle_bot_added_to_chat(update: ChatMemberUpdated, state: FSMContext):
    """Handle bot being added to a channel — set as THE global channel."""
    chat = update.chat

    if chat.type == "channel":
        await BotConfigRepository.set("channel_id", str(chat.id))
        await BotConfigRepository.set("channel_title", chat.title or chat.username or str(chat.id))
        await update.answer(
            f"✅ Canal vinculado: {chat.title}\n\n"
            "Este canal ahora tiene encuestas automatizadas.\n\n"
            "🤖 Creado por @somesupercoder"
        )
    else:
        await update.answer(
            f"✅ Bot añadido al chat: {chat.title or chat.username}\n\n"
            "Este bot está diseñado para canales. Para crear encuestas, ábrelo en privado con /start."
        )


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_MEMBER >> IS_NOT_MEMBER))
async def handle_bot_removed_from_chat(update: ChatMemberUpdated, state: FSMContext):
    """Handle bot being removed from a channel — clear global channel."""
    chat = update.chat
    if chat.type == "channel":
        await BotConfigRepository.set("channel_id", "")
        await BotConfigRepository.set("channel_title", "")
        await update.answer(
            f"ℹ️ Canal desvinculado: {chat.title}"
        )
