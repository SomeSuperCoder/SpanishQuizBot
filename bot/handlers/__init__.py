from bot.handlers.start import router as start_router
from bot.handlers.survey import router as survey_router
from bot.handlers.callbacks import router as callbacks_router

__all__ = ["start_router", "survey_router", "callbacks_router"]
