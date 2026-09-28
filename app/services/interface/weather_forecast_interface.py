from abc import ABC, abstractmethod


class WeatherForecastInterface(ABC):

    @abstractmethod
    async def get_weather_forecast(self, city: str, days: int = 3) -> dict[str, str | int | float]:
            """Return current weather data for a city."""
   