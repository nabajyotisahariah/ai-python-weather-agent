# orchestrator/crewai/crew.py

from crewai import Crew, Process

from app.orchestrator.crewai.agents import create_weather_orchestrator
from app.orchestrator.crewai.tasks import create_weather_task


async def run_weather_orchestrator(query: str):

    print("run_weather_orchestrator ",query)
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