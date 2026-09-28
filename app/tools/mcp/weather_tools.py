from typing import Any
import httpx

from app.services.weather_service import WeatherService
from app.services.weather_forecast_service import WeatherForcastService
#from app.config import settings
from app.schema.weather import AgentResponse

weather_service = WeatherService()
weather_forcast_service = WeatherForcastService()


async def get_weather(city: str) -> AgentResponse:
    """
    Get current weather information for a city.

    Args:
        city: City name such as London, Delhi, New York or Tokyo.

    Returns:
        Current weather information.
    """

    city = city.strip()

    if not city:
        raise ValueError("City is required")

    result = await weather_service.get_current_weather(city)

    return {
        "status": 'success',
        "data": result,
        "isCached": True,
    }


async def get_weather_forecast(
    city: str,
    days: int = 3,
) -> AgentResponse:
    """
    Get weather forecast for a city.

    Args:
        city: City name such as London, Delhi, New York or Tokyo.
        days: Number of forecast days, from 1 to 7.

    Returns:
        Weather forecast information.
    """

    city = city.strip()

    if not city:
        raise ValueError("City is required")

    if days < 1 or days > 7:
        raise ValueError("days must be between 1 and 7")

   
    forecasts = await  weather_forcast_service.get_weather_forecast(city, days)
    
    return {
            "status": 'success',
            "data": forecasts,
            "isCached": True,
    }

