import json
import logging
import re

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.methods.send_rich_message_draft import SendRichMessageDraft
from aiogram.methods.send_rich_message import SendRichMessage
from aiogram.types import (
    InputRichMessage, InputRichBlockThinking, InputRichBlockParagraph,
    RichTextCustomEmoji,
)

from bot.database.repository import UserRepository, SurveyRepository, BotConfigRepository
from bot.keyboards.inline import (
    get_start_keyboard,
    get_topic_mode_keyboard,
    get_category_mode_keyboard,
    get_category_auto_confirm_keyboard,
    get_category_counter_keyboard,
    CATEGORIES,
    get_level_keyboard,
    get_dialect_keyboard,
    get_review_keyboard,
    get_edit_selector_keyboard,
    get_edit_done_keyboard,
    get_cancel_keyboard,
)
from bot.states.survey import SurveyCreation
from bot.services.ai_service import AIService, AIServiceError, Quiz, AutoDetected

router = Router()
ai = AIService()

# ── Thinking draft helpers (AIActions emoji pack) ───────────

_EMOJI_GENERATE = "5534951812081123354"
_EMOJI_REVIEW = "5537581341383589905"
_EMOJI_FIX = "5537581341383589905"
_EMOJI_ANALYZE = "5537581341383589905"  # reuse fix emoji for analysis

# Level emoji (1-6 → A1-C2)
_LEVEL_EMOJI = {
    "A1": ("5217450769950737137", "1️⃣"),
    "A2": ("5215574152710229930", "2️⃣"),
    "B1": ("5215514710362855140", "3️⃣"),
    "B2": ("5215227312626241463", "4️⃣"),
    "C1": ("5217601248424925577", "5️⃣"),
    "C2": ("5215366641365322506", "6️⃣"),
}


def _ce(custom_id: str, fallback: str) -> RichTextCustomEmoji:
    """Create a custom emoji rich text entity."""
    return RichTextCustomEmoji(custom_emoji_id=custom_id, alternative_text=fallback)


async def _show_thinking(bot, chat_id: int, draft_id: int, emoji_id: str, fallback: str, text: str) -> None:
    """Send a thinking draft to show the bot is working."""
    try:
        await bot(SendRichMessageDraft(
            chat_id=chat_id,
            draft_id=draft_id,
            rich_message=InputRichMessage(
                blocks=[InputRichBlockThinking(text=[_ce(emoji_id, fallback), text])]
            ),
        ))
    except Exception:
        pass  # private chat only; fail silently


async def _dismiss_thinking(bot, chat_id: int, draft_id: int) -> None:
    """Dismiss the thinking draft by replacing it with a temporary message, then deleting it."""
    try:
        msg = await bot(SendRichMessage(
            chat_id=chat_id,
            draft_id=draft_id,
            rich_message=InputRichMessage(
                blocks=[InputRichBlockParagraph(text=" ")]
            ),
        ))
        await bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
    except Exception:
        pass  # private chat only; fail silently
logger = logging.getLogger(__name__)

COUNTER_MAX = 3


# ── helpers ─────────────────────────────────────────────────


def _prefixed_question(quiz: Quiz, level: str) -> tuple[str, list]:
    """Add level emoji prefix to quiz question.

    Returns (question_text, entities) for use with question_entities.
    """
    emoji_id, fallback = _LEVEL_EMOJI.get(level, ("0", "❓"))
    # Use fallback char as the text representation, entity tells Telegram it's custom emoji
    text = f"{fallback} {quiz.question}"
    entity = {"type": "custom_emoji", "offset": 0, "length": len(fallback), "custom_emoji_id": emoji_id}
    return text, [entity]


async def _send_quiz_preview(target, quiz: Quiz, level: str, bot) -> None:
    """Send a real Telegram quiz poll with level emoji prefix."""
    # Telegram allows max 10 options per poll
    options = quiz.options[:10]
    correct = min(quiz.correct_index, len(options) - 1)
    question, entities = _prefixed_question(quiz, level)
    await bot.send_poll(
        chat_id=target,
        question=question,
        question_entities=entities,
        options=[{"text": opt} for opt in options],
        type="quiz",
        correct_option_id=correct,
        is_anonymous=False,
    )


def _build_summary(quizzes: list[Quiz], level: str) -> str:
    """Build the [n] summary shown in the review message."""
    lines = []
    for q in quizzes:
        emoji_id, fallback = _LEVEL_EMOJI.get(level, ("0", "❓"))
        lines.append(f"[{q.id}] {fallback} {q.question}")
    return "\n".join(lines)


# ── schedule time parser ────────────────────────────────────


