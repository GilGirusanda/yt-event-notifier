# Technical Debt

Items that are not blocking for v1 but should be addressed before hardening the codebase.
Severity: **Critical** | **Warning** | **Suggestion**

---

## [Critical] `/check` polls all groups instead of the invoking group

**File:** `src/bot/commands.py` — `cmd_check`

`cmd_check` calls `run_polling_cycle(context.bot)` with no group filter. This is the same global engine used by the EventBridge scheduler — it iterates over every registered group. An admin in group A therefore triggers YouTube API calls and potentially sends notifications for groups B, C, D.

**Suggested fix:** Add a `group_id` parameter to `run_polling_cycle` (or introduce a separate `run_polling_cycle_for_group`) and pass `update.effective_chat.id` from `cmd_check`.

---

## [Critical] `/status` next poll time is fabricated, not derived from the scheduler

**File:** `src/bot/commands.py` — `cmd_status`

The "next scheduled poll" value is computed as `15 - (now.minute % 15)`, a pure arithmetic guess that assumes a fixed 15-minute cron boundary and has no connection to the actual EventBridge schedule. If the poll interval changes, or if the adaptive 5-minute rule fires first, the displayed value will be silently wrong.

**Suggested fix:** Either remove the next-poll line until real scheduler state is available (e.g. stored as a `last_polled` timestamp in the DB), or derive it from a known `POLL_INTERVAL_MINUTES` constant so at least the assumption is explicit and single-sourced.

---

## [Warning] Unparameterised column names in `update_group` and `update_slot`

**File:** `src/db/queries.py:26–33`, `src/db/queries.py:67–73`

`update_group` and `update_slot` build their SQL SET clause by interpolating kwarg *names* directly into the query string:

```python
set_clause = ", ".join(f"{k} = ?" for k in fields)
```

Values are parameterised (safe), but column names are not. If a caller ever passes a non-hardcoded keyword — e.g. from user input or a dynamic mapping — it would be a SQL injection vector. All current callers use hardcoded keywords so there is no live exploit path, but the design makes it easy to introduce one accidentally.

**Suggested fix:** Either restrict `update_group`/`update_slot` to a fixed allowlist of valid column names and raise on anything outside it, or replace the generic helpers with explicit per-field update functions.

---

## [Warning] S3 upload failure in `db_context` produces a spurious error reply

**File:** `src/db/client.py:61–63`

`db_context` uploads the SQLite file to S3 in the `finally` block, *after* committing and closing the connection. If the upload raises (e.g. expired credentials, network timeout), the exception propagates out of the `async with db_context()` block into the command handler's `except Exception` clause. The user receives an error message even though the DB write succeeded. This affects every command that wraps DB work in a try/except.

**Suggested fix:** Catch and log the S3 upload error separately inside `db_context` rather than letting it propagate, or decouple upload from the context manager exit so command handlers are not exposed to infrastructure failures.

---

## [Suggestion] `/help` omits "next scheduled poll time" from `/status` description

**File:** `src/bot/commands.py` — `cmd_help`

The `/help` entry for `/status` reads "Show bot health and YouTube connection status" but omits the next scheduled poll time, which the command also displays. Once the poll-time display is corrected (see Critical item above), the help text will remain stale.

**Suggested fix:** Update the `/status` line in `cmd_help` to "Show bot health, YouTube connection status, and next scheduled poll time (admin)" once the underlying poll-time logic is fixed.

---

## [Suggestion] `/disconnectyoutube` may leave `yt_channel_name` stale after disconnect

**File:** `src/bot/commands.py` — `cmd_disconnect_youtube`

`cmd_disconnect_youtube` clears `yt_channel_id`, `yt_access_token`, `yt_refresh_token`, and `yt_token_expiry`, but does not clear `yt_channel_name`. If a `yt_channel_name` column is added (see "raw channel ID" item below), a reconnect to a different channel would leave the stale name visible in `/status` until the new OAuth flow overwrites it.

**Suggested fix:** Include `yt_channel_name=None` in the `update_group` call inside `cmd_disconnect_youtube` whenever that column is added.

---

## [Suggestion] Inconsistent reply style across bot commands

**File:** `src/bot/commands.py`

`cmd_set_timezone` uses `✅` / `❌` prefixes on success and error replies. `cmd_set_autocreate` and `cmd_add_slot` do not. This produces an inconsistent UX where some commands feel polished and others do not.

**Suggested fix:** Agree on a single reply style (with or without emoji) and apply it uniformly across all command handlers. Consider centralising message templates in `src/bot/messages.py`.

---

## [Suggestion] `/status` displays raw channel ID instead of channel name

**File:** `src/bot/commands.py` — `cmd_status`

The YouTube connection line in `/status` shows the `yt_channel_id` value (e.g. `UCxxxxxxx`) rather than a human-readable channel name. This is inconsistent with the `{channel}` title template variable, which resolves to the connected channel's display name per the PRD.

The schema has no `yt_channel_name` column; fixing this requires adding the column, fetching the name from the YouTube Data API during the OAuth callback, and storing it alongside the tokens.

**Suggested fix:** Add `yt_channel_name TEXT` to the `groups` table, populate it in `handle_oauth_callback` via a `channels.list` API call, and update `cmd_status` to display it.

---

## [Suggestion] Fragile `db_context` mock pattern in tests

**File:** `tests/test_cmd_set_autocreate.py` (and future test files)

`db_context` is mocked by passing a manually constructed `MagicMock` with `__aenter__`/`__aexit__` as `AsyncMock`. This works because `db_context` is an `@asynccontextmanager` function, but the mock does not carry a `spec`, so if `db_context` is refactored the mock can silently stop exercising the real interface.

**Suggested fix:** Extract a shared `make_db_context_mock()` fixture into `tests/conftest.py` (already done per-file) and consider adding a `spec` guard or switching to a purpose-built `AsyncContextManager` mock helper when the test suite grows.
