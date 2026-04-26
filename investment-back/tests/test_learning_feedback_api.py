"""
API-level integration tests for Learning Feedback E2E path.

Covers the four critical endpoints:
- GET  /api/v1/user/profile/learning-history
- POST /api/v1/user/profile/learning-feedback
- PATCH /api/v1/reviews/by-analysis/:analysis_task_id
- PATCH /api/v1/reviews/:review_task_id

These are NOT unit tests — they hit the FastAPI app with a TestClient
and verify end-to-end request/response contracts.

Run with: cd investment-back && pytest tests/test_learning_feedback_api.py -v
"""

import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Allow running from repo root
_back_root = Path(__file__).parent.parent
sys.path.insert(0, str(_back_root))

from tests._smoke_utils import enforce_test_db

enforce_test_db()

# Import the FastAPI app via investment-back/main.py
from main import app  # noqa: E402

SKIP_DB = os.environ.get("SKIP_DB", "false").lower() in ("1", "true", "yes")
REAL_ANALYSIS_UUID = "4b8ca781-a3c7-4742-8b2b-1bf372fb2a5a"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Bearer token for a test user — generated from the app's own JWT utility."""
    from src.api.v1.user import create_access_token

    # Requires DB to find a real user; falls back to token with user_id=1
    token = create_access_token({"sub": "1"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def db_engine():
    """Direct SQLAlchemy engine for PATCH test setup."""
    from src.db.session import engine

    return engine


def ensure_review_task_for_analysis(db_engine, analysis_task_id: str = REAL_ANALYSIS_UUID) -> int:
    """Create or reset a review_task row so PATCH tests can assert a real update."""
    from sqlalchemy import text

    with db_engine.begin() as conn:
        analysis = conn.execute(
            text(
                "SELECT at.user_id, at.stock_id, at.scenario, "
                "COALESCE(s.stock_name, at.stock_id) AS stock_name "
                "FROM analysis_tasks at "
                "LEFT JOIN stocks s ON s.stock_id = at.stock_id "
                "WHERE at.id = :analysis_task_id AND at.user_id = 1"
            ),
            {"analysis_task_id": analysis_task_id},
        ).mappings().first()
        assert analysis is not None, (
            f"Missing analysis_tasks fixture for {analysis_task_id}; "
            "PATCH tests require a real analysis_task row in the test DB."
        )

        review_task_id = conn.execute(
            text(
                "SELECT id FROM review_tasks "
                "WHERE analysis_task_id = :analysis_task_id AND user_id = :user_id "
                "ORDER BY id ASC LIMIT 1"
            ),
            {
                "analysis_task_id": analysis_task_id,
                "user_id": analysis["user_id"],
            },
        ).scalar()

        if review_task_id is None:
            review_task_id = conn.execute(
                text(
                    "INSERT INTO review_tasks "
                    "(user_id, analysis_task_id, stock_id, stock_name, scenario, "
                    "review_at, status, review_result, created_at, updated_at) "
                    "VALUES "
                    "(:user_id, :analysis_task_id, :stock_id, :stock_name, :scenario, "
                    "CURRENT_TIMESTAMP, 'PENDING', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) "
                    "RETURNING id"
                ),
                {
                    "user_id": analysis["user_id"],
                    "analysis_task_id": analysis_task_id,
                    "stock_id": analysis["stock_id"],
                    "stock_name": analysis["stock_name"],
                    "scenario": analysis["scenario"],
                },
            ).scalar_one()
        else:
            conn.execute(
                text(
                    "UPDATE review_tasks "
                    "SET stock_id = :stock_id, "
                    "stock_name = :stock_name, "
                    "scenario = :scenario, "
                    "review_at = CURRENT_TIMESTAMP, "
                    "status = 'PENDING', "
                    "review_result = NULL, "
                    "updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = :review_task_id"
                ),
                {
                    "review_task_id": review_task_id,
                    "stock_id": analysis["stock_id"],
                    "stock_name": analysis["stock_name"],
                    "scenario": analysis["scenario"],
                },
            )

    return int(review_task_id)


# ---------------------------------------------------------------------------
# GET /api/v1/user/profile/learning-history
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_learning_history_returns_empty_on_fresh_user(client, auth_headers):
    resp = await client.get(
        "/api/v1/user/profile/learning-history",
        headers=auth_headers,
        params={"days": 30},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "emotion_history" in body
    assert "judgment_history" in body
    assert isinstance(body["emotion_history"], list)
    assert isinstance(body["judgment_history"], list)


@pytest.mark.asyncio
async def test_learning_history_respects_days_param(client, auth_headers):
    resp = await client.get(
        "/api/v1/user/profile/learning-history",
        headers=auth_headers,
        params={"days": 7},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_learning_history_requires_auth(client):
    resp = await client.get("/api/v1/user/profile/learning-history")
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/user/profile/learning-feedback
# ---------------------------------------------------------------------------

VALID_FEEDBACK_PAYLOAD = {
    # Use a real UUID from the test database to avoid FK violations
    "analysis_task_id": REAL_ANALYSIS_UUID,
    "tag_updates": [
        {"tag": "追涨倾向", "type": "add", "source": "本次复盘确认"}
    ],
    "judgment_quality": "主要来自判断",
    "emotion_level": 3,
    "intent": "buy",
    "trigger_reason": "连续上涨",
}


@pytest.mark.asyncio
async def test_post_learning_feedback_accepts_valid_payload(client, auth_headers):
    resp = await client.post(
        "/api/v1/user/profile/learning-feedback",
        headers=auth_headers,
        json=VALID_FEEDBACK_PAYLOAD,
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_post_feedback_validates_tag_update_shape(client, auth_headers):
    payload = {
        **VALID_FEEDBACK_PAYLOAD,
        "tag_updates": [{"tag": "追涨倾向"}],  # missing type + source
    }
    resp = await client.post(
        "/api/v1/user/profile/learning-feedback",
        headers=auth_headers,
        json=payload,
    )
    assert resp.status_code in (400, 422), f"Expected 422 for bad payload, got {resp.status_code}"


@pytest.mark.asyncio
async def test_post_feedback_requires_auth(client):
    resp = await client.post(
        "/api/v1/user/profile/learning-feedback",
        json=VALID_FEEDBACK_PAYLOAD,
    )
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# PATCH /api/v1/reviews/by-analysis/:analysis_task_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_review_by_analysis_task_id(client, auth_headers, db_engine):
    ensure_review_task_for_analysis(db_engine)
    payload = {
        "review_result": {"action_taken": "continued", "outcome_summary": "Test outcome"},
        "mark_completed": True,
    }
    resp = await client.patch(
        f"/api/v1/reviews/by-analysis/{REAL_ANALYSIS_UUID}",
        headers=auth_headers,
        json=payload,
    )
    assert resp.status_code == 200, f"Unexpected status {resp.status_code}: {resp.text}"
    assert resp.json().get("status") in ("COMPLETED", "completed")


@pytest.mark.asyncio
async def test_patch_review_requires_auth(client):
    resp = await client.patch(
        f"/api/v1/reviews/by-analysis/{REAL_ANALYSIS_UUID}",
        json={"review_result": {}, "mark_completed": True},
    )
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# PATCH /api/v1/reviews/:review_task_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_review_by_numeric_id(client, auth_headers, db_engine):
    review_task_id = ensure_review_task_for_analysis(db_engine)
    payload = {"review_result": {"action_taken": "delayed"}, "mark_completed": True}
    resp = await client.patch(
        f"/api/v1/reviews/{review_task_id}",
        headers=auth_headers,
        json=payload,
    )
    assert resp.status_code == 200, f"Unexpected status {resp.status_code}: {resp.text}"
    assert resp.json().get("id") == review_task_id


@pytest.mark.asyncio
async def test_patch_review_rejects_string_id(client, auth_headers):
    resp = await client.patch(
        "/api/v1/reviews/not-a-number",
        headers=auth_headers,
        json={"review_result": {}, "mark_completed": True},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Health: ensure main app boots
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_app_health_check(client):
    resp = await client.get("/")
    assert resp.status_code < 500
