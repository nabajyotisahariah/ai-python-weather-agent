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
from redis.asyncio import Redis


class ContextMemory:
    _instance: "ContextMemory | None" = None
    _initialized = False

    def __new__(cls, redis: Redis) -> "ContextMemory":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, redis: Redis):
        if self._initialized:
            return

        self.redis = redis
        self._initialized = True

    def _context_key(self, user_id: str, session_id: str) -> str:
        return f"weather:context:{user_id}:{session_id}"

    async def get_context(
        self,
        user_id: str,
        session_id: str,
    ) -> dict:
        data = await self.redis.get(
            self._context_key(user_id, session_id)
        )
        return json.loads(data) if data else {}

    async def update_context(
        self,
        user_id: str,
        session_id: str,
        updates: dict,
    ) -> dict:
        context = await self.get_context(user_id, session_id)
        context.update(updates)

        await self.redis.set(
            self._context_key(user_id, session_id),
            json.dumps(context),
            ex=86400,
        )
        return context

    async def add_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        key = f"weather:history:{user_id}:{session_id}"

        await self.redis.rpush(
            key,
            json.dumps({"role": role, "content": content}),
        )
        await self.redis.ltrim(key, -10, -1)
        await self.redis.expire(key, 86400)

    async def get_history(
        self,
        user_id: str,
        session_id: str,
    ) -> list[dict]:
        key = f"weather:history:{user_id}:{session_id}"
        messages = await self.redis.lrange(key, 0, -1)
        return [json.loads(message) for message in messages]