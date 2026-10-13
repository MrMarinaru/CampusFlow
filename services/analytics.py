"""
services/analytics.py — Analytics aggregation functions.

All calculations use real MongoDB data.  Functions accept a PyMongo database
and lists of relevant IDs to keep results scoped to teacher-owned content.
"""

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import PyMongoError
import logging

logger = logging.getLogger(__name__)


def submission_status_distribution(
    db: Database, assignment_ids: list[ObjectId]
) -> dict[str, int]:
    """
    Return counts of each submission status for a set of assignments.
    Example: {"graded": 5, "submitted": 3}
    """
    if not assignment_ids:
        return {}
    try:
        pipeline = [
            {"$match": {"assignment_id": {"$in": assignment_ids}}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
        result = db.submissions.aggregate(pipeline)
        return {doc["_id"] or "unknown": doc["count"] for doc in result}
    except PyMongoError as exc:
        logger.error("submission_status_distribution failed: %s", exc)
        return {}


def avg_marks_by_assignment(
    db: Database, assignment_ids: list[ObjectId]
) -> list[dict]:
    """
    Return average marks per assignment (graded submissions only, null excluded).
    Result: [{"assignment_id": ObjectId, "avg_marks": float, "count": int}, ...]
    """
    if not assignment_ids:
        return []
    try:
        pipeline = [
            {
                "$match": {
                    "assignment_id": {"$in": assignment_ids},
                    "marks": {"$ne": None, "$exists": True},
                }
            },
            {
                "$group": {
                    "_id": "$assignment_id",
                    "avg_marks": {"$avg": "$marks"},
                    "count": {"$sum": 1},
                    "min_marks": {"$min": "$marks"},
                    "max_marks": {"$max": "$marks"},
                }
            },
            {"$sort": {"avg_marks": -1}},
        ]
        return list(db.submissions.aggregate(pipeline))
    except PyMongoError as exc:
        logger.error("avg_marks_by_assignment failed: %s", exc)
        return []


def submission_counts_by_assignment(
    db: Database, assignment_ids: list[ObjectId]
) -> list[dict]:
    """
    Return total submission count per assignment.
    Result: [{"assignment_id": ObjectId, "total": int}, ...]
    """
    if not assignment_ids:
        return []
    try:
        pipeline = [
            {"$match": {"assignment_id": {"$in": assignment_ids}}},
            {"$group": {"_id": "$assignment_id", "total": {"$sum": 1}}},
        ]
        return list(db.submissions.aggregate(pipeline))
    except PyMongoError as exc:
        logger.error("submission_counts_by_assignment failed: %s", exc)
        return []


def graded_marks_distribution(
    db: Database, assignment_ids: list[ObjectId]
) -> list[float]:
    """
    Return a flat list of all numeric marks for graded submissions.
    Used for histogram charts.
    """
    if not assignment_ids:
        return []
    try:
        docs = db.submissions.find(
            {
                "assignment_id": {"$in": assignment_ids},
                "marks": {"$ne": None, "$exists": True},
            },
            {"marks": 1},
        )
        return [d["marks"] for d in docs if isinstance(d.get("marks"), (int, float))]
    except PyMongoError as exc:
        logger.error("graded_marks_distribution failed: %s", exc)
        return []


def pending_grading_count(db: Database, assignment_ids: list[ObjectId]) -> int:
    """Count submissions with status != 'graded' (awaiting grading)."""
    if not assignment_ids:
        return 0
    try:
        return db.submissions.count_documents(
            {
                "assignment_id": {"$in": assignment_ids},
                "status": {"$ne": "graded"},
            }
        )
    except PyMongoError as exc:
        logger.error("pending_grading_count failed: %s", exc)
        return 0


def course_summary(db: Database, course_ids: list[ObjectId]) -> list[dict]:
    """
    Per-course: total submissions, graded count, avg marks.
    Joins via assignment_id → course_id.
    """
    if not course_ids:
        return []
    try:
        # Get assignments per course
        course_to_assignments: dict[str, list[ObjectId]] = {}
        for a in db.assignments.find({"course_id": {"$in": course_ids}}, {"_id": 1, "course_id": 1}):
            cid = str(a["course_id"])
            course_to_assignments.setdefault(cid, []).append(a["_id"])

        summaries = []
        for cid_str, asgn_ids in course_to_assignments.items():
            total = db.submissions.count_documents({"assignment_id": {"$in": asgn_ids}})
            graded = db.submissions.count_documents(
                {"assignment_id": {"$in": asgn_ids}, "status": "graded"}
            )
            marks_docs = list(
                db.submissions.find(
                    {"assignment_id": {"$in": asgn_ids}, "marks": {"$ne": None}},
                    {"marks": 1},
                )
            )
            marks_vals = [d["marks"] for d in marks_docs if isinstance(d.get("marks"), (int, float))]
            avg = round(sum(marks_vals) / len(marks_vals), 1) if marks_vals else None
            summaries.append(
                {
                    "course_id": ObjectId(cid_str),
                    "total_submissions": total,
                    "graded": graded,
                    "avg_marks": avg,
                }
            )
        return summaries
    except PyMongoError as exc:
        logger.error("course_summary failed: %s", exc)
        return []
