from bot.states.survey import SurveyCreation


def test_states_exist():
    assert hasattr(SurveyCreation, "waiting_topic")
    assert hasattr(SurveyCreation, "waiting_options")
    assert hasattr(SurveyCreation, "reviewing")
    assert hasattr(SurveyCreation, "waiting_improvement")
    assert hasattr(SurveyCreation, "confirming")
