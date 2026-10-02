# orchestrator/crewai/crew.py

import logging
from crewai import Crew, Process, Agent, Task
from app.orchestrator.crewai.agents import create_weather_orchestrator
from app.orchestrator.crewai.tasks import create_weather_task
from app.utils.redis_cache import AsyncRedisCache

logger = logging.getLogger(__name__)
redis_cache = AsyncRedisCache()

async def run_weather_orchestrator(query: str) -> str:
    cache_key = f"weather:orchestrator:{query.casefold().replace(' ', '_')}"
    cached_result = await redis_cache.get(cache_key)
    
    if cached_result and "raw" in cached_result:
        logger.info("Cache hit for orchestrator query: %s", query)
        return cached_result["raw"]

    logger.info("Executing run_weather_orchestrator with query: %s", query)
    agent: Agent = create_weather_orchestrator()

    task: Task = create_weather_task(
        agent=agent,
        query=query,
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

    return result.raw