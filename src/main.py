import logging
import os
import sys

from dotenv import load_dotenv
from telegram import Bot

from src.logging_config import setup_logging


async def test_telegram_connection() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logging.error("TELEGRAM_BOT_TOKEN is not set. Cannot test Telegram connection.")
        return

    bot = Bot(token=token)
    try:
        me = await bot.get_me()
        logging.info("Successfully connected to Telegram!")
        logging.info("Bot info: @%s (ID: %s, Name: %s)", me.username, me.id, me.first_name)
    except Exception as e:
        logging.error("Failed to connect to Telegram: %s", e)


from src.bot.commands import build_application


def main() -> None:
    # 1. Determine Profile
    profile = os.environ.get("APP_PROFILE", "dev").lower()
    
    # 2. Load configurations based on profile
    if profile == "dev":
        print("Loading development profile...")
        load_dotenv()
        log_level = logging.DEBUG
    elif profile == "prod":
        print("Loading production profile...")
        log_level = logging.INFO
    else:
        print(f"Unknown profile '{profile}'. Exiting.")
        sys.exit(1)

    # 3. Setup App Logging
    setup_logging(level=log_level, profile=profile)
    logger = logging.getLogger(__name__)
    logger.info("Starting application in %s mode", profile.upper())

    # 4. Initialize and run the Telegram bot
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not set. Exiting.")
        sys.exit(1)

    app = build_application(token)
    logger.info("Starting Telegram bot polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
