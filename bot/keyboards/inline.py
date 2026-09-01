from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Crear encuesta", callback_data="create_survey")]
    ])


def get_quantity_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="2", callback_data="quantity:2"),
            InlineKeyboardButton(text="3", callback_data="quantity:3"),
            InlineKeyboardButton(text="4", callback_data="quantity:4"),
            InlineKeyboardButton(text="5", callback_data="quantity:5"),
        ]
    ])


def get_level_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="A1", callback_data="level:A1"),
            InlineKeyboardButton(text="A2", callback_data="level:A2"),
            InlineKeyboardButton(text="B1", callback_data="level:B1"),
        ],
        [
            InlineKeyboardButton(text="B2", callback_data="level:B2"),
            InlineKeyboardButton(text="C1", callback_data="level:C1"),
            InlineKeyboardButton(text="C2", callback_data="level:C2"),
        ],
    ])


def get_review_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Editar", callback_data="survey_edit"),
            InlineKeyboardButton(text="🚀 Publicar todos", callback_data="survey_publish"),
        ]
    ])


def get_edit_selector_keyboard(count: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=str(i), callback_data=f"edit_select:{i}")]
        for i in range(1, count + 1)
    ]
    buttons.append([InlineKeyboardButton(text="❌ Cancelar", callback_data="survey_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_edit_done_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Editar otro", callback_data="survey_edit"),
            InlineKeyboardButton(text="🚀 Publicar todos", callback_data="survey_publish"),
        ]
    ])


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="survey_cancel")]
    ])
