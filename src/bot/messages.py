from datetime import datetime
from zoneinfo import ZoneInfo


def render_reminder(
    title: str,
    scheduled_start: datetime,
    yt_url: str,
    timezone: str,
    custom_message: str = "",
) -> str:
    local_time = scheduled_start.astimezone(ZoneInfo(timezone))
    text = (
        f"Upcoming stream: {title}\n"
        f"{local_time.strftime('%A, %d %b %Y at %H:%M %Z')}\n"
        f"{yt_url}"
    )
    if custom_message:
        text += f"\n\n{custom_message}"
    return text


def render_live_alert(title: str, yt_url: str, custom_message: str = "") -> str:
    text = f"Live now: {title}\n{yt_url}"
    if custom_message:
        text += f"\n\n{custom_message}"
    return text


def render_slot_title(template: str, scheduled_start: datetime, channel: str) -> str:
    return (
        template
        .replace("{{date}}", scheduled_start.strftime("%Y-%m-%d"))
        .replace("{{channel}}", channel)
    )
