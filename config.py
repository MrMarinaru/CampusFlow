"""
config.py — CampusFlow application configuration.

Loads environment variables from .env and exposes typed constants.
Never hardcode credentials here.
"""

import os
from dotenv import load_dotenv

# Load .env from the project root
load_dotenv()

# ---------------------------------------------------------------------------
# MongoDB connection
# ---------------------------------------------------------------------------
MONGODB_URI: str = os.getenv("MONGODB_URI", "")
MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "classflow")

# Expected collections — used for startup validation
EXPECTED_COLLECTIONS = ["users", "courses", "assignments", "submissions"]

# Connection timeout in milliseconds
CONNECTION_TIMEOUT_MS: int = 8_000

# ---------------------------------------------------------------------------
# Application metadata
# ---------------------------------------------------------------------------
APP_NAME = "CampusFlow"
APP_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Role constants (from actual observed data)
# ---------------------------------------------------------------------------
ROLE_TEACHER = "teacher"
ROLE_STUDENT = "student"
