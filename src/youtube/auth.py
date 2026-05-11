import os
from google_auth_oauthlib.flow import Flow

# Store flows in memory so we can retrieve the exact instance (with PKCE code_verifier)
# when the callback hits our server.
OAUTH_FLOWS: dict[str, Flow] = {}

def create_oauth_flow(state: str | None = None) -> Flow:
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
    
    flow = Flow.from_client_config(
        client_config,
        scopes=scopes,
        state=state
    )
    flow.redirect_uri = redirect_uri
    
    if state:
        OAUTH_FLOWS[state] = flow
        
    return flow

def get_oauth_flow(state: str) -> Flow | None:
    return OAUTH_FLOWS.pop(state, None)
