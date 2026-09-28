from abc import ABC, abstractmethod
from app.schema.weather import AgentResponse


class WeatherForecastInterface(ABC):

    @abstractmethod
    async def get_weather_forecast(self, city: str, days: int = 3) -> AgentResponse:
            """Return current weather data for a city."""
   