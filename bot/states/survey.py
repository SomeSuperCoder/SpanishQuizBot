from aiogram.fsm.state import State, StatesGroup


class SurveyCreation(StatesGroup):
    waiting_topic = State()
    waiting_quantity = State()
    waiting_level = State()
    generating = State()
    reviewing = State()
    waiting_improvement = State()
    confirming = State()
