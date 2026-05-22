import logging
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.db.client import db_context
from src.db.queries import (
    upsert_group,
    add_slot,
    list_slots,
    update_group,
    get_group,
    remove_slot,
    update_slot,
    list_active_streams,
)
from src.youtube.oauth import build_auth_url
from src.engine import run_polling_cycle

logger = logging.getLogger(__name__)


def build_application(token: str) -> Application:
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("connectyoutube", cmd_connect_youtube))
    app.add_handler(CommandHandler("disconnectyoutube", cmd_disconnect_youtube))
    app.add_handler(CommandHandler("settimezone", cmd_set_timezone))
    app.add_handler(CommandHandler("setautocreate", cmd_set_autocreate))
    app.add_handler(CommandHandler("setreminder", cmd_set_reminder))
    app.add_handler(CommandHandler("setcheckwindow", cmd_set_check_window))
    app.add_handler(CommandHandler("addslot", cmd_add_slot))
    app.add_handler(CommandHandler("removeslot", cmd_remove_slot))
    app.add_handler(CommandHandler("settemplate", cmd_set_template))
    app.add_handler(CommandHandler("setmessage", cmd_set_message))
    app.add_handler(CommandHandler("listslots", cmd_list_slots))
    app.add_handler(CommandHandler("streams", cmd_streams))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("setbroadcastprivacy", cmd_setbroadcastprivacy))
    app.add_handler(
        CommandHandler("setbroadcastdescription", cmd_setbroadcastdescription)
    )
    app.add_handler(
        CommandHandler("setbroadcastmadeforkids", cmd_setbroadcastmadeforkids)
    )
    return app


async def _require_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    assert update.effective_chat and update.effective_user
    member = await context.bot.get_chat_member(
        update.effective_chat.id, update.effective_user.id
    )
    return member.status in ("administrator", "creator")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message and update.effective_chat
    chat_id = update.effective_chat.id
    try:
        async with db_context():
            await upsert_group(chat_id)
        await update.message.reply_text(
            "Welcome to yt-event-notifier!\n\n"
            "This bot notifies your group about upcoming YouTube live streams.\n\n"
            "Setup steps:\n"
            "1. Set your timezone: /settimezone <tz>  (e.g. /settimezone Europe/London)\n"
            "2. Connect your YouTube channel: /connectyoutube\n"
            "3. Add a weekly stream slot: /addslot <day> <HH:MM> <title>\n"
            "4. Configure reminders and more — see /help for all commands."
        )
    except Exception:
        logger.exception("Failed to register group")
        await update.message.reply_text(
            "Error registering this group. Please try again."
        )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message
    await update.message.reply_text(
        "Available commands:\n\n"
        "/start — Register the bot and display setup instructions\n"
        "/help — Display all available commands\n"
        "/connectyoutube — Link a YouTube channel to this group (admin)\n"
        "/disconnectyoutube — Remove the YouTube channel connection (admin)\n"
        "/settimezone <tz> — Set the group's timezone, e.g. Europe/London (admin)\n"
        "/setautocreate <on|off> — Toggle automatic YouTube stream creation (admin)\n"
        "/setreminder <hours> — Set the reminder window before stream start (admin)\n"
        "/setcheckwindow <hours> — Set how many hours before a slot to check/create the stream (admin)\n"
        "/addslot <day> <HH:MM> [title_template] — Add a weekly recurring slot (admin)\n"
        "/removeslot <slot_id> — Remove a scheduled slot by ID (admin)\n"
        "/settemplate <slot_id> <template> — Set the stream title template for a slot (admin)\n"
        "/setmessage <slot_id> <message> — Set the custom notification message for a slot (admin)\n"
        "/listslots — List all configured slots (admin)\n"
        "/streams — List upcoming tracked streams\n"
        "/status — Show bot health and YouTube connection status (admin)\n"
        "/check — Trigger an immediate poll (admin)\n"
        "/setbroadcastprivacy <public|unlisted|private> — Set auto-created broadcast privacy (admin)\n"
        "/setbroadcastdescription <text> — Set auto-created broadcast description (admin)\n"
        "/setbroadcastmadeforkids <yes|no> — Set whether auto-created broadcasts are made for kids (admin)"
    )


