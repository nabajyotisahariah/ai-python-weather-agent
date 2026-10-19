import json
from uuid import uuid4

from redis.asyncio import Redis

from app.cache.redis_cache import AsyncRedisCache
from app.schema.hitl import HITLStatus


class HITLService:
    def __init__(self, redis: Redis | None) -> None:
        self.redis = redis
        self.ttl_seconds = 900  # 15 minutes

    def _require_redis(self) -> Redis:
        if self.redis is None:
            raise RuntimeError("Redis must be enabled for Human-in-the-Loop requests")
        return self.redis

    def _key(self, request_id: str) -> str:
        return f"weather:hitl:{request_id}"

    async def create_pending_request(
        self,
        *,
        query: str,
        user_id: str,
        session_id: str,
        status: HITLStatus,
        message: str,
        question: str | None = None,
    ) -> dict:
        request_id = str(uuid4())
        redis = self._require_redis()

        pending = {
            "request_id": request_id,
            "query": query,
            "user_id": user_id,
            "session_id": session_id,
            "status": status.value,
            "message": message,
            "clarification_question": question,
        }

        await redis.set(
            self._key(request_id),
            json.dumps(pending),
            ex=self.ttl_seconds,
        )

        return pending

    async def get_pending_request(
        self,
        request_id: str,
    ) -> dict | None:
        value = await self._require_redis().get(
            self._key(request_id)
        )

        if not value:
            return None

        if isinstance(value, bytes):
            value = value.decode("utf-8")

        return json.loads(value)

    async def update_request(
        self,
        request_id: str,
        pending: dict,
    ) -> None:
        await self._require_redis().set(
            self._key(request_id),
            json.dumps(pending),
            ex=self.ttl_seconds,
        )


def get_hitl_service() -> HITLService:
    """Provide HITL storage using the application's shared Redis client."""
    return HITLService(AsyncRedisCache().redis)