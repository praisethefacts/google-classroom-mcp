"""Thin, read-only wrapper around the Google Classroom API v1."""

import json
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .auth import get_credentials

COURSE_STATES = ("ACTIVE", "ARCHIVED", "PROVISIONED", "DECLINED", "SUSPENDED")
COURSEWORK_STATES = ("PUBLISHED", "DRAFT", "DELETED")


@lru_cache(maxsize=1)
def _service():
    return build("classroom", "v1", credentials=get_credentials(), cache_discovery=False)


def _api_call(builder, **params):
    try:
        return builder(**params).execute()
    except HttpError as exc:
        try:
            message = json.loads(exc.content.decode("utf-8"))["error"]["message"]
        except Exception:
            message = getattr(exc, "reason", "") or str(exc)
        raise RuntimeError(f"Google Classroom API error ({exc.status_code}): {message}") from exc


def _paginate(builder, key, limit=None, **params):
    items = []
    page_token = None
    while True:
        call = dict(params)
        if page_token:
            call["pageToken"] = page_token
        response = _api_call(builder, **call)
        items.extend(response.get(key, []))
        page_token = response.get("nextPageToken")
        if not page_token or (limit is not None and len(items) >= limit):
            break
    return items[:limit] if limit is not None else items


def due_iso(due_date, due_time):
    """Render a Classroom dueDate/dueTime pair as an ISO 8601 string."""
    if not due_date:
        return None
    stamp = f"{due_date['year']:04d}-{due_date['month']:02d}-{due_date['day']:02d}"
    if due_time:
        return f"{stamp}T{due_time.get('hours', 0):02d}:{due_time.get('minutes', 0):02d}:00Z"
    return stamp


def _due_datetime(item):
    due_date = item.get("dueDate")
    if not due_date:
        return None
    due_time = item.get("dueTime") or {}
    return datetime(
        due_date["year"],
        due_date["month"],
        due_date["day"],
        due_time.get("hours", 23),
        due_time.get("minutes", 59),
        tzinfo=timezone.utc,
    )


def _course_summary(course):
    return {
        "id": course.get("id"),
        "name": course.get("name"),
        "section": course.get("section"),
        "room": course.get("room"),
        "state": course.get("state"),
        "ownerId": course.get("ownerId"),
        "alternateLink": course.get("alternateLink"),
        "creationTime": course.get("creationTime"),
        "updateTime": course.get("updateTime"),
    }


def _coursework_summary(item, course=None):
    summary = {
        "id": item.get("id"),
        "title": item.get("title"),
        "description": (item.get("description") or "")[:1000] or None,
        "state": item.get("state"),
        "workType": item.get("workType"),
        "maxPoints": item.get("maxPoints"),
        "dueAt": due_iso(item.get("dueDate"), item.get("dueTime")),
        "creationTime": item.get("creationTime"),
        "updateTime": item.get("updateTime"),
        "alternateLink": item.get("alternateLink"),
    }
    if course:
        summary["courseId"] = course.get("id")
        summary["courseName"] = course.get("name")
    return summary


def _announcement_summary(item):
    return {
        "id": item.get("id"),
        "text": (item.get("text") or "")[:1000] or None,
        "state": item.get("state"),
        "creationTime": item.get("creationTime"),
        "updateTime": item.get("updateTime"),
        "alternateLink": item.get("alternateLink"),
    }


def _roster_user(user):
    profile = user.get("profile") or {}
    name = profile.get("name") or {}
    return {
        "userId": user.get("userId"),
        "fullName": name.get("fullName"),
        "emailAddress": profile.get("emailAddress"),
    }


def _submission_summary(submission):
    return {
        "id": submission.get("id"),
        "userId": submission.get("userId"),
        "state": submission.get("state"),
        "late": submission.get("late"),
        "assignedGrade": submission.get("assignedGrade"),
        "draftGrade": submission.get("draftGrade"),
        "updateTime": submission.get("updateTime"),
        "alternateLink": submission.get("alternateLink"),
    }