async def cmd_connect_youtube(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    assert update.message and update.effective_chat
    if not await _require_admin(update, context):
        await update.message.reply_text("Admin privileges required.")
        return

    chat_id = update.effective_chat.id
    try:
        auth_url = build_auth_url(chat_id)
        await update.message.reply_text(
            f"Please click the link below to authorize this bot to manage your YouTube broadcasts:\n\n{auth_url}"
        )
    except Exception as e:
        logger.exception("Failed to create OAuth flow")
        await update.message.reply_text(f"Configuration error: {e}")


async def cmd_disconnect_youtube(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    assert update.message and update.effective_chat
    if not await _require_admin(update, context):
        await update.message.reply_text("Admin privileges required.")
        return

    chat_id = update.effective_chat.id
    try:
        async with db_context():
            await update_group(
                chat_id,
                yt_access_token=None,
                yt_refresh_token=None,
                yt_token_expiry=None,
                yt_channel_id=None,
            )
        await update.message.reply_text(
            "✅ Successfully disconnected YouTube account. Your tokens have been deleted."
        )
    except Exception as e:
        logger.exception("Failed to disconnect YouTube")
        await update.message.reply_text(f"❌ Error disconnecting: {e}")


async def cmd_set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message and update.effective_chat
    if not await _require_admin(update, context):
        await update.message.reply_text("Admin privileges required.")
        return

    args = context.args
    if not args or len(args) != 1:
        await update.message.reply_text(
            "Usage: /settimezone <Timezone>\nExample: /settimezone Europe/London"
        )
        return

    tz_str = args[0]

    try:
        # Validate timezone
        ZoneInfo(tz_str)
    except ZoneInfoNotFoundError:
        await update.message.reply_text(
            f"Invalid timezone: '{tz_str}'. Please use standard IANA formats (e.g., Europe/London)."
        )
        return

    chat_id = update.effective_chat.id
    try:
        async with db_context():
            await upsert_group(chat_id)
            await update_group(chat_id, timezone=tz_str)

        logger.info("Set timezone to %s for chat %s", tz_str, chat_id)
        await update.message.reply_text(f"✅ Timezone successfully set to {tz_str}.")
    except Exception as e:
        logger.exception("Failed to set timezone")
        await update.message.reply_text(f"❌ Error setting timezone: {e}")


async def cmd_set_autocreate(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    assert update.message and update.effective_chat
    if not await _require_admin(update, context):
        await update.message.reply_text("Admin privileges required.")
        return

    args = context.args
    if not args or len(args) != 1 or args[0].lower() not in ["on", "off"]:
        await update.message.reply_text(
            "Usage: /setautocreate <on/off>\nExample: /setautocreate on"
        )
        return

    is_enabled = args[0].lower() == "on"
    chat_id = update.effective_chat.id

    try:
        async with db_context():
            await upsert_group(chat_id)
            await update_group(chat_id, auto_create=is_enabled)

        status = "Enabled ✅" if is_enabled else "Disabled ❌"
        await update.message.reply_text(f"Auto-create streams is now {status}.")
    except Exception as e:
        logger.exception("Failed to toggle auto_create")
        await update.message.reply_text(f"Error updating setting: {e}")


async def cmd_set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message and update.effective_chat
    if not await _require_admin(update, context):
        await update.message.reply_text("Admin privileges required.")
        return

    args = context.args
    if not args or len(args) != 1:
        await update.message.reply_text(
            "Usage: /setreminder <hours>\nExample: /setreminder 1"
        )
        return

    try:
        hours = float(args[0])
    except (ValueError, TypeError):
        await update.message.reply_text(
            "Usage: /setreminder <hours>\nExample: /setreminder 1"
        )
        return

    if hours <= 0:
        await update.message.reply_text("Reminder hours must be greater than 0.")
        return

    chat_id = update.effective_chat.id
    try:
        async with db_context():
            await upsert_group(chat_id)
            await update_group(chat_id, reminder_hours=hours)

        logger.info("Set reminder_hours to %s for chat %s", hours, chat_id)
        await update.message.reply_text(
            f"Reminder set to {hours:g} hour(s) before stream start."
        )
    except Exception:
        logger.exception("Failed to set reminder_hours")
        await update.message.reply_text("Error setting reminder. Please try again.")


async def cmd_set_check_window(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    assert update.message and update.effective_chat
    if not await _require_admin(update, context):
        await update.message.reply_text("Admin privileges required.")
        return

    args = context.args
    if not args or len(args) != 1:
        await update.message.reply_text(
            "Usage: /setcheckwindow <hours>\nExample: /setcheckwindow 24"
        )
        return

    try:
        hours = float(args[0])
    except (ValueError, TypeError):
        await update.message.reply_text(
            "Usage: /setcheckwindow <hours>\nExample: /setcheckwindow 24"
        )
        return

    if hours <= 0:
        await update.message.reply_text("Check window hours must be greater than 0.")
        return

    chat_id = update.effective_chat.id
    try:
        async with db_context():
            await upsert_group(chat_id)
            await update_group(chat_id, check_window_hours=hours)

        logger.info("Set check_window_hours to %s for chat %s", hours, chat_id)
        await update.message.reply_text(
            f"Check window set to {hours:g} hour(s) before slot time."
        )
    except Exception:
        logger.exception("Failed to set check_window_hours")
        await update.message.reply_text("Error setting check window. Please try again.")


async def cmd_add_slot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message and update.effective_chat
    if not await _require_admin(update, context):
        await update.message.reply_text("Admin privileges required.")
        return

    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            "Usage: /addslot <day> <HH:MM> [title_template]\nExample: /addslot monday 20:00 Weekly Stream"
        )
        return

    day_str = args[0]
    time_str = args[1]
    title_template = " ".join(args[2:]) if len(args) > 2 else ""
    days = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]

    day_str_lower = day_str.lower()
    if day_str_lower not in days:
        await update.message.reply_text(
            f"Invalid day '{day_str}'. Must be one of: {', '.join(days)}"
        )
        return

    day_of_week = days.index(day_str_lower)

    try:
        # Validate time format
        dt = datetime.strptime(time_str, "%H:%M")
        formatted_time = dt.strftime("%H:%M")
    except ValueError:
        await update.message.reply_text(
            "Invalid time format. Please use HH:MM (e.g., 20:00)."
        )
        return

    chat_id = update.effective_chat.id

    try:
        async with db_context():
            # Ensure the group is registered before adding a slot
            await upsert_group(chat_id)
            slot_id = await add_slot(
                group_id=chat_id,
                day_of_week=day_of_week,
                local_time=formatted_time,
                title_template=title_template,
            )

        logger.info("Added slot %s for chat %s", slot_id, chat_id)
        title_part = f" with title: '{title_template}'" if title_template else ""
        await update.message.reply_text(
            f"Slot {slot_id} added successfully for {day_str.capitalize()} at {formatted_time}{title_part}."
        )
    except Exception as e:
        logger.exception("Failed to add slot to DB")
        await update.message.reply_text(f"Error saving slot to database: {e}")


async def cmd_remove_slot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message and update.effective_chat
    if not await _require_admin(update, context):
        await update.message.reply_text("Admin privileges required.")
        return

    args = context.args
    if not args or len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text(
            "Usage: /removeslot <slot_id>\nUse /listslots to find the ID."
        )
        return

    slot_id = int(args[0])
    if slot_id <= 0:
        await update.message.reply_text("Slot ID must be a positive integer.")
        return

    try:
        async with db_context():
            await remove_slot(slot_id, update.effective_chat.id)
        await update.message.reply_text(f"✅ Slot {slot_id} removed successfully.")
    except Exception as e:
        logger.exception("Failed to remove slot")
        await update.message.reply_text(f"❌ Error removing slot: {e}")


async def cmd_set_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message and update.effective_chat
    if not await _require_admin(update, context):
        await update.message.reply_text("Admin privileges required.")
        return

    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            "Usage: /settemplate <slot_id> <template>\n"
            "Example: /settemplate 1 Weekly Stream {date}"
        )
        return

    try:
        slot_id = int(args[0])
    except (ValueError, TypeError):
        await update.message.reply_text(
            "Usage: /settemplate <slot_id> <template>\n"
            "Example: /settemplate 1 Weekly Stream {date}"
        )
        return

    if slot_id <= 0:
        await update.message.reply_text("Slot ID must be a positive integer.")
        return

    template = " ".join(args[1:])
    chat_id = update.effective_chat.id

    try:
        async with db_context():
            await update_slot(slot_id, chat_id, title_template=template)

        logger.info("Set title_template for slot %s in chat %s", slot_id, chat_id)
        await update.message.reply_text(
            f"Template for slot {slot_id} updated to: '{template}'."
        )
    except Exception:
        logger.exception("Failed to set title_template")
        await update.message.reply_text("Error setting template. Please try again.")


async def cmd_set_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message and update.effective_chat
    if not await _require_admin(update, context):
        await update.message.reply_text("Admin privileges required.")
        return

    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            "Usage: /setmessage <slot_id> <message>\n"
            "Example: /setmessage 1 Join us for the weekly stream!"
        )
        return

    try:
        slot_id = int(args[0])
    except (ValueError, TypeError):
        await update.message.reply_text(
            "Usage: /setmessage <slot_id> <message>\n"
            "Example: /setmessage 1 Join us for the weekly stream!"
        )
        return

    if slot_id <= 0:
        await update.message.reply_text("Slot ID must be a positive integer.")
        return

    message = " ".join(args[1:])
    chat_id = update.effective_chat.id

    try:
        async with db_context():
            await update_slot(slot_id, chat_id, custom_message=message)

        logger.info("Set custom_message for slot %s in chat %s", slot_id, chat_id)
        await update.message.reply_text(
            f"Message for slot {slot_id} updated to: '{message}'."
        )
    except Exception:
        logger.exception("Failed to set custom_message")
        await update.message.reply_text("Error setting message. Please try again.")


