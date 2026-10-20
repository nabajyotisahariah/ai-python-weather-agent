from enum import Enum
from pydantic import BaseModel, Field
from dataclasses import dataclass

@dataclass(frozen=True)
class ActionIntent:
    action: str
    target: str | None = None


class WeatherRequest(BaseModel):
    city: str | None = Field(None, description="City to get weather for")
    query: str | None = Field(None, description="Query string for weather")
    session_id: str | None = Field(None, description="Session ID for the request")
    user_id: str | None = Field(None, description="User ID for the request")


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


class ApprovalData(BaseModel):
    approval_id: str


class Status(str, Enum):
    SUCCESS = "success"
    FAIL = "fail"
    ERROR = "error"
    PENDING_CLARIFICATION = "pending_clarification"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    EXPIRED = "expired"

class AgentResponse(BaseModel):
    
    #status: Literal["success", "fail", "error", "approved",
    #                "rejected","pending_clarification","pending_approval",
    #                ] = Field(default="success", description="Status of the response")  
    status: Status = Field (default="success", description="Status of the response") 
    message: str | None = Field(default=None, max_length=2000)
    data: WeatherData | list[ForecastDay] | ApprovalData | None = None
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

