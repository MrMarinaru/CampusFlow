"""
services/assignments.py — Assignment database operations.

Field reference (from actual schema):
  course_id, title, description, deadline (BSON Date), max_marks
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

def get_assignments_for_course(db: Database, course_id: ObjectId) -> list[dict]:
    """Return all assignments for a course, sorted by deadline ascending."""
    try:
        return list(db.assignments.find({"course_id": course_id}).sort("deadline", 1))
    except PyMongoError as exc:
        logger.error("get_assignments_for_course failed: %s", exc)
        return []


def get_assignments_for_courses(db: Database, course_ids: list[ObjectId]) -> list[dict]:
    """Bulk-fetch assignments for multiple course IDs."""
    if not course_ids:
        return []
    try:
        return list(
            db.assignments.find({"course_id": {"$in": course_ids}}).sort("deadline", 1)
        )
    except PyMongoError as exc:
        logger.error("get_assignments_for_courses failed: %s", exc)
        return []


def get_assignment_by_id(db: Database, assignment_id: ObjectId) -> Optional[dict]:
    """Return a single assignment by _id, or None."""
    try:
        return db.assignments.find_one({"_id": assignment_id})
    except PyMongoError as exc:
        logger.error("get_assignment_by_id failed: %s", exc)
        return None


def get_all_assignments(db: Database) -> list[dict]:
    """Return all assignments sorted by deadline."""
    try:
        return list(db.assignments.find({}).sort("deadline", 1))
    except PyMongoError as exc:
        logger.error("get_all_assignments failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_assignment_fields(
    title: str,
    description: str,
    deadline: datetime,
    max_marks: float,
) -> tuple[bool, str]:
    """Validate assignment creation/edit inputs. Returns (ok, error_message)."""
    if not title.strip():
        return False, "Title cannot be empty."
    if not description.strip():
        return False, "Description cannot be empty."
    if deadline is None:
        return False, "Deadline is required."
    if deadline < datetime.now():
        return False, "Deadline must be in the future."
    if max_marks <= 0:
        return False, "Maximum marks must be greater than zero."
    return True, ""


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def create_assignment(
    db: Database,
    course_id: ObjectId,
    teacher_id: ObjectId,
    title: str,
    description: str,
    deadline: datetime,
    max_marks: float,
) -> tuple[bool, str]:
    """
    Create an assignment for a teacher-owned course.
    Returns (success, message).
    """
    # Verify ownership
    from services.courses import teacher_owns_course
    if not teacher_owns_course(db, course_id, teacher_id):
        return False, "You can only create assignments for your own courses."

    ok, err = validate_assignment_fields(title, description, deadline, max_marks)
    if not ok:
        return False, err

    # Ensure deadline is timezone-aware for consistent storage
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    doc = {
        "course_id": course_id,
        "title": title.strip(),
        "description": description.strip(),
        "deadline": deadline,
        "max_marks": float(max_marks),
    }
    try:
        result = db.assignments.insert_one(doc)
        return bool(result.inserted_id), "Assignment created successfully."
    except PyMongoError as exc:
        logger.error("create_assignment failed: %s", exc)
        return False, "Database error while creating assignment."


def update_assignment(
    db: Database,
    assignment_id: ObjectId,
    teacher_id: ObjectId,
    title: str,
    description: str,
    deadline: datetime,
    max_marks: float,
) -> tuple[bool, str]:
    """
    Update an existing assignment after verifying teacher ownership.
    """
    assignment = get_assignment_by_id(db, assignment_id)
    if assignment is None:
        return False, "Assignment not found."

    from services.courses import teacher_owns_course
    if not teacher_owns_course(db, assignment["course_id"], teacher_id):
        return False, "You can only edit assignments in your own courses."

    ok, err = validate_assignment_fields(title, description, deadline, max_marks)
    if not ok:
        return False, err

    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    try:
        result = db.assignments.update_one(
            {"_id": assignment_id},
            {
                "$set": {
                    "title": title.strip(),
                    "description": description.strip(),
                    "deadline": deadline,
                    "max_marks": float(max_marks),
                }
            },
        )
        if result.matched_count == 0:
            return False, "Assignment not found for update."
        return True, "Assignment updated successfully."
    except PyMongoError as exc:
        logger.error("update_assignment failed: %s", exc)
        return False, "Database error while updating assignment."


def delete_assignment(
    db: Database,
    assignment_id: ObjectId,
    teacher_id: ObjectId,
) -> tuple[bool, str]:
    """
    Delete an assignment after verifying ownership.
    Note: Related submissions are NOT automatically deleted.
    """
    assignment = get_assignment_by_id(db, assignment_id)
    if assignment is None:
        return False, "Assignment not found."

    from services.courses import teacher_owns_course
    if not teacher_owns_course(db, assignment["course_id"], teacher_id):
        return False, "You can only delete assignments in your own courses."

    # Count orphaned submissions for user awareness
    sub_count = db.submissions.count_documents({"assignment_id": assignment_id})

    try:
        result = db.assignments.delete_one({"_id": assignment_id})
        if result.deleted_count:
            warning = ""
            if sub_count:
                warning = (
                    f" Note: {sub_count} existing submission(s) for this assignment "
                    f"were NOT deleted and remain in the database."
                )
            return True, f"Assignment deleted.{warning}"
        return False, "Assignment could not be deleted."
    except PyMongoError as exc:
        logger.error("delete_assignment failed: %s", exc)
        return False, "Database error while deleting assignment."
