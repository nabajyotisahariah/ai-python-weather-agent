from fastapi import APIRouter, Depends
from app.services.weather_service import (
    CityNotFoundError,
    WeatherProviderError,
)
from app.services.interface.weather_forecast_interface import WeatherForecastInterface
from app.services.weather_forecast_service import WeatherForecastService
from app.schema.weather import AgentResponse, WeatherRequest, WeatherResponse
from app.guardrails.input_guardrails import GuardrailViolation, validate_query
from app.utils.response import generic_api_response
import logging

router = APIRouter()
weather_service: WeatherForecastInterface = WeatherForecastService()

logger = logging.getLogger(__name__)

def get_weather_forecast_service() -> WeatherForecastInterface:
    return weather_service


@router.get("/weather/forecast", response_model_exclude_none=True)
async def get_weather_forecast_route(
    request: WeatherRequest = Depends(),
    service: WeatherForecastInterface = Depends(get_weather_forecast_service),
) -> AgentResponse:
    """Return the current weather for a city."""
    if not request.city or not request.city.strip():
        return generic_api_response(401, "fail", "City name cannot be empty.")
    try:
        logger.info("Fetching current weather for city: %s", request.city.strip())
        return await service.get_weather_forecast(request.city.strip())
    except CityNotFoundError as exc:
        return generic_api_response(404, "fail", str(exc))
    except WeatherProviderError as exc:
        return generic_api_response(502, "fail", str(exc))

@router.get("/weather/forecast/crewai", response_model_exclude_none=True)
async def get_crewai_weather_route(
    request: WeatherRequest = Depends(),
    service: WeatherForecastInterface = Depends(get_weather_forecast_service),
) -> AgentResponse:
    """Return a CrewAI-generated weather summary for a city."""
    if not request.city or not request.city.strip():
        return generic_api_response(401, "fail", "City name cannot be empty.")
    try:
        city = validate_query(request.city)
    except GuardrailViolation as exc:
        return generic_api_response(400, "fail", str(exc))

    try:
        logger.info("Fetching CrewAI weather report for city: %s", city)
        return await service.get_weather_forecast_crewai(city)
    except CityNotFoundError as exc:
        return generic_api_response(404, "fail", str(exc))
    except WeatherProviderError:
        logger.warning("CrewAI weather provider failed for city: %s", request.city.strip())
        return generic_api_response(502, "fail", "Weather assistant unavailable")
    except Exception as exc:
        logger.exception("Unexpected CrewAI weather error for city: %s", request.city.strip())
        return generic_api_response(500, "fail", "An unexpected error occurred")