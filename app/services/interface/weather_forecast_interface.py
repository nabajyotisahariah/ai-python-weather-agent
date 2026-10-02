from abc import ABC, abstractmethod
from app.schema.weather import AgentResponse


class WeatherForecastInterface(ABC):

    @abstractmethod
    async def get_weather_forecast(self, city: str, days: int = 3) -> AgentResponse:
        """Return weather forecast data for a city."""
        raise NotImplementedError

    @abstractmethod
    async def get_weather_forecast_crewai(self, city: str) -> AgentResponse:
        """Return an LLM-generated weather forecast report for a city."""
        raise NotImplementedError
   