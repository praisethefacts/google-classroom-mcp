# google-classroom-mcp

Read-only Google Classroom access for DeepSeek — and any other MCP-capable agent.

This is a [Model Context Protocol](https://modelcontextprotocol.io) server that turns your
Google Classroom account into tools an LLM can call: courses, coursework, due dates,
announcements, rosters and student submissions.

DeepSeek's API does not speak MCP by itself, so point an MCP-capable harness at this server
and select a DeepSeek model there. Works with opencode, Claude Desktop, Cursor, or the bundled
example agent (`examples/deepseek_agent.py`) that calls the DeepSeek API directly.

## Tools

| Tool | Returns |
| --- | --- |
| `list_courses` | Courses you teach or attend (id, name, section, room, state, link) |
| `get_course` | One course with description and enrollment code |
| `list_coursework` | Assignments, quizzes, questions and materials, with due dates |
| `list_due_soon` | Upcoming coursework across all active courses, sorted by due date |
| `list_announcements` | Recent announcements in a course |
| `list_teachers` | Teacher roster (name, email) |
| `list_students` | Student roster (name, email) |
| `list_submissions` | Submission state and grades for one assignment |

Every tool is read-only. The server cannot create, edit or delete anything in Classroom.

## Setup

### 1. Create a Google OAuth client

1. Open the [Google Cloud Console](https://console.cloud.google.com/) and create a project.
2. **APIs & Services → Library**: enable the **Google Classroom API**.
3. **APIs & Services → OAuth consent screen**: choose **External**, fill in the required
   fields, and add your own Google account under **Test users**.
   In *Testing* mode Google expires refresh tokens after 7 days. For a durable personal setup,
   click **Publish app** (no verification needed for personal use; you will see an
   "unverified app" warning during sign-in).
4. **APIs & Services → Credentials → Create credentials → OAuth client ID**:
   application type **Desktop app**, then download the JSON.
5. Save the file as `~/.google-classroom-mcp/client_secret.json`
   (Windows: `%USERPROFILE%\.google-classroom-mcp\client_secret.json`), or set
   `CLASSROOM_MCP_CLIENT_SECRET_FILE` to its path.

### 2. Install

```bash
git clone https://github.com/PTFacts/google-classroom-mcp
cd google-classroom-mcp
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .
```

### 3. Sign in once

```bash
google-classroom-mcp-auth
```

A browser window opens; grant the read-only scopes. The refreshable token is cached at
`~/.google-classroom-mcp/token.json`.

### 4. Connect an MCP host

**opencode** (`~/.config/opencode/opencode.json`):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "google-classroom": {
      "type": "local",
      "command": ["google-classroom-mcp"],
      "enabled": true
    }
  }
}
```

**Claude Desktop / Cursor** (`claude_desktop_config.json` or `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "google-classroom": {
      "command": "google-classroom-mcp"
    }
  }
}
```

If the host cannot find `google-classroom-mcp`, use the absolute path to the script inside
your venv (Windows: `...\.venv\Scripts\google-classroom-mcp.exe`).

### 5. Optional: run it from a plain DeepSeek script

```bash
pip install -e ".[example]"
set DEEPSEEK_API_KEY=sk-...        # PowerShell: $env:DEEPSEEK_API_KEY="sk-..."
python examples/deepseek_agent.py "What do I have due this week?"
```

The example starts the MCP server, converts its tools into OpenAI-style function schemas,
and lets `deepseek-chat` call them in a loop.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `CLASSROOM_MCP_CONFIG_DIR` | Override the config directory (default `~/.google-classroom-mcp`) |
| `CLASSROOM_MCP_CLIENT_SECRET_FILE` | Path to the OAuth client JSON |
| `CLASSROOM_MCP_TOKEN_FILE` | Path to the cached token (default `<config>/token.json`) |
| `CLASSROOM_MCP_CLIENT_ID` / `CLASSROOM_MCP_CLIENT_SECRET` | Inline OAuth client instead of a file |
| `CLASSROOM_MCP_TOKEN_JSON` | Inline token JSON, for hosted/remote setups |
| `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL` | Used only by `examples/deepseek_agent.py` |

## Security

- Only read-only Classroom scopes are requested (see `classroom_mcp/auth.py`).
- The token lives outside the repository and is git-ignored. Never commit it.
- Revoke access anytime at [myaccount.google.com/permissions](https://myaccount.google.com/permissions).

## Development

```bash
pip install -e ".[dev]"
pytest -q
```

## License

[MIT](LICENSE)
