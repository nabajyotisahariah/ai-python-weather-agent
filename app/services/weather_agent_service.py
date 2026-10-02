import os
import asyncio
from dataclasses import dataclass
from urllib.parse import quote

import httpx
from redis.asyncio import Redis
#from dotenv import load_dotenv

from app.services.interface.weather_agent_interface import WeatherAgentInterface
from app.orchestrator.crewai.crew import run_weather_orchestrator
from app.config import settings
import logging

from app.schema.weather import AgentResponse

logger = logging.getLogger(__name__)

class WeatherAgentService(WeatherAgentInterface):


    base_url: str = settings.weather_api_url
    timeout_seconds: float = settings.weather_timeout_seconds

    async def get_weather_agent_crewai(self, query: str, days: int = 3) -> AgentResponse:
        """Return current weather & forecast data for a city."""
        #userQuery = f"What is the weather forecast for {city} for {days} days?"
        print("get_weather_agent_crewai ",query)
        response = await run_weather_orchestrator(query)
        
        return AgentResponse(
            status="success",
            message=str(response),
            data=None,
            isCached=False
        )