def parse_interval(text: str) -> int | None:
    """
    Parse a time interval string into seconds.

    Accepted formats:
      "30s"  → 30 seconds
      "5m"   → 300 seconds
      "2h"   → 7200 seconds
      "1h30m" → 5400 seconds
      "2h15m30s" → 8130 seconds
      "90"   → 90 seconds (bare number = seconds)

    Returns None if the format is invalid.
    """
    text = text.strip().lower()
    if not text:
        return None

    # Bare number → seconds
    if text.isdigit():
        secs = int(text)
        return secs if secs > 0 else None

    # Compound: e.g. 1h30m45s
    pattern = r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$"
    match = re.fullmatch(pattern, text)
    if not match:
        return None

    h, m, s = match.groups()
    total = 0
    if h:
        total += int(h) * 3600
    if m:
        total += int(m) * 60
    if s:
        total += int(s)

    return total if total > 0 else None


def format_interval(seconds: int) -> str:
    """Human-readable interval: 30s, 5m, 1h30m."""
    parts = []
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    if s:
        parts.append(f"{s}s")
    return "".join(parts) if parts else "0s"


CATEGORY_LEGEND = (
    "📝 Espacios en blanco\n"
    "📖 Significado de expresión\n"
    "🔄 Sinónimos / antónimos\n"
    "🎭 EDUCADO / Slang"
)


def _get_counter_es_text(data: dict) -> str:
    """Build the Spanish category counter display text."""
    topic = data.get("topic", "")
    counts = data.get("counts_es", {})
    total = sum(counts.values())
    return (
        f"📊 Tema: *{topic}*\n\n"
        f"🇪🇸 *Categorías en español* (total: *{total}*)\n\n"
        f"Usa las flechas para ajustar:\n\n"
        f"{CATEGORY_LEGEND}"
    )


def _get_counter_ru_text(data: dict) -> str:
    """Build the Russian category counter display text."""
    topic = data.get("topic", "")
    counts_es = data.get("counts_es", {})
    total_es = sum(counts_es.values())
    counts_ru = data.get("counts_ru", {})
    total_ru = sum(counts_ru.values())
    return (
        f"📊 Tema: *{topic}*\n"
        f"📝 Total español: *{total_es}*\n\n"
        f"🇷🇺 *Categorías en ruso* (total: *{total_ru}*)\n\n"
        f"Usa las flechas para ajustar:\n\n"
        f"{CATEGORY_LEGEND}"
    )


def _get_counts(data: dict, lang: str) -> dict[str, int]:
    """Get category counts from FSM data."""
    return data.get(f"counts_{lang}", {c["key"]: 0 for c in CATEGORIES})


def _get_total(data: dict, lang: str) -> int:
    """Get total quizzes for a language."""
    return sum(_get_counts(data, lang).values())


async def _generate_and_preview(callback_query: CallbackQuery, state: FSMContext) -> None:
    """Shared generation logic — called from dialect handler and auto-detect path."""
    data = await state.get_data()
    topic = data["topic"]
    examples = data.get("examples", [])
    counts_es = _get_counts(data, "es")
    counts_ru = _get_counts(data, "ru")
    total_es = sum(counts_es.values())
    total_ru = sum(counts_ru.values())
    level = data["level"]
    dialect = data["dialect"]
    total = total_es + total_ru
    chat_id = callback_query.message.chat.id
    bot = callback_query.bot

    # ── Stage 1: Initial generation ─────────────────────────
    await callback_query.answer()
    await _show_thinking(bot, chat_id, 1, _EMOJI_GENERATE, "🔄",
        f" Generando {total_es} quizzes en español y {total_ru} en ruso...")

    try:
        quizzes = await ai.generate_quizzes(
            topic, counts_es, counts_ru, level, dialect, examples=examples
        )
    except AIServiceError as e:
        await _dismiss_thinking(bot, chat_id, 1)
        await callback_query.message.edit_text(
            f"❌ {e}\n\nIntenta de nuevo.",
            reply_markup=get_start_keyboard(),
        )
        await state.clear()
        return
    except Exception:
        logger.exception("Unexpected error generating quizzes")
        await _dismiss_thinking(bot, chat_id, 1)
        await callback_query.message.edit_text(
            "❌ Error inesperado al generar los quizzes. Intenta de nuevo.",
            reply_markup=get_start_keyboard(),
        )
        await state.clear()
        return

    # ── Stage 2: AI self-review ─────────────────────────────
    await _show_thinking(bot, chat_id, 1, _EMOJI_REVIEW, "🔍",
        f" Revisión — verificando {total} quizzes")

    try:
        issues = await ai.review_quizzes(quizzes, topic, level, dialect)
    except Exception:
        logger.exception("AI review failed")
        issues = []

    # ── Stage 3: Fix issues ─────────────────────────────────
    fixed_count = 0
    if issues:
        await _show_thinking(bot, chat_id, 1, _EMOJI_FIX, "🔧",
            f" Corrección — {len(issues)} problema(s) detectado(s)")

        history = [q.to_dict() for q in quizzes]
        for issue in issues:
            quiz_id = issue.get("id")
            fix_desc = issue.get("issue", "problema detectado")
            fix_data = issue.get("fix")

            if not quiz_id or not fix_data:
                continue

            feedback = f"Corregir: {fix_desc}. Usar esta versión: {json.dumps(fix_data, ensure_ascii=False)}"

            try:
                edited = await ai.edit_quiz(topic, history, quiz_id, feedback)
                for i, q in enumerate(quizzes):
                    if q.id == quiz_id:
                        quizzes[i] = edited
                        break
                history = [q.to_dict() for q in quizzes]
                fixed_count += 1
            except Exception:
                logger.exception("Failed to fix quiz %d", quiz_id)

    # Serialize quizzes for FSM storage
    quizzes_data = [q.to_dict() for q in quizzes]
    await state.update_data(quizzes=quizzes_data)
    await state.set_state(SurveyCreation.reviewing)

    # Dismiss the thinking draft
    await _dismiss_thinking(bot, chat_id, 1)

    # Delete the original button message
    try:
        await callback_query.message.delete()
    except Exception:
        pass

    # Send all polls as preview
    for quiz in quizzes:
        await _send_quiz_preview(chat_id, quiz, level, callback_query.bot)

    # Summary + action buttons
    summary = _build_summary(quizzes, level)
    review_note = f"\n✅ Auto-revisión: {fixed_count} corrección(es)" if fixed_count else ""
    await callback_query.bot.send_message(
        chat_id,
        f"👆 {len(quizzes)} quizzes nivel {level} — {dialect} (del más fácil al más difícil):\n\n"
        f"{summary}{review_note}\n\n¿Qué quieres hacer?",
        reply_markup=get_review_keyboard(),
    )


