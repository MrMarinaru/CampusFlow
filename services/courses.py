"""
services/courses.py — Course database operations.

All functions accept a PyMongo database object and return plain Python
dicts/lists.  ObjectId conversion happens at the database boundary here, not
in UI code.
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

def get_all_courses(db: Database) -> list[dict]:
    """Return all courses, sorted by created_at descending."""
    try:
        return list(db.courses.find({}).sort("created_at", -1))
    except PyMongoError as exc:
        logger.error("get_all_courses failed: %s", exc)
        return []


def get_courses_for_teacher(db: Database, teacher_id: ObjectId) -> list[dict]:
    """Return courses whose teacher_id matches the given ObjectId."""
    try:
        return list(db.courses.find({"teacher_id": teacher_id}).sort("created_at", -1))
    except PyMongoError as exc:
        logger.error("get_courses_for_teacher failed: %s", exc)
        return []


def get_courses_for_student(db: Database, student_id: ObjectId) -> list[dict]:
    """Return courses where student_id appears in student_ids array."""
    try:
        return list(db.courses.find({"student_ids": student_id}).sort("created_at", -1))
    except PyMongoError as exc:
        logger.error("get_courses_for_student failed: %s", exc)
        return []


def get_course_by_id(db: Database, course_id: ObjectId) -> Optional[dict]:
    """Return a single course by _id, or None."""
    try:
        return db.courses.find_one({"_id": course_id})
    except PyMongoError as exc:
        logger.error("get_course_by_id failed: %s", exc)
        return None


def get_users_by_ids(db: Database, user_ids: list[ObjectId]) -> dict[str, dict]:
    """
    Bulk-fetch users by a list of ObjectIds.
    Returns a dict keyed by str(ObjectId) → user doc.
    """
    if not user_ids:
        return {}
    try:
        users = db.users.find(
            {"_id": {"$in": user_ids}},
            {"name": 1, "email": 1, "role": 1},
        )
        return {str(u["_id"]): u for u in users}
    except PyMongoError as exc:
        logger.error("get_users_by_ids failed: %s", exc)
        return {}


def get_all_students(db: Database) -> list[dict]:
    """Return all users with role 'student'."""
    try:
        return list(db.users.find({"role": "student"}, {"name": 1, "email": 1, "role": 1}))
    except PyMongoError as exc:
        logger.error("get_all_students failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def create_course(
    db: Database,
    title: str,
    description: str,
    teacher_id: ObjectId,
    student_ids: list[ObjectId],
) -> tuple[bool, str]:
    """
    Insert a new course document.
    Returns (success, message).
    """
    if not title.strip():
        return False, "Course title cannot be empty."
    if not description.strip():
        return False, "Course description cannot be empty."

    doc = {
        "title": title.strip(),
        "description": description.strip(),
        "teacher_id": teacher_id,
        "student_ids": list(set(student_ids)),  # deduplicate
        "created_at": datetime.now(timezone.utc),
    }
    try:
        result = db.courses.insert_one(doc)
        if result.inserted_id:
            return True, f"Course created successfully."
        return False, "Insert did not return an ID."
    except PyMongoError as exc:
        logger.error("create_course failed: %s", exc)
        return False, "Database error while creating course."


def add_students_to_course(
    db: Database,
    course_id: ObjectId,
    teacher_id: ObjectId,
    new_student_ids: list[ObjectId],
) -> tuple[bool, str]:
    """
    Add student ObjectIds to a course's student_ids array.
    Verifies teacher ownership first.
    """
    course = get_course_by_id(db, course_id)
    if course is None:
        return False, "Course not found."
    if course.get("teacher_id") != teacher_id:
        return False, "You can only modify your own courses."

    try:
        result = db.courses.update_one(
            {"_id": course_id, "teacher_id": teacher_id},
            {"$addToSet": {"student_ids": {"$each": new_student_ids}}},
        )
        if result.modified_count:
            return True, f"Added {len(new_student_ids)} student(s)."
        return True, "No changes made (students may already be enrolled)."
    except PyMongoError as exc:
        logger.error("add_students_to_course failed: %s", exc)
        return False, "Database error while updating enrollment."


def remove_student_from_course(
    db: Database,
    course_id: ObjectId,
    teacher_id: ObjectId,
    student_id: ObjectId,
) -> tuple[bool, str]:
    """
    Remove a single student from a course's student_ids array.
    Verifies teacher ownership first.
    """
    course = get_course_by_id(db, course_id)
    if course is None:
        return False, "Course not found."
    if course.get("teacher_id") != teacher_id:
        return False, "You can only modify your own courses."

    try:
        result = db.courses.update_one(
            {"_id": course_id, "teacher_id": teacher_id},
            {"$pull": {"student_ids": student_id}},
        )
        if result.modified_count:
            return True, "Student removed from course."
        return False, "Student was not enrolled."
    except PyMongoError as exc:
        logger.error("remove_student_from_course failed: %s", exc)
        return False, "Database error while removing student."


def teacher_owns_course(db: Database, course_id: ObjectId, teacher_id: ObjectId) -> bool:
    """Return True if the course belongs to this teacher."""
    course = get_course_by_id(db, course_id)
    return course is not None and course.get("teacher_id") == teacher_id
