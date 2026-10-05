import asyncio
from app.agents.langgraph.weather_agent import run_weather_agent
from app.config import settings

def test_run():
    print(run_weather_agent("noida"))

test_run()