# ── /start & create ─────────────────────────────────────────


@router.callback_query(F.data == "create_survey")
async def handle_create_survey(callback_query: CallbackQuery, state: FSMContext):
    """User clicked 'Crear encuesta' — ask for topic mode."""
    await state.set_state(SurveyCreation.waiting_topic_mode)
    await callback_query.message.edit_text(
        "📝 *Crear encuesta*\n\n"
        "Elige cómo quieres definir el tema de tus quizzes:",
        reply_markup=get_topic_mode_keyboard(),
        parse_mode="Markdown",
    )
    await callback_query.answer()


# ── topic mode: manual or auto-detect ───────────────────────


@router.callback_query(SurveyCreation.waiting_topic_mode, F.data == "topic:manual")
async def handle_topic_manual_mode(callback_query: CallbackQuery, state: FSMContext):
    """User chose manual input — wait for text."""
    await state.set_state(SurveyCreation.waiting_topic_manual)
    await callback_query.message.edit_text(
        "✏️ Escribe el tema:\n"
        "(Ej: Imperfecto de subjuntivo, Ser vs Estar, Pretérito indefinido...)"
    )
    await callback_query.answer()


@router.callback_query(SurveyCreation.waiting_topic_mode, F.data == "topic:auto")
async def handle_topic_auto_mode(callback_query: CallbackQuery, state: FSMContext):
    """User chose auto-detect — wait for forwarded message."""
    await state.set_state(SurveyCreation.waiting_topic_forward)
    await callback_query.message.edit_text(
        "🔄 Reenvía un mensaje de un canal de español.\n"
        "Yo extraeré el tema automáticamente."
    )
    await callback_query.answer()


# ── topic: manual input ─────────────────────────────────────


@router.message(SurveyCreation.waiting_topic_manual)
async def handle_topic_manual(message: Message, state: FSMContext):
    """Receive manual topic → show Spanish category counters."""
    topic = (message.text or "").strip()
    if not topic:
        return

    # Two SEPARATE dicts — never share the same object
    counts_es = {c["key"]: 0 for c in CATEGORIES}
    counts_ru = {c["key"]: 0 for c in CATEGORIES}
    await state.update_data(
        topic=topic, examples=[],
        counts_es=counts_es, counts_ru=counts_ru
    )
    await state.set_state(SurveyCreation.waiting_counter_es)

    data = await state.get_data()
    await message.answer(
        _get_counter_es_text(data),
        reply_markup=get_category_counter_keyboard(_get_counts(data, "es"), show_skip=True),
        parse_mode="Markdown",
    )


# ── topic: forwarded message ────────────────────────────────


