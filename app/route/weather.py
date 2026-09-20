from fastapi import APIRouter, Depends, HTTPException
from app.services.weather_service import (
    CityNotFoundError,
    WeatherProviderError,
)
from app.services.interface.weather_service_interface import WeatherServiceInterface
from app.services.weather_service import WeatherService
from app.schema.weather import WeatherRequest, WeatherResponse, CrewAIWeatherResponse
import logging

router = APIRouter()
weather_service: WeatherServiceInterface = WeatherService()

logger = logging.getLogger(__name__)

def get_weather_service() -> WeatherServiceInterface:
    return weather_service

@router.get("/weather")
async def get_current_weather_route(
    request: WeatherRequest = Depends(),
    service: WeatherServiceInterface = Depends(get_weather_service),
) -> WeatherResponse:
    """Return the current weather for a city."""
    try:
        logger.info("Fetching current weather for city: %s", request.city.strip())
        return await service.get_current_weather(request.city.strip())
    except CityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WeatherProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/weather/crewai")
async def get_crewai_weather_route(
    request: WeatherRequest = Depends(),
    service: WeatherServiceInterface = Depends(get_weather_service),
) -> CrewAIWeatherResponse:
    """Return a CrewAI-generated weather summary for a city."""
    try:
        logger.info("Fetching CrewAI weather report for city: %s", request.city.strip())
        return await service.get_crewai_weather_report(request.city.strip())
    except CityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WeatherProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Weather assistant unavailable") from exc

@router.get("/weather/opengen")
async def get_opengen_weather_route(
    request: WeatherRequest = Depends(),
    service: WeatherServiceInterface = Depends(get_weather_service),
) -> CrewAIWeatherResponse:
    """Return a CrewAI-generated weather summary for a city."""
    try:
        print("Fetching OpenGen weather report for city: %s", request.city.strip())
        return await service.get_opengen_weather_report(request.city.strip())
    except CityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WeatherProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Weather assistant unavailable") from exc

@router.get("/weather/langgraph")
async def get_langgraph_weather_route(
    request: WeatherRequest = Depends(),
    service: WeatherServiceInterface = Depends(get_weather_service),
) -> CrewAIWeatherResponse:
    """Return a LangGraph-generated weather summary for a city."""
    try:
        logger.info("Fetching LangGraph weather report for city: %s", request.city.strip())
        return await service.get_langgraph_weather_report(request.city.strip())
    except CityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WeatherProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Weather assistant unavailable") from exc

@router.get("/weather/autogen")
async def get_autogen_weather_route(
    request: WeatherRequest = Depends(),
    service: WeatherServiceInterface = Depends(get_weather_service),
) -> CrewAIWeatherResponse:
    """Return an AutoGen-generated weather summary for a city."""
    try:
        logger.info("Fetching AutoGen weather report for city: %s", request.city.strip())
        return await service.get_autogen_weather_report(request.city.strip())
    except CityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WeatherProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Weather assistant unavailable") from exc


@router.get("/weather/google-adk")
async def get_google_adk_weather_route(
    request: WeatherRequest = Depends(),
    service: WeatherServiceInterface = Depends(get_weather_service),
) -> CrewAIWeatherResponse:
    """Return an Google ADK-generated weather summary for a city."""
    try:
        logger.info("Fetching Google ADK weather report for city: %s", request.city.strip())
        return await service.get_google_adk_weather_report(request.city.strip())
    except CityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WeatherProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Weather assistant unavailable") from exc
