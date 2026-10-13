"""
pages/1_Courses.py — CampusFlow Courses Page.

Teachers can:
  - View all managed courses
  - Create new courses
  - Manage student enrollments (add/remove)

Students can:
  - View enrolled courses and course details
"""

import streamlit as st

st.set_page_config(
    page_title="CampusFlow — Courses",
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
)
from components.tables import courses_table
from components import feedback as fb
from database import get_db
from auth import init_auth, get_current_user, is_teacher, is_student
from services.courses import (
    get_courses_for_teacher,
    get_courses_for_student,
    get_course_by_id,
    get_all_students,
    create_course,
    add_students_to_course,
    remove_student_from_course,
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

# ── Build shared user map for name resolution ────────────────────────────────
all_user_docs = list(db.users.find({}, {"name": 1, "email": 1, "role": 1}))
user_map = {str(u["_id"]): u for u in all_user_docs}

# ═════════════════════════════════════════════════════════════════════════════
# TEACHER VIEW
# ═════════════════════════════════════════════════════════════════════════════
if is_teacher():
    teacher_id = user["_id"]
    page_header(
        title="Courses",
        subtitle=f"Manage syllabus offerings and student cohorts · {user['name']}",
        eyebrow="COURSE MANAGEMENT",
    )

    courses = get_courses_for_teacher(db, teacher_id)

    # ── Create Course Expander ───────────────────────────────────────────────
    with st.expander("＋ Create New Course", expanded=len(courses) == 0):
        with st.form("create_course_form", clear_on_submit=True):
            st.markdown("<p style='font-size:0.95rem;font-weight:700;color:#14243A;margin-bottom:0.5rem;'>Course Details</p>", unsafe_allow_html=True)
            col_t1, col_t2 = st.columns([1, 1])
            with col_t1:
                title = st.text_input("Course Title *", placeholder="e.g. Distributed Database Systems", max_chars=120)
            with col_t2:
                all_students = get_all_students(db)
                student_options = {s["name"]: s["_id"] for s in all_students}
                selected_names = st.multiselect(
                    "Initial Student Cohort (Optional)",
                    options=list(student_options.keys()),
                    help="Select existing student accounts to enroll immediately.",
                )

            description = st.text_area("Course Syllabus & Description *", placeholder="Enter key topics, prerequisites, and learning objectives...", height=80)
            submitted = st.form_submit_button("Create Course", type="primary")

        if submitted:
            selected_ids = [student_options[n] for n in selected_names]
            ok, msg = create_course(db, title, description, teacher_id, selected_ids)
            if ok:
                fb.success(msg)
                st.rerun()
            else:
                fb.error(msg)

    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

    # ── Course Directory ─────────────────────────────────────────────────────
    if not courses:
        empty_state(
            "You have no active courses.",
            "Use the 'Create New Course' form above to initialize your first class.",
        )
    else:
        col_s1, col_s2 = st.columns([3, 1])
        with col_s1:
            search = st.text_input("Search courses", placeholder="Filter courses by title...", key="course_search", label_visibility="collapsed")
        with col_s2:
            st.markdown(f"<p style='text-align:right;font-size:0.82rem;color:#68758A;padding-top:8px;'>Showing <b>{len(courses)}</b> course(s)</p>", unsafe_allow_html=True)

        filtered = [c for c in courses if search.lower() in c.get("title", "").lower()] if search else courses

        if not filtered:
            empty_state(f"No courses found matching '{search}'.")
        else:
            courses_table(filtered, user_map)

        # ── Manage Cohort Enrollment ─────────────────────────────────────────
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:0.95rem;font-weight:700;color:#14243A;margin-bottom:0.6rem;'>Cohort Enrollment Management</p>", unsafe_allow_html=True)

        course_labels = {c["title"]: c["_id"] for c in courses}
        selected_course_title = st.selectbox("Select course to manage roster", list(course_labels.keys()), key="manage_course_sel")
        selected_course_id = course_labels[selected_course_title]
        course_doc = get_course_by_id(db, selected_course_id)

        if course_doc:
            enrolled_ids = course_doc.get("student_ids", [])
            enrolled_users = [user_map.get(str(eid)) for eid in enrolled_ids if str(eid) in user_map]
            enrolled_users = [u for u in enrolled_users if u]

            col_roster, col_add = st.columns([1, 1], gap="medium")

            with col_roster:
                st.markdown(f"<p style='font-size:0.85rem;font-weight:600;color:#14243A;'>Current Students ({len(enrolled_users)})</p>", unsafe_allow_html=True)
                if enrolled_users:
                    for eu in enrolled_users:
                        col1, col2 = st.columns([4, 1])
                        col1.markdown(f"<p style='font-size:0.85rem;margin:4px 0;'><b>{eu['name']}</b> · <span style='color:#68758A;'>{eu.get('email', '—')}</span></p>", unsafe_allow_html=True)
                        if col2.button("Remove", key=f"rm_{eu['_id']}_{selected_course_id}"):
                            ok, msg = remove_student_from_course(db, selected_course_id, teacher_id, eu["_id"])
                            if ok:
                                fb.success(msg)
                                st.rerun()
                            else:
                                fb.error(msg)
                else:
                    st.caption("No students currently enrolled in this course.")

            with col_add:
                st.markdown("<p style='font-size:0.85rem;font-weight:600;color:#14243A;'>Enroll Additional Students</p>", unsafe_allow_html=True)
                unenrolled = [s for s in get_all_students(db) if s["_id"] not in enrolled_ids]
                if unenrolled:
                    with st.form("add_students_form"):
                        add_options = {f"{s['name']} ({s.get('email', '')})": s["_id"] for s in unenrolled}
                        to_add = st.multiselect("Select students", list(add_options.keys()))
                        add_submit = st.form_submit_button("Add Selected Students", type="primary")

                    if add_submit:
                        add_ids = [add_options[n] for n in to_add]
                        if not add_ids:
                            fb.warning("Please choose at least one student to enroll.")
                        else:
                            ok, msg = add_students_to_course(db, selected_course_id, teacher_id, add_ids)
                            if ok:
                                fb.success(msg)
                                st.rerun()
                            else:
                                fb.error(msg)
                else:
                    st.caption("All registered students are currently enrolled in this course.")

# ═════════════════════════════════════════════════════════════════════════════
# STUDENT VIEW
# ═════════════════════════════════════════════════════════════════════════════
elif is_student():
    student_id = user["_id"]
    page_header(
        title="My Courses",
        subtitle=f"Courses and academic cohorts you are registered in · {user['name']}",
        eyebrow="STUDENT ENROLLMENT",
    )

    courses = get_courses_for_student(db, student_id)

    if not courses:
        empty_state(
            "You are not enrolled in any active courses.",
            "Ask your course instructor to add you to their class roster.",
        )
    else:
        col_s1, col_s2 = st.columns([3, 1])
        with col_s1:
            search = st.text_input("Search courses", placeholder="Filter courses by title...", key="student_course_search", label_visibility="collapsed")
        with col_s2:
            st.markdown(f"<p style='text-align:right;font-size:0.82rem;color:#68758A;padding-top:8px;'>Enrolled in <b>{len(courses)}</b> course(s)</p>", unsafe_allow_html=True)

        filtered = [c for c in courses if search.lower() in c.get("title", "").lower()] if search else courses

        courses_table(filtered, user_map)

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:0.95rem;font-weight:700;color:#14243A;margin-bottom:0.6rem;'>Course Syllabus & Classmates</p>", unsafe_allow_html=True)

        course_labels = {c["title"]: c["_id"] for c in courses}
        sel_title = st.selectbox("Select course to inspect syllabus", list(course_labels.keys()), key="student_course_det")
        sel_doc = get_course_by_id(db, course_labels[sel_title])

        if sel_doc:
            teacher = user_map.get(str(sel_doc.get("teacher_id", "")), {})
            enrolled_ids = sel_doc.get("student_ids", [])
            enrolled_names = [
                user_map[str(eid)]["name"]
                for eid in enrolled_ids
                if str(eid) in user_map
            ]

            st.markdown(
                f"""
                <div class="cf-panel">
                  <p style="font-size:0.95rem;font-weight:700;color:#14243A;margin-bottom:6px;">{sel_doc.get('title')}</p>
                  <p style="font-size:0.84rem;color:#4569E8;font-weight:600;margin-bottom:8px;">Instructor: {teacher.get('name', 'Faculty Member')}</p>
                  <p style="font-size:0.86rem;color:#17263C;margin-bottom:12px;line-height:1.5;">{sel_doc.get('description', 'No syllabus summary provided.')}</p>
                  <hr style="margin:8px 0;border-top:1px solid #EEF1F6;">
                  <p style="font-size:0.8rem;color:#68758A;margin:0;"><b>Classmates ({len(enrolled_names)}):</b> {', '.join(enrolled_names) or 'None'}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

else:
    page_header("Courses", eyebrow="ACCOUNTS")
    empty_state(
        f"Role '{user.get('role', 'unknown')}' does not have an active course workspace.",
        "Please switch to a Teacher or Student identity in the sidebar.",
    )
