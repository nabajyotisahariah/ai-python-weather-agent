import asyncio
from app.orchestrator.crewai.crew import run_weather_orchestrator

async def main():
    res = await run_weather_orchestrator("What is the weather forecast of Delhi?")
    print("RESULT:", res)

asyncio.run(main())
