"""
components/feedback.py — Consistent feedback / notification helpers.
"""

import streamlit as st


def success(message: str) -> None:
    st.success(message, icon="✅")


def error(message: str) -> None:
    st.error(message, icon="❌")


def warning(message: str) -> None:
    st.warning(message, icon="⚠️")


def info(message: str) -> None:
    st.info(message, icon="ℹ️")
