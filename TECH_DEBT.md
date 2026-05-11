# Technical Debt

Items that are not blocking for v1 but should be addressed before hardening the codebase.
Severity: **Critical** | **Warning** | **Suggestion**

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

## [Suggestion] Inconsistent reply style across bot commands

**File:** `src/bot/commands.py`

`cmd_set_timezone` uses `✅` / `❌` prefixes on success and error replies. `cmd_set_autocreate` and `cmd_add_slot` do not. This produces an inconsistent UX where some commands feel polished and others do not.

**Suggested fix:** Agree on a single reply style (with or without emoji) and apply it uniformly across all command handlers. Consider centralising message templates in `src/bot/messages.py`.

---

## [Suggestion] Fragile `db_context` mock pattern in tests

**File:** `tests/test_cmd_set_autocreate.py` (and future test files)

`db_context` is mocked by passing a manually constructed `MagicMock` with `__aenter__`/`__aexit__` as `AsyncMock`. This works because `db_context` is an `@asynccontextmanager` function, but the mock does not carry a `spec`, so if `db_context` is refactored the mock can silently stop exercising the real interface.

**Suggested fix:** Extract a shared `make_db_context_mock()` fixture into `tests/conftest.py` (already done per-file) and consider adding a `spec` guard or switching to a purpose-built `AsyncContextManager` mock helper when the test suite grows.
