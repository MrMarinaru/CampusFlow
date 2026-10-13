"""
database.py — CampusFlow MongoDB connection layer.

Creates a single cached PyMongo client using st.cache_resource so the
connection is reused across every Streamlit rerun.  Credentials are read
exclusively from environment variables.

Usage
-----
    from database import get_db, get_connection_status
    db = get_db()
    if db is not None:
        users = list(db.users.find({}))
"""

import logging
from typing import Optional

import streamlit as st
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import (
    ConfigurationError,
    ConnectionFailure,
    OperationFailure,
    ServerSelectionTimeoutError,
)

from config import (
    MONGODB_URI,
    MONGODB_DB_NAME,
    CONNECTION_TIMEOUT_MS,
    EXPECTED_COLLECTIONS,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connection status singleton (stored in session_state so the UI can show it)
# ---------------------------------------------------------------------------

def _init_conn_status() -> None:
    if "conn_status" not in st.session_state:
        st.session_state["conn_status"] = {
            "ok": False,
            "message": "Not connected",
        }


# ---------------------------------------------------------------------------
# Cached client — created once per Streamlit process
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def _get_client() -> Optional[MongoClient]:
    """
    Return a MongoClient or None on failure.
    Credentials are never logged or surfaced to the UI.
    """
    if not MONGODB_URI:
        logger.error("MONGODB_URI is not set.")
        return None

    try:
        client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=CONNECTION_TIMEOUT_MS,
            connectTimeoutMS=CONNECTION_TIMEOUT_MS,
            socketTimeoutMS=CONNECTION_TIMEOUT_MS,
        )
        # Verify connectivity
        client.admin.command("ping")
        return client
    except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
        logger.error("MongoDB connection failed: %s", type(exc).__name__)
        return None
    except ConfigurationError as exc:
        logger.error("MongoDB configuration error: %s", type(exc).__name__)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected MongoDB error: %s", type(exc).__name__)
        return None


def get_db() -> Optional[Database]:
    """
    Return the application database, or None when unavailable.
    Updates session_state['conn_status'] as a side-effect.
    """
    _init_conn_status()

    if not MONGODB_URI:
        st.session_state["conn_status"] = {
            "ok": False,
            "message": "MONGODB_URI not set — add it to your .env file.",
        }
        return None

    client = _get_client()
    if client is None:
        st.session_state["conn_status"] = {
            "ok": False,
            "message": (
                "Cannot reach MongoDB Atlas. "
                "Check your Atlas Network Access allow-list, "
                "database user credentials, and internet connection."
            ),
        }
        return None

    try:
        db = client[MONGODB_DB_NAME]

        # Soft check: warn if expected collections are missing
        existing = set(db.list_collection_names())
        missing = [c for c in EXPECTED_COLLECTIONS if c not in existing]
        if missing:
            logger.warning("Missing collections: %s", missing)
            st.session_state["conn_status"] = {
                "ok": True,
                "message": f"⚠ Connected — missing collections: {missing}",
            }
        else:
            st.session_state["conn_status"] = {
                "ok": True,
                "message": f"Connected to {MONGODB_DB_NAME}",
            }

        return db

    except OperationFailure as exc:
        logger.error("Database access denied: %s", type(exc).__name__)
        st.session_state["conn_status"] = {
            "ok": False,
            "message": (
                "Database access denied. "
                "Check that your Atlas database user has readWrite permissions."
            ),
        }
        return None
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error accessing database: %s", type(exc).__name__)
        st.session_state["conn_status"] = {
            "ok": False,
            "message": "Unexpected database error. See logs for details.",
        }
        return None


def get_connection_status() -> dict:
    """Return the last known connection status dict."""
    _init_conn_status()
    return st.session_state["conn_status"]
