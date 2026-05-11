import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.bot.commands import cmd_remove_slot


def make_update(chat_id: int = 123456) -> MagicMock:
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.message.reply_text = AsyncMock()
    return update


def make_context(args) -> MagicMock:
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
async def test_remove_slot_success():
    update = make_update()
    context = make_context(["42"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.remove_slot", new=AsyncMock()) as mock_remove,
    ):
        await cmd_remove_slot(update, context)

    mock_remove.assert_awaited_once_with(42)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "slot" in reply_text and "42" in reply_text


@pytest.mark.asyncio
async def test_remove_slot_non_admin():
    update = make_update()
    context = make_context(["1"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=False)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.remove_slot", new=AsyncMock()) as mock_remove,
    ):
        await cmd_remove_slot(update, context)

    update.message.reply_text.assert_awaited_once_with("Admin privileges required.")
    mock_remove.assert_not_awaited()


@pytest.mark.asyncio
async def test_remove_slot_no_args():
    update = make_update()
    context = make_context([])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.remove_slot", new=AsyncMock()) as mock_remove,
    ):
        await cmd_remove_slot(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "/removeslot" in reply_text
    mock_remove.assert_not_awaited()


@pytest.mark.asyncio
async def test_remove_slot_args_none():
    update = make_update()
    context = make_context(None)

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.remove_slot", new=AsyncMock()) as mock_remove,
    ):
        await cmd_remove_slot(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "/removeslot" in reply_text
    mock_remove.assert_not_awaited()


@pytest.mark.asyncio
async def test_remove_slot_too_many_args():
    update = make_update()
    context = make_context(["1", "extra"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.remove_slot", new=AsyncMock()) as mock_remove,
    ):
        await cmd_remove_slot(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "/removeslot" in reply_text
    mock_remove.assert_not_awaited()


@pytest.mark.asyncio
async def test_remove_slot_non_integer_id():
    update = make_update()
    context = make_context(["abc"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.remove_slot", new=AsyncMock()) as mock_remove,
    ):
        await cmd_remove_slot(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "/removeslot" in reply_text or "invalid" in reply_text
    mock_remove.assert_not_awaited()


@pytest.mark.asyncio
async def test_remove_slot_float_id():
    update = make_update()
    context = make_context(["1.5"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.remove_slot", new=AsyncMock()) as mock_remove,
    ):
        await cmd_remove_slot(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "/removeslot" in reply_text or "invalid" in reply_text
    mock_remove.assert_not_awaited()


@pytest.mark.asyncio
async def test_remove_slot_zero_id():
    update = make_update()
    context = make_context(["0"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.remove_slot", new=AsyncMock()) as mock_remove,
    ):
        await cmd_remove_slot(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "positive" in reply_text or "invalid" in reply_text or "usage" in reply_text
    mock_remove.assert_not_awaited()


@pytest.mark.asyncio
async def test_remove_slot_negative_id():
    update = make_update()
    context = make_context(["-1"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.remove_slot", new=AsyncMock()) as mock_remove,
    ):
        await cmd_remove_slot(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "positive" in reply_text or "invalid" in reply_text or "usage" in reply_text
    mock_remove.assert_not_awaited()


@pytest.mark.asyncio
async def test_remove_slot_db_error():
    update = make_update()
    context = make_context(["1"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.remove_slot", new=AsyncMock(side_effect=RuntimeError("db fail"))) as mock_remove,
    ):
        await cmd_remove_slot(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "error" in reply_text or "fail" in reply_text
    mock_remove.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_remove_slot_minimum_valid_id():
    update = make_update()
    context = make_context(["1"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.remove_slot", new=AsyncMock()) as mock_remove,
    ):
        await cmd_remove_slot(update, context)

    mock_remove.assert_awaited_once_with(1)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "slot" in reply_text and "removed" in reply_text


@pytest.mark.asyncio
async def test_remove_slot_large_id():
    update = make_update()
    context = make_context(["999999"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.remove_slot", new=AsyncMock()) as mock_remove,
    ):
        await cmd_remove_slot(update, context)

    mock_remove.assert_awaited_once_with(999999)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "slot" in reply_text and "removed" in reply_text
