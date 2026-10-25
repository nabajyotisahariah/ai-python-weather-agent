from urllib.parse import quote

import requests
from crewai.tools import tool

from app.config import settings
from app.guardrails.input_guardrails import validate_query
from app.guardrails.tool_guardrails import validate_tool_call


def fetch_air_quality(city: str) -> str:
    city = validate_query(city)
    validate_tool_call("get_air_quality", {"city": city})

    if not settings.waqi_api_token:
        raise RuntimeError("WAQI_API_TOKEN is not configured")

    url = f"{settings.waqi_api_url.rstrip('/')}/feed/{quote(city, safe='')}/"
    try:
        response = requests.get(
            url,
            params={"token": settings.waqi_api_token},
            timeout=settings.weather_timeout_seconds,
        )
        response.raise_for_status()
        result = response.json()
       
    except requests.RequestException:
        raise RuntimeError("WAQI provider request failed") from None
    except ValueError:
        raise RuntimeError("WAQI provider returned invalid JSON") from None

    if not isinstance(result, dict) or result.get("status") != "ok":
        raise RuntimeError("WAQI provider did not return air-quality data")

    data = result.get("data")
    if not isinstance(data, dict) or data.get("aqi") is None:
        raise RuntimeError("WAQI provider response is missing the AQI value")

    city_data = data.get("city")
    city_name = city_data.get("name") if isinstance(city_data, dict) else city
    report = [f"City: {city_name}", f"Air Quality Index (AQI): {data['aqi']}"]

    dominant_pollutant = data.get("dominentpol")
    if dominant_pollutant:
        report.append(f"Dominant pollutant: {dominant_pollutant}")

    iaqi = data.get("iaqi")
    if isinstance(iaqi, dict):
        pollutant_names = {
            "pm25": "PM2.5",
            "pm10": "PM10",
            "o3": "Ozone",
            "no2": "Nitrogen dioxide",
            "so2": "Sulfur dioxide",
            "co": "Carbon monoxide",
        }
        for key, label in pollutant_names.items():
            measurement = iaqi.get(key)
            if isinstance(measurement, dict) and measurement.get("v") is not None:
                report.append(f"{label}: {measurement['v']}")

    time_data = data.get("time")
    if isinstance(time_data, dict) and time_data.get("s"):
        report.append(f"Observed at: {time_data['s']}")

    return "\n".join(report)


@tool("get_air_quality")
def get_air_quality(city: str) -> str:
    """Get the current air quality index and available pollutant readings for a city."""
    return fetch_air_quality(city)
