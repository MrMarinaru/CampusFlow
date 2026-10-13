"""
auth.py — CampusFlow demo identity selector.

Renders a clearly labelled selectbox in the sidebar backed by real MongoDB
users.  This is NOT production authentication — it is a convenience for
demonstration only.

Usage
-----
    from auth import init_auth, get_current_user, is_teacher, is_student
    init_auth(db)
    user = get_current_user()
"""

from typing import Optional
import streamlit as st
from bson import ObjectId
from config import ROLE_TEACHER, ROLE_STUDENT
from components.layout import render_identity_panel


# ---------------------------------------------------------------------------
# Session-state keys
# ---------------------------------------------------------------------------
_KEY_USER_ID  = "demo_user_id"
_KEY_USER_DOC = "demo_user_doc"


def init_auth(db) -> None:
    """
    Render the demo identity selector in the sidebar.
    Must be called after render_sidebar_header().
    """
    if db is None:
        st.session_state[_KEY_USER_ID]  = None
        st.session_state[_KEY_USER_DOC] = None
        return

    # Fetch all users from the real collection
    users = list(db.users.find({}, {"name": 1, "email": 1, "role": 1}))

    if not users:
        st.sidebar.warning("No users found in the database.")
        st.session_state[_KEY_USER_ID]  = None
        st.session_state[_KEY_USER_DOC] = None
        return

    def _label(u: dict) -> str:
        role = u.get("role", "unknown").capitalize()
        return f"{u['name']} ({role})"

    labels   = [_label(u)      for u in users]
    user_ids = [str(u["_id"])  for u in users]

    # Restore previous selection index if still valid
    prev_id     = st.session_state.get(_KEY_USER_ID)
    default_idx = 0
    if prev_id and prev_id in user_ids:
        default_idx = user_ids.index(prev_id)

    # ── Small label above the selectbox ──────────────────────────────────────
    st.sidebar.markdown(
        "<p style='font-size:0.64rem;font-weight:700;letter-spacing:0.12em;"
        "color:#64748B;text-transform:uppercase;margin:0.5rem 0.55rem 4px 0.55rem;'>"
        "SELECT USER</p>",
        unsafe_allow_html=True,
    )

    selected_label = st.sidebar.selectbox(
        "Switch user",
        options=labels,
        index=default_idx,
        key="demo_identity_select",
        label_visibility="collapsed",
    )

    selected_idx  = labels.index(selected_label)
    selected_id   = user_ids[selected_idx]
    selected_user = users[selected_idx]

    # Persist into session state
    st.session_state[_KEY_USER_ID]  = selected_id
    st.session_state[_KEY_USER_DOC] = {
        "_id":   selected_user["_id"],   # keep as ObjectId
        "name":  selected_user["name"],
        "email": selected_user.get("email", ""),
        "role":  selected_user.get("role", "unknown"),
    }

    # Render the styled identity card panel directly below the selectbox
    render_identity_panel(st.session_state[_KEY_USER_DOC])


def get_current_user() -> Optional[dict]:
    """Return the current demo user document (with ObjectId _id), or None."""
    return st.session_state.get(_KEY_USER_DOC)


def get_current_user_id() -> Optional[ObjectId]:
    """Return the ObjectId of the current demo user, or None."""
    user = get_current_user()
    return user["_id"] if user else None


def is_teacher() -> bool:
    user = get_current_user()
    return user is not None and user.get("role") == ROLE_TEACHER


def is_student() -> bool:
    user = get_current_user()
    return user is not None and user.get("role") == ROLE_STUDENT
