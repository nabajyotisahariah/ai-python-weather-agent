import os
import asyncio
from dataclasses import dataclass
from urllib.parse import quote

import httpx
from redis.asyncio import Redis
#from dotenv import load_dotenv

from app.services.interface.weather_forecast_interface import WeatherForecastInterface
from app.config import settings
from app.schema.weather import AgentResponse
from app.utils.redis_cache import AsyncRedisCache
from app.utils.langfuse_observability import observe_operation, update_observation
import logging

logger = logging.getLogger(__name__)

#load_dotenv()


class WeatherServiceError(Exception):
    """Base error for weather provider failures."""


class CityNotFoundError(WeatherServiceError):
    """The weather provider could not find the requested city."""


class WeatherProviderError(WeatherServiceError):
    """The weather provider could not return a valid response."""


class WeatherForcastService(WeatherForecastInterface):
    base_url: str = settings.weather_api_url
    timeout_seconds: float = settings.weather_timeout_seconds

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
                "isCached": True,
            }
        return None

    async def _cache_report(self, provider: str, city: str, report: AgentResponse) -> None:
        await self.cache.set(self._report_cache_key(provider, city), report, ex=3600)

    #def __post_init__(self) -> None:
    #    object.__setattr__(self, "weather_crew", build_weather_crew())

    

    async def get_weather_forecast(self, city: str, days: int = 3) -> dict[str, str | int | float]:
        """
        Get weather forecast for a city.

        Args:
            city: City name.
            days: Number of forecast days (1-7).

        Returns:
            List of daily weather forecast information.
        """
        city = city.strip()
        if not city:
            raise CityNotFoundError("City name is required")

        with observe_operation("weather:forecast:current", input_data={"city": city}) as observation:
            cache_key = self._cache_key(city)
            cached_weather = await self.cache.get(cache_key)
            if cached_weather:
                update_observation(observation, output=cached_weather, metadata={"is_cached": True})
                return cached_weather

            url = f"{self.base_url.rstrip('/')}/{quote(city, safe='')}"
            async with httpx.AsyncClient(timeout=settings.weather_timeout_seconds) as client:
                response = await client.get(
                    url,
                    params={"format": "j1"},
                )
        
            response.raise_for_status()
        
            data = response.json()
        
            forecasts = []
        
            for item in data.get("weather", [])[:days]:
        
                hourly = item.get("hourly", [])
        
                # Get a representative weather condition.
                # wttr.in provides multiple hourly entries per day.
                current_hour = hourly[len(hourly) // 2] if hourly else {}
        
                weather_desc = current_hour.get("weatherDesc", [{}])
        
                forecasts.append(
                    {
                        "date": item.get("date"),
                        "max_temp_c": item.get("maxtempC"),
                        "min_temp_c": item.get("mintempC"),
                        "avg_temp_c": item.get("avgtempC"),
                        "condition": (
                            weather_desc[0].get("value")
                            if weather_desc
                            else None
                        ),
                        "humidity": current_hour.get("humidity"),
                        "wind_speed_kmph": current_hour.get("windspeedKmph"),
                        "chance_of_rain": current_hour.get("chanceofrain"),
                        "chance_of_snow": current_hour.get("chanceofsnow"),
                        "uv_index": item.get("uvIndex"),
                    }
                )
        
            return forecasts
