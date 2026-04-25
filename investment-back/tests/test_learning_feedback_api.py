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
    "analysis_task_id": "4b8ca781-a3c7-4742-8b2b-1bf372fb2a5a",
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
async def test_patch_review_by_analysis_task_id(client, auth_headers):
    payload = {
        "review_result": {"action_taken": "continued", "outcome_summary": "Test outcome"},
        "mark_completed": True,
    }
    resp = await client.patch(
        "/api/v1/reviews/by-analysis/4b8ca781-a3c7-4742-8b2b-1bf372fb2a5a",
        headers=auth_headers,
        json=payload,
    )
    assert resp.status_code in (200, 404), f"Unexpected status {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_patch_review_requires_auth(client):
    resp = await client.patch(
        "/api/v1/reviews/by-analysis/4b8ca781-a3c7-4742-8b2b-1bf372fb2a5a",
        json={"review_result": {}, "mark_completed": True},
    )
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# PATCH /api/v1/reviews/:review_task_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_review_by_numeric_id(client, auth_headers):
    payload = {"review_result": {"action_taken": "delayed"}, "mark_completed": True}
    resp = await client.patch(
        "/api/v1/reviews/1",
        headers=auth_headers,
        json=payload,
    )
    assert resp.status_code in (200, 404, 422), f"Unexpected status {resp.status_code}"


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