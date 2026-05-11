import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.bot.commands import cmd_start


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


@pytest.mark.asyncio
async def test_start_success():
    update = make_update()
    context = make_context([])

    with (
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
    ):
        await cmd_start(update, context)

    mock_upsert.assert_awaited_once_with(update.effective_chat.id)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "welcome" in reply_text or "setup" in reply_text


@pytest.mark.asyncio
async def test_start_reply_contains_setup_instructions():
    update = make_update()
    context = make_context([])

    with (
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
    ):
        await cmd_start(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert "/settimezone" in reply_text
    assert "/connectyoutube" in reply_text
    assert "/addslot" in reply_text


@pytest.mark.asyncio
async def test_start_no_admin_guard():
    """start is available to all members — no admin check should occur."""
    update = make_update()
    context = make_context([])

    with (
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=False)) as mock_admin,
    ):
        await cmd_start(update, context)

    mock_admin.assert_not_awaited()
    update.message.reply_text.assert_awaited_once()
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "welcome" in reply_text or "setup" in reply_text


@pytest.mark.asyncio
async def test_start_ignores_extra_args():
    """Extra args are silently ignored; command still registers and replies."""
    update = make_update()
    context = make_context(["unexpected", "args"])

    with (
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
    ):
        await cmd_start(update, context)

    mock_upsert.assert_awaited_once_with(update.effective_chat.id)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "welcome" in reply_text or "setup" in reply_text


@pytest.mark.asyncio
async def test_start_args_none():
    """None args are handled gracefully."""
    update = make_update()
    context = make_context(None)

    with (
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
    ):
        await cmd_start(update, context)

    mock_upsert.assert_awaited_once_with(update.effective_chat.id)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "welcome" in reply_text or "setup" in reply_text


@pytest.mark.asyncio
async def test_start_uses_chat_id():
    """upsert_group is called with the correct chat ID."""
    update = make_update(chat_id=999888)
    context = make_context([])

    with (
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
    ):
        await cmd_start(update, context)

    mock_upsert.assert_awaited_once_with(999888)


@pytest.mark.asyncio
async def test_start_db_error():
    """DB failure results in an error reply; handler does not crash."""
    update = make_update()
    context = make_context([])

    with (
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock(side_effect=RuntimeError("db fail"))) as mock_upsert,
    ):
        await cmd_start(update, context)

    mock_upsert.assert_awaited_once_with(update.effective_chat.id)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "error" in reply_text or "fail" in reply_text
