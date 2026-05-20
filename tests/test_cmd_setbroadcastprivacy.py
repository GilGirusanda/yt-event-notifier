import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.bot.commands import cmd_setbroadcastprivacy


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
async def test_setbroadcastprivacy_public_success():
    update = make_update()
    context = make_context(["public"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_setbroadcastprivacy(update, context)

    mock_upsert.assert_awaited_once_with(update.effective_chat.id)
    mock_update.assert_awaited_once_with(update.effective_chat.id, broadcast_privacy="public")
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "public" in reply_text


@pytest.mark.asyncio
async def test_setbroadcastprivacy_unlisted_success():
    update = make_update()
    context = make_context(["unlisted"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_setbroadcastprivacy(update, context)

    mock_upsert.assert_awaited_once_with(update.effective_chat.id)
    mock_update.assert_awaited_once_with(update.effective_chat.id, broadcast_privacy="unlisted")
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "unlisted" in reply_text


@pytest.mark.asyncio
async def test_setbroadcastprivacy_private_success():
    update = make_update()
    context = make_context(["private"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_setbroadcastprivacy(update, context)

    mock_upsert.assert_awaited_once_with(update.effective_chat.id)
    mock_update.assert_awaited_once_with(update.effective_chat.id, broadcast_privacy="private")
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "private" in reply_text


@pytest.mark.asyncio
async def test_setbroadcastprivacy_case_insensitive_PUBLIC():
    update = make_update()
    context = make_context(["PUBLIC"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_setbroadcastprivacy(update, context)

    mock_upsert.assert_awaited_once_with(update.effective_chat.id)
    mock_update.assert_awaited_once_with(update.effective_chat.id, broadcast_privacy="public")
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "public" in reply_text


@pytest.mark.asyncio
async def test_setbroadcastprivacy_case_insensitive_Unlisted():
    update = make_update()
    context = make_context(["Unlisted"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_setbroadcastprivacy(update, context)

    mock_upsert.assert_awaited_once_with(update.effective_chat.id)
    mock_update.assert_awaited_once_with(update.effective_chat.id, broadcast_privacy="unlisted")
    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "unlisted" in reply_text


@pytest.mark.asyncio
async def test_setbroadcastprivacy_non_admin():
    update = make_update()
    context = make_context(["public"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=False)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_setbroadcastprivacy(update, context)

    update.message.reply_text.assert_awaited_once_with("Admin privileges required.")
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_setbroadcastprivacy_no_args():
    update = make_update()
    context = make_context([])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_setbroadcastprivacy(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "setbroadcastprivacy" in reply_text
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_setbroadcastprivacy_too_many_args():
    update = make_update()
    context = make_context(["public", "extra"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_setbroadcastprivacy(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "setbroadcastprivacy" in reply_text
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_setbroadcastprivacy_args_none():
    update = make_update()
    context = make_context(None)

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_setbroadcastprivacy(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "setbroadcastprivacy" in reply_text
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_setbroadcastprivacy_invalid_arg():
    update = make_update()
    context = make_context(["hidden"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_setbroadcastprivacy(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "setbroadcastprivacy" in reply_text
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_setbroadcastprivacy_numeric_arg():
    update = make_update()
    context = make_context(["1"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_setbroadcastprivacy(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "usage" in reply_text or "setbroadcastprivacy" in reply_text
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_setbroadcastprivacy_db_error():
    update = make_update()
    context = make_context(["public"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock(side_effect=RuntimeError("db fail"))),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_setbroadcastprivacy(update, context)

    reply_text = update.message.reply_text.call_args[0][0].lower()
    assert "error" in reply_text or "fail" in reply_text
    mock_update.assert_not_awaited()
