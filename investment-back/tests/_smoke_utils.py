"""
Shared test infrastructure used by all smoke / E2E test suites.

Keeps the DB guard logic in one place so it can be imported before the app
module is loaded (which would otherwise pull in the default .env DATABASE_URL
and make the guard too late to help).
"""

from __future__ import annotations

import os
from pathlib import Path

# Path to the investment-back root — derived once at import time
_BACK_ROOT = Path(__file__).parent.parent


def db_name_from_env_or_file() -> str:
    """Return the database name from the shell env var or from .env on disk."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        env_path = _BACK_ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("DATABASE_URL="):
                    url = line.split("=", 1)[1].strip()
                    break
    return url.split("/")[-1].split("?")[0].strip() if url else ""


KNOWN_TEST_DBS = frozenset(("test", "investment_test", "test_investment"))


def enforce_test_db():
    """
    Raise RuntimeError if the configured database is not a recognised test DB.

    Smoke tests that write / update rows must call this before any module-level
    import that could load the real database session.
    """
    db = db_name_from_env_or_file()
    if db and db.lower() not in KNOWN_TEST_DBS:
        raise RuntimeError(
            f"[TEST GUARD] Refusing to run data-modifying tests against DB '{db}'. "
            "Rename the DB to contain 'test' or set DATABASE_URL to a dedicated "
            "test database. These tests DELETE and UPDATE rows and will corrupt "
            "production data."
        )
