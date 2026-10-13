"""
components/layout.py — CampusFlow shared layout helpers and design system.

Central home for:
  - Global CSS (typography, sidebar, navigation, metrics, badges, tables, forms)
  - SVG logo / brand assets
  - Sidebar header renderer (st.logo, brand block, and connection status)
  - Identity panel renderer
  - Page header renderer
  - Metric row renderer
  - Status badge helper
  - Empty state renderer
  - DB-failure banner
"""

import os
from datetime import datetime, timezone
import streamlit as st
from database import get_connection_status


# ─────────────────────────────────────────────────────────────────────────────
# Datetime helper — safe for BSON naive UTC comparisons without deprecation warnings
# ─────────────────────────────────────────────────────────────────────────────

def get_utc_now() -> datetime:
    """Return timezone-naive UTC datetime for safe comparison with PyMongo BSON dates."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ─────────────────────────────────────────────────────────────────────────────
# CampusFlow Brand Assets (inline SVG fallback & sidebar brand block)
# ─────────────────────────────────────────────────────────────────────────────

_LOGO_SYMBOL_SIDEBAR = """
<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 28 28" fill="none" aria-label="CampusFlow">
  <rect x="7" y="2" width="18" height="22" rx="3.5" fill="#4569E8" opacity="0.45"/>
  <rect x="2" y="6" width="18" height="22" rx="3.5" fill="#FFFFFF"/>
  <rect x="6" y="11" width="10" height="2" rx="1" fill="#14243A" opacity="0.85"/>
  <rect x="6" y="16" width="6" height="2" rx="1" fill="#4569E8"/>
  <rect x="6" y="21" width="8" height="2" rx="1" fill="#14243A" opacity="0.55"/>
</svg>
"""

_SIDEBAR_BRAND_HTML = f"""
<div class="cf-sidebar-brand">
  <div class="cf-brand-mark">{_LOGO_SYMBOL_SIDEBAR.strip()}</div>
  <div class="cf-brand-text">
    <span class="cf-wordmark">CampusFlow</span>
    <span class="cf-tagline">LEARNING WORKSPACE</span>
  </div>
</div>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────────────────────────────────────

