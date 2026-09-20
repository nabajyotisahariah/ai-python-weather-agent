from abc import ABC, abstractmethod


class WeatherServiceInterface(ABC):

    @abstractmethod
    async def get_current_weather(self, city: str) -> dict[str, str | int | float]:
            """Return current weather data for a city."""
            raise NotImplementedError
    
    @abstractmethod
    async def get_crewai_weather_report(self, city: str) -> dict[str, str]:
        """Return an LLM-generated weather report for a city."""
        raise NotImplementedError

    @abstractmethod
    async def get_opengen_weather_report(self, city: str) -> dict[str, str]:
           """Return an LLM-generated weather report for a city."""
           raise NotImplementedError