async def cmd_list_slots(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message and update.effective_chat
    if not await _require_admin(update, context):
        await update.message.reply_text("Admin privileges required.")
        return

    chat_id = update.effective_chat.id

    try:
        async with db_context():
            slots = await list_slots(chat_id)

        if not slots:
            await update.message.reply_text(
                "No slots configured for this group. Use /addslot to add one."
            )
            return

        days = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        lines = ["📅 *Configured Slots:*"]
        for slot in slots:
            slot_id = slot["slot_id"]
            day = days[slot["day_of_week"]]
            time = slot["local_time"]
            title = slot["title_template"]
            lines.append(f"• ID: `{slot_id}` | {day} @ {time} | Title: '{title}'")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    except Exception as e:
        logger.exception("Failed to list slots")
        await update.message.reply_text(f"Error fetching slots: {e}")


async def cmd_streams(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message and update.effective_chat

    chat_id = update.effective_chat.id
    try:
        async with db_context():
            group = await get_group(chat_id)
            streams = await list_active_streams(chat_id)
    except Exception as e:
        logger.exception("Failed to list streams")
        await update.message.reply_text(f"Error fetching streams: {e}")
        return

    if not streams:
        await update.message.reply_text("No upcoming streams to display.")
        return

    group_tz = ZoneInfo(group["timezone"]) if group else ZoneInfo("UTC")

    lines = ["📡 *Tracked Streams*"]
    for stream in streams:
        sched_dt = datetime.fromtimestamp(
            stream["scheduled_start"], tz=group_tz
        ).strftime("%Y-%m-%d %H:%M %Z")
        status = stream["status"]
        lines.append(f"• [{status}] Scheduled: `{sched_dt}` | URL: {stream['yt_url']}")

    await update.message.reply_text(
        "\n".join(lines), parse_mode="Markdown", disable_web_page_preview=True
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message and update.effective_chat
    if not await _require_admin(update, context):
        await update.message.reply_text("Admin privileges required.")
        return

    chat_id = update.effective_chat.id

    try:
        async with db_context():
            group = await get_group(chat_id)
    except Exception:
        logger.exception("Failed to fetch group status")
        await update.message.reply_text("Error fetching status. Please try again.")
        return

    if not group:
        await update.message.reply_text(
            "This group is not registered. Run /start to register."
        )
        return

    timezone = group["timezone"]
    auto_create = "Enabled ✅" if group["auto_create"] else "Disabled ❌"
    yt_status = (
        f"Connected (channel: {group['yt_channel_id']}) 🟢"
        if group["yt_channel_id"]
        else "Not connected 🔴"
    )
    now = datetime.now()
    minutes_until_poll = 15 - (now.minute % 15)

    lines = [
        "⚙️ *Bot Status: OK*",
        f"• *Timezone*: `{timezone}`",
        f"• *Auto-Create Streams*: {auto_create}",
        f"• *YouTube Connection*: {yt_status}",
        f"• *Next scheduled poll*: in ~{minutes_until_poll} minute(s)",
        "",
        "To manage slots, use `/listslots`.",
    ]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message and update.effective_chat
    if not await _require_admin(update, context):
        await update.message.reply_text("Admin privileges required.")
        return

    await update.message.reply_text("🔄 Running manual sync with YouTube...")
    try:
        await run_polling_cycle(context.bot, group_id=update.effective_chat.id)
        await update.message.reply_text(
            "✅ Sync complete! Use /streams to see tracked broadcasts."
        )
    except Exception as e:
        logger.exception("Manual check failed")
        await update.message.reply_text(f"❌ Error during sync: {e}")


async def cmd_setbroadcastdescription(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    assert update.message and update.effective_chat
    if not await _require_admin(update, context):
        await update.message.reply_text("Admin privileges required.")
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: /setbroadcastdescription <text>\n"
            "Example: /setbroadcastdescription Weekly live Q&A stream"
        )
        return

    description = " ".join(args)
    chat_id = update.effective_chat.id

    try:
        async with db_context():
            await upsert_group(chat_id)
            await update_group(chat_id, broadcast_description=description)

        logger.info("Set broadcast_description for chat %s", chat_id)
        await update.message.reply_text(
            f"Broadcast description set to: '{description}'."
        )
    except Exception:
        logger.exception("Failed to set broadcast_description")
        await update.message.reply_text(
            "Error setting broadcast description. Please try again."
        )


async def cmd_setbroadcastmadeforkids(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    assert update.message and update.effective_chat
    if not await _require_admin(update, context):
        await update.message.reply_text("Admin privileges required.")
        return

    valid_values = ("yes", "no")
    args = context.args
    if not args or len(args) != 1 or args[0].lower() not in valid_values:
        await update.message.reply_text(
            "Usage: /setbroadcastmadeforkids <yes|no>\n"
            "Example: /setbroadcastmadeforkids no"
        )
        return

    value = args[0].lower() == "yes"
    chat_id = update.effective_chat.id

    try:
        async with db_context():
            await upsert_group(chat_id)
            await update_group(chat_id, broadcast_made_for_kids=value)

        label = "yes" if value else "no"
        logger.info("Set broadcast_made_for_kids to %s for chat %s", label, chat_id)
        await update.message.reply_text(f"Broadcast made for kids set to {label}.")
    except Exception:
        logger.exception("Failed to set broadcast_made_for_kids")
        await update.message.reply_text(
            "Error setting broadcast made for kids. Please try again."
        )


async def cmd_setbroadcastprivacy(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    assert update.message and update.effective_chat
    if not await _require_admin(update, context):
        await update.message.reply_text("Admin privileges required.")
        return

    valid_values = ("public", "unlisted", "private")
    args = context.args
    if not args or len(args) != 1 or args[0].lower() not in valid_values:
        await update.message.reply_text(
            "Usage: /setbroadcastprivacy <public|unlisted|private>\n"
            "Example: /setbroadcastprivacy public"
        )
        return

    value = args[0].lower()
    chat_id = update.effective_chat.id

    try:
        async with db_context():
            await upsert_group(chat_id)
            await update_group(chat_id, broadcast_privacy=value)

        logger.info("Set broadcast_privacy to %s for chat %s", value, chat_id)
        await update.message.reply_text(f"Broadcast privacy set to {value}.")
    except Exception:
        logger.exception("Failed to set broadcast_privacy")
        await update.message.reply_text(
            "Error setting broadcast privacy. Please try again."
        )
