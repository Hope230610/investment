from __future__ import annotations

import os
from pathlib import Path


if os.environ.get("PYTEST_ALLOW_PRODUCTION_CONFIG", "").strip().lower() not in {
    "1",
    "true",
    "yes",
    "on",
}:
    os.environ["DEBUG"] = "true"
    os.environ["ENVIRONMENT"] = "development"


def _run_data_modifying_tests() -> bool:
    return os.environ.get("RUN_DATA_MODIFYING_TESTS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


collect_ignore: list[str] = []

if not _run_data_modifying_tests():
    root = Path(__file__).parent
    collect_ignore.extend([
        str(root / "test_learning_feedback_api.py"),
        str(root / "test_learning_feedback_e2e.py"),
    ])
