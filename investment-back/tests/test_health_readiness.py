import pytest
from httpx import ASGITransport, AsyncClient

import main
from main import app


@pytest.mark.asyncio
async def test_health_exposes_worker_mode():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["dependencies"]["worker_mode"] in {"rq", "in_process_background_tasks"}
    assert body["dependencies"]["redis"] in {"required", "not_required"}


@pytest.mark.asyncio
async def test_ready_checks_redis_when_rq_worker_mode(monkeypatch):
    monkeypatch.setattr(main.settings, "RQ_ASYNC", False)
    monkeypatch.setattr(main, "_check_redis_connection", lambda: None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"] == "healthy"
    assert body["checks"]["redis"] == "healthy"
    assert body["checks"]["worker_mode"] == "rq"


@pytest.mark.asyncio
async def test_ready_reports_degraded_when_required_redis_unreachable(monkeypatch):
    monkeypatch.setattr(main.settings, "RQ_ASYNC", False)
    monkeypatch.setattr(main, "_check_redis_connection", lambda: "connection refused")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["reason"] == "redis unreachable"
    assert body["checks"]["database"] == "healthy"
    assert body["checks"]["redis"] == "unhealthy"
