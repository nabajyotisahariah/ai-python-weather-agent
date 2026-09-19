from crewai import Agent, Task, Crew, Process
from app.tools.crewai.weather_tool import get_weather


weather_agent = Agent(
    role="Weather Assistant",

    goal="Provide accurate and easy-to-understand weather information",

    backstory="""
    You are an expert weather assistant.
    You retrieve current weather information
    and explain it clearly to users.
    """,

    tools=[get_weather],

    verbose=True
)


weather_task = Task(
    description="""
    Get the current weather information for Delhi.

    Use the get_weather tool to retrieve the information.

    Provide:
    - Temperature
    - Feels-like temperature
    - Humidity
    - Weather condition
    - Wind speed
    """,

    expected_output="""
    A concise weather report containing:
    city, temperature, feels-like temperature,
    humidity, weather condition, and wind speed.
    """,

    agent=weather_agent
)


weather_crew = Crew(
    agents=[weather_agent],

    tasks=[weather_task],

    process=Process.sequential,

    verbose=True
)


result = weather_crew.kickoff()

print("\nWeather Result:")
print(result)