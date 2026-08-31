from bot.keyboards.inline import (
    get_start_keyboard,
    get_survey_review_keyboard,
    get_confirm_keyboard,
    get_cancel_keyboard,
)


def test_start_keyboard():
    kb = get_start_keyboard()
    assert kb.inline_keyboard[0][0].callback_data == "create_survey"


def test_review_keyboard():
    kb = get_survey_review_keyboard()
    assert len(kb.inline_keyboard[0]) == 2
    assert "Perfecto" in kb.inline_keyboard[0][0].text


def test_confirm_keyboard():
    kb = get_confirm_keyboard()
    assert "Publicar" in kb.inline_keyboard[0][0].text


def test_cancel_keyboard():
    kb = get_cancel_keyboard()
    assert "Cancelar" in kb.inline_keyboard[0][0].text
