import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.bot.commands import cmd_setbroadcastmadeforkids


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
async def test_setbroadcastmadeforkids_no_success():
    update = make_update()
    context = make_context(["no"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_setbroadcastmadeforkids(update, context)

    mock_upsert.assert_awaited_once_with(update.effective_chat.id)
    mock_update.assert_awaited_once_with(update.effective_chat.id, broadcast_made_for_kids=False)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "no" in reply_text


@pytest.mark.asyncio
async def test_setbroadcastmadeforkids_yes_success():
    update = make_update()
    context = make_context(["yes"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_setbroadcastmadeforkids(update, context)

    mock_upsert.assert_awaited_once_with(update.effective_chat.id)
    mock_update.assert_awaited_once_with(update.effective_chat.id, broadcast_made_for_kids=True)
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "yes" in reply_text


@pytest.mark.asyncio
async def test_setbroadcastmadeforkids_case_insensitive_NO():
    update = make_update()
    context = make_context(["NO"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_setbroadcastmadeforkids(update, context)

    mock_update.assert_awaited_once_with(update.effective_chat.id, broadcast_made_for_kids=False)


@pytest.mark.asyncio
async def test_setbroadcastmadeforkids_case_insensitive_Yes():
    update = make_update()
    context = make_context(["Yes"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_setbroadcastmadeforkids(update, context)

    mock_update.assert_awaited_once_with(update.effective_chat.id, broadcast_made_for_kids=True)


@pytest.mark.asyncio
async def test_setbroadcastmadeforkids_non_admin():
    update = make_update()
    context = make_context(["no"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=False)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_setbroadcastmadeforkids(update, context)

    update.message.reply_text.assert_awaited_once_with("Admin privileges required.")
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_setbroadcastmadeforkids_no_args():
    update = make_update()
    context = make_context([])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_setbroadcastmadeforkids(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "setbroadcastmadeforkids" in reply_text
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_setbroadcastmadeforkids_invalid_arg():
    update = make_update()
    context = make_context(["maybe"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_setbroadcastmadeforkids(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "setbroadcastmadeforkids" in reply_text
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_setbroadcastmadeforkids_too_many_args():
    update = make_update()
    context = make_context(["no", "extra"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_setbroadcastmadeforkids(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "setbroadcastmadeforkids" in reply_text
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_setbroadcastmadeforkids_args_none():
    update = make_update()
    context = make_context(None)

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_setbroadcastmadeforkids(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "setbroadcastmadeforkids" in reply_text
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_setbroadcastmadeforkids_db_error():
    update = make_update()
    context = make_context(["no"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock(side_effect=RuntimeError("db fail"))),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_setbroadcastmadeforkids(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "error" in reply_text or "fail" in reply_text
    mock_update.assert_not_awaited()
