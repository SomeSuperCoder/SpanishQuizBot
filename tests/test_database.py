import pytest
from bot.database.repository import UserRepository, SurveyRepository


@pytest.mark.asyncio
async def test_user_create(db):
    user = await UserRepository.get_or_create(123, "user1", "Test")
    assert user["telegram_id"] == 123


@pytest.mark.asyncio
async def test_user_get_existing(db):
    await UserRepository.get_or_create(123, "user1", "Test")
    user2 = await UserRepository.get_or_create(123, "user1", "Test")
    assert user2["telegram_id"] == 123


@pytest.mark.asyncio
async def test_user_update_channel(db):
    await UserRepository.get_or_create(123, "user1", "Test")
    await UserRepository.update_channel(123, -100123, "My Channel")
    user = await UserRepository.get_or_create(123, "user1", "Test")
    assert user["channel_id"] == -100123


@pytest.mark.asyncio
async def test_survey_create(db):
    user = await UserRepository.get_or_create(123, "user1", "Test")
    sid = await SurveyRepository.create(user["id"], "Topic", "Content", "A,B")
    assert sid > 0


@pytest.mark.asyncio
async def test_survey_get(db):
    user = await UserRepository.get_or_create(123, "user1", "Test")
    sid = await SurveyRepository.create(user["id"], "T", "C", "X,Y")
    s = await SurveyRepository.get(sid)
    assert s["topic"] == "T"
    assert s["status"] == "draft"


@pytest.mark.asyncio
async def test_survey_update(db):
    user = await UserRepository.get_or_create(123, "user1", "Test")
    sid = await SurveyRepository.create(user["id"], "T", "orig", "A,B")
    await SurveyRepository.update(sid, content="new", status="pub")
    s = await SurveyRepository.get(sid)
    assert s["content"] == "new"
    assert s["status"] == "pub"
