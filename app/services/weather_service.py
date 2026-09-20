import os
import asyncio
from dataclasses import dataclass
from urllib.parse import quote

import httpx
from crewai import Agent, Crew, Process, Task
from dotenv import load_dotenv

from app.tools.weather_tool import get_weather


load_dotenv()


class WeatherServiceError(Exception):
    """Base error for weather provider failures."""


class CityNotFoundError(WeatherServiceError):
    """The weather provider could not find the requested city."""


class WeatherProviderError(WeatherServiceError):
    """The weather provider could not return a valid response."""


@dataclass(frozen=True)
class WeatherService:
    base_url: str = os.getenv("WEATHER_API_URL", "https://wttr.in")
    timeout_seconds: float = float(os.getenv("WEATHER_TIMEOUT_SECONDS", "10"))

    def __post_init__(self) -> None:
        weather_agent = Agent(
            role="Weather Assistant",
            goal="Provide accurate and easy-to-understand weather information",
            backstory="""
            You are an expert weather assistant.
            You retrieve current weather information
            and explain it clearly to users.
            """,
            tools=[get_weather],
            verbose=True,
        )
        weather_task = Task(
            description="""
            Get the current weather information for {city}.

            Use the get_weather tool to retrieve the information.

            Provide:
            - Temperature
            - Feels-like temperature
            - Humidity
            - Weather condition
            - Wind speed
            """,
            expected_output="""
            A concise weather report containing:
            city, temperature, feels-like temperature,
            humidity, weather condition, and wind speed.
            """,
            agent=weather_agent,
        )
        weather_crew = Crew(
            agents=[weather_agent],
            tasks=[weather_task],
            process=Process.sequential,
            verbose=True,
        )
        object.__setattr__(self, "weather_crew", weather_crew)

    async def get_llm_weather_report(self, city: str) -> str:
        """Run the CrewAI weather agent without blocking the API event loop."""
        result = await asyncio.to_thread(
            self.weather_crew.kickoff,
            inputs={"city": city},
        )
        return str(result)

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


weather_service = WeatherService()