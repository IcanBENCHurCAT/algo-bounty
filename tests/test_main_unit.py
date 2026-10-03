import pytest
from fastapi.testclient import TestClient
from gateway.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_health_check_endpoint_healthy():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["db"] == "ok"
    assert "version" in data

@pytest.mark.asyncio
async def test_health_check_endpoint_degraded(monkeypatch):
    # Mock gateway.main.async_engine.connect directly using a patch on the module
    import gateway.main

    class MockAsyncConnection:
        async def __aenter__(self):
            raise Exception("DB is down")

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    class MockEngine:
        def connect(self):
            return MockAsyncConnection()

    monkeypatch.setattr(gateway.main, "async_engine", MockEngine())

    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["db"] == "down"
    assert "version" in data
