from urllib.parse import quote

import httpx
from langchain_core.tools import tool

from app.config import settings
from app.guardrails.input_guardrails import validate_query
from app.guardrails.tool_guardrails import validate_tool_call


@tool
async def get_weather(city: str) -> str:
    """Get current weather information for a city."""
    validate_tool_call("get_weather", {"city": city})
    city = city.strip()
    url = f"{settings.weather_api_url.rstrip('/')}/{quote(city, safe='')}"

    async with httpx.AsyncClient(timeout=settings.weather_timeout_seconds) as client:
        response = await client.get(
            url,
            params={"format": "j1"},
            timeout=settings.weather_timeout_seconds,
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


@tool
async def get_weather_forecast(city: str, days: int = 7) -> str:
    """Get weather forecast information for a city for the requested number of days."""
    validate_tool_call(
        "get_weather_forecast",
        {"city": city, "days": days},
    )
    city = validate_query(city)
    url = f"{settings.weather_api_url.rstrip('/')}/{quote(city, safe='')}"

    async with httpx.AsyncClient(timeout=settings.weather_timeout_seconds) as client:
        response = await client.get(
            url,
            params={"format": "j1"},
            timeout=settings.weather_timeout_seconds,
        )
        response.raise_for_status()

    forecasts = []
    for item in response.json().get("weather", [])[:days]:
        hourly = item.get("hourly", [])
        current_hour = hourly[len(hourly) // 2] if hourly else {}
        weather_desc = current_hour.get("weatherDesc", [{}])
        condition = weather_desc[0].get("value") if weather_desc else "Unknown"
        forecasts.append(
            f"Date: {item.get('date')}, "
            f"Max Temp: {item.get('maxtempC')}°C, "
            f"Min Temp: {item.get('mintempC')}°C, "
            f"Condition: {condition}"
        )
    return "\n".join(forecasts)
