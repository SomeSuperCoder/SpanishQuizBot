import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.database.repository import UserRepository, SurveyRepository
from bot.keyboards.inline import (
    get_survey_review_keyboard,
    get_confirm_keyboard,
    get_cancel_keyboard,
    get_start_keyboard,
)
from bot.states.survey import SurveyCreation
from bot.services.ai_service import AIService, AIServiceError, Quiz

router = Router()
ai = AIService()


def _quiz_preview(quiz: Quiz) -> str:
    """Format a quiz for preview."""
    lines = [f"📊 {quiz.question}\n"]
    labels = ["🅰️", "🅱️", "🅲", "🅳"]
    for i, opt in enumerate(quiz.options):
        marker = "✅" if i == quiz.correct_index else "  "
        lines.append(f"{labels[i]}  {opt}  {marker}")
    return "\n".join(lines)


def _quiz_publish_text(quiz: Quiz) -> str:
    """Format a quiz for the channel (no correct answer shown)."""
    labels = ["🅰️", "🅱️", "🅲", "🅳"]
    lines = [f"📊 {quiz.question}\n"]
    for i, opt in enumerate(quiz.options):
        lines.append(f"{labels[i]}  {opt}")
    return "\n".join(lines)


def _vote_keyboard(quiz: Quiz, survey_id: int) -> InlineKeyboardMarkup:
    """Inline keyboard for voting in the channel."""
    labels = ["🅰️", "🅱️", "🅲", "🅳"]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{labels[i]}  {opt}",
            callback_data=f"vote:{survey_id}:{i}",
        )]
        for i, opt in enumerate(quiz.options)
    ])


@router.callback_query(F.data == "create_survey")
async def handle_create_survey(callback_query: CallbackQuery, state: FSMContext):
    """User clicked 'Crear encuesta' — ask for topic."""
    await state.set_state(SurveyCreation.waiting_topic)
    await callback_query.message.edit_text(
        "📝 ¡Genial! Vamos a crear un quiz.\n\n"
        "¿Cuál es el tema?\n"
        "(Ej: Imperfecto de subjuntivo, Ser vs Estar, Pretérito indefinido...)"
    )
    await callback_query.answer()


@router.message(SurveyCreation.waiting_topic)
async def handle_topic(message: Message, state: FSMContext):
    """Receive topic → AI generates quiz automatically."""
    topic = message.text.strip()
    await state.update_data(topic=topic)
    await state.set_state(SurveyCreation.generating)

    loading_msg = await message.answer("🔄 Generando quiz con IA...")

    try:
        quiz = await ai.generate_quiz(topic)
    except AIServiceError as e:
        await loading_msg.edit_text(
            f"❌ {e}\n\nIntenta de nuevo con otro tema.",
            reply_markup=get_start_keyboard(),
        )
        await state.clear()
        return
    except Exception as e:
        logger.exception("Unexpected error generating quiz")
        await loading_msg.edit_text(
            "❌ Error inesperado al generar el quiz. Intenta de nuevo.",
            reply_markup=get_start_keyboard(),
        )
        await state.clear()
        return

    # Save to DB
    survey_id = await SurveyRepository.create(
        user_id=message.from_user.id,
        topic=topic,
        content=quiz.question,
        options=json.dumps(quiz.options),
        correct_index=quiz.correct_index,
    )

    await state.update_data(
        survey_id=survey_id,
        quiz_question=quiz.question,
        quiz_options=quiz.options,
        quiz_correct=quiz.correct_index,
    )
    await state.set_state(SurveyCreation.reviewing)

    preview = _quiz_preview(quiz)
    await loading_msg.edit_text(preview, reply_markup=get_survey_review_keyboard())


@router.callback_query(SurveyCreation.reviewing, F.data == "survey_approve")
async def handle_approve(callback_query: CallbackQuery, state: FSMContext):
    """User approved the quiz — show publish confirmation."""
    data = await state.get_data()
    quiz = Quiz(
        question=data["quiz_question"],
        options=data["quiz_options"],
        correct_index=data["quiz_correct"],
    )

    await state.set_state(SurveyCreation.confirming)
    await callback_query.message.edit_text(
        f"✅ ¡Quiz aprobado!\n\n{_quiz_preview(quiz)}\n\n"
        "¿Qué deseas hacer?",
        reply_markup=get_confirm_keyboard(),
    )
    await callback_query.answer()


