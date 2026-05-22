import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.bot.commands import cmd_streams


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


def make_group(timezone="UTC"):
    return {
        "group_id": 123456,
        "timezone": timezone,
        "reminder_hours": 1.0,
        "check_window_hours": 24.0,
        "auto_create": 0,
        "yt_channel_id": None,
        "yt_access_token": None,
        "yt_refresh_token": None,
        "yt_token_expiry": None,
        "last_manual_check": None,
        "broadcast_privacy": "public",
        "broadcast_description": "",
        "broadcast_made_for_kids": 0,
    }


def make_stream(
    broadcast_id="abc123",
    scheduled_start=1700000000,
    status="scheduled",
    yt_url="https://youtube.com/watch?v=abc123",
):
    return {
        "broadcast_id": broadcast_id,
        "group_id": 123456,
        "slot_id": 1,
        "scheduled_start": scheduled_start,
        "status": status,
        "yt_url": yt_url,
        "reminder_sent": 0,
        "live_sent": 0,
    }


@pytest.mark.asyncio
async def test_streams_happy_path():
    update = make_update()
    context = make_context([])
    stream = make_stream()

    with (
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.get_group", new=AsyncMock(return_value=make_group())) as mock_get_group,
        patch("src.bot.commands.list_active_streams", new=AsyncMock(return_value=[stream])) as mock_list,
    ):
        await cmd_streams(update, context)

    mock_get_group.assert_awaited_once_with(update.effective_chat.id)
    mock_list.assert_awaited_once_with(update.effective_chat.id)
    reply_text = update.message.reply_text.call_args[0][0]
    assert stream["yt_url"] in reply_text
    assert "upcoming" in reply_text.lower() or "scheduled" in reply_text.lower()


@pytest.mark.asyncio
async def test_streams_no_streams():
    update = make_update()
    context = make_context([])

    with (
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.get_group", new=AsyncMock(return_value=make_group())),
        patch("src.bot.commands.list_active_streams", new=AsyncMock(return_value=[])) as mock_list,
    ):
        await cmd_streams(update, context)

    mock_list.assert_awaited_once_with(update.effective_chat.id)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "no" in reply_text or "upcoming" in reply_text


@pytest.mark.asyncio
async def test_streams_db_error():
    update = make_update()
    context = make_context([])

    with (
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.get_group", new=AsyncMock(side_effect=RuntimeError("db fail"))) as mock_get_group,
        patch("src.bot.commands.list_active_streams", new=AsyncMock()) as mock_list,
    ):
        await cmd_streams(update, context)

    mock_get_group.assert_awaited_once()
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "error" in reply_text or "fail" in reply_text
    mock_list.assert_not_awaited()


@pytest.mark.asyncio
async def test_streams_no_admin_required():
    """All members (non-admins) can use /streams without admin check."""
    update = make_update()
    context = make_context([])
    stream = make_stream()

    with (
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.get_group", new=AsyncMock(return_value=make_group())),
        patch("src.bot.commands.list_active_streams", new=AsyncMock(return_value=[stream])),
    ):
        await cmd_streams(update, context)

    context.bot.get_chat_member.assert_not_awaited()
    reply_text = update.message.reply_text.call_args[0][0]
    assert stream["yt_url"] in reply_text


@pytest.mark.asyncio
async def test_streams_group_none_falls_back_to_utc():
    """If the group is not registered, the handler defaults to UTC timezone."""
    update = make_update()
    context = make_context([])
    stream = make_stream(scheduled_start=1700000000)

    with (
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.get_group", new=AsyncMock(return_value=None)),
        patch("src.bot.commands.list_active_streams", new=AsyncMock(return_value=[stream])),
    ):
        await cmd_streams(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert stream["yt_url"] in reply_text
    assert "UTC" in reply_text


@pytest.mark.asyncio
async def test_streams_multiple_streams():
    update = make_update()
    context = make_context([])
    stream1 = make_stream(broadcast_id="abc1", yt_url="https://youtube.com/watch?v=abc1")
    stream2 = make_stream(broadcast_id="abc2", yt_url="https://youtube.com/watch?v=abc2")

    with (
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.get_group", new=AsyncMock(return_value=make_group())),
        patch("src.bot.commands.list_active_streams", new=AsyncMock(return_value=[stream1, stream2])),
    ):
        await cmd_streams(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert stream1["yt_url"] in reply_text
    assert stream2["yt_url"] in reply_text


@pytest.mark.asyncio
async def test_streams_live_stream_shown():
    """Live streams (status='live') are included in the listing."""
    update = make_update()
    context = make_context([])
    stream = make_stream(status="live")

    with (
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.get_group", new=AsyncMock(return_value=make_group())),
        patch("src.bot.commands.list_active_streams", new=AsyncMock(return_value=[stream])),
    ):
        await cmd_streams(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert stream["yt_url"] in reply_text
    assert "live" in reply_text.lower()


@pytest.mark.asyncio
async def test_streams_uses_group_timezone():
    """Scheduled times are formatted in the group's configured timezone."""
    update = make_update()
    context = make_context([])
    # epoch 0 = 1970-01-01 00:00 UTC = 1969-12-31 19:00 EST
    stream = make_stream(scheduled_start=0)

    with (
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.get_group", new=AsyncMock(return_value=make_group(timezone="America/New_York"))),
        patch("src.bot.commands.list_active_streams", new=AsyncMock(return_value=[stream])),
    ):
        await cmd_streams(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert stream["yt_url"] in reply_text
    assert "1969" in reply_text or "EST" in reply_text or "EDT" in reply_text


@pytest.mark.asyncio
async def test_streams_reply_once_per_call():
    """Handler sends exactly one reply message per invocation."""
    update = make_update()
    context = make_context([])
    stream = make_stream()

    with (
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.get_group", new=AsyncMock(return_value=make_group())),
        patch("src.bot.commands.list_active_streams", new=AsyncMock(return_value=[stream])),
    ):
        await cmd_streams(update, context)

    assert update.message.reply_text.await_count == 1
