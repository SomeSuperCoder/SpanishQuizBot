from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.database.repository import BotConfigRepository
from bot.keyboards.inline import get_start_keyboard, get_channel_menu_keyboard

router = Router()


@router.callback_query(F.data.startswith("survey_"))
async def handle_survey_callbacks(callback_query: CallbackQuery, state: FSMContext):
    """
    Shared handler for survey-related callbacks.
    Handles edge cases: expired callbacks, invalid states.
    """
    current_state = await state.get_state()
    
    # If no state, callback is expired or invalid
    if current_state is None:
        await callback_query.answer(
            text="⚠️ Esta sesión ha expirado. Por favor, inicia de nuevo.",
            show_alert=True
        )
        
        await callback_query.message.edit_text(
            "⚠️ La sesión ha expirado.\n\n¿Qué quieres hacer?",
            reply_markup=get_start_keyboard()
        )
        return
    
    # Answer callback to remove loading indicator
    await callback_query.answer()


@router.callback_query(F.data == "create_survey")
async def handle_create_survey_fallback(callback_query: CallbackQuery, state: FSMContext):
    """
    Fallback handler for create_survey if state is not set.
    This shouldn't happen if start.py handles it correctly.
    """
    current_state = await state.get_state()
    
    if current_state is not None:
        await callback_query.answer(
            text="⚠️ Ya hay un proceso en curso. Por favor, termínalo primero.",
            show_alert=True
        )
        return
    
    await callback_query.answer()


@router.callback_query(F.data == "view_channel")
async def handle_view_channel(callback_query: CallbackQuery):
    """Show linked channel info or instructions to link one."""
    channel_id = await BotConfigRepository.get_channel_id()
    channel_title = await BotConfigRepository.get_channel_title()

    if channel_id and channel_title:
        text = (
            f"📺 Canal vinculado: {channel_title}\n\n"
            f"ID: {channel_id}"
        )
    else:
        text = (
            "ℹ️ No hay ningún canal vinculado.\n\n"
            "Para vincular un canal, ábreme en el canal con /link"
        )

    await callback_query.answer()
    await callback_query.message.edit_text(
        text,
        reply_markup=get_channel_menu_keyboard(has_channel=bool(channel_id and channel_title)),
    )


@router.callback_query(F.data == "unlink_channel")
async def handle_unlink_channel(callback_query: CallbackQuery):
    """Clear linked channel and confirm."""
    await BotConfigRepository.set("channel_id", "")
    await BotConfigRepository.set("channel_title", "")

    await callback_query.answer()
    await callback_query.message.edit_text(
        "✅ Canal desvinculado correctamente.",
        reply_markup=get_start_keyboard(),
    )


@router.callback_query(F.data == "back_to_start")
async def handle_back_to_start(callback_query: CallbackQuery):
    """Return to the start menu."""
    welcome_text = "¿Qué quieres hacer?"

    await callback_query.answer()
    await callback_query.message.edit_text(
        welcome_text,
        reply_markup=get_start_keyboard(),
    )
