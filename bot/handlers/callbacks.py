from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.keyboards.inline import get_start_keyboard

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
