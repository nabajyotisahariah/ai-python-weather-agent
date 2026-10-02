# orchestrator/crewai/tools.py
import logging
from crewai.tools import tool

from app.agents.crewai import build_weather_crew
from app.agents.crewai.weather_forecast_agent import build_weather_forecast_crew

logger = logging.getLogger(__name__)

def run_weather_agent(city: str):
    weather_crew = build_weather_crew(city)
    result = weather_crew.kickoff(
        inputs={"city": city},
    )
    print("run_weather_agent ",result)
    return result.raw

def run_forecast_agent(city: str):
    weather_crew = build_weather_forecast_crew(city)
    result = weather_crew.kickoff(
        inputs={"city": city},
    )
    return result.raw

@tool("get_current_weather")
def get_current_weather(city: str) -> str:
    """
    Get the current weather conditions for a city.
    """
    return run_weather_agent(city)

@tool("get_weather_forecast")
def get_weather_forecast(city: str, days: int = 5) -> str:
    """
    Get the weather forecast for a city.
    """
    return run_forecast_agent(city)