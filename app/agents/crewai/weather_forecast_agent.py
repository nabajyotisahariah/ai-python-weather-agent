from crewai import Agent, Crew, Process, Task

from app.tools.crewai.weather_forecast_tool import get_weather_forecast


def build_weather_forecast_crew(city: str) -> Crew:
    forecast_agent = Agent(
        role="Weather Forecast Assistant",
        goal="Provide accurate and easy-to-understand weather forecast information",
        backstory="""
        You are an expert weather forecast assistant.
        You retrieve weather forecast information
        and explain it clearly to users.
        """,
        tools=[get_weather_forecast],
        verbose=True,
    )
    forecast_task = Task(
        description=f"""
        Get the weather forecast information for {city}.

        Use the get_weather_forecast tool to retrieve the information.

        Provide:
        - Dates
        - Max and Min Temperatures
        - Weather conditions
        """,
        expected_output="""
        A concise weather forecast report containing:
        dates, max and min temperatures, and weather conditions for the upcoming days.
        """,
        agent=forecast_agent,
    )
    return Crew(
        agents=[forecast_agent],
        tasks=[forecast_task],
        process=Process.sequential,
        verbose=True,
    )
