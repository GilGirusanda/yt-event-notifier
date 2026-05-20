import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.bot.commands import cmd_set_template


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
async def test_set_template_success():
    update = make_update()
    context = make_context(["1", "Weekly", "Stream"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_template(update, context)

    mock_update_slot.assert_awaited_once_with(1, 123456, title_template="Weekly Stream")
    reply_text = update.message.reply_text.call_args[0][0]
    assert "1" in reply_text
    assert "Weekly Stream" in reply_text


@pytest.mark.asyncio
async def test_set_template_single_word_template():
    update = make_update()
    context = make_context(["2", "MyStream"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_template(update, context)

    mock_update_slot.assert_awaited_once_with(2, 123456, title_template="MyStream")
    reply_text = update.message.reply_text.call_args[0][0]
    assert "2" in reply_text
    assert "MyStream" in reply_text


@pytest.mark.asyncio
async def test_set_template_with_template_variables():
    update = make_update()
    context = make_context(["3", "Stream", "{date}", "on", "{channel}"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_template(update, context)

    mock_update_slot.assert_awaited_once_with(3, 123456, title_template="Stream {date} on {channel}")
    reply_text = update.message.reply_text.call_args[0][0]
    assert "3" in reply_text


@pytest.mark.asyncio
async def test_set_template_non_admin():
    update = make_update()
    context = make_context(["1", "Some Template"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=False)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_template(update, context)

    update.message.reply_text.assert_awaited_once_with("Admin privileges required.")
    mock_update_slot.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_template_no_args():
    update = make_update()
    context = make_context([])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_template(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "/settemplate" in reply_text
    mock_update_slot.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_template_only_slot_id():
    update = make_update()
    context = make_context(["1"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_template(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "/settemplate" in reply_text
    mock_update_slot.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_template_none_args():
    update = make_update()
    context = make_context(None)

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_template(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "/settemplate" in reply_text
    mock_update_slot.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_template_non_integer_slot_id():
    update = make_update()
    context = make_context(["abc", "Some Template"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_template(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "/settemplate" in reply_text
    mock_update_slot.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_template_zero_slot_id():
    update = make_update()
    context = make_context(["0", "Some Template"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_template(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "positive" in reply_text or "slot id" in reply_text
    mock_update_slot.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_template_negative_slot_id():
    update = make_update()
    context = make_context(["-1", "Some Template"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_template(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "positive" in reply_text or "slot id" in reply_text
    mock_update_slot.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_template_float_slot_id():
    update = make_update()
    context = make_context(["1.5", "Some Template"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_template(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "/settemplate" in reply_text
    mock_update_slot.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_template_minimum_valid_slot_id():
    update = make_update()
    context = make_context(["1", "Template"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock()) as mock_update_slot,
    ):
        await cmd_set_template(update, context)

    mock_update_slot.assert_awaited_once_with(1, 123456, title_template="Template")
    reply_text = update.message.reply_text.call_args[0][0]
    assert "1" in reply_text


@pytest.mark.asyncio
async def test_set_template_db_error():
    update = make_update()
    context = make_context(["1", "Weekly Stream"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.update_slot", new=AsyncMock(side_effect=RuntimeError("db fail"))),
    ):
        await cmd_set_template(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "error" in reply_text or "fail" in reply_text
