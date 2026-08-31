import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from bot.services.ai_service import AIService


@pytest.mark.asyncio
async def test_generate_survey():
    ai = AIService()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"choices": [{"message": {"content": "Test survey"}}]}
    mock_resp.raise_for_status = MagicMock()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await ai.generate_survey("Topic", ["A", "B"])
        assert result == "Test survey"


@pytest.mark.asyncio
async def test_generate_with_feedback():
    ai = AIService()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"choices": [{"message": {"content": "Improved"}}]}
    mock_resp.raise_for_status = MagicMock()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await ai.generate_survey("T", ["X"], feedback="better")
        assert result == "Improved"
