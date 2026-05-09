import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

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
    pass


async def cmd_set_autocreate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def cmd_set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def cmd_set_check_window(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def cmd_add_slot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def cmd_remove_slot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def cmd_set_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def cmd_set_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def cmd_list_slots(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def cmd_streams(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass
