import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.bot.commands import cmd_check

CHAT_ID = 123456


def make_update(chat_id: int = CHAT_ID) -> MagicMock:
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.message.reply_text = AsyncMock()
    return update


def make_context(args: list[str] | None = None) -> MagicMock:
    context = MagicMock()
    context.args = args
    context.bot.get_chat_member = AsyncMock()
    return context


@pytest.mark.asyncio
async def test_check_success():
    update = make_update()
    context = make_context()

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.run_polling_cycle", new=AsyncMock()) as mock_poll,
    ):
        await cmd_check(update, context)

    mock_poll.assert_awaited_once_with(context.bot)
    calls = [c[0][0].lower() for c in update.message.reply_text.call_args_list]
    assert any("sync" in t or "running" in t for t in calls)
    assert any("complete" in t or "streams" in t for t in calls)


@pytest.mark.asyncio
async def test_check_non_admin():
    update = make_update()
    context = make_context()

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=False)),
        patch("src.bot.commands.run_polling_cycle", new=AsyncMock()) as mock_poll,
    ):
        await cmd_check(update, context)

    update.message.reply_text.assert_awaited_once_with("Admin privileges required.")
    mock_poll.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_polling_error():
    update = make_update()
    context = make_context()

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.run_polling_cycle", new=AsyncMock(side_effect=RuntimeError("poll fail"))) as mock_poll,
    ):
        await cmd_check(update, context)

    mock_poll.assert_awaited_once_with(context.bot)
    reply = update.message.reply_text.call_args[0][0].lower()
    assert "error" in reply or "fail" in reply


@pytest.mark.asyncio
async def test_check_with_extra_args():
    update = make_update()
    context = make_context(["extra", "args"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.run_polling_cycle", new=AsyncMock()) as mock_poll,
    ):
        await cmd_check(update, context)

    mock_poll.assert_awaited_once_with(context.bot)


@pytest.mark.asyncio
async def test_check_with_none_args():
    update = make_update()
    context = make_context(None)

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.run_polling_cycle", new=AsyncMock()) as mock_poll,
    ):
        await cmd_check(update, context)

    mock_poll.assert_awaited_once_with(context.bot)
