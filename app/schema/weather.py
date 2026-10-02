
from typing import Literal
from pydantic import BaseModel, Field

class WeatherRequest(BaseModel):
    city: str | None = Field(None, description="City to get weather for")
    query: str | None = Field(None, description="Query string for weather")


class WeatherResponse(BaseModel):
    city: str
    query: str
    temperature: str | int | float
    feels_like: str | int | float
    humidity: str | int | float
    description: str
    wind_speed: str | int | float

class AgentResponse(BaseModel):
    status: Literal["success", "fail", "error"]
    message: str | None = None
    data: dict | list | None = None
    isCached: bool = Field(
        default=False,
        description="Indicates if the response was served from cache"
    )