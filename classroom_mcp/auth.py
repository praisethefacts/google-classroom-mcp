"""OAuth 2.0 helpers for the Google Classroom MCP server.

Only read-only Classroom scopes are requested. Credentials are cached outside
the repository (default: ``~/.google-classroom-mcp/token.json``).
"""

import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.announcements.readonly",
    "https://www.googleapis.com/auth/classroom.rosters.readonly",
    "https://www.googleapis.com/auth/classroom.profile.emails",
    "https://www.googleapis.com/auth/classroom.coursework.me.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.students.readonly",
]

CONFIG_DIR = Path(
    os.environ.get("CLASSROOM_MCP_CONFIG_DIR", Path.home() / ".google-classroom-mcp")
).expanduser()
TOKEN_FILE = Path(
    os.environ.get("CLASSROOM_MCP_TOKEN_FILE", CONFIG_DIR / "token.json")
).expanduser()

AUTH_HELP = (
    "No valid Google credentials found. Run `google-classroom-mcp-auth` once "
    "(or `python -m classroom_mcp.auth`) to sign in, then start the MCP server "
    "again. See the README for Google Cloud setup."
)


def _client_config() -> dict:
    client_id = os.environ.get("CLASSROOM_MCP_CLIENT_ID")
    client_secret = os.environ.get("CLASSROOM_MCP_CLIENT_SECRET")
    if client_id and client_secret:
        return {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }

    candidate = os.environ.get("CLASSROOM_MCP_CLIENT_SECRET_FILE")
    path = Path(candidate).expanduser() if candidate else CONFIG_DIR / "client_secret.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))

    raise RuntimeError(
        "Google OAuth client not found. Download a Desktop app OAuth client from "
        f"the Google Cloud Console and save it as {CONFIG_DIR / 'client_secret.json'}, "
        "or point CLASSROOM_MCP_CLIENT_SECRET_FILE at it. See the README."
    )


def _load_saved_token() -> Credentials | None:
    raw = None
    inline = os.environ.get("CLASSROOM_MCP_TOKEN_JSON")
    if inline:
        raw = json.loads(inline)
    elif TOKEN_FILE.is_file():
        raw = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))

    if not raw:
        return None

    if not (raw.get("refresh_token") and raw.get("client_id") and raw.get("client_secret")):
        raise RuntimeError(
            f"Token file {TOKEN_FILE} is not in the expected authorized-user format. "
            "Delete it and run `google-classroom-mcp-auth` again."
        )

    return Credentials.from_authorized_user_info(raw, SCOPES)


def save_token(credentials: Credentials) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")


def run_oauth_flow() -> Credentials:
    flow = InstalledAppFlow.from_client_config(_client_config(), SCOPES)
    credentials = flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent",
        open_browser=True,
    )
    save_token(credentials)
    return credentials


def get_credentials(interactive: bool = False) -> Credentials:
    credentials = None
    try:
        credentials = _load_saved_token()
    except RuntimeError:
        if not interactive:
            raise
        credentials = None

    if credentials and not credentials.valid and credentials.refresh_token:
        try:
            credentials.refresh(Request())
            save_token(credentials)
        except Exception:
            credentials = None

    if credentials and credentials.valid:
        return credentials

    if interactive:
        return run_oauth_flow()

    raise RuntimeError(AUTH_HELP)


def main() -> None:
    """Run the interactive Google sign-in flow and cache the token."""
    existing = None
    try:
        existing = _load_saved_token()
    except RuntimeError:
        pass

    if existing and existing.valid:
        print(f"Already authorized. Token cached at {TOKEN_FILE}")
        print("Delete that file and re-run this command to switch accounts.")
        return

    get_credentials(interactive=True)
    print(f"Authorized for Google Classroom. Token cached at {TOKEN_FILE}")


if __name__ == "__main__":
    main()
