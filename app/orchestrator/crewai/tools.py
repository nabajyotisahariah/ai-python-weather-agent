# orchestrator/crewai/tools.py
import logging
from crewai import Crew
from crewai.tools import tool

from app.agents.crewai import build_weather_crew
from app.agents.crewai.weather_forecast_agent import build_weather_forecast_crew

logger = logging.getLogger(__name__)

def run_weather_agent(city: str) -> str:
    weather_crew: Crew = build_weather_crew(city)
    result = weather_crew.kickoff(
        inputs={"city": city},
    )
    print("run_weather_agent ",result)
    return result.raw

def run_forecast_agent(city: str, days: int = 7) -> str:
    weather_crew: Crew = build_weather_forecast_crew(city, days)
    result = weather_crew.kickoff(
        inputs={"city": city},
    )
    return result.raw

@tool("get_current_weather")
def get_current_weather(city: str) -> str:
    """
    Get the current weather conditions for a city.
    """
    print("get_current_weather city ",city)
    return run_weather_agent(city)

@tool("get_weather_forecast")
def get_weather_forecast(city: str, days: int = 7) -> str:
    """
    Get the weather forecast for a city.
    """
    print("get_weather_forecast city ",city, " days ",days)
    return run_forecast_agent(city, days)