@router.message(SurveyCreation.waiting_topic_forward)
async def handle_topic_forward(message: Message, state: FSMContext):
    """Receive forwarded message → extract everything via AI → show counters."""
    if message.forward_origin is None:
        await message.answer(
            "⚠️ Necesito un mensaje reenviado.\n"
            "Haz forward de un post de un canal de español."
        )
        return

    text = message.text or message.caption or ""
    if not text.strip():
        await message.answer(
            "⚠️ El mensaje reenviado no tiene texto.\n"
            "Reenvía un mensaje que contenga texto sobre español."
        )
        return

    await _show_thinking(message.bot, message.chat.id, 2, _EMOJI_ANALYZE, "🔍",
        " Analizando mensaje reenviado...")
    try:
        detected = await ai.determine_topic(text)
    except Exception:
        logger.exception("Failed to determine topic from forwarded message")
        await _dismiss_thinking(message.bot, message.chat.id, 2)
        await message.answer(
            "❌ No pude determinar el tema. Intenta escribirlo manualmente."
        )
        return

    if detected.topic == "NO_TOPIC":
        await _dismiss_thinking(message.bot, message.chat.id, 2)
        await message.answer(
            "⚠️ No encontré material de español en ese mensaje.\n"
            "Reenvía otro mensaje o escribe el tema manualmente."
        )
        return

    await _dismiss_thinking(message.bot, message.chat.id, 2)

    # Two SEPARATE dicts — never share the same object
    counts_es = {c["key"]: 0 for c in CATEGORIES}
    counts_ru = {c["key"]: 0 for c in CATEGORIES}
    await state.update_data(
        topic=detected.topic, examples=detected.examples,
        counts_es=counts_es, counts_ru=counts_ru,
        auto_level=detected.level, auto_dialect=detected.dialect,
    )
    await state.set_state(SurveyCreation.waiting_category_mode)

    await message.answer(
        f"📊 *Tema detectado:* {detected.topic}\n"
        f"📚 *Nivel:* {detected.level} 🔍\n"
        f"🗣️ *Dialecto:* {detected.dialect} 🔍\n\n"
        f"¿Cómo quieres elegir las cantidades de quizzes?",
        reply_markup=get_category_mode_keyboard(),
        parse_mode="Markdown",
    )


# ── category_mode: manual or auto ──────────────────────────


@router.callback_query(SurveyCreation.waiting_category_mode, F.data.startswith("category_mode:") & (F.data != "category_mode:accept"))
async def handle_category_mode(callback_query: CallbackQuery, state: FSMContext):
    """User chose manual or auto category counts."""
    mode = callback_query.data.split(":")[1]

    if mode == "manual":
        # Go to Spanish counter as before
        await state.set_state(SurveyCreation.waiting_counter_es)
        data = await state.get_data()
        await callback_query.message.edit_text(
            _get_counter_es_text(data),
            reply_markup=get_category_counter_keyboard(_get_counts(data, "es"), show_skip=True),
            parse_mode="Markdown",
        )
        await callback_query.answer()
        return

    # Auto mode — ask AI to determine counts
    data = await state.get_data()
    await callback_query.answer()  # Answer immediately before AI call
    await _show_thinking(callback_query.bot, callback_query.message.chat.id, 3, _EMOJI_ANALYZE, "🤖",
        " Analizando contenido...")

    try:
        counts_es, counts_ru = await ai.determine_category_counts(
            topic=data["topic"],
            examples=data.get("examples", []),
            count_es=_get_counts(data, "es"),
            count_ru=_get_counts(data, "ru"),
            level=data.get("level", "A1"),
            dialect=data.get("dialect", "Castellano"),
        )
    except Exception:
        logger.exception("Failed to auto-determine category counts")
        await _dismiss_thinking(callback_query.bot, callback_query.message.chat.id, 3)
        await callback_query.message.edit_text(
            "❌ No pude autodeterminar las cantidades.\n"
            "Elige manualmente.",
            reply_markup=get_category_mode_keyboard(),
        )
        return

    await _dismiss_thinking(callback_query.bot, callback_query.message.chat.id, 3)
    await state.update_data(counts_es=counts_es, counts_ru=counts_ru)

    # Build summary
    def _counts_text(counts: dict[str, int], lang: str) -> str:
        items = []
        for cat in CATEGORIES:
            n = counts.get(cat["key"], 0)
            if n > 0:
                items.append(f"  {cat['emoji']} {cat['label']}: {n}")
        total = sum(counts.values())
        return f"*{lang}* ({total} quizzes):\n" + "\n".join(items) if items else f"*{lang}*: (ninguno)"

    summary = (
        f"📊 *Cantidades sugeridas:*\n\n"
        f"{_counts_text(counts_es, 'Español')}\n\n"
        f"{_counts_text(counts_ru, 'Ruso')}\n\n"
        "¿Estás de acuerdo?"
    )

    await callback_query.message.edit_text(
        summary,
        reply_markup=get_category_auto_confirm_keyboard(),
        parse_mode="Markdown",
    )


# ── category_mode: accept auto-detected counts ──────────────


