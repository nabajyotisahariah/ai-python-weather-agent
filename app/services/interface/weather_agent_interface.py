from abc import ABC, abstractmethod
from app.schema.weather import AgentResponse


class WeatherAgentInterface(ABC):

    @abstractmethod
    async def get_weather_agent_crewai(self, query: str, days: int = 3) -> AgentResponse:
            """Return current weather & forecast data for a city."""

   