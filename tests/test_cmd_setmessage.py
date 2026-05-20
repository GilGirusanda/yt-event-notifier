import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.bot.commands import cmd_set_message


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
async def test_set_message_success_single_word():
    update = make_update()
    context = make_context(["1", "Hello!"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_message(update, context)

    mock_update_slot.assert_awaited_once_with(1, 123456, custom_message="Hello!")
    reply = update.message.reply_text.call_args[0][0]
    assert "1" in reply
    assert "Hello!" in reply


@pytest.mark.asyncio
async def test_set_message_success_multi_word():
    update = make_update()
    context = make_context(["3", "Join", "us", "for", "the", "weekly", "stream!"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_message(update, context)

    mock_update_slot.assert_awaited_once_with(3, 123456, custom_message="Join us for the weekly stream!")
    reply = update.message.reply_text.call_args[0][0]
    assert "3" in reply
    assert "Join us for the weekly stream!" in reply


@pytest.mark.asyncio
async def test_set_message_non_admin():
    update = make_update()
    context = make_context(["1", "Hello!"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=False)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_message(update, context)

    update.message.reply_text.assert_awaited_once_with("Admin privileges required.")
    mock_update_slot.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_message_no_args():
    update = make_update()
    context = make_context([])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_message(update, context)

    reply = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply or "/setmessage" in reply
    mock_update_slot.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_message_args_none():
    update = make_update()
    context = make_context(None)

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_message(update, context)

    reply = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply or "/setmessage" in reply
    mock_update_slot.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_message_only_slot_id_no_message():
    update = make_update()
    context = make_context(["1"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_message(update, context)

    reply = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply or "/setmessage" in reply
    mock_update_slot.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_message_invalid_slot_id_string():
    update = make_update()
    context = make_context(["abc", "Hello!"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_message(update, context)

    reply = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply or "/setmessage" in reply
    mock_update_slot.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_message_slot_id_zero():
    update = make_update()
    context = make_context(["0", "Hello!"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_message(update, context)

    reply = update.message.reply_text.call_args[0][0].lower()
    assert "positive" in reply or "slot id" in reply
    mock_update_slot.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_message_slot_id_negative():
    update = make_update()
    context = make_context(["-1", "Hello!"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_message(update, context)

    reply = update.message.reply_text.call_args[0][0].lower()
    assert "positive" in reply or "slot id" in reply
    mock_update_slot.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_message_slot_id_float_string():
    update = make_update()
    context = make_context(["1.5", "Hello!"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_message(update, context)

    reply = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply or "/setmessage" in reply
    mock_update_slot.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_message_minimum_valid_slot_id():
    update = make_update()
    context = make_context(["1", "msg"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_message(update, context)

    mock_update_slot.assert_awaited_once_with(1, 123456, custom_message="msg")
    reply = update.message.reply_text.call_args[0][0]
    assert "1" in reply


@pytest.mark.asyncio
async def test_set_message_large_slot_id():
    update = make_update()
    context = make_context(["9999", "Some message"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_message(update, context)

    mock_update_slot.assert_awaited_once_with(9999, 123456, custom_message="Some message")
    reply = update.message.reply_text.call_args[0][0]
    assert "9999" in reply


@pytest.mark.asyncio
async def test_set_message_db_error():
    update = make_update()
    context = make_context(["1", "Hello!"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock(side_effect=RuntimeError("db fail"))) as mock_update_slot,
    ):
        await cmd_set_message(update, context)

    mock_update_slot.assert_awaited_once()
    reply = update.message.reply_text.call_args[0][0].lower()
    assert "error" in reply or "fail" in reply
