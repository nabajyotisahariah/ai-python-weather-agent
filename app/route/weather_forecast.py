from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from app.services.weather_service import (
    CityNotFoundError,
    WeatherProviderError,
)
from app.services.interface.weather_forecast_interface import WeatherForecastInterface
from app.services.weather_forecast_service import WeatherForecastService
from app.schema.weather import AgentResponse, WeatherRequest, WeatherResponse
import logging

router = APIRouter()
weather_service: WeatherForecastInterface = WeatherForecastService()

logger = logging.getLogger(__name__)

def get_weather_forecast_service() -> WeatherForecastInterface:
    return weather_service


def assistant_error_response() -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"status": "fail", "message": "Weather assistant unavailable"},
    )

@router.get("/weather/forecast", response_model_exclude_none=True)
async def get_weather_forecast_route(
    request: WeatherRequest = Depends(),
    service: WeatherForecastInterface = Depends(get_weather_forecast_service),
) -> AgentResponse:
    """Return the current weather for a city."""
    if not request.city or not request.city.strip():
        return JSONResponse(
            status_code=401,
            content={"status": "fail", "message": "City name cannot be empty."}
        )
    try:
        logger.info("Fetching current weather for city: %s", request.city.strip())
        return await service.get_weather_forecast(request.city.strip())
    except CityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WeatherProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

@router.get("/weather/forecast/crewai", response_model_exclude_none=True)
async def get_crewai_weather_route(
    request: WeatherRequest = Depends(),
    service: WeatherForecastInterface = Depends(get_weather_forecast_service),
) -> AgentResponse:
    """Return a CrewAI-generated weather summary for a city."""
    if not request.city or not request.city.strip():
        return JSONResponse(
            status_code=401,
            content={"status": "fail", "message": "City name cannot be empty."}
        )
    try:
        logger.info("Fetching CrewAI weather report for city: %s", request.city.strip())
        return await service.get_weather_forecast_crewai(request.city.strip())
    except CityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WeatherProviderError:
        logger.warning("CrewAI weather provider failed for city: %s", request.city.strip())
        return assistant_error_response()
    except Exception as exc:
        logger.exception("Unexpected CrewAI weather error for city: %s", request.city.strip())
        return assistant_error_response()