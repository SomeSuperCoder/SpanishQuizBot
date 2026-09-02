"""Tests for the heartbeat mechanism in _show_thinking / _dismiss_thinking.

Covers:
  1. Heartbeat task creation on successful _show_thinking
  2. Heartbeat cancellation + replacement on second _show_thinking (same draft_id)
  3. Heartbeat cancellation on _dismiss_thinking
  4. No heartbeat created when SendRichMessageDraft raises
  5. Signatures unchanged (import + call check)
  6. asyncio import present in the module
  7. Module compiles cleanly
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import subprocess
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Import the module under test ──────────────────────────────
from bot.handlers.survey import (
    _show_thinking,
    _dismiss_thinking,
    _heartbeat_tasks,
    _heartbeat_loop,
    _ce,
)


# ── Helpers ───────────────────────────────────────────────────

def _make_mock_bot(return_value=None, side_effect=None):
    """Return an AsyncMock that mimics the Telethon bot client."""
    bot = AsyncMock()
    if side_effect is not None:
        bot.side_effect = side_effect
    elif return_value is not None:
        bot.return_value = return_value
    else:
        # Default: return a mock with a message_id for delete_message
        msg = MagicMock()
        msg.message_id = 42
        bot.return_value = msg
    return bot


# ── Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_heartbeat_created_on_successful_show():
    """_show_thinking should create a heartbeat task after a successful draft send."""
    bot = _make_mock_bot()
    draft_id = 1001

    await _show_thinking(bot, chat_id=1, draft_id=draft_id,
                         emoji_id="emo1", fallback="⚙️", text="Working…")

    # Bot was called with SendRichMessageDraft
    bot.assert_awaited_once()
    call_args = bot.call_args
    assert call_args is not None

    # A heartbeat task is now registered
    assert draft_id in _heartbeat_tasks
    task = _heartbeat_tasks[draft_id]
    assert isinstance(task, asyncio.Task)
    assert not task.done()  # still running

    # Cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    _heartbeat_tasks.pop(draft_id, None)


@pytest.mark.asyncio
async def test_heartbeat_cancelled_on_stage_change():
    """Second _show_thinking with the same draft_id must cancel the first heartbeat."""
    bot = _make_mock_bot()
    draft_id = 2001

    # First call — creates heartbeat #1
    await _show_thinking(bot, chat_id=1, draft_id=draft_id,
                         emoji_id="emo1", fallback="⚙️", text="Stage A")
    task1 = _heartbeat_tasks.get(draft_id)
    assert task1 is not None

    # Second call — should cancel task1 and create task2
    await _show_thinking(bot, chat_id=1, draft_id=draft_id,
                         emoji_id="emo2", fallback="🔧", text="Stage B")
    task2 = _heartbeat_tasks.get(draft_id)

    assert task2 is not None
    assert task2 is not task1
    # Yield so the event loop processes the cancellation
    await asyncio.sleep(0)
    assert task1.cancelled()  # old task was cancelled

    # Cleanup
    task2.cancel()
    try:
        await task2
    except asyncio.CancelledError:
        pass
    _heartbeat_tasks.pop(draft_id, None)


@pytest.mark.asyncio
async def test_dismiss_cancels_heartbeat():
    """_dismiss_thinking should cancel any running heartbeat for the draft_id."""
    bot = _make_mock_bot()
    draft_id = 3001

    # Start a heartbeat
    await _show_thinking(bot, chat_id=1, draft_id=draft_id,
                         emoji_id="emo1", fallback="⚙️", text="Working…")
    task = _heartbeat_tasks.get(draft_id)
    assert task is not None
    assert not task.cancelled()

    # Dismiss — should cancel the heartbeat and call SendRichMessage + delete_message
    await _dismiss_thinking(bot, chat_id=1, draft_id=draft_id)

    # Yield so the event loop processes the cancellation
    await asyncio.sleep(0)
    assert task.cancelled()
    assert draft_id not in _heartbeat_tasks

    # _dismiss_thinking made 2 calls: SendRichMessage + delete_message
    assert bot.await_count == 2


@pytest.mark.asyncio
async def test_no_heartbeat_on_show_failure():
    """If SendRichMessageDraft raises, no heartbeat task is created."""
    bot = _make_mock_bot(side_effect=Exception("chat not private"))
    draft_id = 4001

    await _show_thinking(bot, chat_id=1, draft_id=draft_id,
                         emoji_id="emo1", fallback="⚙️", text="Working…")

    # No heartbeat registered
    assert draft_id not in _heartbeat_tasks
    # Bot was still called (the exception happened inside the call)
    bot.assert_awaited_once()


@pytest.mark.asyncio
async def test_dismiss_cleans_up_even_on_failure():
    """_dismiss_thinking cleans heartbeat even if SendRichMessage raises."""
    bot = _make_mock_bot(side_effect=Exception("network error"))
    draft_id = 5001

    # Manually register a heartbeat so we can verify cleanup
    fake_task = asyncio.create_task(asyncio.sleep(999))
    _heartbeat_tasks[draft_id] = fake_task

    await _dismiss_thinking(bot, chat_id=1, draft_id=draft_id)

    assert draft_id not in _heartbeat_tasks
    # Yield so the event loop processes the cancellation
    await asyncio.sleep(0)
    assert fake_task.cancelled()


@pytest.mark.asyncio
async def test_heartbeat_loop_refreshes_draft():
    """_heartbeat_loop should re-send the draft at each interval."""
    bot = _make_mock_bot()
    interval = 0.05  # very fast for testing

    task = asyncio.create_task(
        _heartbeat_loop(bot, chat_id=1, draft_id=99,
                        emoji_id="emo1", fallback="⚙️", text="Thinking…",
                        interval=interval)
    )

    # Let it tick 3 times
    await asyncio.sleep(interval * 3.5)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # bot should have been called at least 3 times
    assert bot.await_count >= 3


@pytest.mark.asyncio
async def test_heartbeat_loop_survives_transient_error():
    """A single failed refresh shouldn't kill the heartbeat loop."""
    bot = AsyncMock()
    call_count = 0

    async def flaky_call(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("transient blip")
        return MagicMock(message_id=1)

    bot.side_effect = flaky_call
    interval = 0.05

    task = asyncio.create_task(
        _heartbeat_loop(bot, chat_id=1, draft_id=88,
                        emoji_id="emo1", fallback="⚙️", text="Thinking…",
                        interval=interval)
    )

    await asyncio.sleep(interval * 2.5)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Should have been called at least twice (1 fail + 1+ success)
    assert call_count >= 2


# ── Static checks ─────────────────────────────────────────────


def test_asyncio_imported():
    """asyncio must be imported at module level."""
    import bot.handlers.survey as mod
    assert hasattr(mod, "asyncio")


def test_show_thinking_signature_unchanged():
    """_show_thinking must accept (bot, chat_id, draft_id, emoji_id, fallback, text)."""
    sig = inspect.signature(_show_thinking)
    params = list(sig.parameters.keys())
    assert params == ["bot", "chat_id", "draft_id", "emoji_id", "fallback", "text"]


def test_dismiss_thinking_signature_unchanged():
    """_dismiss_thinking must accept (bot, chat_id, draft_id)."""
    sig = inspect.signature(_dismiss_thinking)
    params = list(sig.parameters.keys())
    assert params == ["bot", "chat_id", "draft_id"]


def test_module_compiles():
    """python -m py_compile must pass for the module."""
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", "bot/handlers/survey.py"],
        capture_output=True, text=True, cwd="/home/allen/Proyectos/BotDeEncuestas",
    )
    assert result.returncode == 0, f"Compilation failed:\n{result.stderr}"
