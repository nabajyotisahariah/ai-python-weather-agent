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

    @abstractmethod
    async def get_langgraph_weather_report(self, city: str) -> dict[str, str]:
            """Return an LLM-generated weather report for a city."""
            raise NotImplementedError

    @abstractmethod
    async def get_autogen_weather_report(self, city: str) -> dict[str, str]:
            """Return an AutoGen-generated weather report for a city."""
            raise NotImplementedError

    @abstractmethod
    async def get_google_adk_weather_report(self, city: str) -> dict[str, str]:
        """Return an Google ADK-generated weather report for a city."""
        raise NotImplementedError