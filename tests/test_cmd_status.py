import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.bot.commands import cmd_status


def make_update(chat_id: int = 123456) -> MagicMock:
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.message.reply_text = AsyncMock()
    return update


def make_context(args: list[str]) -> MagicMock:
    context = MagicMock()
    context.args = args
    context.bot.get_chat_member = AsyncMock()
    return context


def make_db_context_mock():
    """Return an async context manager mock that does nothing."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=None)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def make_group(**overrides) -> dict:
    defaults = {
        "group_id": 123456,
        "timezone": "UTC",
        "reminder_hours": 1.0,
        "check_window_hours": 24.0,
        "auto_create": 0,
        "yt_channel_id": None,
        "yt_access_token": None,
        "yt_refresh_token": None,
        "yt_token_expiry": None,
        "last_manual_check": None,
        "broadcast_privacy": "public",
    }
    return {**defaults, **overrides}


@pytest.mark.asyncio
async def test_status_youtube_connected():
    update = make_update()
    context = make_context([])
    group = make_group(yt_channel_id="UC123abc")

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.get_group", new=AsyncMock(return_value=group)) as mock_get_group,
    ):
        await cmd_status(update, context)

    mock_get_group.assert_awaited_once_with(update.effective_chat.id)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "ok" in reply_text
    assert "connected" in reply_text
    assert "uc123abc" in reply_text
    assert "minute" in reply_text


@pytest.mark.asyncio
async def test_status_youtube_not_connected():
    update = make_update()
    context = make_context([])
    group = make_group()

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.get_group", new=AsyncMock(return_value=group)) as mock_get_group,
    ):
        await cmd_status(update, context)

    mock_get_group.assert_awaited_once_with(update.effective_chat.id)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "ok" in reply_text
    assert "not connected" in reply_text
    assert "minute" in reply_text


@pytest.mark.asyncio
async def test_status_non_admin():
    update = make_update()
    context = make_context([])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=False)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.get_group", new=AsyncMock()) as mock_get_group,
    ):
        await cmd_status(update, context)

    update.message.reply_text.assert_awaited_once_with("Admin privileges required.")
    mock_get_group.assert_not_awaited()


@pytest.mark.asyncio
async def test_status_group_not_registered():
    update = make_update()
    context = make_context([])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.get_group", new=AsyncMock(return_value=None)) as mock_get_group,
    ):
        await cmd_status(update, context)

    mock_get_group.assert_awaited_once_with(update.effective_chat.id)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "not registered" in reply_text or "register" in reply_text


@pytest.mark.asyncio
async def test_status_db_error():
    update = make_update()
    context = make_context([])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.get_group", new=AsyncMock(side_effect=RuntimeError("db fail"))) as mock_get_group,
    ):
        await cmd_status(update, context)

    mock_get_group.assert_awaited_once_with(update.effective_chat.id)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "error" in reply_text


@pytest.mark.asyncio
async def test_status_extra_args_ignored():
    update = make_update()
    context = make_context(["extra", "args"])
    group = make_group(yt_channel_id="UC456")

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.get_group", new=AsyncMock(return_value=group)) as mock_get_group,
    ):
        await cmd_status(update, context)

    mock_get_group.assert_awaited_once_with(update.effective_chat.id)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "ok" in reply_text


@pytest.mark.asyncio
async def test_status_args_none():
    update = make_update()
    context = make_context(None)
    group = make_group()

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.get_group", new=AsyncMock(return_value=group)) as mock_get_group,
    ):
        await cmd_status(update, context)

    mock_get_group.assert_awaited_once_with(update.effective_chat.id)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "ok" in reply_text
    assert "not connected" in reply_text
