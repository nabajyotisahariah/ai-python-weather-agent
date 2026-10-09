import requests
from crewai.tools import tool
from app.config import settings


@tool("get_weather_forecast")
def get_weather_forecast(city: str, days: int = 7) -> str:
    """
    Get the weather forecast information for a city for a given number of days.
    """

    url = f"{settings.weather_api_url}/{city}?format=j1"

    print("tool.get_weather_forecast city ",city," days ",days)
    response = requests.get(url, timeout=settings.weather_timeout_seconds)
    response.raise_for_status()

    data = response.json()
    forecasts = []

    for item in data.get("weather", [])[:days]:
        date = item.get("date")
        max_temp = item.get("maxtempC")
        min_temp = item.get("mintempC")
        hourly = item.get("hourly", [])
        current_hour = hourly[len(hourly) // 2] if hourly else {}
        weather_desc = current_hour.get("weatherDesc", [{}])
        condition = weather_desc[0].get("value") if weather_desc else "Unknown"

        forecasts.append(
            f"Date: {date}, Max Temp: {max_temp}°C, Min Temp: {min_temp}°C, Condition: {condition}"
        )

    return "\n".join(forecasts)
