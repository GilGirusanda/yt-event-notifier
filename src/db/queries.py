from typing import Any

import aiosqlite

from src.db.client import get_connection


async def upsert_group(group_id: int) -> None:
    conn = get_connection()
    await conn.execute("INSERT OR IGNORE INTO groups (group_id) VALUES (?)", (group_id,))
    await conn.commit()


async def get_group(group_id: int) -> aiosqlite.Row | None:
    conn = get_connection()
    async with conn.execute("SELECT * FROM groups WHERE group_id = ?", (group_id,)) as cur:
        return await cur.fetchone()


async def list_groups() -> list[aiosqlite.Row]:
    conn = get_connection()
    async with conn.execute("SELECT * FROM groups") as cur:
        return await cur.fetchall()


async def update_group(group_id: int, **fields: Any) -> None:
    conn = get_connection()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    await conn.execute(
        f"UPDATE groups SET {set_clause} WHERE group_id = ?",
        (*fields.values(), group_id),
    )
    await conn.commit()


async def add_slot(group_id: int, day_of_week: int, local_time: str) -> int:
    conn = get_connection()
    cursor = await conn.execute(
        "INSERT INTO slots (group_id, day_of_week, local_time) VALUES (?, ?, ?)",
        (group_id, day_of_week, local_time),
    )
    await conn.commit()
    return cursor.lastrowid


async def get_slot(slot_id: int) -> aiosqlite.Row | None:
    conn = get_connection()
    async with conn.execute("SELECT * FROM slots WHERE slot_id = ?", (slot_id,)) as cur:
        return await cur.fetchone()


async def list_slots(group_id: int) -> list[aiosqlite.Row]:
    conn = get_connection()
    async with conn.execute("SELECT * FROM slots WHERE group_id = ?", (group_id,)) as cur:
        return await cur.fetchall()


async def remove_slot(slot_id: int) -> None:
    conn = get_connection()
    await conn.execute("DELETE FROM slots WHERE slot_id = ?", (slot_id,))
    await conn.commit()


async def update_slot(slot_id: int, **fields: Any) -> None:
    conn = get_connection()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    await conn.execute(
        f"UPDATE slots SET {set_clause} WHERE slot_id = ?",
        (*fields.values(), slot_id),
    )
    await conn.commit()


async def upsert_stream(
    broadcast_id: str,
    group_id: int,
    slot_id: int,
    scheduled_start: int,
    yt_url: str,
) -> None:
    conn = get_connection()
    await conn.execute(
        """INSERT OR IGNORE INTO streams
           (broadcast_id, group_id, slot_id, scheduled_start, yt_url)
           VALUES (?, ?, ?, ?, ?)""",
        (broadcast_id, group_id, slot_id, scheduled_start, yt_url),
    )
    await conn.commit()


async def list_active_streams(group_id: int) -> list[aiosqlite.Row]:
    conn = get_connection()
    async with conn.execute(
        "SELECT * FROM streams WHERE group_id = ? AND status != 'ended'", (group_id,)
    ) as cur:
        return await cur.fetchall()


async def update_stream(broadcast_id: str, **fields: Any) -> None:
    conn = get_connection()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    await conn.execute(
        f"UPDATE streams SET {set_clause} WHERE broadcast_id = ?",
        (*fields.values(), broadcast_id),
    )
    await conn.commit()


async def delete_ended_streams(group_id: int) -> None:
    conn = get_connection()
    await conn.execute(
        "DELETE FROM streams WHERE group_id = ? AND status = 'ended'", (group_id,)
    )
    await conn.commit()
