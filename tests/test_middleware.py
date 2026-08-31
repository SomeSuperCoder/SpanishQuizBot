import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, CallbackQuery, User
from bot.middleware.whitelist import WhitelistMiddleware


@pytest.mark.asyncio
async def test_whitelist_allows_authorized_message():
    """Test that authorized users pass through on Message events."""
    middleware = WhitelistMiddleware()

    mock_user = MagicMock(spec=User)
    mock_user.username = "allowed_user"
    mock_user.id = 111

    mock_event = MagicMock(spec=Message)
    mock_event.from_user = mock_user

    mock_handler = AsyncMock(return_value="success")

    with patch('bot.middleware.whitelist.settings') as mock_settings:
        mock_settings.whitelist_usernames = ["allowed_user", "other_user"]
        result = await middleware(mock_handler, mock_event, {})

    assert result == "success"
    mock_handler.assert_called_once_with(mock_event, {})


@pytest.mark.asyncio
async def test_whitelist_blocks_unauthorized_message():
    """Test that unauthorized users are blocked on Message events."""
    middleware = WhitelistMiddleware()

    mock_user = MagicMock(spec=User)
    mock_user.username = "unauthorized_user"
    mock_user.id = 222

    mock_event = MagicMock(spec=Message)
    mock_event.from_user = mock_user
    mock_event.answer = AsyncMock()

    mock_handler = AsyncMock()

    with patch('bot.middleware.whitelist.settings') as mock_settings:
        mock_settings.whitelist_usernames = ["allowed_user"]
        result = await middleware(mock_handler, mock_event, {})

    assert result is None
    mock_handler.assert_not_called()
    mock_event.answer.assert_called_once()


@pytest.mark.asyncio
async def test_whitelist_allows_authorized_callback():
    """Test that authorized users pass through on CallbackQuery events."""
    middleware = WhitelistMiddleware()

    mock_user = MagicMock(spec=User)
    mock_user.username = "allowed_user"
    mock_user.id = 333

    mock_event = MagicMock(spec=CallbackQuery)
    mock_event.from_user = mock_user
    mock_event.answer = AsyncMock()

    mock_handler = AsyncMock(return_value="ok")

    with patch('bot.middleware.whitelist.settings') as mock_settings:
        mock_settings.whitelist_usernames = ["allowed_user"]
        result = await middleware(mock_handler, mock_event, {})

    assert result == "ok"
    mock_handler.assert_called_once()


@pytest.mark.asyncio
async def test_whitelist_blocks_unauthorized_callback():
    """Test that unauthorized users are blocked on CallbackQuery events."""
    middleware = WhitelistMiddleware()

    mock_user = MagicMock(spec=User)
    mock_user.username = "unauthorized_user"
    mock_user.id = 444

    mock_event = MagicMock(spec=CallbackQuery)
    mock_event.from_user = mock_user
    mock_event.answer = AsyncMock()

    mock_handler = AsyncMock()

    with patch('bot.middleware.whitelist.settings') as mock_settings:
        mock_settings.whitelist_usernames = ["allowed_user"]
        result = await middleware(mock_handler, mock_event, {})

    assert result is None
    mock_handler.assert_not_called()
    mock_event.answer.assert_called_once()


@pytest.mark.asyncio
async def test_whitelist_blocks_no_username():
    """Test that users without username are blocked."""
    middleware = WhitelistMiddleware()

    mock_user = MagicMock(spec=User)
    mock_user.username = None
    mock_user.id = 555

    mock_event = MagicMock(spec=Message)
    mock_event.from_user = mock_user
    mock_event.answer = AsyncMock()

    mock_handler = AsyncMock()

    with patch('bot.middleware.whitelist.settings') as mock_settings:
        mock_settings.whitelist_usernames = ["allowed_user"]
        result = await middleware(mock_handler, mock_event, {})

    assert result is None
    mock_handler.assert_not_called()


@pytest.mark.asyncio
async def test_whitelist_case_insensitive():
    """Test that username comparison is case-insensitive."""
    middleware = WhitelistMiddleware()

    mock_user = MagicMock(spec=User)
    mock_user.username = "Allowed_User"
    mock_user.id = 666

    mock_event = MagicMock(spec=Message)
    mock_event.from_user = mock_user

    mock_handler = AsyncMock(return_value="success")

    with patch('bot.middleware.whitelist.settings') as mock_settings:
        mock_settings.whitelist_usernames = ["allowed_user"]
        result = await middleware(mock_handler, mock_event, {})

    assert result == "success"


@pytest.mark.asyncio
async def test_whitelist_empty_list_blocks_all():
    """Test that empty whitelist blocks everyone."""
    middleware = WhitelistMiddleware()

    mock_user = MagicMock(spec=User)
    mock_user.username = "anyone"
    mock_user.id = 777

    mock_event = MagicMock(spec=Message)
    mock_event.from_user = mock_user
    mock_event.answer = AsyncMock()

    mock_handler = AsyncMock()

    with patch('bot.middleware.whitelist.settings') as mock_settings:
        mock_settings.whitelist_usernames = []
        result = await middleware(mock_handler, mock_event, {})

    assert result is None
    mock_handler.assert_not_called()
