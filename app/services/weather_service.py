import os
import asyncio
from dataclasses import dataclass
from urllib.parse import quote

import httpx
#from dotenv import load_dotenv

from app.agents.crewai import build_weather_crew
from app.services.interface.weather_service_interface import WeatherServiceInterface
from app.config import settings
#import logging

#logger = logging.getLogger(__name__)

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

    #def __post_init__(self) -> None:
    #    object.__setattr__(self, "weather_crew", build_weather_crew())

    async def get_llm_weather_report(self, city: str) -> dict[str, str]:
        """Run the CrewAI weather agent without blocking the API event loop."""
        try:
            print("Building CrewAI weather crew for city: %s", city)
            weather_crew = build_weather_crew(city)
            result = await asyncio.to_thread(
                weather_crew.kickoff,
                inputs={"city": city},
            )
        except Exception as exc:
            raise WeatherProviderError("Weather assistant unavailable") from exc

        print("LLM weather report for city: %s", city)
        return {"status": "ok", "message": str(result)}

    async def get_current_weather(self, city: str) -> dict[str, str | int | float]:
        city = city.strip()
        if not city:
            raise CityNotFoundError("City name is required")

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
            return {
                "city": city,
                "temperature": current["temp_C"],
                "feels_like": current["FeelsLikeC"],
                "humidity": current["humidity"],
                "description": current["weatherDesc"][0]["value"],
                "wind_speed": current["windspeedKmph"],
            }
        except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
            raise WeatherProviderError("Weather service returned invalid data") from exc


