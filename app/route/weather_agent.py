from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from app.services.weather_service import (
    CityNotFoundError,
    WeatherProviderError,
)
from app.services.interface.weather_agent_interface import WeatherAgentInterface
from app.services.weather_agent_service import WeatherAgentService
from app.schema.weather import AgentResponse, WeatherRequest
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
    if not query_val or not query_val.strip():
        return JSONResponse(
            status_code=401,
            content={"status": "fail", "message": "City name cannot be empty."}
        )
    try:
        logger.info("Fetching current weather for city (POST): %s", query_val.strip())
        return await service.process_weather_query(query_val.strip())
    except CityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WeatherProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
