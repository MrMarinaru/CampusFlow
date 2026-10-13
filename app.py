"""
app.py — CampusFlow main entry point & Overview Dashboard.

Run with:
    python -m streamlit run app.py
"""

from datetime import datetime
import streamlit as st

# ── Page config (must be the first Streamlit command) ────────────────────────
st.set_page_config(
    page_title="CampusFlow — Overview",
    page_icon="assets/favicon.svg",
    layout="wide",
    initial_sidebar_state="expanded",
)

from components.layout import (
    inject_css,
    render_sidebar_header,
    page_header,
    empty_state,
    no_db_banner,
    metric_row,
    status_badge,
    get_utc_now,
)
from database import get_db
from auth import init_auth, get_current_user, is_teacher, is_student

# ── Global styles & Sidebar scaffold ─────────────────────────────────────────
inject_css()
render_sidebar_header()

db = get_db()
init_auth(db)

user = get_current_user()

# ── Check database availability ──────────────────────────────────────────────
if db is None:
    no_db_banner()
    st.stop()

if user is None:
    page_header("Overview", "Select an identity from the sidebar to continue.", eyebrow="WORKSPACE")
    empty_state(
        "No users found in the database.",
        "Add user documents to the 'users' collection in MongoDB Atlas to begin.",
    )
    st.stop()

now = get_utc_now()
today_str = datetime.now().strftime("%A, %d %B %Y")

