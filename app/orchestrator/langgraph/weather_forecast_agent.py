from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI

from app.orchestrator.langgraph.agent_graph import build_agent_graph, message_text
from app.tools.langgraph.weather_tool import get_weather_forecast


def build_weather_forecast_delegate(llm: ChatOpenAI) -> BaseTool:
    agent, prompt = build_agent_graph(
        llm,
        [get_weather_forecast],
        (
            "You are the weather-forecast specialist. Retrieve the requested "
            "forecast using the forecast tool. Copy numeric values exactly and "
            "disclose unavailable fields; never guess."
        ),
    )

    @tool("delegate_to_weather_forecast")
    async def delegate_to_weather_forecast(city: str, days: int = 7) -> str:
        """Delegate a forecast request for a city to the forecast specialist."""
        result = await agent.ainvoke(
            {
                "messages": [
                    prompt,
                    HumanMessage(
                        content=f"Get the weather forecast for {city} for {days} days."
                    ),
                ]
            }
        )
        return message_text(result["messages"][-1])

    return delegate_to_weather_forecast
