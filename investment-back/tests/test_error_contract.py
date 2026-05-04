import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_validation_error_uses_unified_contract():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/user/login",
            headers={"x-request-id": "error-contract-1"},
            json={"username": "testuser"},
        )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "REQUEST_VALIDATION_ERROR"
    assert body["error"]["retryable"] is False
    assert body["error"]["request_id"] == "error-contract-1"
    assert "password" in body["error"]["message"]


@pytest.mark.asyncio
async def test_auth_error_uses_unified_contract():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/user/profile",
            headers={"x-request-id": "error-contract-2"},
        )

    assert response.status_code in (401, 403)
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == f"HTTP_{response.status_code}"
    assert body["error"]["request_id"] == "error-contract-2"
