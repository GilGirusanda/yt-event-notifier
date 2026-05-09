import asyncio
import json
import logging
from typing import Any

from src.logging_config import setup_logging

setup_logging()

from telegram import Update
from telegram.ext import Application

from src.bot.commands import build_application
from src.db.client import db_context
from src.poller import run_poll
from src.youtube.oauth import handle_oauth_callback

logger = logging.getLogger(__name__)

_application: Application | None = None


async def _get_application() -> Application:
    global _application
    if _application is None:
        import os
        _application = build_application(os.environ["TELEGRAM_BOT_TOKEN"])
        await _application.initialize()
    return _application


async def _handle_webhook(body: str) -> dict[str, Any]:
    app = await _get_application()
    update = Update.de_json(json.loads(body), app.bot)
    async with db_context():
        await app.process_update(update)
    return {"statusCode": 200, "body": "ok"}


async def _handle_oauth_callback(query_params: dict[str, str]) -> dict[str, Any]:
    code = query_params.get("code", "")
    state = query_params.get("state", "")
    async with db_context():
        await handle_oauth_callback(code, state)
    return {"statusCode": 200, "body": "Authorization successful. You may close this tab."}


async def _handle_cron() -> None:
    async with db_context():
        await run_poll()


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    if event.get("source") == "aws.events":
        asyncio.run(_handle_cron())
        return {"statusCode": 200, "body": "ok"}

    path = event.get("path", event.get("rawPath", ""))
    if path == "/oauth/callback":
        query_params = event.get("queryStringParameters") or {}
        return asyncio.run(_handle_oauth_callback(query_params))

    body = event.get("body", "")
    return asyncio.run(_handle_webhook(body))
