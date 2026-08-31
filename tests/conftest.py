import pytest
import asyncio
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db():
    """Test database with temp file."""
    from bot.database.connection import init_db

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    with patch("bot.database.connection.DATABASE_PATH", path):
        await init_db()
        yield path
    os.unlink(path)


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = 123456789
    user.username = "test_user"
    user.first_name = "Test"
    return user


@pytest.fixture
def mock_message(mock_user):
    msg = AsyncMock()
    msg.from_user = mock_user
    msg.text = "test"
    msg.answer = AsyncMock()
    return msg


@pytest.fixture
def mock_callback(mock_user):
    cb = AsyncMock()
    cb.from_user = mock_user
    cb.data = "test"
    cb.answer = AsyncMock()
    cb.message = AsyncMock()
    cb.bot = AsyncMock()
    return cb
