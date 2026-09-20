import pytest
from app.services.redis import redis_service

@pytest.mark.asyncio
async def test_redis_service_connection_check():
    connected, details = await redis_service.check_connection()
    assert isinstance(connected, bool)
    assert isinstance(details, str)
    assert len(details) > 0
