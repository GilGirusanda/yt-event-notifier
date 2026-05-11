import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.bot.commands import cmd_set_reminder


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


# --- Happy path ---

@pytest.mark.asyncio
async def test_set_reminder_integer_success():
    update = make_update()
    context = make_context(["2"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_reminder(update, context)

    mock_upsert.assert_awaited_once_with(update.effective_chat.id)
    mock_update.assert_awaited_once_with(update.effective_chat.id, reminder_hours=2.0)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "2" in reply_text and "hour" in reply_text


@pytest.mark.asyncio
async def test_set_reminder_float_success():
    update = make_update()
    context = make_context(["0.5"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_reminder(update, context)

    mock_upsert.assert_awaited_once_with(update.effective_chat.id)
    mock_update.assert_awaited_once_with(update.effective_chat.id, reminder_hours=0.5)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "hour" in reply_text


@pytest.mark.asyncio
async def test_set_reminder_minimum_positive_value():
    update = make_update()
    context = make_context(["0.01"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_reminder(update, context)

    mock_update.assert_awaited_once_with(update.effective_chat.id, reminder_hours=0.01)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "hour" in reply_text


@pytest.mark.asyncio
async def test_set_reminder_large_value():
    update = make_update()
    context = make_context(["48"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_reminder(update, context)

    mock_update.assert_awaited_once_with(update.effective_chat.id, reminder_hours=48.0)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "hour" in reply_text


# --- Access control ---

@pytest.mark.asyncio
async def test_set_reminder_non_admin():
    update = make_update()
    context = make_context(["1"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=False)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_reminder(update, context)

    update.message.reply_text.assert_awaited_once_with("Admin privileges required.")
    mock_update.assert_not_awaited()


# --- Input validation ---

@pytest.mark.asyncio
async def test_set_reminder_no_args():
    update = make_update()
    context = make_context([])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_reminder(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "/setreminder" in reply_text
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_reminder_args_none():
    update = make_update()
    context = make_context(None)

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_reminder(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "/setreminder" in reply_text
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_reminder_too_many_args():
    update = make_update()
    context = make_context(["1", "2"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_reminder(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "/setreminder" in reply_text
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_reminder_non_numeric_arg():
    update = make_update()
    context = make_context(["abc"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_reminder(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "/setreminder" in reply_text
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_reminder_zero():
    update = make_update()
    context = make_context(["0"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_reminder(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "greater than 0" in reply_text or "must be" in reply_text or "invalid" in reply_text
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_reminder_negative():
    update = make_update()
    context = make_context(["-1"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_reminder(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "greater than 0" in reply_text or "must be" in reply_text or "invalid" in reply_text
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_reminder_whitespace_arg():
    update = make_update()
    context = make_context(["  "])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_reminder(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "/setreminder" in reply_text
    mock_update.assert_not_awaited()


# --- DB error ---

@pytest.mark.asyncio
async def test_set_reminder_db_error():
    update = make_update()
    context = make_context(["1"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock(side_effect=RuntimeError("db fail"))),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_set_reminder(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "error" in reply_text or "fail" in reply_text
    mock_update.assert_not_awaited()
