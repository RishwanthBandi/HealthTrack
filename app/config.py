"""Settings read from environment variables."""

import os

DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./healthtrack.db")
