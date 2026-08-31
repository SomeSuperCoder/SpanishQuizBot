from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Crear encuesta", callback_data="create_survey")]
    ])

def get_survey_review_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Perfecto!", callback_data="survey_approve"),
            InlineKeyboardButton(text="✏️ Mejorar", callback_data="survey_improve")
        ]
    ])

def get_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 Publicar", callback_data="survey_publish"),
            InlineKeyboardButton(text="❌ Cancelar", callback_data="survey_cancel")
        ]
    ])

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="survey_cancel")]
    ])