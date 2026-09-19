from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.weather_service import (
    CityNotFoundError,
    WeatherProviderError,
    weather_service,
)

router = APIRouter()


class WeatherResponse(BaseModel):
    city: str
    temperature: str | int | float
    feels_like: str | int | float
    humidity: str | int | float
    description: str
    wind_speed: str | int | float


@router.get("/weather")
async def get_weather(
	city: str = Query(..., min_length=1, description="City to get weather for"),
) -> WeatherResponse:
	"""Return the current weather for a city."""
	try:
		return await weather_service.get_current_weather(city.strip())
	except CityNotFoundError as exc:
		raise HTTPException(status_code=404, detail=str(exc)) from exc
	except WeatherProviderError as exc:
		raise HTTPException(status_code=502, detail=str(exc)) from exc
