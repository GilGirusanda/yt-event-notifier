import asyncio
import logging
import os

from aiohttp import web
from dotenv import load_dotenv

load_dotenv()

from src.bot.commands import build_application
from src.db.client import db_context
from src.youtube.oauth import handle_oauth_callback

logger = logging.getLogger(__name__)
PORT = int(os.getenv("LOCAL_PORT", "8080"))


async def webhook_handler(request: web.Request) -> web.Response:
    from telegram import Update

    app = request.app["tg_app"]
    body = await request.json()
    update = Update.de_json(body, app.bot)
    async with db_context():
        await app.process_update(update)
    return web.Response(text="ok")


async def oauth_callback_handler(request: web.Request) -> web.Response:
    code = request.rel_url.query.get("code", "")
    state = request.rel_url.query.get("state", "")
    async with db_context():
        await handle_oauth_callback(code, state)
    return web.Response(text="Authorization successful. You may close this tab.")


async def main() -> None:
    tg_app = build_application(os.environ["TELEGRAM_BOT_TOKEN"])
    await tg_app.initialize()

    server = web.Application()
    server["tg_app"] = tg_app
    server.router.add_post("/webhook", webhook_handler)
    server.router.add_get("/oauth/callback", oauth_callback_handler)

    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info("Local server running on http://0.0.0.0:%d", PORT)
    await asyncio.Event().wait()


if __name__ == "__main__":
    from src.logging_config import setup_logging
    setup_logging()
    asyncio.run(main())
