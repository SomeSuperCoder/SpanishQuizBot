from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# ── categories ──────────────────────────────────────────────

CATEGORIES = [
    {"key": "fill_blank", "emoji": "📝", "label": "Cumplimentar espacios en blanco"},
    {"key": "meaning", "emoji": "📖", "label": "Significado de expresión"},
    {"key": "synonyms", "emoji": "🔄", "label": "Sinónimos / antónimos"},
    {"key": "slang", "emoji": "🎭", "label": "EDUCADO / Slang"},
]

COUNTER_MAX = 3


# ── reusable counter component ──────────────────────────────


def get_category_counter_keyboard(
    counts: dict[str, int],
    confirm_callback: str = "counter:ok",
    show_skip: bool = False,
    skip_callback: str = "counter:skip",
) -> InlineKeyboardMarkup:
    """
    4-category counter keyboard.
    counts = {"fill_blank": 2, "meaning": 0, ...}
    When total == 0 and show_skip: shows "⏭️ Saltar" button.
    When total >= 1: shows "✅ Listo" button in same position.
    """
    rows = []
    for cat in CATEGORIES:
        key = cat["key"]
        emoji = cat["emoji"]
        value = counts.get(key, 0)
        rows.append([
            InlineKeyboardButton(text="◀️", callback_data=f"counter:{key}:-"),
            InlineKeyboardButton(text=f"{emoji} {value}", callback_data=f"counter:{key}:show"),
            InlineKeyboardButton(text="▶️", callback_data=f"counter:{key}:+"),
        ])

    total = sum(counts.get(c["key"], 0) for c in CATEGORIES)
    if total >= 1:
        rows.append([
            InlineKeyboardButton(text="✅ Listo", callback_data=confirm_callback)
        ])
    elif show_skip:
        rows.append([
            InlineKeyboardButton(text="⏭️ Saltar", callback_data=skip_callback)
        ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── bot keyboards ───────────────────────────────────────────


def get_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Crear encuesta", callback_data="create_survey")]
    ])


def get_topic_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Escribir tema manualmente", callback_data="topic:manual")],
        [InlineKeyboardButton(text="🔄 Reenviar post para autodetectar", callback_data="topic:auto")],
    ])


def get_category_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Elegir manualmente", callback_data="category_mode:manual")],
        [InlineKeyboardButton(text="🤖 Autodeterminar", callback_data="category_mode:auto")],
    ])


def get_category_auto_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Aceptar", callback_data="category_mode:accept")],
        [InlineKeyboardButton(text="✏️ Elegir manualmente", callback_data="category_mode:manual")],
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
        ],
        [
            InlineKeyboardButton(text="⏰ Programar", callback_data="survey_schedule"),
        ],
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
        ],
        [
            InlineKeyboardButton(text="⏰ Programar", callback_data="survey_schedule"),
        ],
    ])


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancelar", callback_data="survey_cancel")]
    ])


def get_post_accumulation_keyboard(post_count: int) -> InlineKeyboardMarkup:
    """Keyboard shown after forwarding a post — add more or generate."""
    singular = post_count == 1
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Agregar otro post", callback_data="post_add_more")],
        [InlineKeyboardButton(
            text=f"🚀 Generar desde {'este' if singular else 'estos'}",
            callback_data="post_generate",
        )],
    ])
