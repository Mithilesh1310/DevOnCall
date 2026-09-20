import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_status_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "devoncall-api"
    assert "version" in data
    assert "database" in data
    assert "redis" in data
    assert "connected" in data["database"]
    assert "connected" in data["redis"]