@router.callback_query(SurveyCreation.reviewing, F.data == "survey_improve")
async def handle_improve(callback_query: CallbackQuery, state: FSMContext):
    """User wants to improve — ask for feedback."""
    await state.set_state(SurveyCreation.waiting_improvement)
    await callback_query.message.edit_text(
        "✏️ Cuéntame qué quieres mejorar.\n\n"
        "¿Qué cambios necesitas?",
        reply_markup=get_cancel_keyboard(),
    )
    await callback_query.answer()


@router.message(SurveyCreation.waiting_improvement)
async def handle_improvement(message: Message, state: FSMContext):
    """Receive feedback → regenerate quiz."""
    feedback = message.text.strip()
    data = await state.get_data()
    topic = data["topic"]
    survey_id = data["survey_id"]

    loading_msg = await message.answer("🔄 Regenerando quiz...")

    try:
        quiz = await ai.generate_quiz(topic, feedback=feedback)
    except AIServiceError as e:
        await loading_msg.edit_text(
            f"❌ {e}\n\nVuelve a intentar.",
            reply_markup=get_survey_review_keyboard(),
        )
        return
    except Exception:
        logger.exception("Unexpected error regenerating quiz")
        await loading_msg.edit_text(
            "❌ Error inesperado. Intenta de nuevo.",
            reply_markup=get_survey_review_keyboard(),
        )
        return

    # Update DB
    await SurveyRepository.update(
        survey_id,
        content=quiz.question,
        options=json.dumps(quiz.options),
        correct_index=quiz.correct_index,
    )

    await state.update_data(
        quiz_question=quiz.question,
        quiz_options=quiz.options,
        quiz_correct=quiz.correct_index,
    )
    await state.set_state(SurveyCreation.reviewing)

    preview = _quiz_preview(quiz)
    await loading_msg.edit_text(preview, reply_markup=get_survey_review_keyboard())


@router.callback_query(SurveyCreation.confirming, F.data == "survey_publish")
async def handle_publish(callback_query: CallbackQuery, state: FSMContext):
    """Publish quiz to the connected channel."""
    data = await state.get_data()
    survey_id = data["survey_id"]
    topic = data["topic"]
    quiz = Quiz(
        question=data["quiz_question"],
        options=data["quiz_options"],
        correct_index=data["quiz_correct"],
    )

    user = await UserRepository.get_or_create(
        callback_query.from_user.id,
        callback_query.from_user.username or "",
        callback_query.from_user.first_name or "",
    )

    if not user.get("channel_id"):
        await callback_query.message.edit_text(
            "⚠️ No tienes un canal conectado.\n\n"
            "Añade el bot a tu canal primero y luego vuelve a intentar.",
            reply_markup=get_start_keyboard(),
        )
        await state.clear()
        await callback_query.answer()
        return

    channel_id = user["channel_id"]
    text = _quiz_publish_text(quiz)
    kb = _vote_keyboard(quiz, survey_id)

    try:
        sent = await callback_query.bot.send_message(
            chat_id=channel_id, text=text, reply_markup=kb,
        )
        await SurveyRepository.update(
            survey_id,
            status="published",
            channel_id=channel_id,
            message_id=sent.message_id,
        )
        await callback_query.message.edit_text(
            f"🚀 ¡Quiz publicado!\n\n"
            f"📍 Canal: {user.get('channel_title', 'desconocido')}\n"
            f"📊 Tema: {topic}",
            reply_markup=get_start_keyboard(),
        )
    except Exception:
        logger.exception("Failed to publish quiz")
        await callback_query.message.edit_text(
            "❌ Error al publicar.\n\n"
            "Verifica que el bot sea administrador del canal.",
            reply_markup=get_start_keyboard(),
        )

    await state.clear()
    await callback_query.answer()


@router.callback_query(F.data == "survey_cancel")
async def handle_cancel(callback_query: CallbackQuery, state: FSMContext):
    """Cancel at any stage."""
    await state.clear()
    await callback_query.message.edit_text(
        "❌ Cancelado.\n\n¿Qué quieres hacer?",
        reply_markup=get_start_keyboard(),
    )
    await callback_query.answer()
