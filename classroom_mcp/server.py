"""FastMCP server exposing read-only Google Classroom tools."""

try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

from . import classroom

mcp = FastMCP(
    "google-classroom",
    instructions=(
        "Read-only access to the signed-in user's Google Classroom. Use ids from "
        "one call in the next (for example course_id from list_courses with "
        "list_coursework). Dates are ISO 8601 UTC. All tools only read data."
    ),
)


@mcp.tool()
def list_courses(course_states: list[str] | None = None) -> dict:
    """List Google Classroom courses for the signed-in account (teacher or student).

    Args:
        course_states: Optional state filter. Defaults to ["ACTIVE"]. Other
            values: "ARCHIVED", "PROVISIONED", "DECLINED", "SUSPENDED";
            pass several to include multiple states.
    """
    return classroom.list_courses(course_states)


@mcp.tool()
def get_course(course_id: str) -> dict:
    """Get one course by id, including description and enrollment code.

    Args:
        course_id: Course id from list_courses (numeric string).
    """
    return classroom.get_course(course_id)


@mcp.tool()
def list_coursework(course_id: str, states: list[str] | None = None, limit: int = 25) -> dict:
    """List coursework (assignments, quizzes, questions, materials) for a course.

    Args:
        course_id: Course id from list_courses.
        states: Optional state filter. Defaults to ["PUBLISHED"]; can include
            "DRAFT" or "DELETED".
        limit: Maximum number of items to return.
    """
    return classroom.list_coursework(course_id, states, limit)


@mcp.tool()
def list_due_soon(days: int = 7, include_overdue: bool = False) -> dict:
    """Upcoming coursework across all active courses, sorted by due date.

    Args:
        days: Look-ahead window in days (default 7).
        include_overdue: Also include items whose due date already passed.
    """
    return classroom.list_due_soon(days, include_overdue)


@mcp.tool()
def list_announcements(course_id: str, limit: int = 10) -> dict:
    """Recent announcements for a course.

    Args:
        course_id: Course id from list_courses.
        limit: Maximum number of announcements to return.
    """
    return classroom.list_announcements(course_id, limit)


@mcp.tool()
def list_teachers(course_id: str) -> dict:
    """Teacher roster (names and emails) for a course.

    Args:
        course_id: Course id from list_courses.
    """
    return classroom.list_teachers(course_id)


@mcp.tool()
def list_students(course_id: str) -> dict:
    """Student roster (names and emails) for a course.

    Args:
        course_id: Course id from list_courses.
    """
    return classroom.list_students(course_id)


@mcp.tool()
def list_submissions(course_id: str, coursework_id: str, user_id: str = "me", limit: int = 100) -> dict:
    """Submission state and grades for one assignment.

    Args:
        course_id: Course id from list_courses.
        coursework_id: Coursework id from list_coursework.
        user_id: "me" (default) for the signed-in student's submission, a
            student's numeric id/email, or "-" for all students (teachers only).
        limit: Maximum number of submissions to return.
    """
    return classroom.list_submissions(course_id, coursework_id, user_id, limit)


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
