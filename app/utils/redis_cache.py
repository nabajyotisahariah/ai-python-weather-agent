import json
import logging
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import settings

logger = logging.getLogger(__name__)


class AsyncRedisCache:
    def __init__(self, redis_client: Redis | None = None) -> None:
        self.redis = redis_client or Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )

    async def get(self, key: str) -> dict[str, Any] | None:
        try:
            cached_value = await self.redis.get(key)
            if cached_value:
                return json.loads(cached_value)
        except (RedisError, json.JSONDecodeError, TypeError) as exc:
            logger.warning("Redis cache read failed for key %s: %s", key, exc)

        return None

    async def set(self, key: str, value: dict[str, Any], ex: int | None = None) -> None:
        try:
            await self.redis.setex(
                key,
                ex or settings.REDIS_CACHE_TTL_SECONDS,
                json.dumps(value),
            )
        except RedisError as exc:
            logger.warning("Redis cache write failed for key %s: %s", key, exc)