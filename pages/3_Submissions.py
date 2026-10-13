"""
pages/3_Submissions.py — CampusFlow Submissions & Grading Page.

Teachers can:
  - View all student submissions across managed courses
  - Filter submissions by course, grading status, and student
  - Review student submission details and evaluate coursework
  - Enter marks, provide feedback, and record graded status

Students can:
  - Review their submission log and status across courses
  - View awarded marks and instructor feedback
"""

import streamlit as st

st.set_page_config(
    page_title="CampusFlow — Submissions & Grading",
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
    status_badge,
)
from components.tables import submissions_table
from components import feedback as fb
from database import get_db
from auth import init_auth, get_current_user, is_teacher, is_student
from services.courses import get_courses_for_teacher, get_courses_for_student, get_users_by_ids
from services.assignments import get_assignments_for_courses
from services.submissions import (
    get_submissions_for_teacher_courses,
    get_submissions_for_student,
    get_submission_by_id,
    grade_submission,
)

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

# ═════════════════════════════════════════════════════════════════════════════
# TEACHER VIEW
# ═════════════════════════════════════════════════════════════════════════════
if is_teacher():
    teacher_id = user["_id"]
    page_header(
        title="Submissions & Grading",
        subtitle=f"Evaluate coursework, assign marks, and write constructive feedback · {user['name']}",
        eyebrow="ASSESSMENT & EVALUATION",
    )

    courses = get_courses_for_teacher(db, teacher_id)
    if not courses:
        empty_state("You have no active courses.", "Create a course on the Courses page first.")
        st.stop()

    course_map = {str(c["_id"]): c for c in courses}
    course_ids = [c["_id"] for c in courses]
    assignments = get_assignments_for_courses(db, course_ids)
    assign_map = {str(a["_id"]): a for a in assignments}
    assign_ids = [a["_id"] for a in assignments]

    submissions = get_submissions_for_teacher_courses(db, assign_ids)

    # Student map
    student_ids_in_submissions = list({s["student_id"] for s in submissions})
    student_map = get_users_by_ids(db, student_ids_in_submissions)

    # ── Filter Bar ───────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns([2, 2, 2])
    with col_f1:
        course_filter = st.selectbox(
            "Course", ["All Courses"] + [c["title"] for c in courses], key="sub_course_f"
        )
    with col_f2:
        status_filter = st.selectbox(
            "Grading Status", ["All Submissions", "Pending Grading", "Graded Only"], key="sub_status_f"
        )
    with col_f3:
        student_names = sorted({student_map[str(sid)]["name"] for sid in student_ids_in_submissions if str(sid) in student_map})
        student_filter = st.selectbox("Student", ["All Students"] + student_names, key="sub_student_f")

    filtered = submissions
    if course_filter != "All Courses":
        fid = next((c["_id"] for c in courses if c["title"] == course_filter), None)
        if fid:
            assign_ids_for_course = [a["_id"] for a in assignments if a.get("course_id") == fid]
            filtered = [s for s in filtered if s.get("assignment_id") in assign_ids_for_course]

    if status_filter == "Pending Grading":
        filtered = [s for s in filtered if s.get("status") != "graded"]
    elif status_filter == "Graded Only":
        filtered = [s for s in filtered if s.get("status") == "graded"]

    if student_filter != "All Students":
        target_id = next(
            (uid for uid, u in student_map.items() if u.get("name") == student_filter), None
        )
        if target_id:
            filtered = [s for s in filtered if str(s.get("student_id")) == target_id]

    if not filtered:
        empty_state("No submissions match the selected filters.")
    else:
        submissions_table(filtered, student_map, assign_map, course_map)

    # ── Grading Studio ───────────────────────────────────────────────────────
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:0.95rem;font-weight:700;color:#14243A;margin-bottom:0.6rem;'>Grading & Feedback Studio</p>", unsafe_allow_html=True)

    if not submissions:
        empty_state("No submissions logged for grading yet.")
    else:
        def _sub_label(s: dict) -> str:
            student = student_map.get(str(s.get("student_id")), {})
            assign = assign_map.get(str(s.get("assignment_id")), {})
            status = (s.get("status") or "submitted").upper()
            return f"{student.get('name', 'Student')} — {assign.get('title', 'Assignment')} [{status}]"

        all_sub_labels = {_sub_label(s): s["_id"] for s in submissions}
        sel_sub_label = st.selectbox("Select Submission to Grade", list(all_sub_labels.keys()), key="grade_sel")
        sel_sub_id = all_sub_labels[sel_sub_label]
        sel_sub = get_submission_by_id(db, sel_sub_id)

        if sel_sub:
            assign = assign_map.get(str(sel_sub.get("assignment_id")), {})
            student = student_map.get(str(sel_sub.get("student_id")), {})
            max_marks = assign.get("max_marks", 100)
            existing_marks = sel_sub.get("marks")
            existing_feedback = sel_sub.get("feedback", "")
            current_status = sel_sub.get("status", "submitted")

            col_info, col_form = st.columns([1, 1], gap="medium")

            with col_info:
                st.markdown(
                    f"""
                    <div class="cf-panel">
                      <p style="font-size:0.85rem;font-weight:700;color:#68758A;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">Submission Metadata</p>
                      <p style="font-size:1.05rem;font-weight:700;color:#14243A;margin-bottom:4px;">{student.get('name', 'Student')}</p>
                      <p style="font-size:0.84rem;color:#4569E8;font-weight:600;margin-bottom:8px;">{assign.get('title', 'Assignment')}</p>
                      <hr style="margin:8px 0;border-top:1px solid #EEF1F6;">
                      <p style="font-size:0.82rem;color:#68758A;margin:3px 0;">Current State: {status_badge(current_status)}</p>
                      <p style="font-size:0.82rem;color:#68758A;margin:3px 0;">Max Points Available: <b>{int(max_marks) if isinstance(max_marks, float) and max_marks.is_integer() else max_marks}</b></p>
                      <p style="font-size:0.82rem;color:#68758A;margin:3px 0;">Recorded Marks: <b>{existing_marks if existing_marks is not None else 'Ungraded'}</b></p>
                      {'<p style="font-size:0.8rem;color:#17263C;margin-top:6px;font-style:italic;background:#F8FAFC;padding:6px 8px;border-radius:4px;">Prior Feedback: "' + existing_feedback + '"</p>' if existing_feedback else ''}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col_form:
                with st.form("grade_form"):
                    st.markdown("<p style='font-size:0.9rem;font-weight:700;color:#14243A;margin-bottom:6px;'>Assign Score & Comments</p>", unsafe_allow_html=True)
                    marks_val = float(existing_marks) if existing_marks is not None else 0.0
                    new_marks = st.number_input(
                        f"Marks (Scale 0 – {int(max_marks) if isinstance(max_marks, float) and max_marks.is_integer() else max_marks}) *",
                        min_value=0.0,
                        max_value=float(max_marks),
                        value=marks_val,
                        step=0.5,
                    )
                    new_feedback = st.text_area("Teacher Feedback & Comments", value=existing_feedback or "", height=80, placeholder="Highlight strengths and areas for revision...")
                    save = st.form_submit_button("Save Grades & Feedback", type="primary")

                if save:
                    ok, msg = grade_submission(
                        db,
                        sel_sub_id,
                        teacher_id,
                        new_marks,
                        new_feedback,
                        course_ids,
                    )
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
        title="My Submissions",
        subtitle=f"History of logged submissions, instructor grading, and feedback · {user['name']}",
        eyebrow="ACADEMIC PROGRESS",
    )

    courses = get_courses_for_student(db, student_id)
    course_map = {str(c["_id"]): c for c in courses}
    course_ids = [c["_id"] for c in courses]
    assignments = get_assignments_for_courses(db, course_ids)
    assign_map = {str(a["_id"]): a for a in assignments}

    submissions = get_submissions_for_student(db, student_id)

    if not submissions:
        empty_state(
            "You have no logged submissions.",
            "Navigate to the Assignments page to review pending tasks and log completion.",
        )
    else:
        student_map = {str(student_id): user}

        col_sf1, col_sf2 = st.columns([2, 4])
        with col_sf1:
            status_filter = st.selectbox("Filter Status", ["All Submissions", "Submitted", "Graded"], key="s_sub_filter", label_visibility="collapsed")

        filtered = submissions
        if status_filter != "All Submissions":
            filtered = [s for s in filtered if (s.get("status") or "").lower() == status_filter.lower()]

        if not filtered:
            empty_state(f"No {status_filter.lower()} submissions found.")
        else:
            submissions_table(filtered, student_map, assign_map, course_map)

        # Graded Cards
        graded = [s for s in submissions if s.get("status") == "graded"]
        if graded:
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            st.markdown("<p style='font-size:0.95rem;font-weight:700;color:#14243A;margin-bottom:0.6rem;'>Detailed Instructor Reviews</p>", unsafe_allow_html=True)
            for s in graded:
                assign = assign_map.get(str(s.get("assignment_id")), {})
                c_title = course_map.get(str(assign.get("course_id")), {}).get("title", "Course")
                marks = s.get("marks")
                max_m = assign.get("max_marks", "—")
                marks_str = f"{int(marks) if isinstance(marks, float) and marks.is_integer() else marks}" if marks is not None else "—"
                fb_text = s.get("feedback", "").strip() or "No written remarks provided."

                st.markdown(
                    f"""
                    <div class="cf-panel">
                      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                        <span style="font-size:0.95rem;font-weight:700;color:#14243A;">{assign.get('title', 'Assignment')}</span>
                        <span class="badge badge-graded">{marks_str} / {max_m} Marks</span>
                      </div>
                      <p style="font-size:0.8rem;color:#4569E8;font-weight:600;margin:0 0 6px 0;">{c_title}</p>
                      <div style="background:#FAFBFD;border:1px solid #EEF1F6;border-radius:6px;padding:8px 12px;">
                        <span style="font-size:0.75rem;font-weight:600;color:#68758A;text-transform:uppercase;letter-spacing:0.06em;">Instructor Remarks:</span>
                        <p style="font-size:0.85rem;color:#17263C;margin:3px 0 0 0;font-style:italic;">"{fb_text}"</p>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

else:
    page_header("Submissions", eyebrow="ACCOUNTS")
    empty_state(f"Role '{user.get('role', 'unknown')}' does not have a submissions view.")
