from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# ── reusable counter component ──────────────────────────────


def get_counter_keyboard(
    counters: dict[str, tuple[str, int]],
    min_total: int = 1,
    max_value: int = 3,
    confirm_callback: str = "counter:ok",
) -> InlineKeyboardMarkup:
    """
    Reusable counter keyboard.

    counters = {
        "key": ("Label shown to user", current_value),
        ...
    }
    min_total: minimum combined value across all counters to enable confirm
    max_value: maximum value per counter (inclusive)
    """
    rows = []
    for key, (label, value) in counters.items():
        rows.append([
            InlineKeyboardButton(
                text="◀️",
                callback_data=f"counter:{key}:-",
            ),
            InlineKeyboardButton(
                text=f"{label} — {value}",
                callback_data=f"counter:{key}:show",
            ),
            InlineKeyboardButton(
                text="▶️",
                callback_data=f"counter:{key}:+",
            ),
        ])

    total = sum(v for _, v in counters.values())
    if total >= min_total:
        rows.append([
            InlineKeyboardButton(
                text="✅ Listo",
                callback_data=confirm_callback,
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── bot keyboards ───────────────────────────────────────────


def get_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Crear encuesta", callback_data="create_survey")]
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


def get_dialect_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇪🇸 Castellano", callback_data="dialect:Castellano")],
        [InlineKeyboardButton(text="🇲🇽 Mexicano", callback_data="dialect:Mexicano")],
        [InlineKeyboardButton(text="🇦🇷 Argentino", callback_data="dialect:Argentino")],
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
