import requests
from crewai.tools import tool
from app.config import settings


@tool("get_weather")
def get_weather(city: str) -> str:
    """
    Get the current weather information for a city.
    """

    url = f"{settings.weather_api_url}/{city}?format=j1"

    response = requests.get(url, timeout=settings.weather_timeout_seconds)
    response.raise_for_status()

    data = response.json()

    current = data["current_condition"][0]

    return f"""
    City: {city}
    Temperature: {current['temp_C']}°C
    Feels Like: {current['FeelsLikeC']}°C
    Humidity: {current['humidity']}%
    Weather: {current['weatherDesc'][0]['value']}
    Wind Speed: {current['windspeedKmph']} km/h
    """
