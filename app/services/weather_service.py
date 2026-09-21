import os
import asyncio
from dataclasses import dataclass
from urllib.parse import quote

import httpx
from redis.asyncio import Redis
#from dotenv import load_dotenv

from app.agents.crewai import build_weather_crew
from app.agents.langgraph import run_weather_agent as run_langgraph_weather_agent
from app.agents.autogen import run_weather_agent as run_autogen_weather_agent
from app.agents.google_adk import run_weather_agent as run_google_adk_weather_agent
from app.services.interface.weather_service_interface import WeatherServiceInterface
from app.config import settings
from app.schema.weather import AgentResponse
from app.utils.redis_cache import AsyncRedisCache
import logging

logger = logging.getLogger(__name__)

#load_dotenv()


class WeatherServiceError(Exception):
    """Base error for weather provider failures."""


class CityNotFoundError(WeatherServiceError):
    """The weather provider could not find the requested city."""


class WeatherProviderError(WeatherServiceError):
    """The weather provider could not return a valid response."""


class WeatherService(WeatherServiceInterface):
    base_url: str = settings.WEATHER_API_URL
    timeout_seconds: float = settings.WEATHER_TIMEOUT_SECONDS

    def __init__(self, redis_client: Redis | None = None) -> None:
        self.cache = AsyncRedisCache(redis_client)

    @staticmethod
    def _cache_key(city: str) -> str:
        return f"weather:current:{city.casefold()}"

    @staticmethod
    def _report_cache_key(provider: str, city: str) -> str:
        return f"weather:report:{provider}:{city.casefold()}"

    async def _get_cached_report(self, provider: str, city: str) -> AgentResponse | None:
        cached_report = await self.cache.get(self._report_cache_key(provider, city))
        if cached_report and "status" in cached_report and "message" in cached_report:
            return {
                "status": str(cached_report["status"]),
                "message": str(cached_report["message"]),
            }
        return None

    async def _cache_report(self, provider: str, city: str, report: AgentResponse) -> None:
        await self.cache.set(self._report_cache_key(provider, city), report)

    #def __post_init__(self) -> None:
    #    object.__setattr__(self, "weather_crew", build_weather_crew())

    

    async def get_current_weather(self, city: str) -> dict[str, str | int | float]:
        city = city.strip()
        if not city:
            raise CityNotFoundError("City name is required")

        cache_key = self._cache_key(city)
        cached_weather = await self.cache.get(cache_key)
        if cached_weather:
            return cached_weather

        url = f"{self.base_url.rstrip('/')}/{quote(city, safe='')}"
        params = {"format": "j1"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url, params=params, timeout=self.timeout_seconds)
        except httpx.HTTPError as exc:
            raise WeatherProviderError("Weather service unavailable") from exc

        if response.status_code == 404:
            raise CityNotFoundError("City not found")
        if response.status_code != 200:
            raise WeatherProviderError("Weather service returned an error")

        try:
            payload = response.json()
            current = payload["current_condition"][0]
            weather = {
                "city": city,
                "temperature": current["temp_C"],
                "feels_like": current["FeelsLikeC"],
                "humidity": current["humidity"],
                "description": current["weatherDesc"][0]["value"],
                "wind_speed": current["windspeedKmph"],
            }
        except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
            raise WeatherProviderError("Weather service returned invalid data") from exc

        await self.cache.set(cache_key, weather)

        return weather

    async def get_crewai_weather_report(self, city: str) -> AgentResponse:
        """Run the CrewAI weather agent without blocking the API event loop."""
        city = city.strip()
        cached_report = await self._get_cached_report("crewai", city)
        if cached_report:
            return cached_report

        try:
            logger.info("Building CrewAI weather crew for city: %s", city)
            weather_crew = build_weather_crew(city)
            result = await asyncio.to_thread(
                weather_crew.kickoff,
                inputs={"city": city},
            )
        except Exception as exc:
            raise WeatherProviderError("Weather assistant unavailable") from exc

        logger.info("LLM weather report for city: %s", city)
        report = {"status": "ok", "message": str(result)}
        await self._cache_report("crewai", city, report)
        return report

    async def get_langgraph_weather_report(self, city: str) -> AgentResponse:
        """Run the LangGraph weather agent without blocking the API event loop."""
        city = city.strip()
        cached_report = await self._get_cached_report("langgraph", city)
        if cached_report:
            return cached_report

        try:
            logger.info("Running LangGraph weather agent for city: %s", city)
            result = await asyncio.to_thread(run_langgraph_weather_agent, city)
        except Exception as exc:
            raise WeatherProviderError("Weather assistant unavailable") from exc

        logger.info("LangGraph weather report generated for city: %s", city)
        report = {"status": "ok", "message": result}
        await self._cache_report("langgraph", city, report)
        return report

    async def get_autogen_weather_report(self, city: str) -> AgentResponse:
        """Run the AutoGen weather agent without blocking the API event loop."""
        city = city.strip()
        cached_report = await self._get_cached_report("autogen", city)
        if cached_report:
            return cached_report

        try:
            logger.info("Running AutoGen weather agent for city: %s", city)
            result = await asyncio.to_thread(run_autogen_weather_agent, city)
        except Exception as exc:
            raise WeatherProviderError("Weather assistant unavailable") from exc

        logger.info("AutoGen weather report generated for city: %s", city)
        report = {"status": "ok", "message": result}
        await self._cache_report("autogen", city, report)
        return report

    async def get_google_adk_weather_report(self, city: str) -> AgentResponse:
        """Run the Google ADK weather agent without blocking the API event loop."""
        city = city.strip()
        cached_report = await self._get_cached_report("google-adk", city)
        if cached_report:
            return cached_report

        try:
            logger.info("Running Google ADK weather agent for city: %s", city)
            result = await asyncio.to_thread(run_google_adk_weather_agent, city)
        except Exception as exc:
            raise WeatherProviderError("Weather assistant unavailable") from exc

        logger.info("Google ADK weather report generated for city: %s", city)
        report = {"status": "ok", "message": result}
        await self._cache_report("google-adk", city, report)
        return report