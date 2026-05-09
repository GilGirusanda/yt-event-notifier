import hashlib
import hmac
import json
import logging
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from src.db import queries

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/youtube"]


def _client_config() -> dict:
    return {
        "web": {
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "redirect_uris": [os.environ["GOOGLE_REDIRECT_URI"]],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def _sign_state(group_id: int) -> str:
    secret = os.environ["TELEGRAM_BOT_TOKEN"].encode()
    sig = hmac.new(secret, str(group_id).encode(), hashlib.sha256).hexdigest()
    return json.dumps({"group_id": group_id, "sig": sig})


def _verify_state(state: str) -> int:
    data = json.loads(state)
    secret = os.environ["TELEGRAM_BOT_TOKEN"].encode()
    expected = hmac.new(secret, str(data["group_id"]).encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, data["sig"]):
        raise ValueError("Invalid OAuth state signature")
    return data["group_id"]


def build_auth_url(group_id: int) -> str:
    flow = Flow.from_client_config(_client_config(), scopes=_SCOPES)
    flow.redirect_uri = os.environ["GOOGLE_REDIRECT_URI"]
    url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=_sign_state(group_id),
    )
    return url


async def handle_oauth_callback(code: str, state: str) -> int:
    group_id = _verify_state(state)
    flow = Flow.from_client_config(_client_config(), scopes=_SCOPES, state=state)
    flow.redirect_uri = os.environ["GOOGLE_REDIRECT_URI"]
    flow.fetch_token(code=code)
    creds = flow.credentials
    await queries.update_group(
        group_id,
        yt_access_token=creds.token,
        yt_refresh_token=creds.refresh_token,
        yt_token_expiry=int(creds.expiry.timestamp()) if creds.expiry else None,
    )
    logger.info("OAuth tokens stored for group %d", group_id)
    return group_id


async def get_credentials(group_id: int) -> Credentials:
    group = await queries.get_group(group_id)
    if not group or not group["yt_refresh_token"]:
        raise ValueError(f"No OAuth tokens for group {group_id}")

    creds = Credentials(
        token=group["yt_access_token"],
        refresh_token=group["yt_refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
    )
    if creds.expired:
        creds.refresh(Request())
        await queries.update_group(
            group_id,
            yt_access_token=creds.token,
            yt_token_expiry=int(creds.expiry.timestamp()) if creds.expiry else None,
        )
    return creds