@router.callback_query(SurveyCreation.waiting_category_mode, F.data == "category_mode:accept")
async def handle_category_accept(callback_query: CallbackQuery, state: FSMContext):
    """User accepted auto-detected counts → move to level/dialect."""
    data = await state.get_data()
    total_es = _get_total(data, "es")
    total_ru = _get_total(data, "ru")

    # Check if level/dialect were auto-detected
    auto_level = data.get("auto_level")
    auto_dialect = data.get("auto_dialect")

    if auto_level and auto_dialect:
        await state.update_data(level=auto_level, dialect=auto_dialect)
        await state.set_state(SurveyCreation.generating)

        level_label = f"{auto_level} 🔍"
        dialect_label = f"{auto_dialect} 🔍"

        await callback_query.message.edit_text(
            f"📊 Tema: *{data['topic']}*\n"
            f"📝 Total: *{total_es}* español + *{total_ru}* ruso\n"
            f"📚 Nivel: *{level_label}* (detectado)\n"
            f"🗣️ Dialecto: *{dialect_label}* (detectado)"
        )
        await callback_query.answer()
        await _generate_and_preview(callback_query, state)
        return

    # Manual mode — ask for level
    await state.set_state(SurveyCreation.waiting_level)
    await callback_query.message.edit_text(
        f"📊 Tema: *{data['topic']}*\n"
        f"📝 Total: *{total_es}* español + *{total_ru}* ruso\n\n"
        "¿Qué nivel?",
        reply_markup=get_level_keyboard(),
        parse_mode="Markdown",
    )
    await callback_query.answer()


# ── counter_es: Spanish categories ──────────────────────────


@router.callback_query(SurveyCreation.waiting_counter_es, F.data.startswith("counter:"))
async def handle_counter_es(callback_query: CallbackQuery, state: FSMContext):
    """Handle Spanish category counter press."""
    parts = callback_query.data.split(":")

    # counter:ok — confirm → move to Russian
    if len(parts) == 2 and parts[1] == "ok":
        data = await state.get_data()
        await state.set_state(SurveyCreation.waiting_counter_ru)
        total_es = _get_total(data, "es")
        await callback_query.message.edit_text(
            _get_counter_ru_text(data),
            reply_markup=get_category_counter_keyboard(
                _get_counts(data, "ru"),
                show_skip=(total_es >= 1),  # skip only if Spanish has ≥1
            ),
            parse_mode="Markdown",
        )
        await callback_query.answer()
        return

    # counter:skip — set all Spanish to 0, move to Russian (no skip allowed)
    if len(parts) == 2 and parts[1] == "skip":
        counts_es = {c["key"]: 0 for c in CATEGORIES}
        await state.update_data(counts_es=counts_es)
        data = await state.get_data()
        await state.set_state(SurveyCreation.waiting_counter_ru)
        await callback_query.message.edit_text(
            _get_counter_ru_text(data),
            reply_markup=get_category_counter_keyboard(
                _get_counts(data, "ru"),
                show_skip=False,  # Spanish is 0, can't skip Russian
            ),
            parse_mode="Markdown",
        )
        await callback_query.answer()
        return

    # counter:key:+/-  (3 parts)
    action = parts[2]
    key = parts[1]

    data = await state.get_data()
    counts = _get_counts(data, "es")
    current = counts.get(key, 0)

    if action == "+":
        counts[key] = min(current + 1, COUNTER_MAX)
    elif action == "-":
        counts[key] = max(current - 1, 0)

    await state.update_data(counts_es=counts)
    data = await state.get_data()

    await callback_query.message.edit_text(
        _get_counter_es_text(data),
        reply_markup=get_category_counter_keyboard(
            _get_counts(data, "es"),
            show_skip=True,  # Spanish always allows skip
        ),
        parse_mode="Markdown",
    )
    await callback_query.answer()


# ── counter_ru: Russian categories ──────────────────────────


