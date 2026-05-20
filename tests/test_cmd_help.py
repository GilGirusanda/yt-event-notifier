import pytest
from unittest.mock import AsyncMock, MagicMock

from src.bot.commands import cmd_help


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
async def test_help_displays_all_commands():
    update = make_update()
    context = make_context([])

    await cmd_help(update, context)

    update.message.reply_text.assert_awaited_once()
    reply_text = update.message.reply_text.call_args[0][0]
    for cmd in [
        "/start", "/help", "/connectyoutube", "/disconnectyoutube",
        "/settimezone", "/setautocreate", "/setreminder", "/setcheckwindow",
        "/addslot", "/removeslot", "/settemplate", "/setmessage",
        "/listslots", "/streams", "/status", "/check",
        "/setbroadcastprivacy", "/setbroadcastdescription",
    ]:
        assert cmd in reply_text, f"Expected '{cmd}' in help output"


@pytest.mark.asyncio
async def test_help_available_to_non_admin():
    update = make_update()
    context = make_context([])
    context.bot.get_chat_member.return_value = MagicMock(status="member")

    await cmd_help(update, context)

    update.message.reply_text.assert_awaited_once()
    reply_text = update.message.reply_text.call_args[0][0]
    assert "/help" in reply_text


@pytest.mark.asyncio
async def test_help_ignores_extra_args():
    update = make_update()
    context = make_context(["extra", "args"])

    await cmd_help(update, context)

    update.message.reply_text.assert_awaited_once()
    reply_text = update.message.reply_text.call_args[0][0]
    assert "/help" in reply_text


@pytest.mark.asyncio
async def test_help_with_none_args():
    update = make_update()
    context = make_context(None)

    await cmd_help(update, context)

    update.message.reply_text.assert_awaited_once()
    reply_text = update.message.reply_text.call_args[0][0]
    assert "/help" in reply_text


@pytest.mark.asyncio
async def test_help_reply_contains_admin_label():
    update = make_update()
    context = make_context([])

    await cmd_help(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert "admin" in reply_text.lower()


@pytest.mark.asyncio
async def test_help_reply_is_string():
    update = make_update()
    context = make_context([])

    await cmd_help(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert isinstance(reply_text, str)
    assert len(reply_text) > 0
