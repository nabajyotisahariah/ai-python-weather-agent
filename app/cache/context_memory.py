"""
This stores the last ten messages and a separate context object. In production, validate the fields 
you allow into persistent context rather than letting arbitrary model output overwrite it.

For example:
{"role": "user", "content": "I am from the city Noida?"}
{"role": "assistant", "content": "The current weather in Noida is 33C with a feels-like temperature of 30\u00b0C. The humidity level is 20%. The weather condition is a dust storm, and the wind speed is 9 km/h."}
{"role": "user", "content": "Will it raid today?"}
{"role": "assistant", "content": "The weather forecast for Noida today indicates a dust storm with a maximum temperature of 33\u00b0C and a minimum temperature of 25\u00b0C. There is no indication of rain today."}
{"role": "user", "content": "I am moved to Delhi"
{"role": "assistant", "content": "Since you have moved to Delhi, here is the weather forecast for Delhi for the next three days:\n\n- October 18, 2026: Maximum temperature 33\u00b0C, minimum temperature 25\u00b0C, sunny.\n- October 19, 2026: Maximum temperature 34\u00b0C, minimum temperature 25\u00b0C, sunny.\n- October 20, 2026: Maximum temperature 34\u00b0C, minimum temperature 26\u00b0C, sunny.\n\nIf you need any specific weather information or assistance for Delhi, feel free to ask!"}
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

    async def add_message(self, session_id: str, user_id: str, role: str, content: str) -> None:
        key = f"weather:context:{session_id}:{user_id}"

        await self.redis.rpush(
            key,
            json.dumps({"role": role, "content": content}),
        )
        await self.redis.ltrim(key, -10, -1)
        await self.redis.expire(key, 86400)

    async def get_history(self, session_id: str, user_id: str) -> list[dict]:
        key = f"weather:context:{session_id}:{user_id}"
        messages = await self.redis.lrange(key, 0, -1)
        return [json.loads(message) for message in messages]

    async def set_resolved_city(
        self,
        session_id: str,
        user_id: str,
        city: str,
    ) -> None:
        if self.redis is None:
            return

        key = f"weather:location:{session_id}:{user_id}"
        await self.redis.hset(key, "resolved_city", city)
        await self.redis.expire(key, 86400)

    async def get_resolved_city(
        self,
        session_id: str,
        user_id: str,
    ) -> str | None:
        if self.redis is None:
            return None

        key = f"weather:location:{session_id}:{user_id}"
        return await self.redis.hget(key, "resolved_city")