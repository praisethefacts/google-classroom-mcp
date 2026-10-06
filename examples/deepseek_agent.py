"""Minimal DeepSeek agent that uses this MCP server as its tool layer.

Usage:
    pip install -e ".[example]"
    python examples/deepseek_agent.py "What homework is due this week?"

Requires DEEPSEEK_API_KEY and a signed-in token (google-classroom-mcp-auth).
"""

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI

MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
MAX_STEPS = 12

SYSTEM_PROMPT = (
    "You are a helpful school assistant with read-only access to the user's "
    "Google Classroom. Look up real data with the tools before answering, and "
    "cite course and assignment names."
)


def _tool_result_text(result) -> str:
    parts = [block.text for block in result.content if getattr(block, "text", None)]
    return "\n".join(parts) if parts else "(no output)"


async def run(question: str) -> None:
    server = StdioServerParameters(command=sys.executable, args=["-m", "classroom_mcp"])
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            listed = await session.list_tools()
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                    },
                }
                for tool in listed.tools
            ]

            client = AsyncOpenAI(
                api_key=os.environ["DEEPSEEK_API_KEY"],
                base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            )
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ]

            for _ in range(MAX_STEPS):
                response = await client.chat.completions.create(
                    model=MODEL, messages=messages, tools=tools
                )
                message = response.choices[0].message
                messages.append(message.model_dump(exclude_none=True))

                if not message.tool_calls:
                    print(message.content or "(no answer)")
                    return

                for call in message.tool_calls:
                    arguments = json.loads(call.function.arguments or "{}")
                    print(f"[tool] {call.function.name}({json.dumps(arguments)})", file=sys.stderr)
                    try:
                        result = await session.call_tool(call.function.name, arguments)
                        text = _tool_result_text(result)
                    except Exception as exc:
                        text = f"Tool error: {exc}"
                    messages.append({"role": "tool", "tool_call_id": call.id, "content": text})

            print("Stopped after too many tool steps.", file=sys.stderr)


def main() -> None:
    question = " ".join(sys.argv[1:]).strip() or "What do I have due in the next 7 days?"
    asyncio.run(run(question))


if __name__ == "__main__":
    main()
