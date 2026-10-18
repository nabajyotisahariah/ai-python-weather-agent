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
     #[{'role': 'user', 'content': {'session_id': 'abc6612', 'user_id': 'default_user', 'last_query': 'Shall I need umbrella tomorrow?', 'last_result': "Tomorrow's weather is forecasted to be cloudy with a maximum temperature of 16°C and a minimum of 2°C. There is no indication of rain, so you likely do not need to take an umbrella."}}, {'role': 'user', 'content': {'session_id': 'abc6612', 'user_id': 'default_user', 'last_query': 'What is the temp of Noida', 'last_result': 'The current temperature in Noida is 33°C, with a feels-like temperature of 30°C. The weather condition is a dust storm, humidity is at 20%, and the wind speed is 9 km/h.'}}, {'role': 'user', 'content': {'session_id': 'abc6612', 'user_id': 'default_user', 'last_query': 'I am from which City?', 'last_result': "I don't have information about your city. Could you please tell me which city you are from?"}}]

    cache_context_data : list[str] = [msg["content"]["last_result"] for msg in cached_context] if cached_context else []
    # Option 1: Join with newline
    cache_context_text: str = "\n".join(cache_context_data)

    #print(f"Cached context for session_id {session_id} and user_id {user_id}: {cached_context}")
    print(f"Cache context text for session_id {session_id} and user_id {user_id}: {cache_context_text}")

    agent: Agent = create_weather_orchestrator()

    task: Task = create_weather_task(
        agent=agent,
        query=query,
        cached_context=cache_context_text if cache_context_text else None,
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
    await redis_context.add_message(
                session_id, 
                user_id, 
                "user", 
                {
                    "session_id": session_id, "user_id": user_id, "last_query": query, 
                    "last_result": result.raw
                 }
            )   

    return [result.raw, cache_key, False]