"""
This stores the last ten messages and a separate context object. In production, validate the fields 
you allow into persistent context rather than letting arbitrary model output overwrite it.

For example:
{
  "preferred_city": "Delhi",
  "temperature_unit": "celsius",
  "last_intent": "forecast",
  "last_query": "Will it rain tomorrow?"
}
"""

import json
import logging
from redis.asyncio import Redis
from app.config import settings


logger = logging.getLogger(__name__)


class ContextMemory:
    _instance: "ContextMemory | None" = None
    _initialized = False

    def __new__(cls) -> "ContextMemory":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.redis: Redis | None = (
            Redis.from_url(settings.redis_url, decode_responses=True)
            if settings.redis_enabled
            else None
        )
        self._initialized = True

    async def add_message(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
    ) -> None:
        key = f"weather:history:{session_id}:{user_id}"

        await self.redis.rpush(
            key,
            json.dumps({"role": role, "content": content}),
        )
        await self.redis.ltrim(key, -10, -1)
        await self.redis.expire(key, 86400)

    async def get_history(
        self,
        session_id: str,
        user_id: str,
    ) -> list[dict]:
        key = f"weather:history:{session_id}:{user_id}"
        messages = await self.redis.lrange(key, 0, -1)
        return [json.loads(message) for message in messages]