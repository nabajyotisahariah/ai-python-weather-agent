import os
from dataclasses import dataclass

import httpx


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

    async def get_current_weather(self, city: str) -> dict[str, str | int | float]:
        url = f"{self.base_url.rstrip('/')}/{city}"
        params = {"format": "j1"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=self.timeout_seconds)
        except httpx.HTTPError as exc:
            raise WeatherProviderError("Weather service unavailable") from exc

        if response.status_code == 404:
            raise CityNotFoundError("City not found")
        if response.status_code != 200:
            raise WeatherProviderError("Weather service returned an error")

        try:
            current = response.json()["current_condition"][0]
            return {
                "city": city,
                "temperature": current["temp_C"],
                "feels_like": current["FeelsLikeC"],
                "humidity": current["humidity"],
                "description": current["weatherDesc"][0]["value"],
                "wind_speed": current["windspeedKmph"],
            }
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise WeatherProviderError("Weather service returned invalid data") from exc


weather_service = WeatherService()