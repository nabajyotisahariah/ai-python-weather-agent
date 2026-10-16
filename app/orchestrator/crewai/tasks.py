# orchestrator/crewai/tasks.py

from crewai import Task


def create_weather_task(agent, query: str) -> Task:

    return Task(
        description=f"""
        Analyze the following user request:

        {query}

        Determine which weather or FAQ capabilities are required.

        If the user asks for current weather, use the current weather
        capability.

        If the user asks for forecast, use the forecast capability.

        If the user asks a general question about the application, pricing,
        subscriptions, or usage, use the FAQ capability.

        Combine the results into one clear response.
        Use only facts returned by the selected tools. Copy numeric weather
        values exactly, and disclose when requested data is unavailable.
        """,

        expected_output="""
        A concise and accurate response containing all
        information requested by the user.
        """,

        agent=agent,
    )
