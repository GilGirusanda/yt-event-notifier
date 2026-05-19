import os
import secrets
from google_auth_oauthlib.flow import Flow

# Store flows in memory so we can retrieve the exact instance (with PKCE code_verifier)
# when the callback hits our server.
# TODO: OAUTH_FLOWS is in-memory and incompatible with Lambda's stateless invocation model.
# The /connectyoutube command and /oauth/callback run in separate Lambda invocations, so
# the dict will always be empty in the callback. Replace with a short-lived persistent store
# (e.g. a DynamoDB item with a TTL of ~10 minutes) keyed by state, storing the code_verifier.
OAUTH_FLOWS: dict[str, tuple[Flow, int]] = {}

def create_oauth_flow(chat_id: int) -> Flow:
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8080/oauth/callback")

    if not client_id or not client_secret:
        raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set")

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }

    scopes = [
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/youtube.readonly",
    ]

    state = secrets.token_urlsafe(32)
    flow = Flow.from_client_config(
        client_config,
        scopes=scopes,
        state=state
    )
    flow.redirect_uri = redirect_uri
    OAUTH_FLOWS[state] = (flow, chat_id)

    return flow

def get_oauth_flow(state: str) -> tuple[Flow, int] | None:
    return OAUTH_FLOWS.pop(state, None)
