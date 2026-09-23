import asyncio
import logging
import os

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.config import settings
from app.tools.autogen.weather_tool import get_weather

logger = logging.getLogger(__name__)

APP_NAME = "weather_application"
USER_ID = "weather_user"


def _build_agent() -> Agent:
    if settings.google_api_key:
        os.environ.setdefault("GOOGLE_API_KEY", settings.google_api_key)

    return Agent(
        name="weather_assistant",
        model=settings.google_adk_model,
        instruction=(
            "You are a weather assistant. Use the get_weather tool to retrieve "
            "current conditions, then provide a concise report with the city, "
            "temperature, feels-like temperature, humidity, weather condition, "
            "and wind speed."
        ),
        tools=[get_weather],
    )


async def _run_weather_agent(city: str) -> str:
    try:
        session_service = InMemorySessionService()
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
        )
        runner = Runner(
            app_name=APP_NAME,
            agent=_build_agent(),
            session_service=session_service,
        )
        message = types.Content(
            role="user",
            parts=[types.Part(text=f"What is the current weather in {city}?")],
        )

        final_text = ""
        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=session.id,
            new_message=message,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_text = event.content.parts[0].text or final_text

        if not final_text:
            raise RuntimeError("Google ADK returned an empty response")
        return final_text
    except Exception as exc:
        logger.exception("Google ADK weather agent failed for city: %s", city)
        raise RuntimeError(f"Google ADK weather agent failed for city: {city}") from exc


def run_weather_agent(city: str) -> str:
    """Run the Google ADK weather assistant and return its final response."""
    logger.info("Running Google ADK weather agent for city: %s", city)
    try:
        return asyncio.run(_run_weather_agent(city))
    except Exception as exc:
        logger.exception("Google ADK weather agent crashed for city: %s", city)
        raise RuntimeError(f"Google ADK weather agent failed for city: {city}") from exc
