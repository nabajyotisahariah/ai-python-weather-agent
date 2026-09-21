
from typing import Literal

from pydantic import BaseModel, Field

class WeatherRequest(BaseModel):
    city: str = Field(..., min_length=1, description="City to get weather for")


class WeatherResponse(BaseModel):
    city: str
    temperature: str | int | float
    feels_like: str | int | float
    humidity: str | int | float
    description: str
    wind_speed: str | int | float


class AgentResponse(BaseModel):
    status: Literal["ok", "fail"]
    message: str
    isCached: bool = Field(default=False, description="Indicates if the response was served from cache")
