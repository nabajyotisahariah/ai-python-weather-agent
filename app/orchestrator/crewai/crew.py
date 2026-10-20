# orchestrator/crewai/crew.py

import logging
import re
import json
import secrets
from datetime import datetime, timedelta, timezone
from urllib import response
from crewai import Crew, Process, Agent, Task
from app.orchestrator.crewai.agents import create_weather_orchestrator
from app.orchestrator.crewai.tasks import create_weather_task
from app.cache.redis_cache import AsyncRedisCache
from app.guardrails.input_guardrails import validate_query
from app.cache.context_memory import ContextMemory


class CrewAIOrchestrator:

    def __init__(self):
        self.ttl_seconds = 3600  # Set TTL to 1 hour
        self.redis = AsyncRedisCache()
        self.redis_context = ContextMemory()
        self.logger = logging.getLogger(__name__)

    async def run_weather_orchestrator(self, query: str, session_id: str | None = None, user_id: str | None = None) -> str:
        query = validate_query(query)

        query_str = query.casefold().replace(' ', '_')
        cache_key = f"weather:orchestrator:{query_str}:{session_id}:{user_id}"
        
        cached_result = await self.redis.get(cache_key)      
        
        if cached_result:
            self.logger.info("Cache hit for orchestrator query: %s", query)
            return [cached_result, cache_key, True]

        self.logger.info("Executing run_weather_orchestrator with query: %s", query)

        # Get cached context if available
        cached_context = await self.redis_context.get_history(session_id, user_id)

        # Log the cached context for debugging
        print(f"Cached context for session_id {session_id} and user_id {user_id}: {cached_context}")
        
        resolved_cities: list[str] = []
        agent: Agent = create_weather_orchestrator(resolved_cities.append)

        task: Task = create_weather_task(
            agent=agent,
            query=query,
            cached_context=cached_context if cached_context else None,
        )

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            cache=True,
            verbose=True,
        )

        result = await crew.kickoff_async()

        if resolved_cities and session_id is not None and user_id is not None:
            await self.redis_context.set_resolved_city(
                session_id,
                user_id,
                resolved_cities[-1],
            )

        # Cache the result
        await self.redis.set(cache_key,  result.raw, ex=3600)

        # Update the context with the latest query and result
        
        await self.redis_context.add_message(session_id,  user_id,  "user", query)  
        await self.redis_context.add_message(session_id,  user_id,  "assistant", result.raw)   

        return [result.raw, cache_key, False]
   
    async def run_weather_orchestrator_hitl(self, query: str, session_id: str | None = None, user_id: str | None = None) -> str:
        query = validate_query(query)

        query_str = query.casefold().replace(' ', '_')
        cache_key = f"weather:orchestrator:hitl:{query_str}:{session_id}:{user_id}"
        
        cached_result = await self.redis.get(cache_key)      
        
        if cached_result:
            self.logger.info("Cache hit for orchestrator query: %s", query)
            return [cached_result, cache_key, True]

        self.logger.info("Executing run_weather_orchestrator with query: %s", query)

        # Get cached context if available
        cached_context = await self.redis_context.get_history(session_id, user_id)

        # Log the cached context for debugging
        print(f"Cached context for session_id {session_id} and user_id {user_id}: {cached_context}")
        
        resolved_cities: list[str] = []
        agent: Agent = create_weather_orchestrator(resolved_cities.append)

        task: Task = create_weather_task(
            agent=agent,
            query=query,
            cached_context=cached_context if cached_context else None,
        )

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            cache=True,
            verbose=True,
        )

        result = await crew.kickoff_async()

        if resolved_cities and session_id is not None:
            await self.redis_context.set_resolved_city(
                session_id,
                user_id,
                resolved_cities[-1],
            )

        #response = str(result.raw or "")        
        # has_temperature = bool(
        #     re.search(r"-?\d+(?:\.\d+)?\s*°[CF]\b", response)
        # )

        # Determine whether the result contains a recognizable
        # weather-related response.
        #if has_temperature:# or has_weather_keyword:
         
        # Cache the result
        await self.redis.set(cache_key,  result.raw, ex=3600)

        # Update the context with the latest query and result
        await self.redis_context.add_message(session_id,  user_id,  "user", query)  
        await self.redis_context.add_message(session_id,  user_id,  "assistant", result.raw)   

        return [result.raw, cache_key, False]
   
    async def set_user_hitl(self, query: str, message: str, session_id: str | None = None, user_id: str | None = None) -> None:
        await self.redis_context.add_message(session_id,  user_id,  "user", query)  
        await self.redis_context.add_message(session_id,  user_id,  "assistant", message) 

    async def get_user_context(self, session_id: str | None = None, user_id: str | None = None) -> list[str]:
        return await self.redis_context.get_history(session_id, user_id)

    async def get_resolved_city(
        self,
        session_id: str,
        user_id: str,
    ) -> str | None:
        return await self.redis_context.get_resolved_city(session_id, user_id)


    async def create_pending(self, session_id: str, user_id: str, action: str, payload: dict,) -> dict:

        now = datetime.now(timezone.utc)

        approval_id = f"appr_{secrets.token_urlsafe(16)}"

        approval = {
            "approval_id": approval_id,
            "session_id": session_id,
            "requester_id": user_id,
            "action": action,
            "payload": payload,
            "status": "PENDING",
            "created_at": now.isoformat(),
            "expires_at": (
                now + timedelta(seconds=self.ttl_seconds)
            ).isoformat(),
            "idempotency_key": approval_id,
        }

        redis_key = f"weather:approval:{approval_id}"

        await self.redis.set(
            redis_key,
            json.dumps(approval),
            ex=self.ttl_seconds
        )

        return approval