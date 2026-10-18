# orchestrator/crewai/crew.py

import logging
from crewai import Crew, Process, Agent, Task
from app.orchestrator.crewai.agents import create_weather_orchestrator
from app.orchestrator.crewai.tasks import create_weather_task
from app.cache.redis_cache import AsyncRedisCache
from app.guardrails.input_guardrails import validate_query
from app.cache.context_memory import ContextMemory

logger = logging.getLogger(__name__)
redis_cache = AsyncRedisCache()
redis_context = ContextMemory()

async def run_weather_orchestrator(query: str, session_id: str | None = None, user_id: str | None = None) -> str:
    
    query = validate_query(query)

    query_str = query.casefold().replace(' ', '_')
    cache_key = f"weather:orchestrator:{query_str}:{session_id}:{user_id}"
    
    #"weather:context:{user_id}:{session_id}"
    cached_result = await redis_cache.get(cache_key)      
    
    if cached_result and "raw" in cached_result:
        logger.info("Cache hit for orchestrator query: %s", query)
        return [cached_result["raw"], cache_key, True]

    logger.info("Executing run_weather_orchestrator with query: %s", query)

    # Get cached context if available
    cached_context = await redis_context.get_history(session_id, user_id)
    print(f"Cached context for session_id {session_id} and user_id {user_id}: {cached_context}")

    agent: Agent = create_weather_orchestrator()

    task: Task = create_weather_task(
        agent=agent,
        query=query,
        cached_context=cached_context or [],
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        cache=True,
        verbose=True,
    )

    result = await crew.kickoff_async()

    # Cache the result
    await redis_cache.set(cache_key, {"raw": result.raw}, ex=3600)

    # Update the context with the latest query and result
    await redis_context.add_message(session_id, user_id, "user", {"last_query": query, "last_result": result.raw})   

    return [result.raw, cache_key, False]