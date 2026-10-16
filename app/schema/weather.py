from typing import Literal

from pydantic import BaseModel, Field, model_validator


class WeatherRequest(BaseModel):
    city: str | None = Field(None, description="City to get weather for")
    query: str | None = Field(None, description="Query string for weather")


class WeatherData(BaseModel):
   
    city: str = Field(min_length=1)
    temperature: float | None = Field(default=None, allow_inf_nan=False)
    feels_like: float | None = Field(default=None, allow_inf_nan=False)
    humidity: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    description: str | None = None
    wind_speed: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    unavailable_fields: list[str] = Field(default_factory=list)


class ForecastDay(BaseModel):
  
    date: str | None = None
    max_temp_c: float | None = Field(default=None, allow_inf_nan=False)
    min_temp_c: float | None = Field(default=None, allow_inf_nan=False)
    avg_temp_c: float | None = Field(default=None, allow_inf_nan=False)
    condition: str | None = None
    humidity: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    wind_speed_kmph: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    chance_of_rain: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    chance_of_snow: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    uv_index: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    unavailable_fields: list[str] = Field(default_factory=list)


class AgentResponse(BaseModel):
    
    status: Literal["success", "fail", "error"]
    message: str | None = Field(default=None, max_length=2000)
    data: WeatherData | list[ForecastDay] | None = None
    isCached: bool = Field(
        default=False,
        strict=True,
        description="Indicates if the response was served from cache",
    )
    cacheKey: str | None = Field(
        default=None,
        description="Key for caching the response",
    )

WeatherResponse = WeatherData
