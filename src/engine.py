import logging
import os
from datetime import datetime

from dateutil import tz
from dateutil.relativedelta import relativedelta
from google.oauth2.credentials import Credentials
from telegram import Bot

from src.db.client import db_context
from src.db.queries import (
    list_active_streams,
    list_groups,
    list_slots,
    update_stream,
    upsert_stream,
)
from src.youtube.client import YouTubeClient

logger = logging.getLogger(__name__)


def get_next_occurrence(day_of_week: int, local_time: str, timezone: str) -> datetime:
    """Calculate the next exact occurrence in UTC for the given slot."""
    zone = tz.gettz(timezone)
    if not zone:
        zone = tz.UTC
        
    now_local = datetime.now(zone)
    hours, minutes = map(int, local_time.split(":"))
    
    candidate = now_local.replace(hour=hours, minute=minutes, second=0, microsecond=0)
    
    if candidate <= now_local:
        candidate += relativedelta(days=1)
        
    while candidate.weekday() != day_of_week:
        candidate += relativedelta(days=1)
        
    return candidate.astimezone(tz.UTC)


async def _process_group(bot: Bot, group: dict) -> None:
    chat_id = group["group_id"]
    timezone = group["timezone"]
    auto_create = group["auto_create"]
    
    credentials = Credentials(
        token=group["yt_access_token"],
        refresh_token=group["yt_refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ.get("GOOGLE_CLIENT_ID"),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    )
    yt = YouTubeClient(credentials)
    
    # 1. Active Streams Monitoring
    active_streams = await list_active_streams(chat_id)
    for stream in active_streams:
        broadcast_id = stream["broadcast_id"]
        status = yt.get_broadcast_status(broadcast_id)
        
        if not status:
            continue
            
        if status in ("complete", "revoked"):
            await update_stream(broadcast_id, status="ended")
            continue
            
        if status == "live" and not stream["live_sent"]:
            await bot.send_message(chat_id, f"🔴 We are LIVE! Join here: {stream['yt_url']}")
            await update_stream(broadcast_id, status="live", live_sent=1)
            
        if status in ("ready", "created") and not stream["reminder_sent"]:
            sched_dt = datetime.fromtimestamp(stream["scheduled_start"], tz=tz.UTC)
            if (sched_dt - datetime.now(tz.UTC)).total_seconds() <= 3600:
                await bot.send_message(chat_id, f"⏰ Stream starting in less than 1 hour!\n{stream['yt_url']}")
                await update_stream(broadcast_id, reminder_sent=1)

    # 2. Slot checking and Auto-Create
    slots = await list_slots(chat_id)
    now_utc = datetime.now(tz.UTC)
    
    for slot in slots:
        next_dt_utc = get_next_occurrence(slot["day_of_week"], slot["local_time"], timezone)
        time_until = (next_dt_utc - now_utc).total_seconds()
        
        if time_until <= 86400:
            iso_start = next_dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            target_ts = int(next_dt_utc.timestamp())
            
            tracked = any(s["slot_id"] == slot["slot_id"] and s["scheduled_start"] == target_ts for s in active_streams)
            
            if not tracked and auto_create:
                existing = yt.find_broadcast(iso_start)
                
                if existing:
                    b_id = existing["id"]
                    url = f"https://youtube.com/live/{b_id}"
                    await upsert_stream(b_id, chat_id, slot["slot_id"], target_ts, url)
                else:
                    title = slot["title_template"].replace("{date}", next_dt_utc.strftime("%Y-%m-%d"))
                    broadcast_resp = yt.create_broadcast(title, iso_start)
                    b_id = broadcast_resp["id"]
                    url = f"https://youtube.com/live/{b_id}"
                    
                    stream_resp = yt.create_stream(title)
                    s_id = stream_resp["id"]
                    yt.bind_broadcast(b_id, s_id)
                    
                    await upsert_stream(b_id, chat_id, slot["slot_id"], target_ts, url)
                    await bot.send_message(chat_id, f"✅ Auto-created upcoming stream for '{title}':\n{url}")


async def run_polling_cycle(bot: Bot) -> None:
    logger.info("Starting polling cycle")
    async with db_context():
        groups = await list_groups()
        for group in groups:
            if not group["yt_access_token"]:
                continue
                
            try:
                await _process_group(bot, group)
            except Exception as e:
                logger.exception("Error processing group %s", group["group_id"])
    logger.info("Finished polling cycle")
