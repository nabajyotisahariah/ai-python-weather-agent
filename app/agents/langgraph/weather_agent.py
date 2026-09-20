from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.config import settings
from app.tools.langgraph.weather_tool import get_weather

import logging

logger = logging.getLogger(__name__)

class WeatherState(TypedDict):
    messages: Annotated[list, add_messages]


def _build_graph():
    tools: list[BaseTool] = [get_weather]
    llm = ChatOpenAI(model=settings.openai_api_model, temperature=0)
    llm_with_tools = llm.bind_tools(tools)

    logger.info("LangGraph weather agent initialized with model: %s", settings.openai_api_model)

    def weather_agent(state: WeatherState):
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def should_continue(state: WeatherState):
        if state["messages"][-1].tool_calls:
            return "tools"
        return END

    graph = StateGraph(WeatherState)
    graph.add_node("weather_agent", weather_agent)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "weather_agent")
    graph.add_conditional_edges("weather_agent", should_continue)
    graph.add_edge("tools", "weather_agent")
    return graph.compile()


def run_weather_agent(city: str) -> str:
    """Run the LangGraph weather assistant and return its final response."""
    logger.info("Running LangGraph weather agent for city: %s", city)
    result = _build_graph().invoke(
        {"messages": [HumanMessage(content=f"What is the weather in {city}?")]}
    )
    logger.info("LangGraph weather agent completed for city: %s", city)
    return result["messages"][-1].content