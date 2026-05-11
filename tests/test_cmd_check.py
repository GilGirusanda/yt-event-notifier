import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.bot.commands import cmd_check

CHAT_ID = 123456
NOW_TS = 1_000_000


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


def make_db_context_mock():
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=None)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def make_datetime_mock(now_ts: int = NOW_TS):
    mock_dt = MagicMock()
    mock_dt.now.return_value.timestamp.return_value = float(now_ts)
    return mock_dt


def make_group_row(last_manual_check=None):
    return {"last_manual_check": last_manual_check}


@pytest.mark.asyncio
async def test_check_success_no_prior_check():
    update = make_update()
    context = make_context()

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.datetime", make_datetime_mock()),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
        patch("src.bot.commands.get_group", new=AsyncMock(return_value=make_group_row(None))) as mock_get,
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_check(update, context)

    mock_upsert.assert_awaited_once_with(CHAT_ID)
    mock_get.assert_awaited_once_with(CHAT_ID)
    mock_update.assert_awaited_once_with(CHAT_ID, last_manual_check=NOW_TS)
    reply = update.message.reply_text.call_args[0][0].lower()
    assert "poll triggered" in reply or "triggered" in reply


@pytest.mark.asyncio
async def test_check_success_rate_limit_expired():
    update = make_update()
    context = make_context()
    last_check = NOW_TS - 400

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.datetime", make_datetime_mock()),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.get_group", new=AsyncMock(return_value=make_group_row(last_check))),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_check(update, context)

    mock_update.assert_awaited_once_with(CHAT_ID, last_manual_check=NOW_TS)
    reply = update.message.reply_text.call_args[0][0].lower()
    assert "poll triggered" in reply or "triggered" in reply


@pytest.mark.asyncio
async def test_check_success_exactly_at_rate_limit():
    """Exactly 300 s since last check — allowed (boundary)."""
    update = make_update()
    context = make_context()
    last_check = NOW_TS - 300

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.datetime", make_datetime_mock()),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
        patch("src.bot.commands.get_group", new=AsyncMock(return_value=make_group_row(last_check))) as mock_get,
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_check(update, context)

    mock_upsert.assert_awaited_once_with(CHAT_ID)
    mock_get.assert_awaited_once_with(CHAT_ID)
    mock_update.assert_awaited_once_with(CHAT_ID, last_manual_check=NOW_TS)
    reply = update.message.reply_text.call_args[0][0].lower()
    assert "poll triggered" in reply or "triggered" in reply


@pytest.mark.asyncio
async def test_check_rate_limited():
    """100 s since last check — rate limited."""
    update = make_update()
    context = make_context()
    last_check = NOW_TS - 100

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.datetime", make_datetime_mock()),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.get_group", new=AsyncMock(return_value=make_group_row(last_check))),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_check(update, context)

    mock_update.assert_not_awaited()
    reply = update.message.reply_text.call_args[0][0].lower()
    assert "rate" in reply or "wait" in reply or "limit" in reply


@pytest.mark.asyncio
async def test_check_rate_limited_boundary_299():
    """299 s since last check — still rate limited."""
    update = make_update()
    context = make_context()
    last_check = NOW_TS - 299

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.datetime", make_datetime_mock()),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.get_group", new=AsyncMock(return_value=make_group_row(last_check))),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_check(update, context)

    mock_update.assert_not_awaited()
    reply = update.message.reply_text.call_args[0][0].lower()
    assert "rate" in reply or "wait" in reply or "limit" in reply


@pytest.mark.asyncio
async def test_check_non_admin():
    update = make_update()
    context = make_context()

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=False)),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()) as mock_upsert,
        patch("src.bot.commands.get_group", new=AsyncMock()) as mock_get,
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_check(update, context)

    update.message.reply_text.assert_awaited_once_with("Admin privileges required.")
    mock_upsert.assert_not_awaited()
    mock_get.assert_not_awaited()
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_db_error():
    update = make_update()
    context = make_context()

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.datetime", make_datetime_mock()),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock(side_effect=RuntimeError("db fail"))),
        patch("src.bot.commands.get_group", new=AsyncMock()) as mock_get,
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_check(update, context)

    reply = update.message.reply_text.call_args[0][0].lower()
    assert "error" in reply or "fail" in reply
    mock_get.assert_not_awaited()
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_with_none_args():
    """No arguments required; None args behaves like no args."""
    update = make_update()
    context = make_context(None)

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.datetime", make_datetime_mock()),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.get_group", new=AsyncMock(return_value=make_group_row(None))),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_check(update, context)

    mock_update.assert_awaited_once_with(CHAT_ID, last_manual_check=NOW_TS)
    reply = update.message.reply_text.call_args[0][0].lower()
    assert "poll triggered" in reply or "triggered" in reply


@pytest.mark.asyncio
async def test_check_with_extra_args():
    """Extra args are ignored — command still succeeds."""
    update = make_update()
    context = make_context(["extra", "args"])

    with (
        patch("src.bot.commands._require_admin", new=AsyncMock(return_value=True)),
        patch("src.bot.commands.datetime", make_datetime_mock()),
        patch("src.bot.commands.db_context", return_value=make_db_context_mock()),
        patch("src.bot.commands.upsert_group", new=AsyncMock()),
        patch("src.bot.commands.get_group", new=AsyncMock(return_value=make_group_row(None))),
        patch("src.bot.commands.update_group", new=AsyncMock()) as mock_update,
    ):
        await cmd_check(update, context)

    mock_update.assert_awaited_once_with(CHAT_ID, last_manual_check=NOW_TS)
    reply = update.message.reply_text.call_args[0][0].lower()
    assert "poll triggered" in reply or "triggered" in reply
