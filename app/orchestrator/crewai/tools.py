# orchestrator/crewai/tools.py
import logging
from collections.abc import Callable

from crewai import Crew
from crewai.tools import tool

from app.agents.crewai import (
    build_faq_crew,
    build_weather_aqi_crew,
    build_weather_crew,
    build_weather_forecast_crew,
)
from app.guardrails.input_guardrails import validate_query
from app.guardrails.tool_guardrails import validate_tool_call

logger = logging.getLogger(__name__)

def run_weather_agent(city: str) -> str:

    city = validate_query(city)
    
    weather_crew: Crew = build_weather_crew(city)
    
    result = weather_crew.kickoff(
        inputs={"city": city},
    )
    
    print("run_weather_agent ",result)
    return result.raw

def run_forecast_agent(city: str, days: int = 7) -> str:

    city = validate_query(city)
    
    weather_crew: Crew = build_weather_forecast_crew(city, days)
    
    result = weather_crew.kickoff(
        inputs={"city": city},
    )
    return result.raw


def run_air_quality_agent(city: str) -> str:
    city = validate_query(city)
    aqi_crew: Crew = build_weather_aqi_crew(city)
    result = aqi_crew.kickoff(inputs={"city": city})
    return result.raw


def run_faq_agent(question: str) -> str:

    question = validate_query(question)
    
    faq_crew: Crew = build_faq_crew(question)
    
    result = faq_crew.kickoff(
        inputs={"question": question},
    )
    return result.raw


def _get_current_weather(
    city: str,
    on_city_resolved: Callable[[str], None] | None = None,
) -> str:
    
    validate_tool_call("get_weather", {"city": city})
    print("get_current_weather city ", city)

    result = run_weather_agent(city)
    
    if on_city_resolved is not None:
        on_city_resolved(city)
    return result


def _get_weather_forecast(
    city: str,
    days: int = 7,
    on_city_resolved: Callable[[str], None] | None = None,
) -> str:
    validate_tool_call(
        "get_weather_forecast",
        {"city": city, "days": days},
    )
    print("get_weather_forecast city ", city, " days ", days)
    result = run_forecast_agent(city, days)
    if on_city_resolved is not None:
        on_city_resolved(city)
    return result


def _get_air_quality(
    city: str,
    on_city_resolved: Callable[[str], None] | None = None,
) -> str:
    validate_tool_call("get_air_quality", {"city": city})
    result = run_air_quality_agent(city)
    if on_city_resolved is not None:
        on_city_resolved(city)
    return result


@tool("get_current_weather")
def get_current_weather(city: str) -> str:
    """
    Get the current weather conditions for a city.
    """
    return _get_current_weather(city)

@tool("get_weather_forecast")
def get_weather_forecast(city: str, days: int = 7) -> str:
    """
    Get the weather forecast for a city.
    """
    return _get_weather_forecast(city, days)


@tool("get_air_quality")
def get_air_quality(city: str) -> str:
    """Get current air quality information for a city."""
    return _get_air_quality(city)


@tool("answer_faq_question")
def answer_faq_question(question: str) -> str:
    """
    Answer FAQ questions related to weather pricing, subscriptions, and usage.
    """
    validate_tool_call("search_faq", {"query": question})
    print("answer_faq_question question ", question)
    return run_faq_agent(question)


def create_weather_tools(
    on_city_resolved: Callable[[str], None],
):
    @tool("get_current_weather")
    def get_current_weather_for_request(city: str) -> str:
        """Get current weather and remember the city used for this request."""
        return _get_current_weather(city, on_city_resolved)

    @tool("get_weather_forecast")
    def get_weather_forecast_for_request(city: str, days: int = 7) -> str:
        """Get a weather forecast and remember the city used for this request."""
        return _get_weather_forecast(city, days, on_city_resolved)

    @tool("get_air_quality")
    def get_air_quality_for_request(city: str) -> str:
        """Get air quality and remember the city used for this request."""
        return _get_air_quality(city, on_city_resolved)

    return [
        get_current_weather_for_request,
        get_weather_forecast_for_request,
        get_air_quality_for_request,
        answer_faq_question,
    ]
