"""
pages/2_Assignments.py — CampusFlow Assignments Page.

Teachers can:
  - Browse assignments across managed courses
  - Create new assignments with deadlines and max marks
  - Edit existing assignment instructions and due dates
  - Delete assignments safely (with orphan warnings)

Students can:
  - Browse assignments for enrolled courses
  - Filter by upcoming/past deadline and course
  - Track submission status, grades, and feedback
  - Record submission status (status-only action)
"""

from datetime import datetime, timedelta
import streamlit as st

st.set_page_config(
    page_title="CampusFlow — Assignments",
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
    get_utc_now,
)
from components.tables import assignments_table
from components import feedback as fb
from database import get_db
from auth import init_auth, get_current_user, is_teacher, is_student
from services.courses import get_courses_for_teacher, get_courses_for_student
from services.assignments import (
    get_assignments_for_courses,
    get_assignment_by_id,
    create_assignment,
    update_assignment,
    delete_assignment,
)
from services.submissions import get_submissions_for_student, mark_as_submitted

inject_css()
render_sidebar_header()

db = get_db()
init_auth(db)

if db is None:
    no_db_banner()
    st.stop()

user = get_current_user()
if user is None:
    empty_state("No user selected.", "Use the sidebar to choose a demo identity.")
    st.stop()

now = get_utc_now()

