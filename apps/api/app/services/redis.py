import redis.asyncio as redis
from app.config import settings

class RedisService:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._client: redis.Redis | None = None

    def get_client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(self.redis_url, decode_responses=True)
        return self._client

    async def check_connection(self) -> tuple[bool, str]:
        try:
            client = self.get_client()
            pong = await client.ping()
            if pong:
                return True, "Redis connection active (PONG received)"
            return False, "Redis returned unexpected response"
        except Exception as e:
            return False, f"Redis connection failed: {str(e)}"

    async def close(self):
        if self._client:
            await self._client.close()
            self._client = None

redis_service = RedisService(settings.REDIS_URL)
