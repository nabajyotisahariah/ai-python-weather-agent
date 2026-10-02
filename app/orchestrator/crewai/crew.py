# orchestrator/crewai/crew.py

import logging
from crewai import Crew, Process, Agent

from app.orchestrator.crewai.agents import create_weather_orchestrator
from app.orchestrator.crewai.tasks import create_weather_task

logger = logging.getLogger(__name__)

async def run_weather_orchestrator(query: str) -> Agent:

    logger.info("Executing run_weather_orchestrator with query: %s", query)
    agent = create_weather_orchestrator()

    task = create_weather_task(
        agent=agent,
        query=query,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    result = await crew.kickoff_async()

    return result.raw