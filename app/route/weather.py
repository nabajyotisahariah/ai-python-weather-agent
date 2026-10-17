from fastapi import APIRouter, Depends
from app.services.weather_service import (
    CityNotFoundError,
    WeatherProviderError,
)
from app.services.interface.weather_interface import WeatherServiceInterface
from app.services.weather_service import WeatherService
from app.schema.weather import AgentResponse, WeatherRequest, WeatherResponse
from app.guardrails.input_guardrails import GuardrailViolation, validate_query
from app.utils.response import generic_api_response
import logging

router = APIRouter()
weather_service: WeatherServiceInterface = WeatherService()

logger = logging.getLogger(__name__)

def get_weather_service() -> WeatherServiceInterface:
    return weather_service


@router.get("/weather", response_model_exclude_none=True)
async def get_current_weather_route(
    request: WeatherRequest = Depends(),
    service: WeatherServiceInterface = Depends(get_weather_service),
) -> AgentResponse:
    """Return the current weather for a city."""
    if not request.city or not request.city.strip():
        return generic_api_response(401, "fail", "City name cannot be empty.")
    try:
        logger.info("Fetching current weather for city: %s", request.city.strip())
        return await service.get_current_weather(request.city.strip())
    except CityNotFoundError as exc:
        return generic_api_response(404, "fail", str(exc))
    except WeatherProviderError as exc:
        return generic_api_response(502, "fail", str(exc))


@router.get("/weather/crewai", response_model_exclude_none=True)
async def get_crewai_weather_route(
    request: WeatherRequest = Depends(),
    service: WeatherServiceInterface = Depends(get_weather_service),
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
        return await service.get_crewai_weather_report(city)
    except CityNotFoundError as exc:
        return generic_api_response(404, "fail", str(exc))
    except WeatherProviderError:
        logger.warning("CrewAI weather provider failed for city: %s", request.city.strip())
        return generic_api_response(502, "fail", "Weather assistant unavailable")
    except Exception as exc:
        logger.exception("Unexpected CrewAI weather error for city: %s", request.city.strip())
        return generic_api_response(500, "fail", "An unexpected error occurred")

@router.get("/weather/langgraph", response_model_exclude_none=True)
async def get_langgraph_weather_route(
    request: WeatherRequest = Depends(),
    service: WeatherServiceInterface = Depends(get_weather_service),
) -> AgentResponse:
    """Return a LangGraph-generated weather summary for a city."""
    if not request.city or not request.city.strip():
        return generic_api_response(401, "fail", "City name cannot be empty.")
    try:
        city = validate_query(request.city)
    except GuardrailViolation as exc:
        return generic_api_response(400, "fail", str(exc))

    try:
        logger.info("Fetching LangGraph weather report for city: %s", city)
        return await service.get_langgraph_weather_report(city)
    except CityNotFoundError as exc:
        return generic_api_response(404, "fail", str(exc))
    except WeatherProviderError:
        logger.warning("LangGraph weather provider failed for city: %s", request.city.strip())
        return generic_api_response(502, "fail", "Weather assistant unavailable")
    except Exception as exc:
        logger.exception("Unexpected LangGraph weather error for city: %s", request.city.strip())
        return generic_api_response(500, "fail", "An unexpected error occurred")

@router.get("/weather/autogen", response_model_exclude_none=True)
async def get_autogen_weather_route(
    request: WeatherRequest = Depends(),
    service: WeatherServiceInterface = Depends(get_weather_service),
) -> AgentResponse:
    """Return an AutoGen-generated weather summary for a city."""
    if not request.city or not request.city.strip():
        return generic_api_response(401, "fail", "City name cannot be empty.")
    try:
        city = validate_query(request.city)
    except GuardrailViolation as exc:
        return generic_api_response(400, "fail", str(exc))

    try:
        logger.info("Fetching AutoGen weather report for city: %s", city)
        return await service.get_autogen_weather_report(city)
    except CityNotFoundError as exc:
        return generic_api_response(404, "fail", str(exc))
    except Exception as exc:
        logger.exception("Unexpected AutoGen weather error for city: %s", request.city.strip())
        return generic_api_response(500, "fail", "An unexpected error occurred")


# @router.get("/weather/google-adk", response_model_exclude_none=True)
# async def get_google_adk_weather_route(
#     request: WeatherRequest = Depends(),
#     service: WeatherServiceInterface = Depends(get_weather_service),
# ) -> AgentResponse:
#     """Return an Google ADK-generated weather summary for a city."""
#     try:
#         logger.info("Fetching Google ADK weather report for city: %s", request.city.strip())
#         return await service.get_google_adk_weather_report(request.city.strip())
#     except CityNotFoundError as exc:
#         raise HTTPException(status_code=404, detail=str(exc)) from exc
#     except WeatherProviderError:
#         logger.warning("Google ADK weather provider failed for city: %s", request.city.strip())
#         return assistant_error_response()
#     except Exception as exc:
#         logger.exception("Unexpected Google ADK weather error for city: %s", request.city.strip())
#         return assistant_error_response()
