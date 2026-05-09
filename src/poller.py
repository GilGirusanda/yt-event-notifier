import asyncio
import logging

from src.db import queries

logger = logging.getLogger(__name__)


async def run_poll() -> None:
    groups = await queries.list_groups()
    await asyncio.gather(*[_poll_group(dict(group)) for group in groups])


async def _poll_group(group: dict) -> None:
    group_id = group["group_id"]
    try:
        await _check_and_create_streams(group)
        await _send_reminders(group)
        await _detect_live(group)
        await _cleanup_ended(group_id)
    except Exception:
        logger.exception("Poll failed for group %d", group_id)


async def _check_and_create_streams(group: dict) -> None:
    pass


async def _send_reminders(group: dict) -> None:
    pass


async def _detect_live(group: dict) -> None:
    pass


async def _cleanup_ended(group_id: int) -> None:
    await queries.delete_ended_streams(group_id)
