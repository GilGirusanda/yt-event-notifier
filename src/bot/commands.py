import logging
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.db.client import db_context
from src.db.queries import upsert_group, add_slot, list_slots

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
    return app


async def _require_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    member = await context.bot.get_chat_member(
        update.effective_chat.id, update.effective_user.id
    )
    return member.status in ("administrator", "creator")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def cmd_connect_youtube(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def cmd_disconnect_youtube(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def cmd_set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_admin(update, context):
        await update.message.reply_text("Admin privileges required.")
        return
    logger.info("set_timezone args: %s by %s", context.args, update.effective_user.username)
    await update.message.reply_text(f"Logged timezone args: {context.args}")


async def cmd_set_autocreate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def cmd_set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def cmd_set_check_window(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def cmd_add_slot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_admin(update, context):
        await update.message.reply_text("Admin privileges required.")
        return

    args = context.args
    if not args or len(args) < 3:
        await update.message.reply_text("Usage: /addslot <day> <HH:MM> <Title...>\nExample: /addslot monday 20:00 Weekly Stream")
        return

    day_str = args[0]
    time_str = args[1]
    title_template = " ".join(args[2:])
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    
    day_str_lower = day_str.lower()
    if day_str_lower not in days:
        await update.message.reply_text(f"Invalid day '{day_str}'. Must be one of: {', '.join(days)}")
        return
        
    day_of_week = days.index(day_str_lower)

    try:
        # Validate time format
        dt = datetime.strptime(time_str, "%H:%M")
        formatted_time = dt.strftime("%H:%M")
    except ValueError:
        await update.message.reply_text("Invalid time format. Please use HH:MM (e.g., 20:00).")
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
                title_template=title_template
            )
            
        logger.info("Added slot %s for chat %s", slot_id, chat_id)
        await update.message.reply_text(
            f"Slot {slot_id} added successfully for {day_str.capitalize()} at {formatted_time} with title: '{title_template}'."
        )
    except Exception as e:
        logger.exception("Failed to add slot to DB")
        await update.message.reply_text(f"Error saving slot to database: {e}")


async def cmd_remove_slot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def cmd_set_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def cmd_set_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def cmd_list_slots(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_admin(update, context):
        await update.message.reply_text("Admin privileges required.")
        return

    chat_id = update.effective_chat.id
    
    try:
        async with db_context():
            slots = await list_slots(chat_id)
            
        if not slots:
            await update.message.reply_text("No slots configured for this group. Use /addslot to add one.")
            return

        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
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
    pass


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass
