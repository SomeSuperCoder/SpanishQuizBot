import json
import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.database.repository import UserRepository, SurveyRepository, BotConfigRepository
from bot.keyboards.inline import (
    get_start_keyboard,
    get_quantity_keyboard,
    get_level_keyboard,
    get_review_keyboard,
    get_edit_selector_keyboard,
    get_edit_done_keyboard,
    get_cancel_keyboard,
)
from bot.states.survey import SurveyCreation
from bot.services.ai_service import AIService, AIServiceError, Quiz

router = Router()
ai = AIService()
logger = logging.getLogger(__name__)


# ── helpers ─────────────────────────────────────────────────


def _prefixed_question(quiz: Quiz, level: str) -> str:
    """Add [level] prefix to quiz question."""
    return f"[{level}] {quiz.question}"


async def _send_quiz_preview(target, quiz: Quiz, level: str, bot) -> None:
    """Send a real Telegram quiz poll with [level] prefix."""
    await bot.send_poll(
        chat_id=target,
        question=_prefixed_question(quiz, level),
        options=[{"text": opt} for opt in quiz.options],
        type="quiz",
        correct_option_id=quiz.correct_index,
        is_anonymous=False,
    )


def _build_summary(quizzes: list[Quiz], level: str) -> str:
    """Build the [n] summary shown in the review message."""
    lines = []
    for q in quizzes:
        lines.append(f"[{q.id}] {_prefixed_question(q, level)}")
    return "\n".join(lines)


# ── /start & create ─────────────────────────────────────────


@router.callback_query(F.data == "create_survey")
async def handle_create_survey(callback_query: CallbackQuery, state: FSMContext):
    """User clicked 'Crear encuesta' — ask for topic."""
    await state.set_state(SurveyCreation.waiting_topic)
    await callback_query.message.edit_text(
        "📝 ¡Genial! Vamos a crear quizzes.\n\n"
        "¿Cuál es el tema?\n"
        "(Ej: Imperfecto de subjuntivo, Ser vs Estar, Pretérito indefinido...)"
    )
    await callback_query.answer()


# ── topic → quantity ────────────────────────────────────────


@router.message(SurveyCreation.waiting_topic)
async def handle_topic(message: Message, state: FSMContext):
    """Receive topic → ask how many quizzes."""
    topic = message.text.strip()
    await state.update_data(topic=topic)
    await state.set_state(SurveyCreation.waiting_quantity)

    await message.answer(
        f"📊 Tema: *{topic}*\n\n¿Cuántas encuestas quieres crear?",
        reply_markup=get_quantity_keyboard(),
        parse_mode="Markdown",
    )


# ── quantity → level ────────────────────────────────────────


@router.callback_query(SurveyCreation.waiting_quantity, F.data.startswith("quantity:"))
async def handle_quantity(callback_query: CallbackQuery, state: FSMContext):
    """User chose quantity → ask for level."""
    count = int(callback_query.data.split(":")[1])
    await state.update_data(count=count)
    await state.set_state(SurveyCreation.waiting_level)

    await callback_query.message.edit_text(
        f"📊 Tema: *{callback_query.message.text.split(chr(10))[0].replace('📊 Tema: ', '').replace('*', '')}*\n"
        f"📝 Cantidad: *{count}*\n\n"
        "¿Qué nivel?",
        reply_markup=get_level_keyboard(),
        parse_mode="Markdown",
    )
    await callback_query.answer()


# ── level → generate N quizzes ─────────────────────────────


@router.callback_query(SurveyCreation.waiting_level, F.data.startswith("level:"))
async def handle_level(callback_query: CallbackQuery, state: FSMContext):
    """User chose level → generate N quizzes with AI."""
    level = callback_query.data.split(":")[1]
    data = await state.get_data()
    topic = data["topic"]
    count = data["count"]

    await state.update_data(level=level)
    await state.set_state(SurveyCreation.generating)
    await callback_query.message.edit_text(
        f"🔄 Generando {count} quizzes nivel {level} con IA..."
    )
    await callback_query.answer()

    try:
        quizzes = await ai.generate_quizzes(topic, count, level)
    except AIServiceError as e:
        await callback_query.message.edit_text(
            f"❌ {e}\n\nIntenta de nuevo.",
            reply_markup=get_start_keyboard(),
        )
        await state.clear()
        return
    except Exception:
        logger.exception("Unexpected error generating quizzes")
        await callback_query.message.edit_text(
            "❌ Error inesperado al generar los quizzes. Intenta de nuevo.",
            reply_markup=get_start_keyboard(),
        )
        await state.clear()
        return

    # Serialize quizzes for FSM storage
    quizzes_data = [q.to_dict() for q in quizzes]
    await state.update_data(quizzes=quizzes_data)
    await state.set_state(SurveyCreation.reviewing)

    # Send all polls as preview
    await callback_query.message.delete()
    for quiz in quizzes:
        await _send_quiz_preview(callback_query.message.chat.id, quiz, level, callback_query.bot)

    # Summary + action buttons
    summary = _build_summary(quizzes, level)
    await callback_query.message.answer(
        f"👆 {len(quizzes)} quizzes nivel {level} (del más fácil al más difícil):\n\n"
        f"{summary}\n\n¿Qué quieres hacer?",
        reply_markup=get_review_keyboard(),
    )


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
            await callback_query.bot.send_poll(
                chat_id=channel_id,
                question=_prefixed_question(quiz, level),
                options=[{"text": opt} for opt in quiz.options],
                type="quiz",
                correct_option_id=quiz.correct_index,
                is_anonymous=True,
            )

        await callback_query.message.edit_text(
            f"🚀 ¡{len(quizzes)} quizzes nivel {level} publicados!\n\n"
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


# ── edit flow: select quiz → feedback → regenerate ─────────


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

    loading_msg = await message.answer(f"🔄 Regenerando quiz #{editing_id}...")

    # Build history for AI context
    history = [q.to_dict() for q in quizzes]

    try:
        edited_quiz = await ai.edit_quiz(topic, history, editing_id, feedback)
    except AIServiceError as e:
        await loading_msg.edit_text(
            f"❌ {e}\n\nVuelve a intentar.",
            reply_markup=get_edit_selector_keyboard(len(quizzes)),
        )
        await state.set_state(SurveyCreation.reviewing)
        return
    except Exception:
        logger.exception("Unexpected error editing quiz")
        await loading_msg.edit_text(
            "❌ Error inesperado. Intenta de nuevo.",
            reply_markup=get_edit_selector_keyboard(len(quizzes)),
        )
        await state.set_state(SurveyCreation.reviewing)
        return

    # Replace the edited quiz in the list
    edited_quiz.id = editing_id
    quizzes[editing_id - 1] = edited_quiz

    # Update state
    await state.update_data(quizzes=[q.to_dict() for q in quizzes])
    await state.set_state(SurveyCreation.reviewing)

    # Delete "Regenerando..." message, send the updated poll
    await loading_msg.delete()
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