GLOBAL_CSS = """
<style>
/* ══════════════════════════════════════════════════════════════════
   BASE & TYPOGRAPHY
══════════════════════════════════════════════════════════════════ */
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
    font-size: 14.5px;
    -webkit-font-smoothing: antialiased;
}

/* ══════════════════════════════════════════════════════════════════
   CANVAS & LAYOUT
══════════════════════════════════════════════════════════════════ */
.main {
    background-color: #F6F5F0;
}
.main .block-container {
    padding: 1.5rem 2.2rem 3rem 2.2rem;
    max-width: 1040px;
    margin: 0 auto;
}

/* ══════════════════════════════════════════════════════════════════
   SIDEBAR — STYLES & HIERARCHY
══════════════════════════════════════════════════════════════════ */
section[data-testid="stSidebar"] {
    background-color: #14243A !important;
    min-width: 236px !important;
    max-width: 260px !important;
}

/* Default sidebar text color */
section[data-testid="stSidebar"] * {
    color: #CBD5E1;
}

/* ── Brand block ── */
.cf-sidebar-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 1rem 0.9rem 0.8rem 0.9rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    margin-bottom: 0.35rem;
}
.cf-brand-mark { flex-shrink: 0; line-height: 0; }
.cf-brand-text { display: flex; flex-direction: column; gap: 1px; }
.cf-wordmark {
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em;
    color: #FFFFFF !important;
    line-height: 1.2;
}
.cf-tagline {
    font-size: 0.62rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.12em;
    color: #64748B !important;
    text-transform: uppercase;
    line-height: 1;
}

/* ── Connection status indicator ── */
.cf-conn-row {
    padding: 0.3rem 0.9rem 0.6rem 0.9rem;
    font-size: 0.72rem;
    display: flex;
    align-items: center;
    gap: 6px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    margin-bottom: 0.5rem;
}
.cf-conn-dot-ok   { color: #10B981 !important; font-size: 0.75rem; }
.cf-conn-dot-fail { color: #EF4444 !important; font-size: 0.75rem; }
.cf-conn-text-ok   { color: #94A3B8 !important; font-size: 0.74rem; font-weight: 500; }
.cf-conn-text-fail { color: #FCA5A5 !important; font-size: 0.74rem; font-weight: 500; }

/* ── Sidebar Multipage Navigation ── */
[data-testid="stSidebarNav"] {
    padding-top: 0.25rem !important;
    padding-bottom: 0.5rem !important;
}
[data-testid="stSidebarNav"] ul {
    padding-left: 0.5rem !important;
    padding-right: 0.5rem !important;
}
[data-testid="stSidebarNav"] li {
    margin-bottom: 3px !important;
}
[data-testid="stSidebarNav"] a {
    padding: 0.45rem 0.75rem !important;
    border-radius: 6px !important;
    color: #94A3B8 !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    transition: all 0.15s ease !important;
    display: flex !important;
    align-items: center !important;
    text-decoration: none !important;
}
[data-testid="stSidebarNav"] a:hover {
    background-color: rgba(255, 255, 255, 0.07) !important;
    color: #FFFFFF !important;
}
/* Active link highlighting */
[data-testid="stSidebarNav"] a[aria-current="page"],
[data-testid="stSidebarNav"] li:has([aria-current="page"]) a {
    background-color: #4569E8 !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25) !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"] span,
[data-testid="stSidebarNav"] li:has([aria-current="page"]) a span {
    color: #FFFFFF !important;
    font-weight: 600 !important;
}
/* Transform default 'app' label to 'Overview' */
[data-testid="stSidebarNav"] li:first-child a span {
    font-size: 0 !important;
    display: none !important;
}
[data-testid="stSidebarNav"] li:first-child a::before {
    content: "Overview" !important;
    font-size: 0.88rem !important;
    font-weight: inherit !important;
    color: inherit !important;
}

/* ── Identity Panel in Sidebar ── */
.cf-identity-panel {
    margin: 0.6rem 0.55rem 0.65rem 0.55rem;
    padding: 0.85rem 0.9rem 0.75rem 0.9rem;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
}
.cf-identity-label {
    font-size: 0.62rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.12em;
    color: #64748B !important;
    text-transform: uppercase;
    display: block;
    margin-bottom: 4px;
}
.cf-identity-name {
    font-size: 0.92rem !important;
    font-weight: 600 !important;
    color: #FFFFFF !important;
    margin-bottom: 2px;
}
.cf-identity-role-badge {
    display: inline-block;
    padding: 1px 7px;
    border-radius: 3px;
    font-size: 0.68rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    background-color: rgba(69, 105, 232, 0.25) !important;
    color: #93C5FD !important;
    border: 1px solid rgba(69, 105, 232, 0.4);
    margin-top: 3px;
    margin-bottom: 6px;
}
.cf-identity-notice {
    font-size: 0.68rem !important;
    color: #64748B !important;
    line-height: 1.35;
    margin-top: 5px;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
    padding-top: 5px;
}

/* ── Form Selectbox inside sidebar (Fixed Contrast) ── */
section[data-testid="stSidebar"] [data-testid="stSelectbox"] {
    margin: 0 0.55rem 0.5rem 0.55rem !important;
}
section[data-testid="stSidebar"] [data-testid="stSelectbox"] > div {
    background-color: #1A2E4A !important;
    border: 1px solid rgba(255, 255, 255, 0.18) !important;
    border-radius: 6px !important;
}
section[data-testid="stSidebar"] [data-testid="stSelectbox"] > div:hover {
    border-color: #4569E8 !important;
}
section[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] {
    background-color: #1A2E4A !important;
    border-radius: 6px !important;
}
section[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] * {
    color: #FFFFFF !important;
    background-color: transparent !important;
    font-size: 0.86rem !important;
    font-weight: 500 !important;
}
section[data-testid="stSidebar"] [data-testid="stSelectbox"] svg {
    fill: #94A3B8 !important;
}

/* Dropdown popover list items */
[data-baseweb="popover"] [role="listbox"],
[data-baseweb="popover"] ul {
    background-color: #14243A !important;
    border: 1px solid #2A4365 !important;
    border-radius: 6px !important;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4) !important;
    padding: 4px !important;
}
[data-baseweb="popover"] [role="option"],
[data-baseweb="popover"] li {
    background-color: transparent !important;
    color: #E2E8F0 !important;
    font-size: 0.85rem !important;
    padding: 8px 12px !important;
    border-radius: 4px !important;
    cursor: pointer !important;
}
[data-baseweb="popover"] [role="option"]:hover,
[data-baseweb="popover"] [role="option"][aria-selected="true"],
[data-baseweb="popover"] li:hover {
    background-color: #4569E8 !important;
    color: #FFFFFF !important;
}

/* ══════════════════════════════════════════════════════════════════
   PAGE HEADER
══════════════════════════════════════════════════════════════════ */
.cf-page-header {
    margin-bottom: 1.4rem;
    padding-bottom: 0.8rem;
    border-bottom: 1px solid #DFE4EC;
}
.cf-page-eyebrow {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #4569E8;
    margin: 0 0 3px 0;
}
.cf-page-title {
    font-size: 1.55rem;
    font-weight: 700;
    color: #14243A;
    margin: 0;
    letter-spacing: -0.02em;
    line-height: 1.2;
}
.cf-page-subtitle {
    font-size: 0.86rem;
    color: #68758A;
    margin: 4px 0 0 0;
}

/* ══════════════════════════════════════════════════════════════════
   METRIC CARDS (Top of Dashboard & Pages)
══════════════════════════════════════════════════════════════════ */
.cf-metric {
    background: #FFFFFF;
    border: 1px solid #DFE4EC;
    border-radius: 8px;
    padding: 1rem 1.1rem;
    border-top: 3px solid #4569E8;
    box-shadow: 0 1px 2px rgba(20, 36, 58, 0.03);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.cf-metric-value {
    font-size: 2rem;
    font-weight: 700;
    color: #14243A;
    line-height: 1;
    letter-spacing: -0.03em;
}
.cf-metric-label {
    font-size: 0.7rem;
    font-weight: 600;
    color: #68758A;
    margin-top: 6px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

/* ══════════════════════════════════════════════════════════════════
   DASHBOARD PANELS & LIST ROWS
══════════════════════════════════════════════════════════════════ */
.cf-panel {
    background: #FFFFFF;
    border: 1px solid #DFE4EC;
    border-radius: 8px;
    padding: 1.1rem 1.25rem;
    box-shadow: 0 1px 3px rgba(20, 36, 58, 0.03);
    margin-bottom: 1rem;
}
.cf-panel-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: #14243A;
    margin: 0 0 0.8rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #EEF1F6;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.cf-row-item {
    padding: 0.65rem 0;
    border-bottom: 1px solid #F1F4F8;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
}
.cf-row-item:last-child {
    border-bottom: none;
    padding-bottom: 0.2rem;
}
.cf-row-primary {
    font-size: 0.9rem;
    font-weight: 600;
    color: #17263C;
    margin: 0 0 2px 0;
}
.cf-row-meta {
    font-size: 0.78rem;
    color: #68758A;
    margin: 0;
}

/* ══════════════════════════════════════════════════════════════════
   STATUS BADGES
══════════════════════════════════════════════════════════════════ */
.badge {
    display: inline-block;
    padding: 2.5px 8px;
    border-radius: 4px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.badge-graded    { background: #D1FAE5; color: #065F46; border: 1px solid #A7F3D0; }
.badge-submitted { background: #DBEAFE; color: #1E40AF; border: 1px solid #BFDBFE; }
.badge-pending   { background: #FEF3C7; color: #92400E; border: 1px solid #FDE68A; }
.badge-upcoming  { background: #E0E7FF; color: #3730A3; border: 1px solid #C7D2FE; }
.badge-past      { background: #F1F5F9; color: #475569; border: 1px solid #CBD5E1; }
.badge-unknown   { background: #F1F5F9; color: #64748B; border: 1px solid #CBD5E1; }

/* ══════════════════════════════════════════════════════════════════
   TABLES
══════════════════════════════════════════════════════════════════ */
.stDataFrame {
    border: 1px solid #DFE4EC !important;
    border-radius: 8px !important;
    background: #FFFFFF !important;
}

/* ══════════════════════════════════════════════════════════════════
   FORMS & CONTROLS
══════════════════════════════════════════════════════════════════ */
.stForm {
    background: #FFFFFF !important;
    border: 1px solid #DFE4EC !important;
    border-radius: 8px !important;
    padding: 1.25rem !important;
    box-shadow: 0 1px 3px rgba(20, 36, 58, 0.02) !important;
}
.stTextInput input,
.stTextArea textarea,
.stNumberInput input,
.stDateInput input,
.stTimeInput input {
    border: 1px solid #DFE4EC !important;
    border-radius: 6px !important;
    font-size: 0.88rem !important;
    color: #17263C !important;
    background: #FFFFFF !important;
}
.stTextInput input:focus,
.stTextArea textarea:focus,
.stNumberInput input:focus {
    border-color: #4569E8 !important;
    box-shadow: 0 0 0 2px rgba(69, 105, 232, 0.15) !important;
}

/* ══════════════════════════════════════════════════════════════════
   BUTTONS
══════════════════════════════════════════════════════════════════ */
.stButton > button {
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    padding: 0.4rem 1.1rem !important;
    border: 1px solid #DFE4EC !important;
    color: #17263C !important;
    background: #FFFFFF !important;
    transition: all 0.15s ease !important;
}
.stButton > button:hover {
    border-color: #4569E8 !important;
    color: #4569E8 !important;
    background: #F0F4FF !important;
}
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
    background: #4569E8 !important;
    color: #FFFFFF !important;
    border-color: #4569E8 !important;
    box-shadow: 0 1px 3px rgba(69, 105, 232, 0.25) !important;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="baseButton-primary"]:hover {
    background: #3457D5 !important;
    border-color: #3457D5 !important;
    color: #FFFFFF !important;
}

/* ══════════════════════════════════════════════════════════════════
   EXPANDERS & TABS
══════════════════════════════════════════════════════════════════ */
.stExpander {
    border: 1px solid #DFE4EC !important;
    border-radius: 8px !important;
    background: #FFFFFF !important;
    margin-bottom: 1rem !important;
}
.stExpander header {
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    color: #17263C !important;
}
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 2px solid #DFE4EC !important;
}
.stTabs [data-baseweb="tab"] {
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    color: #68758A !important;
    padding: 0.45rem 1rem !important;
    border-bottom: 2px solid transparent !important;
    margin-bottom: -2px !important;
}
.stTabs [aria-selected="true"] {
    color: #4569E8 !important;
    border-bottom-color: #4569E8 !important;
}

/* ══════════════════════════════════════════════════════════════════
   DIVIDERS & EMPTY STATES
══════════════════════════════════════════════════════════════════ */
hr {
    border: none !important;
    border-top: 1px solid #DFE4EC !important;
    margin: 1.1rem 0 !important;
}
.cf-empty {
    text-align: center;
    color: #68758A;
    padding: 2.2rem 1.2rem;
    background: #FAFBFD;
    border: 1.5px dashed #DFE4EC;
    border-radius: 8px;
    font-size: 0.88rem;
    line-height: 1.6;
}

/* Footer and toolbar clutter */
footer { visibility: hidden; }
#MainMenu { visibility: hidden; }
[data-testid="stAppDeployButton"] { display: none !important; }
.stDeployButton { display: none !important; }

/* Ensure header container allows the sidebar expand control to be clicked */
header[data-testid="stHeader"] {
    background-color: transparent !important;
    z-index: 99 !important;
}

/* Sidebar collapse button (inside sidebar) */
[data-testid="stSidebarCollapseButton"] button {
    color: #94A3B8 !important;
}
[data-testid="stSidebarCollapseButton"] button:hover {
    color: #FFFFFF !important;
}
[data-testid="stSidebarCollapseButton"] svg {
    fill: #94A3B8 !important;
}
[data-testid="stSidebarCollapseButton"]:hover svg {
    fill: #FFFFFF !important;
}

/* When sidebar is collapsed, the expand button in top-left */
[data-testid="stExpandSidebarButton"] {
    display: inline-flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    background-color: #FFFFFF !important;
    border: 1px solid #DFE4EC !important;
    border-radius: 6px !important;
    box-shadow: 0 1px 3px rgba(20, 36, 58, 0.08) !important;
    transition: all 0.15s ease !important;
    margin: 8px 0 0 10px !important;
}
[data-testid="stExpandSidebarButton"]:hover {
    background-color: #F0F4FF !important;
    border-color: #4569E8 !important;
}
[data-testid="stExpandSidebarButton"] button {
    color: #14243A !important;
}
[data-testid="stExpandSidebarButton"] svg {
    fill: #14243A !important;
}
[data-testid="stExpandSidebarButton"]:hover svg {
    fill: #4569E8 !important;
}
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Public Component Functions
# ─────────────────────────────────────────────────────────────────────────────

def inject_css() -> None:
    """Inject global CampusFlow styles. Call once per page."""
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def render_sidebar_header() -> None:
    """
    Render CampusFlow logo at top of sidebar and connection status indicator.
    Call this on every page before init_auth().
    """
    # Use st.logo if svg asset is present
    logo_path = "assets/logo.svg"
    icon_path = "assets/favicon.svg"
    if os.path.exists(logo_path) and hasattr(st, "logo"):
        try:
            st.logo(logo_path, icon_image=icon_path if os.path.exists(icon_path) else None)
        except Exception:
            pass

    # Render branded sidebar header
    st.sidebar.markdown(_SIDEBAR_BRAND_HTML, unsafe_allow_html=True)

    # Render connection status dot
    status = get_connection_status()
    if status["ok"]:
        dot_cls, txt_cls = "cf-conn-dot-ok", "cf-conn-text-ok"
    else:
        dot_cls, txt_cls = "cf-conn-dot-fail", "cf-conn-text-fail"

    st.sidebar.markdown(
        f"""
        <div class="cf-conn-row">
          <span class="{dot_cls}">●</span>
          <span class="{txt_cls}">{status['message']}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_identity_panel(user: dict | None) -> None:
    """
    Render the styled identity panel below the selectbox in the sidebar.
    Shows the currently selected user's name, role, and the demo disclaimer.
    """
    if user is None:
        return
    role_display = user.get("role", "unknown").capitalize()
    name = user.get("name", "—")
    st.sidebar.markdown(
        f"""
        <div class="cf-identity-panel">
          <span class="cf-identity-label">DEMO IDENTITY</span>
          <div class="cf-identity-name">{name}</div>
          <span class="cf-identity-role-badge">{role_display}</span>
          <div class="cf-identity-notice">
            Demonstration mode only. Not secure public authentication.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_header(
    title: str,
    subtitle: str = "",
    eyebrow: str = "",
) -> None:
    """
    Render a compact, typographically crisp page header.

    Parameters
    ----------
    title    : The main page heading.
    subtitle : Optional secondary description line.
    eyebrow  : Small uppercase context badge (e.g. 'TEACHER WORKSPACE').
    """
    eyebrow_html = (
        f"<p class='cf-page-eyebrow'>{eyebrow}</p>" if eyebrow else ""
    )
    sub_html = (
        f"<p class='cf-page-subtitle'>{subtitle}</p>" if subtitle else ""
    )
    st.markdown(
        f"""
        <div class="cf-page-header">
          {eyebrow_html}
          <p class="cf-page-title">{title}</p>
          {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_row(metrics: list[tuple[str, str | int]]) -> None:
    """
    Render a compact row of styled metric cards.

    Parameters
    ----------
    metrics : list of (label, value) tuples.
    """
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.markdown(
                f"""
                <div class="cf-metric">
                  <div class="cf-metric-value">{value}</div>
                  <div class="cf-metric-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def status_badge(status: str) -> str:
    """Return an HTML badge string for a submission status value."""
    _map = {
        "graded":    "badge-graded",
        "submitted": "badge-submitted",
        "pending":   "badge-pending",
        "upcoming":  "badge-upcoming",
        "past":      "badge-past",
    }
    cls = _map.get((status or "").lower(), "badge-unknown")
    return f"<span class='badge {cls}'>{status or 'unknown'}</span>"


def empty_state(message: str, action: str = "") -> None:
    """Render a styled empty-state block."""
    action_html = f"<br><small style='color:#68758A;'>{action}</small>" if action else ""
    st.markdown(
        f"<div class='cf-empty'>{message}{action_html}</div>",
        unsafe_allow_html=True,
    )


def no_db_banner() -> None:
    """Show an actionable error banner when MongoDB connection is unavailable."""
    st.error(
        "**Database unavailable.** "
        "Check that your `.env` file contains a valid `MONGODB_URI` and "
        "that your Atlas Network Access allow-list includes your current IP address.",
        icon="🔌",
    )