# ═════════════════════════════════════════════════════════════════════════════
# TEACHER OVERVIEW DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════
if is_teacher():
    from services.courses import get_courses_for_teacher
    from services.assignments import get_assignments_for_courses
    from services.analytics import pending_grading_count

    teacher_id = user["_id"]
    courses = get_courses_for_teacher(db, teacher_id)
    course_ids = [c["_id"] for c in courses]
    course_map = {str(c["_id"]): c for c in courses}
    assignments = get_assignments_for_courses(db, course_ids)
    assign_ids = [a["_id"] for a in assignments]

    total_students = sum(len(c.get("student_ids", [])) for c in courses)
    pending = pending_grading_count(db, assign_ids)

    # Filter upcoming assignments
    upcoming = []
    for a in assignments:
        dl = a.get("deadline")
        if isinstance(dl, datetime):
            dl_cmp = dl.replace(tzinfo=None) if dl.tzinfo else dl
            if dl_cmp > now:
                upcoming.append(a)
    upcoming.sort(key=lambda x: x["deadline"].replace(tzinfo=None) if x["deadline"].tzinfo else x["deadline"])

    # Header
    page_header(
        title="Overview",
        subtitle=f"Welcome back, {user['name']} · {today_str}",
        eyebrow="TEACHER WORKSPACE",
    )

    # Metrics row
    metric_row(
        [
            ("Active Courses", len(courses)),
            ("Total Assignments", len(assignments)),
            ("Pending Grading", pending),
            ("Enrolled Students", total_students),
        ]
    )

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 1], gap="medium")

    # Column 1: Upcoming Deadlines
    with col_left:
        st.markdown(
            f"""
            <div class="cf-panel">
              <div class="cf-panel-title">
                <span>Upcoming Deadlines</span>
                <span style="font-size:0.75rem;font-weight:600;color:#4569E8;">{len(upcoming)} Scheduled</span>
              </div>
            """,
            unsafe_allow_html=True,
        )
        if upcoming:
            for a in upcoming[:5]:
                course = course_map.get(str(a.get("course_id")), {})
                c_title = course.get("title", "Course")
                dl = a["deadline"]
                dl_str = dl.strftime("%d %b %Y, %H:%M") if isinstance(dl, datetime) else "—"
                max_m = int(a.get("max_marks", 0)) if float(a.get("max_marks", 0)).is_integer() else a.get("max_marks", 0)
                st.markdown(
                    f"""
                    <div class="cf-row-item">
                      <div>
                        <p class="cf-row-primary">{a['title']}</p>
                        <p class="cf-row-meta">{c_title} · Due {dl_str}</p>
                      </div>
                      <div>
                        <span class="badge badge-upcoming">{max_m} Marks</span>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            empty_state("No upcoming deadlines scheduled.", "Create an assignment on the Assignments page.")
        st.markdown("</div>", unsafe_allow_html=True)

    # Column 2: Managed Courses
    with col_right:
        st.markdown(
            f"""
            <div class="cf-panel">
              <div class="cf-panel-title">
                <span>Your Courses</span>
                <span style="font-size:0.75rem;font-weight:600;color:#68758A;">{len(courses)} Total</span>
              </div>
            """,
            unsafe_allow_html=True,
        )
        if courses:
            for c in courses:
                enrolled = len(c.get("student_ids", []))
                created = c.get("created_at")
                c_date = created.strftime("%d %b %Y") if isinstance(created, datetime) else "—"
                st.markdown(
                    f"""
                    <div class="cf-row-item">
                      <div>
                        <p class="cf-row-primary">{c['title']}</p>
                        <p class="cf-row-meta">Created {c_date} · {c.get('description', '')[:50]}</p>
                      </div>
                      <div>
                        <span class="badge badge-submitted">{enrolled} Students</span>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            empty_state("You have not created any courses yet.", "Create your first course on the Courses page.")
        st.markdown("</div>", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# STUDENT OVERVIEW DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════
elif is_student():
    from services.courses import get_courses_for_student
    from services.assignments import get_assignments_for_courses
    from services.submissions import get_submissions_for_student

    student_id = user["_id"]
    courses = get_courses_for_student(db, student_id)
    course_ids = [c["_id"] for c in courses]
    course_map = {str(c["_id"]): c for c in courses}
    assignments = get_assignments_for_courses(db, course_ids)
    submissions = get_submissions_for_student(db, student_id)

    # Categorize deadlines
    upcoming = []
    for a in assignments:
        dl = a.get("deadline")
        if isinstance(dl, datetime):
            dl_cmp = dl.replace(tzinfo=None) if dl.tzinfo else dl
            if dl_cmp > now:
                upcoming.append(a)
    upcoming.sort(key=lambda x: x["deadline"].replace(tzinfo=None) if x["deadline"].tzinfo else x["deadline"])

    submitted_ids = {str(s["assignment_id"]) for s in submissions}
    graded = [s for s in submissions if s.get("status") == "graded"]

    # Header
    page_header(
        title="Overview",
        subtitle=f"Welcome back, {user['name']} · {today_str}",
        eyebrow="STUDENT WORKSPACE",
    )

    # Metrics row
    metric_row(
        [
            ("Enrolled Courses", len(courses)),
            ("Course Assignments", len(assignments)),
            ("Tasks Submitted", len(submissions)),
            ("Graded Submissions", len(graded)),
        ]
    )

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 1], gap="medium")

    # Column 1: Upcoming Deadlines
    with col_left:
        st.markdown(
            f"""
            <div class="cf-panel">
              <div class="cf-panel-title">
                <span>Upcoming Deadlines</span>
                <span style="font-size:0.75rem;font-weight:600;color:#4569E8;">{len(upcoming)} Due</span>
              </div>
            """,
            unsafe_allow_html=True,
        )
        if upcoming:
            for a in upcoming[:5]:
                course = course_map.get(str(a.get("course_id")), {})
                c_title = course.get("title", "Course")
                dl = a["deadline"]
                dl_str = dl.strftime("%d %b %Y, %H:%M") if isinstance(dl, datetime) else "—"
                is_sub = str(a["_id"]) in submitted_ids
                b_text = "Submitted" if is_sub else "Pending"
                b_cls = "badge-graded" if is_sub else "badge-pending"

                st.markdown(
                    f"""
                    <div class="cf-row-item">
                      <div>
                        <p class="cf-row-primary">{a['title']}</p>
                        <p class="cf-row-meta">{c_title} · Due {dl_str}</p>
                      </div>
                      <div>
                        <span class="badge {b_cls}">{b_text}</span>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            empty_state("No upcoming assignment deadlines.", "Check back as courses post new assignments.")
        st.markdown("</div>", unsafe_allow_html=True)

    # Column 2: Recent Grades
    with col_right:
        st.markdown(
            f"""
            <div class="cf-panel">
              <div class="cf-panel-title">
                <span>Recent Grades & Feedback</span>
                <span style="font-size:0.75rem;font-weight:600;color:#065F46;">{len(graded)} Graded</span>
              </div>
            """,
            unsafe_allow_html=True,
        )
        if graded:
            sorted_graded = sorted(
                graded,
                key=lambda x: x.get("submitted_at") or datetime.min,
                reverse=True,
            )
            for s in sorted_graded[:5]:
                assignment = next((a for a in assignments if a["_id"] == s.get("assignment_id")), None)
                a_title = assignment["title"] if assignment else "Assignment"
                max_m = assignment.get("max_marks", "—") if assignment else "—"
                marks = s.get("marks")
                marks_str = f"{int(marks) if isinstance(marks, float) and marks.is_integer() else marks}" if marks is not None else "—"
                feedback = s.get("feedback", "").strip()

                st.markdown(
                    f"""
                    <div class="cf-row-item">
                      <div>
                        <p class="cf-row-primary">{a_title}</p>
                        <p class="cf-row-meta" style="color:#065F46;font-weight:600;">{marks_str} / {max_m} Marks</p>
                        {'<p style="font-size:0.76rem;color:#68758A;margin:2px 0 0 0;font-style:italic;">"' + feedback[:65] + ('…' if len(feedback)>65 else '') + '"</p>' if feedback else ''}
                      </div>
                      <div>
                        <span class="badge badge-graded">Graded</span>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            empty_state("No graded submissions yet.", "Submitted tasks will appear here once graded by your instructor.")
        st.markdown("</div>", unsafe_allow_html=True)

else:
    role = user.get("role", "unknown")
    page_header("Overview", f"Account role: {role}", eyebrow="ACCOUNT")
    empty_state(
        f"Role '{role}' is not configured with a dedicated workspace dashboard.",
        "Please select a Teacher or Student identity from the sidebar selector.",
    )