@router.callback_query(SurveyCreation.waiting_counter_ru, F.data.startswith("counter:"))
async def handle_counter_ru(callback_query: CallbackQuery, state: FSMContext):
    """Handle Russian category counter press."""
    parts = callback_query.data.split(":")

    # counter:ok — confirm → move to level (or skip if auto-detected)
    if len(parts) == 2 and parts[1] == "ok":
        data = await state.get_data()
        total_es = _get_total(data, "es")
        total_ru = _get_total(data, "ru")

        if total_ru < 1:
            await callback_query.answer("⚠️ Necesitas al menos 1 quiz en ruso", show_alert=True)
            return

        # Check if level/dialect were auto-detected
        auto_level = data.get("auto_level")
        auto_dialect = data.get("auto_dialect")

        if auto_level and auto_dialect:
            # Skip level/dialect selection — go straight to generating
            await state.update_data(level=auto_level, dialect=auto_dialect)
            await state.set_state(SurveyCreation.generating)

            level_label = f"{auto_level} 🔍" if auto_level else auto_level
            dialect_label = f"{auto_dialect} 🔍" if auto_dialect else auto_dialect

            await callback_query.message.edit_text(
                f"📊 Tema: *{data['topic']}*\n"
                f"📝 Total: *{total_es}* español + *{total_ru}* ruso\n"
                f"📚 Nivel: *{level_label}* (detectado)\n"
                f"🗣️ Dialecto: *{dialect_label}* (detectado)"
            )
            await callback_query.answer()

            # Trigger generation directly
            await _generate_and_preview(callback_query, state)
            return

        # Manual mode — ask for level
        await state.set_state(SurveyCreation.waiting_level)
        await callback_query.message.edit_text(
            f"📊 Tema: *{data['topic']}*\n"
            f"📝 Total: *{total_es}* español + *{total_ru}* ruso\n\n"
            "¿Qué nivel?",
            reply_markup=get_level_keyboard(),
            parse_mode="Markdown",
        )
        await callback_query.answer()
        return

    # counter:skip — set all Russian to 0, continue to level/dialect
    if len(parts) == 2 and parts[1] == "skip":
        counts_ru = {c["key"]: 0 for c in CATEGORIES}
        await state.update_data(counts_ru=counts_ru)
        data = await state.get_data()
        total_es = _get_total(data, "es")

        # Check if level/dialect were auto-detected
        auto_level = data.get("auto_level")
        auto_dialect = data.get("auto_dialect")

        if auto_level and auto_dialect:
            await state.update_data(level=auto_level, dialect=auto_dialect)
            await state.set_state(SurveyCreation.generating)

            level_label = f"{auto_level} 🔍" if auto_level else auto_level
            dialect_label = f"{auto_dialect} 🔍" if auto_dialect else auto_dialect

            await callback_query.message.edit_text(
                f"📊 Tema: *{data['topic']}*\n"
                f"📝 Total: *{total_es}* español + *0* ruso\n"
                f"📚 Nivel: *{level_label}* (detectado)\n"
                f"🗣️ Dialecto: *{dialect_label}* (detectado)"
            )
            await callback_query.answer()
            await _generate_and_preview(callback_query, state)
            return

        # Manual mode — ask for level
        await state.set_state(SurveyCreation.waiting_level)
        await callback_query.message.edit_text(
            f"📊 Tema: *{data['topic']}*\n"
            f"📝 Total: *{total_es}* español + *0* ruso\n\n"
            "¿Qué nivel?",
            reply_markup=get_level_keyboard(),
            parse_mode="Markdown",
        )
        await callback_query.answer()
        return

    # counter:key:+/-  (3 parts)
    action = parts[2]
    key = parts[1]

    data = await state.get_data()
    counts = _get_counts(data, "ru")
    current = counts.get(key, 0)

    if action == "+":
        counts[key] = min(current + 1, COUNTER_MAX)
    elif action == "-":
        counts[key] = max(current - 1, 0)

    await state.update_data(counts_ru=counts)
    data = await state.get_data()
    total_es = _get_total(data, "es")

    await callback_query.message.edit_text(
        _get_counter_ru_text(data),
        reply_markup=get_category_counter_keyboard(
            _get_counts(data, "ru"),
            show_skip=(total_es >= 1),  # skip only if Spanish has ≥1
        ),
        parse_mode="Markdown",
    )
    await callback_query.answer()


# ── level → dialect ─────────────────────────────────────────


@router.callback_query(SurveyCreation.waiting_level, F.data.startswith("level:"))
async def handle_level(callback_query: CallbackQuery, state: FSMContext):
    """User chose level → ask for dialect."""
    level = callback_query.data.split(":")[1]
    await state.update_data(level=level)
    await state.set_state(SurveyCreation.waiting_dialect)

    data = await state.get_data()
    total_es = _get_total(data, "es")
    total_ru = _get_total(data, "ru")

    await callback_query.message.edit_text(
        f"📊 Tema: *{data['topic']}*\n"
        f"📝 Total: *{total_es}* español + *{total_ru}* ruso\n"
        f"📚 Nivel: *{level}*\n\n"
        "¿Qué dialecto?",
        reply_markup=get_dialect_keyboard(),
        parse_mode="Markdown",
    )
    await callback_query.answer()


# ── dialect → generate quizzes ─────────────────────────────


@router.callback_query(SurveyCreation.waiting_dialect, F.data.startswith("dialect:"))
async def handle_dialect(callback_query: CallbackQuery, state: FSMContext):
    """User chose dialect → generate quizzes with AI."""
    dialect = callback_query.data.split(":")[1]
    await state.update_data(dialect=dialect)

    data = await state.get_data()
    counts_es = _get_counts(data, "es")
    counts_ru = _get_counts(data, "ru")
    total_es = sum(counts_es.values())
    total_ru = sum(counts_ru.values())

    await state.set_state(SurveyCreation.generating)
    await callback_query.answer()

    await _generate_and_preview(callback_query, state)


# ── review: edit or publish ─────────────────────────────────


