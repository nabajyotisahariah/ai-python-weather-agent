from urllib.parse import quote

import requests

from app.config import settings


def get_weather(city: str) -> str:
    """Get current weather information for a city."""
    city = city.strip()
    url = f"{settings.WEATHER_API_URL.rstrip('/')}/{quote(city, safe='')}"
    response = requests.get(
        url,
        params={"format": "j1"},
        timeout=settings.WEATHER_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    current = response.json()["current_condition"][0]
    return (
        f"City: {city}\n"
        f"Temperature: {current['temp_C']}°C\n"
        f"Feels Like: {current['FeelsLikeC']}°C\n"
        f"Humidity: {current['humidity']}%\n"
        f"Weather: {current['weatherDesc'][0]['value']}\n"
        f"Wind Speed: {current['windspeedKmph']} km/h"
    )