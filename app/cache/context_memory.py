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
import secrets
from redis.asyncio import Redis
from redis.exceptions import RedisError
from app.config import settings


logger = logging.getLogger(__name__)

CLARIFICATION_TTL_SECONDS = 900
LOCATION_TTL_SECONDS = 86400


class HITLStateUnavailableError(RuntimeError):
    """Raised when Redis-backed HITL state cannot be read or persisted."""


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
        if self.redis is None:
            return

        key = f"weather:history:{session_id}:{user_id}"

        await self.redis.rpush(
            key,
            json.dumps({"role": role, "content": content}),
        )
        await self.redis.ltrim(key, -10, -1)
        await self.redis.expire(key, 86400)

    async def get_history(self, session_id: str, user_id: str) -> list[dict]:
        if self.redis is None:
            return []

        key = f"weather:history:{session_id}:{user_id}"
        messages = await self.redis.lrange(key, 0, -1)
        return [json.loads(message) for message in messages]

    async def get_resolved_city(self, session_id: str, user_id: str) -> str | None:
        if self.redis is None:
            return None

        try:
            return await self.redis.get(
                f"weather:location:{session_id}:{user_id}"
            )
        except RedisError as exc:
            raise HITLStateUnavailableError(
                "Unable to read the session's resolved location."
            ) from exc

    async def set_resolved_city(
        self,
        session_id: str,
        user_id: str,
        city: str,
    ) -> None:
        if self.redis is None:
            return

        try:
            await self.redis.setex(
                f"weather:location:{session_id}:{user_id}",
                LOCATION_TTL_SECONDS,
                city,
            )
        except RedisError as exc:
            raise HITLStateUnavailableError(
                "Unable to save the session's resolved location."
            ) from exc

    async def create_pending_clarification(
        self,
        query: str,
        session_id: str,
        user_id: str,
    ) -> str:
        if self.redis is None:
            raise HITLStateUnavailableError(
                "Redis is required to persist a pending clarification."
            )

        clarification_id = secrets.token_urlsafe(24)
        key = f"weather:clarification:{clarification_id}"
        payload = json.dumps(
            {
                "query": query,
                "session_id": session_id,
                "user_id": user_id,
            }
        )
        try:
            await self.redis.setex(key, CLARIFICATION_TTL_SECONDS, payload)
        except RedisError as exc:
            raise HITLStateUnavailableError(
                "Unable to save the pending clarification."
            ) from exc
        return clarification_id

    async def consume_pending_clarification(
        self,
        clarification_id: str,
        session_id: str,
        user_id: str,
    ) -> str | None:
        if self.redis is None:
            raise HITLStateUnavailableError(
                "Redis is required to retrieve a pending clarification."
            )

        key = f"weather:clarification:{clarification_id}"
        consume_script = """
        local payload = redis.call('GET', KEYS[1])
        if not payload then
            return nil
        end
        local state = cjson.decode(payload)
        if state['session_id'] ~= ARGV[1] or state['user_id'] ~= ARGV[2] then
            return nil
        end
        redis.call('DEL', KEYS[1])
        return payload
        """
        try:
            payload = await self.redis.eval(
                consume_script,
                1,
                key,
                session_id,
                user_id,
            )
        except (RedisError, json.JSONDecodeError, TypeError) as exc:
            raise HITLStateUnavailableError(
                "Unable to retrieve the pending clarification."
            ) from exc

        if payload is None:
            return None
        return json.loads(payload)["query"]