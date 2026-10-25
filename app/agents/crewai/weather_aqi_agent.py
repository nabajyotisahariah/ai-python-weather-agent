from crewai import Agent, Crew, Process, Task

from app.guardrails.input_guardrails import validate_query
from app.tools.crewai.weather_aqi_tool import get_air_quality


def build_weather_aqi_crew(city: str) -> Crew:
    city = validate_query(city)
    aqi_agent = Agent(
        role="Air Quality Assistant",
        goal="Provide accurate air quality information for a city",
        backstory=(
            "You are an air quality specialist. You retrieve current AQI "
            "and pollutant readings from the WAQI provider and explain them clearly."
        ),
        tools=[get_air_quality],
        verbose=True,
        max_iter=1,
    )
    aqi_task = Task(
        description=f"""
        Get the current air quality information for {city}.

        Use the get_air_quality tool to retrieve the provider data.
        Report the AQI, dominant pollutant, available pollutant readings,
        and observation time when returned. Copy every value exactly.
        Do not estimate or infer missing values.
        """,
        expected_output=(
            "A concise air quality report containing the provider's AQI and "
            "any available pollutant readings."
        ),
        agent=aqi_agent,
    )
    return Crew(
        agents=[aqi_agent],
        tasks=[aqi_task],
        process=Process.sequential,
        verbose=True,
    )
