# orchestrator/crewai/tasks.py

from crewai import Task


def create_weather_task(agent, query: str) -> Task:

    return Task(
        description=f"""
        Analyze the following user request:

        {query}

        Determine which weather capabilities are required.

        If the user asks for current weather, use the current weather
        capability.

        If the user asks for forecast, use the forecast capability.

        If the user asks for both, use both capabilities.

        Combine the results into one clear response.
        """,

        expected_output="""
        A concise and accurate weather response containing all
        information requested by the user.
        """,

        agent=agent,
    )