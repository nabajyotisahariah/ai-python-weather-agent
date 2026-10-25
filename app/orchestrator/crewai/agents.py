# orchestrator/crewai/agents.py

from crewai import Agent
from collections.abc import Callable

from .tools import (
    create_weather_tools,
    answer_faq_question,
    get_current_weather,
    get_air_quality,
    get_weather_forecast,
)

def create_weather_orchestrator(
    on_city_resolved: Callable[[str], None] | None = None,
) -> Agent:
    tools = (
        [
            get_current_weather,
            get_weather_forecast,
            get_air_quality,
            answer_faq_question,
        ]
        if on_city_resolved is None
        else create_weather_tools(on_city_resolved)
    )

    return Agent(
        role="Weather Intelligence Orchestrator",

        goal=(
            "Understand the user's weather request and use the "
            "appropriate weather capabilities to provide an accurate response."
        ),

        backstory=(
            "You are an intelligent weather assistant capable of coordinating "
            "specialized current-weather, forecast, air-quality, and FAQ agents."
        ),

        tools=tools,
        verbose=True,
        allow_delegation=False,
        max_iter=1,
    )
