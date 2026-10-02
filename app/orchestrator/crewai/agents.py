# orchestrator/crewai/agents.py

from crewai import Agent

from .tools import (
    get_current_weather,
    get_weather_forecast,
)

def create_weather_orchestrator() -> Agent:

    return Agent(
        role="Weather Intelligence Orchestrator",

        goal=(
            "Understand the user's weather request and use the "
            "appropriate weather capabilities to provide an accurate response."
        ),

        backstory=(
            "You are an intelligent weather assistant capable of coordinating "
            "specialized weather and forecast agents."
        ),

        tools=[
            get_current_weather,
            get_weather_forecast,
        ],
        verbose=True,
        allow_delegation=False,
    )