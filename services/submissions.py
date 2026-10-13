"""
services/submissions.py — Submission database operations.

Confirmed submission fields: assignment_id, student_id, submitted_at,
status, marks, feedback.

There is NO answer/file field in the confirmed schema.
"""

from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import PyMongoError
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def get_submissions_for_assignment(db: Database, assignment_id: ObjectId) -> list[dict]:
    """Return all submissions for a specific assignment."""
    try:
        return list(db.submissions.find({"assignment_id": assignment_id}))
    except PyMongoError as exc:
        logger.error("get_submissions_for_assignment failed: %s", exc)
        return []


def get_submissions_for_student(db: Database, student_id: ObjectId) -> list[dict]:
    """Return all submissions by a specific student."""
    try:
        return list(db.submissions.find({"student_id": student_id}).sort("submitted_at", -1))
    except PyMongoError as exc:
        logger.error("get_submissions_for_student failed: %s", exc)
        return []


def get_submission(
    db: Database, assignment_id: ObjectId, student_id: ObjectId
) -> Optional[dict]:
    """Return a single submission for a student+assignment pair, or None."""
    try:
        return db.submissions.find_one(
            {"assignment_id": assignment_id, "student_id": student_id}
        )
    except PyMongoError as exc:
        logger.error("get_submission failed: %s", exc)
        return None


def get_submission_by_id(db: Database, submission_id: ObjectId) -> Optional[dict]:
    """Return a single submission by _id, or None."""
    try:
        return db.submissions.find_one({"_id": submission_id})
    except PyMongoError as exc:
        logger.error("get_submission_by_id failed: %s", exc)
        return None


def get_submissions_for_teacher_courses(
    db: Database, assignment_ids: list[ObjectId]
) -> list[dict]:
    """Return all submissions for a list of assignment IDs."""
    if not assignment_ids:
        return []
    try:
        return list(
            db.submissions.find({"assignment_id": {"$in": assignment_ids}}).sort(
                "submitted_at", -1
            )
        )
    except PyMongoError as exc:
        logger.error("get_submissions_for_teacher_courses failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_grade(marks: float, max_marks: float) -> tuple[bool, str]:
    """Validate marks input. Returns (ok, error_message)."""
    if marks < 0:
        return False, "Marks cannot be negative."
    if marks > max_marks:
        return False, f"Marks ({marks}) exceed maximum ({max_marks})."
    return True, ""


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def grade_submission(
    db: Database,
    submission_id: ObjectId,
    teacher_id: ObjectId,
    marks: float,
    feedback: str,
    teacher_course_ids: list[ObjectId],
) -> tuple[bool, str]:
    """
    Update marks, feedback, and status on an existing submission.

    Verifies that the submission's assignment belongs to one of the teacher's
    courses before writing.

    Returns (success, message).
    """
    submission = get_submission_by_id(db, submission_id)
    if submission is None:
        return False, "Submission not found."

    # Verify the assignment is in a teacher-owned course
    from services.assignments import get_assignment_by_id
    assignment = get_assignment_by_id(db, submission["assignment_id"])
    if assignment is None:
        return False, "Related assignment not found."

    if assignment["course_id"] not in teacher_course_ids:
        return False, "You can only grade submissions in your own courses."

    max_marks = assignment.get("max_marks", 100)
    ok, err = validate_grade(marks, max_marks)
    if not ok:
        return False, err

    try:
        result = db.submissions.update_one(
            {"_id": submission_id},
            {
                "$set": {
                    "marks": float(marks),
                    "feedback": feedback.strip(),
                    "status": "graded",
                }
            },
        )
        if result.matched_count == 0:
            return False, "Submission not found for update."
        return True, "Grades saved successfully."
    except PyMongoError as exc:
        logger.error("grade_submission failed: %s", exc)
        return False, "Database error while saving grades."


def mark_as_submitted(
    db: Database,
    assignment_id: ObjectId,
    student_id: ObjectId,
    course_id: ObjectId,
    student_course_ids: list[ObjectId],
) -> tuple[bool, str]:
    """
    Create a submission status record for a student.

    IMPORTANT: This creates a status record only — it does NOT store an answer
    or file.  The confirmed schema has no answer/file field.

    Verifies that the student is enrolled in the relevant course.
    """
    if course_id not in student_course_ids:
        return False, "You are not enrolled in this course."

    # Check for duplicate
    existing = get_submission(db, assignment_id, student_id)
    if existing is not None:
        return False, "A submission record already exists for this assignment."

    doc = {
        "assignment_id": assignment_id,
        "student_id": student_id,
        "submitted_at": datetime.now(timezone.utc),
        "status": "submitted",
        "marks": None,
        "feedback": "",
    }
    try:
        result = db.submissions.insert_one(doc)
        return bool(result.inserted_id), (
            "Submission status recorded. "
            "Note: this records your status only — no answer file is stored."
        )
    except PyMongoError as exc:
        logger.error("mark_as_submitted failed: %s", exc)
        return False, "Database error while recording submission."
