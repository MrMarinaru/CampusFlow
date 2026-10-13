"""
components/tables.py — Reusable table renderers for CampusFlow.

Transforms raw MongoDB documents into display-friendly DataFrames with
clean labels, formatted dates, and marks.
"""

from datetime import datetime
from bson import ObjectId
import pandas as pd
import streamlit as st
from components.layout import get_utc_now


def _fmt_date(val) -> str:
    """Format a datetime for display, handling None and strings."""
    if val is None:
        return "—"
    if isinstance(val, datetime):
        return val.strftime("%d %b %Y, %H:%M")
    return str(val)


def _fmt_marks(val) -> str:
    if val is None:
        return "—"
    if isinstance(val, float) and val.is_integer():
        return str(int(val))
    return str(val)


def courses_table(
    courses: list[dict],
    user_map: dict[str, dict],
) -> None:
    """
    Display a courses table.

    Parameters
    ----------
    courses   : list of course documents
    user_map  : str(ObjectId) → user doc (for resolving teacher_id)
    """
    if not courses:
        return

    rows = []
    for c in courses:
        teacher_id_str = str(c.get("teacher_id", ""))
        teacher = user_map.get(teacher_id_str, {})
        rows.append(
            {
                "Course Title": c.get("title", "—"),
                "Description": (c.get("description", "") or "")[:80],
                "Teacher": teacher.get("name", "Unknown"),
                "Enrolled Students": len(c.get("student_ids", [])),
                "Created Date": _fmt_date(c.get("created_at")),
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, hide_index=True, width="stretch")


def assignments_table(
    assignments: list[dict],
    course_map: dict[str, dict],
    submission_map: dict[str, dict] | None = None,
) -> None:
    """
    Display an assignments table.

    Parameters
    ----------
    assignments   : list of assignment documents
    course_map    : str(ObjectId) → course doc
    submission_map: str(assignment_id) → submission doc (optional, for student view)
    """
    if not assignments:
        return

    now = get_utc_now()
    rows = []
    for a in assignments:
        course_id_str = str(a.get("course_id", ""))
        course = course_map.get(course_id_str, {})
        deadline = a.get("deadline")
        # Ensure deadline comparison handles tzinfo safely
        if isinstance(deadline, datetime):
            dl_cmp = deadline.replace(tzinfo=None) if deadline.tzinfo else deadline
            is_past = dl_cmp < now
        else:
            is_past = False

        row = {
            "Assignment Title": a.get("title", "—"),
            "Course": course.get("title", "—"),
            "Deadline": _fmt_date(deadline),
            "Timeline": "Past Due" if is_past else "Upcoming",
            "Max Marks": _fmt_marks(a.get("max_marks")),
        }

        if submission_map is not None:
            sub = submission_map.get(str(a["_id"]))
            if sub:
                row["Submitted"] = "Yes"
                row["Grade Awarded"] = f"{_fmt_marks(sub.get('marks'))} / {_fmt_marks(a.get('max_marks'))}"
                row["Status"] = (sub.get("status") or "submitted").title()
            else:
                row["Submitted"] = "No"
                row["Grade Awarded"] = "—"
                row["Status"] = "Pending"

        rows.append(row)

    df = pd.DataFrame(rows)
    st.dataframe(df, hide_index=True, width="stretch")


def submissions_table(
    submissions: list[dict],
    student_map: dict[str, dict],
    assignment_map: dict[str, dict],
    course_map: dict[str, dict],
) -> None:
    """
    Display a submissions table with all resolved references.
    """
    if not submissions:
        return

    rows = []
    for s in submissions:
        student = student_map.get(str(s.get("student_id", "")), {})
        assignment = assignment_map.get(str(s.get("assignment_id", "")), {})
        course_id_str = str(assignment.get("course_id", ""))
        course = course_map.get(course_id_str, {})

        rows.append(
            {
                "Student Name": student.get("name", "Unknown"),
                "Assignment": assignment.get("title", "—"),
                "Course": course.get("title", "—"),
                "Submitted At": _fmt_date(s.get("submitted_at")),
                "Status": (s.get("status") or "submitted").title(),
                "Awarded Marks": _fmt_marks(s.get("marks")),
                "Max Marks": _fmt_marks(assignment.get("max_marks")),
                "Teacher Feedback": (s.get("feedback") or "—")[:80],
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, hide_index=True, width="stretch")
