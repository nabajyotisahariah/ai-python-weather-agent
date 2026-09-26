from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from app.services.weather_service import (
    CityNotFoundError,
    WeatherProviderError,
)
from app.services.interface.weather_forecast_interface import WeatherForecastInterface
from app.services.weather_forecast_service import WeatherForcastService
from app.schema.weather import AgentResponse, WeatherRequest, WeatherResponse
import logging

router = APIRouter()
weather_service: WeatherForecastInterface = WeatherForcastService()

logger = logging.getLogger(__name__)

def get_weather_forcast_service() -> WeatherForecastInterface:
    return weather_service


def assistant_error_response() -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"status": "fail", "message": "Weather assistant unavailable"},
    )

@router.get("/weather/forecast")
async def get_weather_forcast_route(
    request: WeatherRequest = Depends(),
    service: WeatherForecastInterface = Depends(get_weather_forcast_service),
) -> WeatherResponse:
    """Return the current weather for a city."""
    try:
        logger.info("Fetching current weather for city: %s", request.city.strip())
        return await service.get_weather_forecast(request.city.strip())
    except CityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WeatherProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
