from typing import Literal
from enum import Enum
from pydantic import BaseModel, Field, model_validator
import re
from dataclasses import dataclass

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

class HITLDecision(str, Enum):
    EXECUTE = "execute"
    CLARIFICATION_REQUIRED = "clarification_required"
    APPROVAL_REQUIRED = "approval_required"
    REJECT = "reject"


@dataclass(frozen=True)
class ActionIntent:
    action: str
    target: str | None = None


ACTION_PATTERNS = (
    (
        "broadcast_alert",
        re.compile(
            r"\b(broadcast|send|issue|publish)\b.{0,100}"
            r"\b(alert|notification|email|message)\b"
            r".{0,100}\b(all users|all customers|everyone)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "bulk_notification",
        re.compile(
            r"\b(notify|email|message)\b.{0,100}"
            r"\b(all users|all customers|everyone)\b",
            re.IGNORECASE,
        ),
    ),
)


def detect_consequential_action(query: str) -> ActionIntent | None:
    for action, pattern in ACTION_PATTERNS:
        if pattern.search(query):
            return ActionIntent(action=action)

    return None

#temp = detect_consequential_action("Please broadcast an alert to all users about the weather warning.")
#print(temp)  # Output: ActionIntent(action='broadcast_alert', target=None)

def needs_location_clarification(
    query: str,
    resolved_city: str | None,
) -> bool:
    if resolved_city:
        return False

    # These examples are intentionally simple.
    # Use your intent router and location extractor in production.
    weather_terms = (
        "weather",
        "rain",
        "umbrella",
        "forecast",
        "temperature",
    )

    query_lower = query.casefold()

    is_weather_query = any(
        term in query_lower for term in weather_terms
    )

    if not is_weather_query:
        return False

    return True