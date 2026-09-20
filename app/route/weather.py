from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.weather_service import (
    CityNotFoundError,
    WeatherProviderError,
    WeatherService
)

router = APIRouter()
weather_service = WeatherService()

class WeatherResponse(BaseModel):
    city: str
    temperature: str | int | float
    feels_like: str | int | float
    humidity: str | int | float
    description: str
    wind_speed: str | int | float


@router.get("/weather")
async def get_current_weather_route(
    city: str = Query(..., min_length=1, description="City to get weather for"),
) -> WeatherResponse:
    """Return the current weather for a city."""
    try:
        return await weather_service.get_current_weather(city.strip())
    except CityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WeatherProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/weather/crewai")
async def get_crewai_weather_route(
    city: str = Query(..., min_length=1, description="City to get weather for"),
) -> str:
    """Return a CrewAI-generated weather summary for a city."""
    try:
        return await weather_service.get_llm_weather_report(city.strip())
    except CityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WeatherProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
