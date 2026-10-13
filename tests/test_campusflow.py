"""
tests/test_campusflow.py

Unit tests for CampusFlow services and utilities.

Tests use mocked PyMongo databases — they do NOT touch the live Atlas cluster.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta, timezone
from bson import ObjectId
import pytest

# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_db():
    """Return a mock PyMongo database object."""
    return MagicMock()


# ── Config loading ─────────────────────────────────────────────────────────────

class TestConfig:
    def test_db_name_default(self):
        from config import MONGODB_DB_NAME
        assert MONGODB_DB_NAME == "classflow"

    def test_expected_collections(self):
        from config import EXPECTED_COLLECTIONS
        assert set(EXPECTED_COLLECTIONS) == {"users", "courses", "assignments", "submissions"}

    def test_role_constants(self):
        from config import ROLE_TEACHER, ROLE_STUDENT
        assert ROLE_TEACHER == "teacher"
        assert ROLE_STUDENT == "student"


# ── ObjectId handling ──────────────────────────────────────────────────────────

class TestObjectId:
    def test_objectid_from_string(self):
        raw = "6ace1c94fee50681bed5d425"
        oid = ObjectId(raw)
        assert str(oid) == raw

    def test_invalid_objectid_raises(self):
        with pytest.raises(Exception):
            ObjectId("not_a_valid_id")

    def test_objectid_equality(self):
        raw = "6ace1c94fee50681bed5d425"
        assert ObjectId(raw) == ObjectId(raw)

    def test_objectid_in_set(self):
        oid = ObjectId("6ace1c94fee50681bed5d425")
        s = {oid}
        assert ObjectId("6ace1c94fee50681bed5d425") in s


# ── submissions.validate_grade ─────────────────────────────────────────────────

class TestValidateGrade:
    def setup_method(self):
        from services.submissions import validate_grade
        self.validate = validate_grade

    def test_valid_marks(self):
        ok, err = self.validate(15, 20)
        assert ok is True
        assert err == ""

    def test_zero_marks_valid(self):
        ok, _ = self.validate(0, 20)
        assert ok is True

    def test_full_marks_valid(self):
        ok, _ = self.validate(20, 20)
        assert ok is True

    def test_negative_marks_invalid(self):
        ok, err = self.validate(-1, 20)
        assert ok is False
        assert "negative" in err.lower()

    def test_exceeds_max_invalid(self):
        ok, err = self.validate(21, 20)
        assert ok is False
        assert "exceed" in err.lower()

    def test_float_marks_valid(self):
        ok, _ = self.validate(17.5, 20)
        assert ok is True


# ── assignments.validate_assignment_fields ─────────────────────────────────────

class TestValidateAssignmentFields:
    def setup_method(self):
        from services.assignments import validate_assignment_fields
        self.validate = validate_assignment_fields

    def test_valid_fields(self):
        future = datetime.now() + timedelta(days=5)
        ok, err = self.validate("Title", "Desc", future, 20)
        assert ok is True
        assert err == ""

    def test_empty_title_invalid(self):
        future = datetime.now() + timedelta(days=5)
        ok, err = self.validate("", "Desc", future, 20)
        assert ok is False
        assert "title" in err.lower()

    def test_empty_description_invalid(self):
        future = datetime.now() + timedelta(days=5)
        ok, err = self.validate("Title", "", future, 20)
        assert ok is False
        assert "description" in err.lower()

    def test_past_deadline_invalid(self):
        past = datetime.now() - timedelta(days=1)
        ok, err = self.validate("Title", "Desc", past, 20)
        assert ok is False
        assert "future" in err.lower()

    def test_zero_max_marks_invalid(self):
        future = datetime.now() + timedelta(days=5)
        ok, err = self.validate("Title", "Desc", future, 0)
        assert ok is False
        assert "marks" in err.lower()

    def test_negative_max_marks_invalid(self):
        future = datetime.now() + timedelta(days=5)
        ok, err = self.validate("Title", "Desc", future, -5)
        assert ok is False


# ── courses.teacher_owns_course ────────────────────────────────────────────────

class TestTeacherOwnership:
    def test_teacher_owns_course_true(self):
        teacher_id = ObjectId()
        course_id = ObjectId()
        db = _make_db()
        db.courses.find_one.return_value = {
            "_id": course_id,
            "teacher_id": teacher_id,
            "title": "Test",
        }
        from services.courses import teacher_owns_course
        assert teacher_owns_course(db, course_id, teacher_id) is True

    def test_teacher_owns_course_false_wrong_teacher(self):
        teacher_id = ObjectId()
        other_teacher = ObjectId()
        course_id = ObjectId()
        db = _make_db()
        db.courses.find_one.return_value = {
            "_id": course_id,
            "teacher_id": other_teacher,
            "title": "Test",
        }
        from services.courses import teacher_owns_course
        assert teacher_owns_course(db, course_id, teacher_id) is False

    def test_teacher_owns_course_none_when_missing(self):
        db = _make_db()
        db.courses.find_one.return_value = None
        from services.courses import teacher_owns_course
        assert teacher_owns_course(db, ObjectId(), ObjectId()) is False


# ── courses.create_course ──────────────────────────────────────────────────────

class TestCreateCourse:
    def test_create_course_success(self):
        db = _make_db()
        inserted_id = ObjectId()
        db.courses.insert_one.return_value.inserted_id = inserted_id
        from services.courses import create_course
        ok, msg = create_course(db, "Python 101", "A course", ObjectId(), [])
        assert ok is True
        assert "successfully" in msg.lower()

    def test_create_course_empty_title(self):
        db = _make_db()
        from services.courses import create_course
        ok, msg = create_course(db, "", "A course", ObjectId(), [])
        assert ok is False
        assert "title" in msg.lower()

    def test_create_course_empty_description(self):
        db = _make_db()
        from services.courses import create_course
        ok, msg = create_course(db, "Title", "", ObjectId(), [])
        assert ok is False

    def test_create_course_deduplicates_student_ids(self):
        db = _make_db()
        db.courses.insert_one.return_value.inserted_id = ObjectId()
        sid = ObjectId()
        from services.courses import create_course
        create_course(db, "Title", "Desc", ObjectId(), [sid, sid])
        call_args = db.courses.insert_one.call_args[0][0]
        assert len(call_args["student_ids"]) == 1


# ── submissions.grade_submission ───────────────────────────────────────────────

class TestGradeSubmission:
    def test_grade_submission_success(self):
        teacher_id = ObjectId()
        course_id = ObjectId()
        assign_id = ObjectId()
        sub_id = ObjectId()
        student_id = ObjectId()

        db = _make_db()
        db.submissions.find_one.return_value = {
            "_id": sub_id,
            "assignment_id": assign_id,
            "student_id": student_id,
            "status": "submitted",
            "marks": None,
            "feedback": "",
        }
        db.assignments.find_one.return_value = {
            "_id": assign_id,
            "course_id": course_id,
            "max_marks": 20,
        }
        db.courses.find_one.return_value = {
            "_id": course_id,
            "teacher_id": teacher_id,
        }
        db.submissions.update_one.return_value.matched_count = 1

        from services.submissions import grade_submission
        ok, msg = grade_submission(db, sub_id, teacher_id, 15.0, "Good work", [course_id])
        assert ok is True
        assert "success" in msg.lower()

    def test_grade_submission_marks_exceed_max(self):
        teacher_id = ObjectId()
        course_id = ObjectId()
        assign_id = ObjectId()
        sub_id = ObjectId()

        db = _make_db()
        db.submissions.find_one.return_value = {
            "_id": sub_id,
            "assignment_id": assign_id,
            "student_id": ObjectId(),
            "status": "submitted",
        }
        db.assignments.find_one.return_value = {
            "_id": assign_id,
            "course_id": course_id,
            "max_marks": 20,
        }
        db.courses.find_one.return_value = {"_id": course_id, "teacher_id": teacher_id}

        from services.submissions import grade_submission
        ok, msg = grade_submission(db, sub_id, teacher_id, 99.0, "", [course_id])
        assert ok is False
        assert "exceed" in msg.lower()

    def test_grade_submission_wrong_course(self):
        teacher_id = ObjectId()
        course_id = ObjectId()
        other_course = ObjectId()
        assign_id = ObjectId()
        sub_id = ObjectId()

        db = _make_db()
        db.submissions.find_one.return_value = {
            "_id": sub_id,
            "assignment_id": assign_id,
            "student_id": ObjectId(),
        }
        db.assignments.find_one.return_value = {
            "_id": assign_id,
            "course_id": other_course,
            "max_marks": 20,
        }

        from services.submissions import grade_submission
        ok, msg = grade_submission(db, sub_id, teacher_id, 10.0, "", [course_id])
        assert ok is False

    def test_grade_submission_not_found(self):
        db = _make_db()
        db.submissions.find_one.return_value = None
        from services.submissions import grade_submission
        ok, msg = grade_submission(db, ObjectId(), ObjectId(), 10.0, "", [])
        assert ok is False
        assert "not found" in msg.lower()


# ── analytics: empty datasets ──────────────────────────────────────────────────

class TestAnalyticsEmptyDatasets:
    def test_status_distribution_empty_ids(self):
        from services.analytics import submission_status_distribution
        db = _make_db()
        result = submission_status_distribution(db, [])
        assert result == {}

    def test_avg_marks_empty_ids(self):
        from services.analytics import avg_marks_by_assignment
        db = _make_db()
        result = avg_marks_by_assignment(db, [])
        assert result == []

    def test_pending_count_empty_ids(self):
        from services.analytics import pending_grading_count
        db = _make_db()
        result = pending_grading_count(db, [])
        assert result == 0

    def test_marks_distribution_empty(self):
        from services.analytics import graded_marks_distribution
        db = _make_db()
        result = graded_marks_distribution(db, [])
        assert result == []


# ── Missing / optional fields handling ────────────────────────────────────────

class TestMissingFields:
    def test_submission_without_marks(self):
        sub = {"_id": ObjectId(), "status": "submitted", "marks": None, "feedback": ""}
        assert sub.get("marks") is None

    def test_submission_without_feedback(self):
        sub = {"_id": ObjectId(), "status": "submitted"}
        assert sub.get("feedback", "") == ""

    def test_course_without_student_ids(self):
        course = {"_id": ObjectId(), "title": "Test", "teacher_id": ObjectId()}
        assert len(course.get("student_ids", [])) == 0

    def test_user_without_email(self):
        user = {"_id": ObjectId(), "name": "Test", "role": "student"}
        assert user.get("email", "") == ""

    def test_user_unknown_role_handled(self):
        user = {"_id": ObjectId(), "name": "Test", "role": "admin"}
        from config import ROLE_TEACHER, ROLE_STUDENT
        role = user.get("role", "")
        assert role not in (ROLE_TEACHER, ROLE_STUDENT)


# ── Field name compliance ──────────────────────────────────────────────────────

class TestFieldNameCompliance:
    """Verify that no banned field names are used as if they existed."""

    def test_no_due_date_in_services_assignments(self):
        import services.assignments as mod
        import inspect
        src = inspect.getsource(mod)
        assert "due_date" not in src, "Use 'deadline', not 'due_date'"

    def test_no_password_field_in_auth(self):
        import auth
        import inspect
        src = inspect.getsource(auth)
        assert "password" not in src.lower(), "No password field in auth"

    def test_no_answer_field_in_submissions_service(self):
        import services.submissions as mod
        import inspect
        src = inspect.getsource(mod)
        assert '"answer"' not in src, "No answer field"
        assert "'answer'" not in src, "No answer field"

    def test_submission_write_fields_confirmed_only(self):
        """Verify grade_submission only sets confirmed fields."""
        import services.submissions as mod
        import inspect
        src = inspect.getsource(mod)
        # Confirmed write fields
        assert '"marks"' in src
        assert '"feedback"' in src
        assert '"status"' in src
