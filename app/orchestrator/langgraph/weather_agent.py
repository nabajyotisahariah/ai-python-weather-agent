from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI

from app.orchestrator.langgraph.agent_graph import build_agent_graph, message_text
from app.tools.langgraph.weather_tool import get_weather


def build_current_weather_delegate(llm: ChatOpenAI) -> BaseTool:
    agent, prompt = build_agent_graph(
        llm,
        [get_weather],
        (
            "You are the current-weather specialist. Retrieve current conditions "
            "using the weather tool. Copy numeric values exactly and disclose "
            "unavailable fields; never guess."
        ),
    )

    @tool("delegate_to_current_weather")
    async def delegate_to_current_weather(city: str) -> str:
        """Delegate a current-conditions request for a city to the weather specialist."""
        result = await agent.ainvoke(
            {
                "messages": [
                    prompt,
                    HumanMessage(content=f"Get current weather for {city}."),
                ]
            }
        )
        return message_text(result["messages"][-1])

    return delegate_to_current_weather