# ═════════════════════════════════════════════════════════════════════════════
# TEACHER VIEW
# ═════════════════════════════════════════════════════════════════════════════
if is_teacher():
    teacher_id = user["_id"]
    page_header(
        title="Assignments",
        subtitle=f"Create course tasks, manage milestones, and set deadlines · {user['name']}",
        eyebrow="COURSEWORK & DEADLINES",
    )

    courses = get_courses_for_teacher(db, teacher_id)
    if not courses:
        empty_state(
            "You have no active courses.",
            "Please create a course on the Courses page before adding assignments.",
        )
        st.stop()

    course_map = {str(c["_id"]): c for c in courses}
    course_ids = [c["_id"] for c in courses]
    assignments = get_assignments_for_courses(db, course_ids)

    # ── Create Assignment Expander ───────────────────────────────────────────
    with st.expander("＋ Create New Assignment", expanded=len(assignments) == 0):
        with st.form("create_assign_form", clear_on_submit=True):
            st.markdown("<p style='font-size:0.95rem;font-weight:700;color:#14243A;margin-bottom:0.5rem;'>Assignment Details</p>", unsafe_allow_html=True)
            col_a1, col_a2 = st.columns([1, 1])
            with col_a1:
                course_options = {c["title"]: c["_id"] for c in courses}
                sel_course_title = st.selectbox("Assign to Course *", list(course_options.keys()))
                a_title = st.text_input("Assignment Title *", placeholder="e.g. Lab 3 — Normalization & Indexes", max_chars=120)
            with col_a2:
                default_deadline = (datetime.now() + timedelta(days=7)).date()
                a_deadline = st.date_input("Due Date *", value=default_deadline)
                col_time, col_marks = st.columns([1, 1])
                with col_time:
                    a_deadline_time = st.time_input("Due Time", value=datetime(2023, 1, 1, 23, 59).time())
                with col_marks:
                    a_max = st.number_input("Maximum Marks *", min_value=1, value=20, step=1)

            a_desc = st.text_area("Instructions & Requirements *", placeholder="Describe deliverables, format expectations, and evaluation rubric...", height=85)
            create_btn = st.form_submit_button("Publish Assignment", type="primary")

        if create_btn:
            combined = datetime.combine(a_deadline, a_deadline_time)
            ok, msg = create_assignment(
                db,
                course_options[sel_course_title],
                teacher_id,
                a_title,
                a_desc,
                combined,
                float(a_max),
            )
            if ok:
                fb.success(msg)
                st.rerun()
            else:
                fb.error(msg)

    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

    # ── Filter Bar ───────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns([3, 2, 2])
    with col_f1:
        search = st.text_input("Search", placeholder="Search by assignment title...", key="a_search", label_visibility="collapsed")
    with col_f2:
        course_filter = st.selectbox(
            "Course", ["All Courses"] + [c["title"] for c in courses], key="a_course_filter", label_visibility="collapsed"
        )
    with col_f3:
        time_filter = st.selectbox(
            "Timeline", ["All Deadlines", "Upcoming Only", "Past Due"], key="a_time_filter", label_visibility="collapsed"
        )

    filtered = assignments
    if search:
        filtered = [a for a in filtered if search.lower() in a.get("title", "").lower()]
    if course_filter != "All Courses":
        fid = next((c["_id"] for c in courses if c["title"] == course_filter), None)
        if fid:
            filtered = [a for a in filtered if a.get("course_id") == fid]

    if time_filter == "Upcoming Only":
        filtered = [
            a for a in filtered
            if isinstance(a.get("deadline"), datetime) and (a["deadline"].replace(tzinfo=None) if a["deadline"].tzinfo else a["deadline"]) > now
        ]
    elif time_filter == "Past Due":
        filtered = [
            a for a in filtered
            if isinstance(a.get("deadline"), datetime) and (a["deadline"].replace(tzinfo=None) if a["deadline"].tzinfo else a["deadline"]) <= now
        ]

    if not filtered:
        empty_state("No assignments match the selected filters.")
    else:
        assignments_table(filtered, course_map)

    # ── Edit / Delete Section ────────────────────────────────────────────────
    if assignments:
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:0.95rem;font-weight:700;color:#14243A;margin-bottom:0.6rem;'>Modify or Remove Assignment</p>", unsafe_allow_html=True)

        assign_options = {
            f"{a['title']} — {course_map.get(str(a.get('course_id')), {}).get('title', 'Course')}": a["_id"]
            for a in assignments
        }
        sel_assign_label = st.selectbox("Select assignment to modify", list(assign_options.keys()), key="edit_assign_sel")
        sel_assign_id = assign_options[sel_assign_label]
        sel_assign = get_assignment_by_id(db, sel_assign_id)

        if sel_assign:
            tab_edit, tab_delete = st.tabs(["Edit Assignment", "Delete Assignment"])

            with tab_edit:
                with st.form("edit_assign_form"):
                    col_e1, col_e2 = st.columns([1, 1])
                    with col_e1:
                        e_title = st.text_input("Title *", value=sel_assign.get("title", ""))
                        existing_dl = sel_assign.get("deadline")
                        dl_date = existing_dl.date() if isinstance(existing_dl, datetime) else (datetime.now() + timedelta(days=7)).date()
                        dl_time = existing_dl.time() if isinstance(existing_dl, datetime) else datetime(2023, 1, 1, 23, 59).time()
                        e_date = st.date_input("Deadline Date *", value=dl_date, key="edit_dl_date")
                    with col_e2:
                        e_time = st.time_input("Deadline Time", value=dl_time, key="edit_dl_time")
                        e_max = st.number_input("Max Marks *", min_value=1, value=int(sel_assign.get("max_marks", 20)), step=1)

                    e_desc = st.text_area("Instructions *", value=sel_assign.get("description", ""), height=80)
                    save_btn = st.form_submit_button("Save Changes", type="primary")

                if save_btn:
                    combined_e = datetime.combine(e_date, e_time)
                    ok, msg = update_assignment(db, sel_assign_id, teacher_id, e_title, e_desc, combined_e, float(e_max))
                    if ok:
                        fb.success(msg)
                        st.rerun()
                    else:
                        fb.error(msg)

            with tab_delete:
                sub_count = db.submissions.count_documents({"assignment_id": sel_assign_id})
                if sub_count:
                    fb.warning(
                        f"Attention: {sub_count} student submission(s) currently reference this assignment. "
                        "Deleting this assignment will orphan those submissions without removing them."
                    )
                st.markdown(f"<p style='font-size:0.9rem;margin:6px 0;'>Confirm deletion of <b>{sel_assign.get('title')}</b>:</p>", unsafe_allow_html=True)
                confirm = st.checkbox("I acknowledge this assignment will be permanently deleted.", key="del_confirm")
                if st.button("Delete Assignment", type="primary", disabled=not confirm):
                    ok, msg = delete_assignment(db, sel_assign_id, teacher_id)
                    if ok:
                        fb.success(msg)
                        st.rerun()
                    else:
                        fb.error(msg)

