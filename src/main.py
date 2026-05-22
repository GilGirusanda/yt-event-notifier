import asyncio
import logging
import os
import sys

from aiohttp import web
from dotenv import load_dotenv

from src.logging_config import setup_logging
from src.bot.commands import build_application
from src.db.client import db_context
from src.youtube.oauth import handle_oauth_callback


async def oauth_callback(request: web.Request) -> web.Response:
    bot = request.app["bot"]
    state = request.query.get("state")
    code = request.query.get("code")

    if not state or not code:
        return web.Response(text="Missing state or code", status=400)

    try:
        async with db_context():
            chat_id = await handle_oauth_callback(code, state)

        await bot.send_message(chat_id=chat_id, text="✅ YouTube successfully connected! You can now use the bot features.")
        return web.Response(text="YouTube connected successfully! You can close this window and return to Telegram.")
    except Exception as e:
        logging.exception("Failed to complete OAuth flow")
        return web.Response(text=f"Failed to connect: {e}", status=500)


async def async_main() -> None:
    profile = os.environ.get("APP_PROFILE", "dev").lower()
    
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

    setup_logging(level=log_level, profile=profile)
    logger = logging.getLogger(__name__)
    logger.info("Starting application in %s mode", profile.upper())

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not set. Exiting.")
        sys.exit(1)

    app = build_application(token)
    
    if profile == "dev":
        logger.info("Starting Telegram bot polling and local web server...")
        await app.initialize()
        await app.start()
        assert app.updater
        await app.updater.start_polling()

        web_app = web.Application()
        web_app["bot"] = app.bot
        web_app.router.add_get('/oauth/callback', oauth_callback)
        
        runner = web.AppRunner(web_app)
        await runner.setup()
        port = int(os.environ.get("LOCAL_PORT", 8080))
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info("Local web server listening on port %d for callbacks", port)
        
        stop_event = asyncio.Event()
        await stop_event.wait()
    else:
        # In prod, AWS Lambda handles API Gateway webhooks and cron events.
        logger.info("PROD mode detected. In production, this bot should be triggered via AWS Lambda.")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
