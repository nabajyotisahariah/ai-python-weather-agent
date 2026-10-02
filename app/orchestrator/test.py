import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))


from app.orchestrator.crewai.crew import run_weather_orchestrator
from app.utils.logger import setup_logging
from app.config import settings
import logging

setup_logging()
logging.info("Starting Weather Assistant API %s", settings)

async def main():
    setup_logging()

    #userQuery =  "What is the weather and 5 day forecast for Delhi?"
    #userQuery =  "What is the weather of Delhi?"
    #userQuery =  "What is the weather forecast for Delhi?"
    userQuery = "what is the weather of delhi & forecast for coming days"
    response = await run_weather_orchestrator(userQuery)
    print("=============Response===================")
    print(response)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())