@router.callback_query(SurveyCreation.reviewing, F.data == "survey_edit")
async def handle_edit(callback_query: CallbackQuery, state: FSMContext):
    """User wants to edit — show quiz selector."""
    data = await state.get_data()
    quizzes = [Quiz.from_dict(q) for q in data["quizzes"]]

    await callback_query.message.edit_text(
        "✏️ ¿Cuál quieres editar?",
        reply_markup=get_edit_selector_keyboard(len(quizzes)),
    )
    await callback_query.answer()


@router.callback_query(SurveyCreation.reviewing, F.data == "survey_publish")
async def handle_publish(callback_query: CallbackQuery, state: FSMContext):
    """Publish all quizzes to the global channel."""
    data = await state.get_data()
    topic = data["topic"]
    level = data["level"]
    dialect = data["dialect"]
    quizzes = [Quiz.from_dict(q) for q in data["quizzes"]]

    channel_id = await BotConfigRepository.get_channel_id()
    channel_title = await BotConfigRepository.get_channel_title()

    if not channel_id:
        await callback_query.message.edit_text(
            "⚠️ No hay canal configurado.\n\n"
            "Un administrador debe añadir el bot a un canal primero.",
            reply_markup=get_start_keyboard(),
        )
        await state.clear()
        await callback_query.answer()
        return

    try:
        for quiz in quizzes:
            question, entities = _prefixed_question(quiz, level)
            await callback_query.bot.send_poll(
                chat_id=channel_id,
                question=question,
                question_entities=entities,
                options=[{"text": opt} for opt in quiz.options],
                type="quiz",
                correct_option_id=quiz.correct_index,
                is_anonymous=True,
            )

        await callback_query.message.edit_text(
            f"🚀 ¡{len(quizzes)} quizzes nivel {level} — {dialect} publicados!\n\n"
            f"📍 Canal: {channel_title or channel_id}\n"
            f"📊 Tema: {topic}",
            reply_markup=get_start_keyboard(),
        )
    except Exception:
        logger.exception("Failed to publish quizzes")
        await callback_query.message.edit_text(
            "❌ Error al publicar.\n\n"
            "Verifica que el bot sea administrador del canal.",
            reply_markup=get_start_keyboard(),
        )

    await state.clear()
    await callback_query.answer()


# ── schedule: ask for interval ──────────────────────────────


@router.callback_query(SurveyCreation.reviewing, F.data == "survey_schedule")
async def handle_schedule(callback_query: CallbackQuery, state: FSMContext):
    """User wants to schedule publication — ask for interval."""
    await state.set_state(SurveyCreation.waiting_schedule_interval)
    await callback_query.message.edit_text(
        "⏰ *Publicación gradual*\n\n"
        "Escribe el intervalo de tiempo entre cada quiz.\n\n"
        "Formatos:\n"
        "  `30s` — 30 segundos\n"
        "  `5m` — 5 minutos\n"
        "  `1h` — 1 hora\n"
        "  `1h30m` — 1 hora y 30 minutos\n"
        "  `90` — 90 segundos (número solo = segundos)\n\n"
        "Escribe el intervalo:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown",
    )
    await callback_query.answer()


@router.message(SurveyCreation.waiting_schedule_interval)
async def handle_schedule_interval(message: Message, state: FSMContext):
    """Receive interval → validate → start background scheduler."""
    interval = parse_interval(message.text)
    if interval is None:
        await message.answer(
            "❌ Formato incorrecto.\n\n"
            "Formatos válidos: `30s`, `5m`, `1h`, `1h30m`, `90`\n"
            "Escribe el intervalo otra vez:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="Markdown",
        )
        return

    data = await state.get_data()
    quizzes = [Quiz.from_dict(q) for q in data["quizzes"]]
    level = data["level"]
    dialect = data["dialect"]
    topic = data["topic"]

    channel_id = await BotConfigRepository.get_channel_id()
    channel_title = await BotConfigRepository.get_channel_title()

    if not channel_id:
        await message.answer(
            "⚠️ No hay canal configurado.\n\n"
            "Un administrador debe añadir el bot a un canal primero.",
            reply_markup=get_start_keyboard(),
        )
        await state.clear()
        return

    # Confirm and start
    await state.set_state(SurveyCreation.generating)
    await message.answer(
        f"⏰ *Publicación programada*\n\n"
        f"📊 {len(quizzes)} quizzes nivel {level} — {dialect}\n"
        f"⏱️ Intervalo: {format_interval(interval)}\n"
        f"📍 Canal: {channel_title or channel_id}\n\n"
        f"🚀 Publicando el primero ahora...",
        parse_mode="Markdown",
    )

    # Launch background scheduler
    import asyncio
    asyncio.create_task(
        _run_scheduled_publish(
            bot=message.bot,
            channel_id=channel_id,
            channel_title=channel_title,
            quizzes=quizzes,
            level=level,
            dialect=dialect,
            topic=topic,
            interval=interval,
            chat_id=message.chat.id,
        )
    )