# ═════════════════════════════════════════════════════════════════════════════
# STUDENT VIEW
# ═════════════════════════════════════════════════════════════════════════════
elif is_student():
    student_id = user["_id"]
    page_header(
        title="Assignments",
        subtitle=f"Coursework deadlines, milestones, and grading feedback · {user['name']}",
        eyebrow="MY COURSEWORK",
    )

    courses = get_courses_for_student(db, student_id)
    if not courses:
        empty_state(
            "You are not enrolled in any courses.",
            "Ask your course instructor to register you on their class roster.",
        )
        st.stop()

    course_map = {str(c["_id"]): c for c in courses}
    course_ids = [c["_id"] for c in courses]
    assignments = get_assignments_for_courses(db, course_ids)
    my_submissions = get_submissions_for_student(db, student_id)
    submission_map = {str(s["assignment_id"]): s for s in my_submissions}

    # ── Filter Bar ───────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns([3, 2, 2])
    with col_f1:
        search = st.text_input("Search", placeholder="Search by assignment title...", key="s_a_search", label_visibility="collapsed")
    with col_f2:
        course_filter = st.selectbox("Course", ["All Courses"] + [c["title"] for c in courses], key="s_a_course", label_visibility="collapsed")
    with col_f3:
        time_filter = st.selectbox("Timeline", ["All Deadlines", "Upcoming Only", "Past Due"], key="s_a_time", label_visibility="collapsed")

    filtered = assignments
    if search:
        filtered = [a for a in filtered if search.lower() in a.get("title", "").lower()]
    if course_filter != "All Courses":
        fid = next((c["_id"] for c in courses if c["title"] == course_filter), None)
        if fid:
            filtered = [a for a in filtered if a.get("course_id") == fid]

    if time_filter == "Upcoming Only":
        filtered = [
            a for a in filtered
            if isinstance(a.get("deadline"), datetime) and (a["deadline"].replace(tzinfo=None) if a["deadline"].tzinfo else a["deadline"]) > now
        ]
    elif time_filter == "Past Due":
        filtered = [
            a for a in filtered
            if isinstance(a.get("deadline"), datetime) and (a["deadline"].replace(tzinfo=None) if a["deadline"].tzinfo else a["deadline"]) <= now
        ]

    if not filtered:
        empty_state("No assignments match the selected filters.")
    else:
        assignments_table(filtered, course_map, submission_map)

        # ── Record Submission Status ─────────────────────────────────────────
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div class="cf-panel">
              <p style="font-size:0.95rem;font-weight:700;color:#14243A;margin-bottom:4px;">Record Submission Status</p>
              <p style="font-size:0.8rem;color:#68758A;margin-bottom:12px;">
                Note: In this database schema, this action logs your completion timestamp and creates a status record for your instructor to grade. It does not upload answer files.
              </p>
            """,
            unsafe_allow_html=True,
        )

        unsubmitted = [
            a for a in filtered
            if str(a["_id"]) not in submission_map
            and isinstance(a.get("deadline"), datetime)
            and (a["deadline"].replace(tzinfo=None) if a["deadline"].tzinfo else a["deadline"]) > now
        ]

        if unsubmitted:
            col_sub1, col_sub2 = st.columns([3, 1])
            assign_opts = {f"{a['title']} ({course_map.get(str(a.get('course_id')),{}).get('title','Course')})": a for a in unsubmitted}
            with col_sub1:
                sel_title = st.selectbox("Select Pending Assignment", list(assign_opts.keys()), key="submit_sel", label_visibility="collapsed")
            with col_sub2:
                sel_assign = assign_opts[sel_title]
                if st.button("Mark as Submitted", type="primary", key="mark_submitted_btn"):
                    ok, msg = mark_as_submitted(
                        db,
                        sel_assign["_id"],
                        student_id,
                        sel_assign["course_id"],
                        course_ids,
                    )
                    if ok:
                        fb.success(msg)
                        st.rerun()
                    else:
                        fb.error(msg)
        else:
            st.caption("All upcoming assignments have already been logged as submitted.")
        st.markdown("</div>", unsafe_allow_html=True)

else:
    page_header("Assignments", eyebrow="ACCOUNTS")
    empty_state(f"Role '{user.get('role', 'unknown')}' does not have an active coursework workspace.")
