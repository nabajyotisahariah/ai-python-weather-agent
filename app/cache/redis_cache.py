import json
import logging
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import settings

logger = logging.getLogger(__name__)


class AsyncRedisCache:
    _instance: "AsyncRedisCache | None" = None
    _initialized = False

    def __new__(cls) -> "AsyncRedisCache":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            print("AsyncRedisCache instance already initialized. Skipping re-initialization.")
            return

        print("AsyncRedisCache Initializing instance.")
        self.redis: Redis | None = (
            Redis.from_url(settings.redis_url, decode_responses=True)
            if settings.redis_enabled
            else None
        )
        self._initialized = True

    async def get(self, key: str) -> dict[str, Any] | None:
        if self.redis is None:
            return None

        try:
            cached_value = await self.redis.get(key)
            if cached_value:
                return json.loads(cached_value)
        except (RedisError, json.JSONDecodeError, TypeError) as exc:
            logger.warning("Redis cache read failed for key %s: %s", key, exc)

        return None

    async def set(self, key: str, value: dict[str, Any], ex: int | None = None) -> None:
        if self.redis is None:
            return

        try:
            await self.redis.setex(
                key,
                ex or settings.redis_cache_ttl_seconds,
                json.dumps(value),
            )
        except RedisError as exc:
            logger.warning("Redis cache write failed for key %s: %s", key, exc)