def list_courses(states=None):
    """List courses the signed-in user belongs to, as teacher or student."""
    service = _service()
    states = [s.upper() for s in states] if states else ["ACTIVE"]
    invalid = [s for s in states if s not in COURSE_STATES]
    if invalid:
        raise ValueError(f"Unknown course state(s): {invalid}. Valid: {list(COURSE_STATES)}")

    courses = {}
    warnings = []
    for extra in ({"studentId": "me"}, {}):
        try:
            for course in _paginate(
                service.courses().list, "courses", courseStates=states, **extra
            ):
                courses[course["id"]] = _course_summary(course)
        except RuntimeError as exc:
            warnings.append(str(exc))

    result = {
        "count": len(courses),
        "courses": sorted(courses.values(), key=lambda c: (c.get("name") or "").lower()),
    }
    if warnings:
        result["warnings"] = warnings
    return result


def get_course(course_id):
    """Fetch one course by id."""
    course = _api_call(_service().courses().get, courseId=course_id)
    summary = _course_summary(course)
    summary["descriptionHeading"] = course.get("descriptionHeading")
    summary["description"] = (course.get("description") or "")[:2000] or None
    summary["enrollmentCode"] = course.get("enrollmentCode")
    return summary


def list_coursework(course_id, states=None, limit=25):
    """List coursework (assignments, quizzes, questions, materials) for a course."""
    states = [s.upper() for s in states] if states else ["PUBLISHED"]
    invalid = [s for s in states if s not in COURSEWORK_STATES]
    if invalid:
        raise ValueError(f"Unknown coursework state(s): {invalid}. Valid: {list(COURSEWORK_STATES)}")

    items = _paginate(
        _service().courses().courseWork().list,
        "courseWork",
        limit=limit,
        courseId=course_id,
        courseWorkStates=states,
    )
    return {
        "courseId": course_id,
        "count": len(items),
        "coursework": [_coursework_summary(item) for item in items],
    }


def list_due_soon(days=7, include_overdue=False):
    """Upcoming coursework across all active courses, sorted by due date."""
    service = _service()
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=max(1, days))

    entries = []
    warnings = []
    for course in list_courses(["ACTIVE"])["courses"]:
        try:
            items = _paginate(
                service.courses().courseWork().list,
                "courseWork",
                limit=200,
                courseId=course["id"],
                courseWorkStates=["PUBLISHED"],
            )
        except RuntimeError as exc:
            warnings.append(f"{course.get('name')}: {exc}")
            continue
        for item in items:
            due = _due_datetime(item)
            if due is None or due > horizon or (due < now and not include_overdue):
                continue
            entries.append(_coursework_summary(item, course))

    entries.sort(key=lambda entry: entry["dueAt"] or "")
    result = {"days": days, "count": len(entries), "coursework": entries}
    if warnings:
        result["warnings"] = warnings
    return result


def list_announcements(course_id, limit=10):
    """Recent announcements for a course."""
    items = _paginate(
        _service().courses().announcements().list,
        "announcements",
        limit=limit,
        courseId=course_id,
    )
    return {
        "courseId": course_id,
        "count": len(items),
        "announcements": [_announcement_summary(item) for item in items],
    }


def list_teachers(course_id):
    """Teacher roster for a course."""
    items = _paginate(_service().courses().teachers().list, "teachers", courseId=course_id)
    return {"courseId": course_id, "count": len(items), "teachers": [_roster_user(u) for u in items]}


def list_students(course_id):
    """Student roster for a course."""
    items = _paginate(_service().courses().students().list, "students", courseId=course_id)
    return {"courseId": course_id, "count": len(items), "students": [_roster_user(u) for u in items]}


def list_submissions(course_id, coursework_id, user_id="me", limit=100):
    """Submission state and grades for one assignment.

    user_id="me" returns the signed-in student's submission; teachers can pass
    "-" to get every student's submission.
    """
    items = _paginate(
        _service().courses().courseWork().studentSubmissions().list,
        "studentSubmissions",
        limit=limit,
        courseId=course_id,
        courseWorkId=coursework_id,
        userId=user_id or "me",
    )
    return {
        "courseId": course_id,
        "courseworkId": coursework_id,
        "count": len(items),
        "submissions": [_submission_summary(item) for item in items],
    }
