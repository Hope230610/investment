"""
Smoke tests for the complete Learning Feedback E2E loop.

Scenarios:
1. POST learning-feedback → verify it writes to DB (check via SELECT)
2. GET learning-history → verify it returns what was just written
3. PATCH review → verify task status changes
4. Full loop: write feedback → read history → verify data round-trips

These tests use the real database and verify end-to-end correctness
of the entire feedback pipeline.

Run with: cd investment-back && pytest tests/test_learning_feedback_e2e.py -v
"""

import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tests._smoke_utils import enforce_test_db

enforce_test_db()

_back_root = Path(__file__).parent.parent
sys.path.insert(0, str(_back_root))
from main import app
from src.api.v1.user import create_access_token

# Use a known valid analysis_task_id from the test DB
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
    token = create_access_token({"sub": "1"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def db_engine():
    """Direct SQLAlchemy engine for verification queries."""
    from src.db.session import engine
    return engine


def ensure_review_task_for_analysis(db_engine, analysis_task_id: str = REAL_ANALYSIS_UUID) -> int:
    """Create or reset a review_task row so PATCH smoke tests assert real updates."""
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
            "PATCH smoke tests require a real analysis_task row in the test DB."
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
# Smoke 1: POST feedback writes emotion_history
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_feedback_writes_emotion_history_row(client, auth_headers, db_engine):
    """After POST, there should be at least one emotion_history row for user_id=1."""
    from sqlalchemy import text

    # Clear prior test data (upsert by date — idempotent per design)
    with db_engine.connect() as conn:
        conn.execute(
            text("DELETE FROM emotion_history WHERE user_id = 1 AND recorded_date = CURRENT_DATE")
        )
        conn.commit()

    payload = {
        "analysis_task_id": REAL_ANALYSIS_UUID,
        "tag_updates": [{"tag": "追涨倾向", "type": "add", "source": "test"}],
        "judgment_quality": "主要来自判断",
        "emotion_level": 4,
        "intent": "buy",
        "trigger_reason": "连续上涨",
    }
    resp = await client.post(
        "/api/v1/user/profile/learning-feedback",
        headers=auth_headers,
        json=payload,
    )
    assert resp.status_code == 200, f"POST failed: {resp.text}"

    # Verify: query the row that was just written
    with db_engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT emotion_level, intent FROM emotion_history "
                "WHERE user_id = 1 AND recorded_date = CURRENT_DATE LIMIT 1"
            )
        )
        row = result.fetchone()
        assert row is not None, "emotion_history row was not written"
        assert row[0] == 4
        assert row[1] == "buy"


# ---------------------------------------------------------------------------
# Smoke 2: GET learning-history returns written data
# Self-contained: writes its own row first, then reads it back.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_learning_history_returns_recent_emotion(client, auth_headers, db_engine):
    """GET should return emotion_history with a row we write in this same test."""
    from sqlalchemy import text

    # Write a row ourselves so this test is order-independent
    with db_engine.connect() as conn:
        conn.execute(
            text("DELETE FROM emotion_history WHERE user_id = 1 AND recorded_date = CURRENT_DATE")
        )
        conn.commit()

    payload = {
        "analysis_task_id": REAL_ANALYSIS_UUID,
        "tag_updates": [],
        "judgment_quality": "主要来自判断",
        "emotion_level": 2,
        "intent": "hold",
        "trigger_reason": "无明显信号",
    }
    post_resp = await client.post(
        "/api/v1/user/profile/learning-feedback",
        headers=auth_headers,
        json=payload,
    )
    assert post_resp.status_code == 200, f"Setup POST failed: {post_resp.text}"

    resp = await client.get(
        "/api/v1/user/profile/learning-history",
        headers=auth_headers,
        params={"days": 7},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body["emotion_history"], list)
    dates = [h["date"] for h in body["emotion_history"]]
    from datetime import date
    today = str(date.today())
    assert any(today in d for d in dates), f"No today's entry in: {dates}"


