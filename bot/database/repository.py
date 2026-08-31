import aiosqlite
from bot.config import settings

DATABASE_PATH = settings.database_path


class UserRepository:
    @staticmethod
    async def get_or_create(telegram_id: int, username: str, first_name: str) -> dict:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)
            await db.execute(
                "INSERT INTO users (telegram_id, username, first_name) VALUES (?, ?, ?)",
                (telegram_id, username, first_name)
            )
            await db.commit()
            cursor = await db.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            )
            return dict(await cursor.fetchone())

    @staticmethod
    async def update_channel(telegram_id: int, channel_id: int, channel_title: str):
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "UPDATE users SET channel_id = ?, channel_title = ? WHERE telegram_id = ?",
                (channel_id, channel_title, telegram_id)
            )
            await db.commit()


class SurveyRepository:
    @staticmethod
    async def create(user_id: int, topic: str, content: str, options: str, correct_index: int = 0) -> int:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                "INSERT INTO surveys (user_id, topic, content, options, correct_index) VALUES (?, ?, ?, ?, ?)",
                (user_id, topic, content, options, correct_index),
            )
            await db.commit()
            return cursor.lastrowid

    @staticmethod
    async def update(survey_id: int, **kwargs):
        async with aiosqlite.connect(DATABASE_PATH) as db:
            sets = ", ".join(f"{k} = ?" for k in kwargs)
            values = list(kwargs.values()) + [survey_id]
            await db.execute(
                f"UPDATE surveys SET {sets}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values
            )
            await db.commit()

    @staticmethod
    async def get(survey_id: int) -> dict:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM surveys WHERE id = ?", (survey_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None