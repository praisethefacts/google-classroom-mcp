"""Smoke tests that need no network or Google credentials."""

import asyncio

from classroom_mcp import classroom
from classroom_mcp.server import mcp

EXPECTED_TOOLS = {
    "list_courses",
    "get_course",
    "list_coursework",
    "list_due_soon",
    "list_announcements",
    "list_teachers",
    "list_students",
    "list_submissions",
}


def _tool_names():
    result = mcp.list_tools()
    if asyncio.iscoroutine(result):
        result = asyncio.run(result)
    return {tool.name for tool in result}


def test_expected_tools_registered():
    assert EXPECTED_TOOLS <= _tool_names()


def test_due_iso_date_only():
    assert classroom.due_iso({"year": 2026, "month": 10, "day": 6}, None) == "2026-10-06"


def test_due_iso_with_time():
    assert (
        classroom.due_iso({"year": 2026, "month": 10, "day": 6}, {"hours": 23, "minutes": 59})
        == "2026-10-06T23:59:00Z"
    )


def test_due_iso_missing():
    assert classroom.due_iso(None, None) is None