async def _run_scheduled_publish(
    bot, channel_id: int, channel_title: str | None,
    quizzes: list[Quiz], level: str, dialect: str, topic: str,
    interval: int, chat_id: int,
) -> None:
    """Background task: publish quizzes one by one with a delay between each."""
    import asyncio

    published = 0
    total = len(quizzes)

    for i, quiz in enumerate(quizzes):
        try:
            question, entities = _prefixed_question(quiz, level)
            await bot.send_poll(
                chat_id=channel_id,
                question=question,
                question_entities=entities,
                options=[{"text": opt} for opt in quiz.options],
                type="quiz",
                correct_option_id=quiz.correct_index,
                is_anonymous=True,
            )
            published = i + 1
        except Exception:
            logger.exception("Failed to publish quiz %d/%d", published + 1, total)
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ Error al publicar quiz #{quiz.id}. "
                         f"Publicados: {published}/{total}. "
                         "Verifica que el bot sea administrador del canal.",
                )
            except Exception:
                pass
            return

        # Progress update after each publish
        if published < total:
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ Publicado {published}/{total} — "
                         f"próximo en {format_interval(interval)}",
                )
            except Exception:
                pass
            await asyncio.sleep(interval)

    # Done
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=f"🚀 ¡{total} quizzes nivel {level} — {dialect} publicados!\n\n"
                 f"📍 Canal: {channel_title or channel_id}\n"
                 f"📊 Tema: {topic}",
            reply_markup=get_start_keyboard(),
        )
    except Exception:
        pass


@router.callback_query(SurveyCreation.reviewing, F.data.startswith("edit_select:"))
async def handle_edit_select(callback_query: CallbackQuery, state: FSMContext):
    """User selected a quiz to edit — ask for feedback."""
    quiz_id = int(callback_query.data.split(":")[1])
    await state.update_data(editing_id=quiz_id)
    await state.set_state(SurveyCreation.waiting_improvement)

    await callback_query.message.edit_text(
        f"✏️ Describe el cambio para el quiz #{quiz_id}:",
        reply_markup=get_cancel_keyboard(),
    )
    await callback_query.answer()


@router.message(SurveyCreation.waiting_improvement)
async def handle_improvement(message: Message, state: FSMContext):
    """Receive feedback → PATCH edit one quiz → show updated preview."""
    feedback = message.text.strip()
    data = await state.get_data()
    topic = data["topic"]
    level = data["level"]
    editing_id = data["editing_id"]
    quizzes = [Quiz.from_dict(q) for q in data["quizzes"]]

    await _show_thinking(message.bot, message.chat.id, 4, _EMOJI_FIX, "🔧",
        f" Regenerando quiz #{editing_id}...")

    # Build history for AI context
    history = [q.to_dict() for q in quizzes]

    try:
        edited_quiz = await ai.edit_quiz(topic, history, editing_id, feedback)
    except AIServiceError as e:
        await _dismiss_thinking(message.bot, message.chat.id, 4)
        await message.answer(
            f"❌ {e}\n\nVuelve a intentar.",
            reply_markup=get_edit_selector_keyboard(len(quizzes)),
        )
        await state.set_state(SurveyCreation.reviewing)
        return
    except Exception:
        logger.exception("Unexpected error editing quiz")
        await _dismiss_thinking(message.bot, message.chat.id, 4)
        await message.answer(
            "❌ Error inesperado. Intenta de nuevo.",
            reply_markup=get_edit_selector_keyboard(len(quizzes)),
        )
        await state.set_state(SurveyCreation.reviewing)
        return

    await _dismiss_thinking(message.bot, message.chat.id, 4)

    # Replace the edited quiz in the list
    edited_quiz.id = editing_id
    quizzes[editing_id - 1] = edited_quiz

    # Update state
    await state.update_data(quizzes=[q.to_dict() for q in quizzes])
    await state.set_state(SurveyCreation.reviewing)

    # Send the updated poll
    await _send_quiz_preview(message.chat.id, edited_quiz, level, message.bot)

    # Summary + edit-done buttons
    summary = _build_summary(quizzes, level)
    await message.answer(
        f"👆 Quiz #{editing_id} actualizado.\n\n"
        f"{summary}\n\n¿Qué quieres hacer?",
        reply_markup=get_edit_done_keyboard(),
    )


# ── cancel ──────────────────────────────────────────────────


@router.callback_query(F.data == "survey_cancel")
async def handle_cancel(callback_query: CallbackQuery, state: FSMContext):
    """Cancel at any stage."""
    await state.clear()
    await callback_query.message.edit_text(
        "❌ Cancelado.\n\n¿Qué quieres hacer?",
        reply_markup=get_start_keyboard(),
    )
    await callback_query.answer()