# ---------------------------------------------------------------------------
# Smoke 3: PATCH review marks task completed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_review_by_analysis_sets_completed(client, auth_headers, db_engine):
    """After PATCH with mark_completed=true, the review_task status should be COMPLETED."""
    from sqlalchemy import text

    review_task_id = ensure_review_task_for_analysis(db_engine)

    resp = await client.patch(
        f"/api/v1/reviews/by-analysis/{REAL_ANALYSIS_UUID}",
        headers=auth_headers,
        json={"review_result": {"action_taken": "continued"}, "mark_completed": True},
    )
    assert resp.status_code == 200, f"Unexpected: {resp.status_code} {resp.text}"
    body = resp.json()
    assert body.get("status") in ("COMPLETED", "completed")

    with db_engine.connect() as conn:
        status = conn.execute(
            text("SELECT status FROM review_tasks WHERE id = :review_task_id"),
            {"review_task_id": review_task_id},
        ).scalar_one()
        assert str(status).upper() == "COMPLETED"


# ---------------------------------------------------------------------------
# Smoke 4: Full round-trip — POST + GET + PATCH
# Uses REAL_ANALYSIS_UUID so the service can find a real analysis_task and
# the emotion_history upsert path works cleanly without FK noise.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_feedback_roundtrip(client, auth_headers, db_engine):
    """Complete loop: write feedback → read history → patch review."""
    from datetime import date

    today = str(date.today())
    ensure_review_task_for_analysis(db_engine)

    # Step 1: POST feedback with real UUID (not random — avoids FK noise)
    payload = {
        "analysis_task_id": REAL_ANALYSIS_UUID,
        "tag_updates": [{"tag": "恐慌卖出", "type": "add", "source": "e2e test"}],
        "judgment_quality": "部分判断 + 部分运气",
        "emotion_level": 5,
        "intent": "sell",
        "trigger_reason": "快速下跌",
    }
    post_resp = await client.post(
        "/api/v1/user/profile/learning-feedback",
        headers=auth_headers,
        json=payload,
    )
    # Accept 200 only — anything else means the service regressed
    assert post_resp.status_code == 200, (
        f"POST feedback regressed: {post_resp.status_code} {post_resp.text}"
    )

    # Step 2: GET history — should always return 200
    get_resp = await client.get(
        "/api/v1/user/profile/learning-history",
        headers=auth_headers,
        params={"days": 7},
    )
    assert get_resp.status_code == 200, get_resp.text
    body = get_resp.json()
    assert "emotion_history" in body
    assert "judgment_history" in body

    # Step 3: PATCH review — accepts 200 (updated) or 404 (no task for this UUID)
    patch_resp = await client.patch(
        f"/api/v1/reviews/by-analysis/{REAL_ANALYSIS_UUID}",
        headers=auth_headers,
        json={"review_result": {}, "mark_completed": True},
    )
    assert patch_resp.status_code == 200, (
        f"PATCH regressed: {patch_resp.status_code} {patch_resp.text}"
    )


# ---------------------------------------------------------------------------
# Smoke 5: Invalid UUID rejected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invalid_analysis_uuid_rejected(client, auth_headers):
    """Non-UUID analysis_task_id returns 400 from reviews.py manual parse."""
    resp = await client.patch(
        "/api/v1/reviews/by-analysis/not-a-valid-uuid",
        headers=auth_headers,
        json={"review_result": {}, "mark_completed": True},
    )
    assert resp.status_code == 400, f"Unexpected status {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_malformed_feedback_payload_rejected(client, auth_headers):
    """Missing required fields in feedback payload returns 4xx."""
    bad_payloads = [
        {},  # all fields missing
        {"tag_updates": [{"tag": "追涨倾向"}]},  # missing type + source
        # bad UUID — Pydantic rejects if UUID validation is wired upstream
        {"analysis_task_id": "not-a-uuid", "tag_updates": [], "judgment_quality": "主要来自判断"},
    ]
    for payload in bad_payloads:
        resp = await client.post(
            "/api/v1/user/profile/learning-feedback",
            headers=auth_headers,
            json=payload,
        )
        assert resp.status_code in (400, 422), f"Payload {payload} got {resp.status_code} not 4xx"
