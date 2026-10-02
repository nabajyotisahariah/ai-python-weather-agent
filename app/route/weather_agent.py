from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from app.services.weather_service import (
    CityNotFoundError,
    WeatherProviderError,
)
from app.services.interface.weather_agent_interface import WeatherAgentInterface
from app.services.weather_agent_service import WeatherAgentService
from app.schema.weather import AgentResponse, WeatherRequest, WeatherResponse
import logging

router = APIRouter()

logger = logging.getLogger(__name__)

weather_agent_service: WeatherAgentInterface = WeatherAgentService()

def get_weather_agent_service() -> WeatherAgentInterface:
    return weather_agent_service

@router.get("/weather/agent", summary="Weather Agent", description="Returns the current Weather & forecast of the API.", tags=["System"], response_model_exclude_none=True)
async def get_weather_forcast_route(
    request: WeatherRequest = Depends(),
    service: WeatherAgentInterface = Depends(get_weather_agent_service),
) -> AgentResponse:
    """Return the current weather & weather forecast for a city."""
    try:
        logger.info("Fetching current weather for city: %s", request.query.strip())
        return await service.get_weather_agent_crewai(request.query.strip())
    except CityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WeatherProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
