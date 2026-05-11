import aiosqlite

_CREATE_GROUPS = """
CREATE TABLE IF NOT EXISTS groups (
    group_id            INTEGER PRIMARY KEY,
    timezone            TEXT    NOT NULL DEFAULT 'UTC',
    reminder_hours      REAL    NOT NULL DEFAULT 1.0,
    check_window_hours  REAL    NOT NULL DEFAULT 24.0,
    auto_create         BOOLEAN NOT NULL DEFAULT 0,
    yt_channel_id       TEXT,
    yt_access_token     TEXT,
    yt_refresh_token    TEXT,
    yt_token_expiry     INTEGER,
    last_manual_check   INTEGER,
    broadcast_privacy   TEXT    NOT NULL DEFAULT 'public'
)
"""

_CREATE_SLOTS = """
CREATE TABLE IF NOT EXISTS slots (
    slot_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id        INTEGER NOT NULL REFERENCES groups(group_id) ON DELETE CASCADE,
    day_of_week     INTEGER NOT NULL,
    local_time      TEXT    NOT NULL,
    title_template  TEXT    NOT NULL DEFAULT '',
    custom_message  TEXT    NOT NULL DEFAULT ''
)
"""

_CREATE_STREAMS = """
CREATE TABLE IF NOT EXISTS streams (
    broadcast_id    TEXT    PRIMARY KEY,
    group_id        INTEGER NOT NULL REFERENCES groups(group_id) ON DELETE CASCADE,
    slot_id         INTEGER NOT NULL REFERENCES slots(slot_id)   ON DELETE CASCADE,
    scheduled_start INTEGER NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'scheduled',
    yt_url          TEXT    NOT NULL DEFAULT '',
    reminder_sent   BOOLEAN NOT NULL DEFAULT 0,
    live_sent       BOOLEAN NOT NULL DEFAULT 0
)
"""


async def init_schema(conn: aiosqlite.Connection) -> None:
    await conn.execute("PRAGMA foreign_keys = ON")
    await conn.execute(_CREATE_GROUPS)
    await conn.execute(_CREATE_SLOTS)
    await conn.execute(_CREATE_STREAMS)
    await conn.commit()
