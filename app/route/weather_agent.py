from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from app.services.weather_service import (
    CityNotFoundError,
    WeatherProviderError,
)
from app.services.interface.weather_agent_interface import WeatherAgentInterface
from app.services.weather_agent_service import WeatherAgentService
from app.schema.weather import AgentResponse, WeatherRequest
from app.guardrails.input_guardrails import GuardrailViolation, validate_query
from app.utils.response import generic_api_response
import logging

router = APIRouter()

logger = logging.getLogger(__name__)

weather_agent_service: WeatherAgentInterface = WeatherAgentService()

def get_weather_agent_service() -> WeatherAgentInterface:
    return weather_agent_service

@router.post("/weather/agent", summary="Weather Agent (POST)", description="Returns the current Weather & forecast of the API using a JSON body.", tags=["System"], response_model_exclude_none=True)
async def post_weather_forecast_route(
    request: WeatherRequest,
    service: WeatherAgentInterface = Depends(get_weather_agent_service),
) -> AgentResponse:
    """Return the current weather & weather forecast for a city using a POST request."""
    query_val = request.query if request.query is not None else request.city
    
    try:
        query_val = validate_query(query_val)

        #"weather:context:{user_id}:{session_id}"
        user_id = "default_user"  # Replace with actual user ID if available
        session_id = request.session_id if request.session_id is not None else None # Replace with actual session ID if available

        if(session_id is None or len(session_id) <= 6):
            logger.warning("User ID or Session ID is None or invalid. Using default values.")
            raise HTTPException("Session ID is None or invalid")
    
        logger.info("Fetching current weather for city (POST): %s", query_val)
        return await service.process_weather_query(query_val, session_id=session_id, user_id=user_id)

    except GuardrailViolation as exc:
        return generic_api_response(400, "fail", str(exc))
    except CityNotFoundError as exc:
        return generic_api_response(404, "fail", str(exc))
    except HTTPException as exc:
        return generic_api_response(400, "fail", str(exc))
    except Exception as exc:
        logger.error("Unexpected error: %s", str(exc))
        return generic_api_response(400, "fail", str(exc))


@router.post("/weather/agent/langgraph", summary="Weather Agent (POST)", description="Returns the current Weather & forecast of the API using a JSON body.", tags=["System"], response_model_exclude_none=True)
async def post_weather_forecast_route_langgraph(
    request: WeatherRequest,
    service: WeatherAgentInterface = Depends(get_weather_agent_service),
) -> AgentResponse:
    """Return the current weather & weather forecast for a city using a POST request."""
    query_val = request.query if request.query is not None else request.city
    
    try:
        query_val = validate_query(query_val)
    
        logger.info("Fetching current weather for city (POST): %s", query_val)
        return await service.process_weather_langgraph_query(query_val)

    except GuardrailViolation as exc:
        return generic_api_response(400, "fail", str(exc))
    except CityNotFoundError as exc:
        return generic_api_response(404, "fail", str(exc))
    except WeatherProviderError as exc:
        return generic_api_response(502, "fail", str(exc))
