import asyncio
import logging

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

from app.config import settings
from app.tools.autogen.weather_tool import get_weather

logger = logging.getLogger(__name__)


async def _run_weather_agent(city: str) -> str:
    model_client = OpenAIChatCompletionClient(
        model=settings.openai_api_model,
        api_key=settings.openai_api_key,
    )
    agent = AssistantAgent(
        name="weather_assistant",
        model_client=model_client,
        tools=[get_weather],
        system_message=(
            "You are a weather assistant. Use the get_weather tool to retrieve "
            "current conditions, then provide a concise report with the city, "
            "temperature, feels-like temperature, humidity, weather condition, "
            "and wind speed."
        ),
    )

    try:
        result = await agent.run(task=f"What is the current weather in {city}?")
        return str(result.messages[-1].content)
    finally:
        await model_client.close()


def run_weather_agent(city: str) -> str:
    """Run the AutoGen weather assistant and return its final response."""
    logger.info("Running AutoGen weather agent for city: %s", city)
    return asyncio.run(_run_weather_agent(city))