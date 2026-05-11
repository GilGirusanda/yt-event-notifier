import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.bot.commands import cmd_set_check_window


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
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=None)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.mark.asyncio
async def test_set_check_window_success_integer():
    update = make_update()
    context = make_context(["24"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_check_window(update, context)

    mock_upsert.assert_awaited_once_with(update.effective_chat.id)
    mock_update.assert_awaited_once_with(update.effective_chat.id, check_window_hours=24.0)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "24" in reply_text
    assert "check window" in reply_text


@pytest.mark.asyncio
async def test_set_check_window_success_float():
    update = make_update()
    context = make_context(["12.5"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_check_window(update, context)

    mock_upsert.assert_awaited_once_with(update.effective_chat.id)
    mock_update.assert_awaited_once_with(update.effective_chat.id, check_window_hours=12.5)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "12.5" in reply_text


@pytest.mark.asyncio
async def test_set_check_window_minimum_valid():
    update = make_update()
    context = make_context(["0.1"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_check_window(update, context)

    mock_upsert.assert_awaited_once_with(update.effective_chat.id)
    mock_update.assert_awaited_once_with(update.effective_chat.id, check_window_hours=0.1)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "check window" in reply_text


@pytest.mark.asyncio
async def test_set_check_window_large_value():
    update = make_update()
    context = make_context(["168"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_check_window(update, context)

    mock_upsert.assert_awaited_once_with(update.effective_chat.id)
    mock_update.assert_awaited_once_with(update.effective_chat.id, check_window_hours=168.0)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "168" in reply_text


@pytest.mark.asyncio
async def test_set_check_window_non_admin():
    update = make_update()
    context = make_context(["24"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=False)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_check_window(update, context)

    update.message.reply_text.assert_awaited_once_with("Admin privileges required.")
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_check_window_no_args():
    update = make_update()
    context = make_context([])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_check_window(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "/setcheckwindow" in reply_text
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_check_window_args_none():
    update = make_update()
    context = make_context(None)

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_check_window(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "/setcheckwindow" in reply_text
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_check_window_too_many_args():
    update = make_update()
    context = make_context(["24", "extra"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_check_window(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "/setcheckwindow" in reply_text
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_check_window_non_numeric_arg():
    update = make_update()
    context = make_context(["abc"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_check_window(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "/setcheckwindow" in reply_text
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_check_window_zero_hours():
    update = make_update()
    context = make_context(["0"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_check_window(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "greater than 0" in reply_text or "must be" in reply_text
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_check_window_negative_hours():
    update = make_update()
    context = make_context(["-5"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_check_window(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "greater than 0" in reply_text or "must be" in reply_text
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_check_window_whitespace_arg():
    update = make_update()
    context = make_context(["  "])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_check_window(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "/setcheckwindow" in reply_text
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_check_window_db_error():
    update = make_update()
    context = make_context(["24"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock(side_effect=RuntimeError("db fail"))),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
        patch("src.bot.commands.logger") as mock_logger,
    ):
        await cmd_set_check_window(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "error" in reply_text or "fail" in reply_text
    mock_update.assert_not_awaited()
    mock_logger.exception.assert_called_once()
