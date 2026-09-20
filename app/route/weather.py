from fastapi import APIRouter, Depends, HTTPException
from app.services.weather_service import (
    CityNotFoundError,
    WeatherProviderError,
    WeatherService
)
from app.schema.weather import WeatherRequest, WeatherResponse, CrewAIWeatherResponse
#from app.utils.logger import setup_logging

router = APIRouter()
weather_service = WeatherService()
#logger = setup_logging()

@router.get("/weather")
async def get_current_weather_route(
    request: WeatherRequest = Depends(),
) -> WeatherResponse:
    """Return the current weather for a city."""
    try:
        print("Fetching current weather for city: %s", request.city.strip())
        return await weather_service.get_current_weather(request.city.strip())
    except CityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WeatherProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/weather/crewai")
async def get_crewai_weather_route(
    request: WeatherRequest = Depends(),
) -> CrewAIWeatherResponse:
    """Return a CrewAI-generated weather summary for a city."""
    try:
        print("Fetching CrewAI weather report for city: %s", request.city.strip())
        return await weather_service.get_llm_weather_report(request.city.strip())
    except CityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WeatherProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Weather assistant unavailable") from exc
