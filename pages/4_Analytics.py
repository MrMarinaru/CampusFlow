"""
pages/4_Analytics.py — CampusFlow Analytics Page.

Visualizes performance distributions, completion rates, and average marks
calculated directly from MongoDB aggregation pipelines.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(
    page_title="CampusFlow — Analytics",
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
)
from database import get_db
from auth import init_auth, get_current_user, is_teacher, is_student
from services.courses import get_courses_for_teacher, get_courses_for_student
from services.assignments import get_assignments_for_courses
from services.submissions import get_submissions_for_student
from services.analytics import (
    submission_status_distribution,
    avg_marks_by_assignment,
    submission_counts_by_assignment,
    graded_marks_distribution,
    pending_grading_count,
    course_summary,
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

# Plotly theme styling helper
def apply_chart_theme(fig, height=270):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif", color="#17263C", size=12),
        margin=dict(l=15, r=15, t=25, b=15),
        height=height,
    )
    return fig

# ═════════════════════════════════════════════════════════════════════════════
# TEACHER ANALYTICS
# ═════════════════════════════════════════════════════════════════════════════
if is_teacher():
    teacher_id = user["_id"]
    page_header(
        title="Analytics",
        subtitle=f"Aggregated coursework metrics, submission distributions, and performance averages · {user['name']}",
        eyebrow="ACADEMIC METRICS",
    )

    courses = get_courses_for_teacher(db, teacher_id)
    if not courses:
        empty_state("No courses available.", "Create a course to begin tracking analytics.")
        st.stop()

    course_map = {str(c["_id"]): c for c in courses}
    course_ids = [c["_id"] for c in courses]
    assignments = get_assignments_for_courses(db, course_ids)
    assign_map = {str(a["_id"]): a for a in assignments}
    assign_ids = [a["_id"] for a in assignments]

    if not assignments:
        empty_state("No assignments created.", "Publish assignments to start collecting analytics telemetry.")
        st.stop()

    # Scope Filter
    col_sc1, col_sc2 = st.columns([2, 4])
    with col_sc1:
        course_filter = st.selectbox(
            "Filter Analytics Scope",
            ["All Managed Courses"] + [c["title"] for c in courses],
            key="analytics_course_filter",
        )

    if course_filter != "All Managed Courses":
        fc = next(c for c in courses if c["title"] == course_filter)
        scoped_assignments = [a for a in assignments if a["course_id"] == fc["_id"]]
        scoped_assign_ids = [a["_id"] for a in scoped_assignments]
        scoped_assign_map = {str(a["_id"]): a for a in scoped_assignments}
    else:
        scoped_assign_ids = assign_ids
        scoped_assign_map = assign_map

    # Core Metrics
    status_dist = submission_status_distribution(db, scoped_assign_ids)
    total_subs = sum(status_dist.values())
    pending = pending_grading_count(db, scoped_assign_ids)
    graded_count = status_dist.get("graded", 0)

    marks_data = graded_marks_distribution(db, scoped_assign_ids)
    avg_mark = round(sum(marks_data) / len(marks_data), 1) if marks_data else None
    avg_str = f"{avg_mark} pts" if avg_mark is not None else "—"

    metric_row(
        [
            ("Total Submissions", total_subs),
            ("Graded Submissions", graded_count),
            ("Awaiting Evaluation", pending),
            ("Cohort Mean Score", avg_str),
        ]
    )

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # Row 1: Charts
    col1, col2 = st.columns(2, gap="medium")

    with col1:
        st.markdown(
            """
            <div class="cf-panel">
              <p class="cf-panel-title"><span>Submission Status Breakdown</span></p>
            """,
            unsafe_allow_html=True,
        )
        if status_dist:
            fig_pie = px.pie(
                names=[k.title() for k in status_dist.keys()],
                values=list(status_dist.values()),
                color=[k.lower() for k in status_dist.keys()],
                color_discrete_map={
                    "graded": "#10B981",
                    "submitted": "#4569E8",
                    "pending": "#F59E0B",
                },
                hole=0.48,
            )
            apply_chart_theme(fig_pie, height=250)
            fig_pie.update_layout(legend=dict(orientation="h", y=-0.15, x=0.15))
            st.plotly_chart(fig_pie, width="stretch")
        else:
            empty_state("No submissions recorded in this scope.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown(
            """
            <div class="cf-panel">
              <p class="cf-panel-title"><span>Score Distribution (Graded Work)</span></p>
            """,
            unsafe_allow_html=True,
        )
        if marks_data:
            fig_hist = px.histogram(
                x=marks_data,
                nbins=8,
                labels={"x": "Marks Awarded", "y": "Submissions Count"},
                color_discrete_sequence=["#4569E8"],
            )
            apply_chart_theme(fig_hist, height=250)
            fig_hist.update_layout(
                xaxis=dict(title="Awarded Score", gridcolor="#EEF1F6"),
                yaxis=dict(title="Submission Count", gridcolor="#EEF1F6"),
                bargap=0.12,
            )
            st.plotly_chart(fig_hist, width="stretch")
        else:
            empty_state("No graded submissions available for score histogram.")
        st.markdown("</div>", unsafe_allow_html=True)

    # Row 2: Performance by Assignment
    st.markdown(
        """
        <div class="cf-panel">
          <p class="cf-panel-title"><span>Mean Score per Assignment</span></p>
        """,
        unsafe_allow_html=True,
    )
    avg_data = avg_marks_by_assignment(db, scoped_assign_ids)
    if avg_data:
        rows = []
        for d in avg_data:
            a = scoped_assign_map.get(str(d["_id"]), {})
            rows.append(
                {
                    "Assignment": a.get("title", str(d["_id"]))[:38],
                    "Mean Score": round(d["avg_marks"], 1),
                    "Evaluated Count": d["count"],
                    "Max Possible": a.get("max_marks", "—"),
                }
            )
        df_avg = pd.DataFrame(rows).sort_values("Mean Score", ascending=True)
        fig_bar = px.bar(
            df_avg,
            x="Mean Score",
            y="Assignment",
            orientation="h",
            text="Mean Score",
            color_discrete_sequence=["#14243A"],
            hover_data={"Evaluated Count": True, "Max Possible": True},
        )
        apply_chart_theme(fig_bar, height=max(180, len(rows) * 44))
        fig_bar.update_layout(
            xaxis=dict(title="Mean Score", gridcolor="#EEF1F6"),
            yaxis=dict(title="", tickfont=dict(size=12, color="#17263C")),
        )
        fig_bar.update_traces(textposition="outside", cliponaxis=False)
        st.plotly_chart(fig_bar, width="stretch")
    else:
        empty_state("No graded assignments to compute averages.")
    st.markdown("</div>", unsafe_allow_html=True)

    # Row 3: Course Summary Table
    st.markdown(
        """
        <div class="cf-panel">
          <p class="cf-panel-title"><span>Comprehensive Course Summary</span></p>
        """,
        unsafe_allow_html=True,
    )
    summaries = course_summary(db, course_ids)
    if summaries:
        rows_s = []
        for s in summaries:
            c = course_map.get(str(s["course_id"]), {})
            rows_s.append(
                {
                    "Course Name": c.get("title", "—"),
                    "Total Logged Submissions": s["total_submissions"],
                    "Graded Submissions": s["graded"],
                    "Average Cohort Marks": f"{s['avg_marks']} pts" if s["avg_marks"] is not None else "—",
                }
            )
        df_s = pd.DataFrame(rows_s)
        st.dataframe(df_s, hide_index=True, width="stretch")
    else:
        empty_state("No course telemetry to summarize.")
    st.markdown("</div>", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# STUDENT ANALYTICS
# ═════════════════════════════════════════════════════════════════════════════
elif is_student():
    student_id = user["_id"]
    page_header(
        title="My Performance",
        subtitle=f"Personal grade trajectory and score distributions · {user['name']}",
        eyebrow="ACADEMIC PROGRESS",
    )

    courses = get_courses_for_student(db, student_id)
    course_ids = [c["_id"] for c in courses]
    assignments = get_assignments_for_courses(db, course_ids)
    assign_map = {str(a["_id"]): a for a in assignments}
    submissions = get_submissions_for_student(db, student_id)
    graded = [s for s in submissions if s.get("status") == "graded" and s.get("marks") is not None]

    metric_row(
        [
            ("Enrolled Courses", len(courses)),
            ("Course Assignments", len(assignments)),
            ("Tasks Submitted", len(submissions)),
            ("Completed & Graded", len(graded)),
        ]
    )

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    if not graded:
        empty_state(
            "No graded coursework logged yet.",
            "Once your instructors review and grade your submissions, performance charts will render here.",
        )
    else:
        st.markdown(
            """
            <div class="cf-panel">
              <p class="cf-panel-title"><span>Marks by Assignment</span></p>
            """,
            unsafe_allow_html=True,
        )
        rows = []
        for s in graded:
            a = assign_map.get(str(s.get("assignment_id")), {})
            marks = s.get("marks")
            max_m = a.get("max_marks", 1)
            pct = round((marks / max_m) * 100, 1) if max_m and marks is not None else 0
            rows.append(
                {
                    "Assignment": a.get("title", "—")[:38],
                    "Awarded Marks": marks,
                    "Max Marks": max_m,
                    "Percentage": pct,
                }
            )
        df = pd.DataFrame(rows)
        fig = px.bar(
            df,
            x="Awarded Marks",
            y="Assignment",
            orientation="h",
            text="Percentage",
            color="Percentage",
            color_continuous_scale=["#EF4444", "#F59E0B", "#10B981"],
            range_color=[0, 100],
            hover_data={"Max Marks": True, "Awarded Marks": True},
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside", cliponaxis=False)
        apply_chart_theme(fig, height=max(200, len(rows) * 45))
        fig.update_layout(
            xaxis=dict(title="Awarded Score", gridcolor="#EEF1F6"),
            yaxis=dict(title="", tickfont=dict(size=12, color="#17263C")),
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig, width="stretch")
        st.markdown("</div>", unsafe_allow_html=True)

else:
    page_header("Analytics", eyebrow="ACCOUNTS")
    empty_state(f"Role '{user.get('role', 'unknown')}' does not have an analytics view.")
