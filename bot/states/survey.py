from aiogram.fsm.state import State, StatesGroup


class SurveyCreation(StatesGroup):
    waiting_topic_mode = State()
    waiting_topic_manual = State()
    waiting_topic_forward = State()
    waiting_category_mode = State()
    waiting_counter_es = State()
    waiting_counter_ru = State()
    waiting_level = State()
    waiting_dialect = State()
    generating = State()
    reviewing = State()
    waiting_improvement = State()
    waiting_schedule_interval = State()
    confirming = State()
