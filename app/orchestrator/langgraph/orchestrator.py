import logging
from typing import Annotated, TypedDict

import httpx
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.config import settings
from app.guardrails.input_guardrails import validate_query
from app.tools.langgraph.faq_tool import search_faq
from app.tools.langgraph.weather_tool import get_weather, get_weather_forecast
from app.utils.redis_cache import AsyncRedisCache

logger = logging.getLogger(__name__)
redis_cache = AsyncRedisCache()


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def _message_text(message: BaseMessage) -> str:
    if not isinstance(message.content, str):
        raise TypeError("LangGraph agent returned a non-text response")
    return message.content


def _build_agent_graph(
    llm: ChatOpenAI,
    agent_tools: list[BaseTool],
    system_prompt: str,
):
    llm_with_tools = llm.bind_tools(agent_tools)

    async def agent(state: AgentState) -> dict[str, list[BaseMessage]]:
        response = await llm_with_tools.ainvoke(state["messages"])
        return {"messages": [response]}

    def should_continue(state: AgentState) -> str:
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(agent_tools))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue)
    graph.add_edge("tools", "agent")
    return graph.compile(), SystemMessage(content=system_prompt)


def _build_orchestrator_graph(llm: ChatOpenAI):
    current_weather_agent, current_weather_prompt = _build_agent_graph(
        llm,
        [get_weather],
        (
            "You are the current-weather specialist. Retrieve current conditions "
            "using the weather tool. Copy numeric values exactly and disclose "
            "unavailable fields; never guess."
        ),
    )
    forecast_agent, forecast_prompt = _build_agent_graph(
        llm,
        [get_weather_forecast],
        (
            "You are the weather-forecast specialist. Retrieve the requested "
            "forecast using the forecast tool. Copy numeric values exactly and "
            "disclose unavailable fields; never guess."
        ),
    )
    faq_agent, faq_prompt = _build_agent_graph(
        llm,
        [search_faq],
        (
            "You are the weather FAQ specialist. Use only information returned "
            "by the FAQ search tool. If it does not contain the answer, say so."
        ),
    )

    @tool("delegate_to_current_weather")
    async def delegate_to_current_weather(city: str) -> str:
        """Delegate a current-conditions request for a city to the weather specialist."""
        result = await current_weather_agent.ainvoke(
            {
                "messages": [
                    current_weather_prompt,
                    HumanMessage(content=f"Get current weather for {city}."),
                ]
            }
        )
        return _message_text(result["messages"][-1])

    @tool("delegate_to_weather_forecast")
    async def delegate_to_weather_forecast(city: str, days: int = 7) -> str:
        """Delegate a forecast request for a city to the forecast specialist."""
        result = await forecast_agent.ainvoke(
            {
                "messages": [
                    forecast_prompt,
                    HumanMessage(
                        content=f"Get the weather forecast for {city} for {days} days."
                    ),
                ]
            }
        )
        return _message_text(result["messages"][-1])

    @tool("delegate_to_weather_faq")
    async def delegate_to_weather_faq(question: str) -> str:
        """Delegate an application, pricing, subscription, or usage question to the FAQ specialist."""
        result = await faq_agent.ainvoke(
            {
                "messages": [
                    faq_prompt,
                    HumanMessage(content=question),
                ]
            }
        )
        return _message_text(result["messages"][-1])

    delegation_tools: list[BaseTool] = [
        delegate_to_current_weather,
        delegate_to_weather_forecast,
        delegate_to_weather_faq,
    ]
    supervisor = llm.bind_tools(delegation_tools)

    async def orchestrator(state: AgentState) -> dict[str, list[BaseMessage]]:
        response = await supervisor.ainvoke(state["messages"])
        return {"messages": [response]}

    def should_delegate(state: AgentState) -> str:
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "specialists"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("orchestrator", orchestrator)
    graph.add_node("specialists", ToolNode(delegation_tools))
    graph.add_edge(START, "orchestrator")
    graph.add_conditional_edges("orchestrator", should_delegate)
    graph.add_edge("specialists", "orchestrator")
    return graph.compile()


async def run_weather_orchestrator_langgraph(query: str) -> tuple[str, str]:
    """Run the LangGraph weather supervisor and return its response and cache key."""
    query = validate_query(query)
    cache_key = (
        f"weather:orchestrator:langgraph:"
        f"{query.casefold().replace(' ', '_')}"
    )
    cached_result = await redis_cache.get(cache_key)
    if cached_result and isinstance(cached_result.get("raw"), str):
        logger.info("LangGraph orchestrator cache hit for query: %s", query)
        return cached_result["raw"], cache_key

    logger.info("Executing run_weather_orchestrator_langgraph for query: %s", query)
    async with httpx.AsyncClient(
        timeout=settings.weather_timeout_seconds
    ) as http_client:
        llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model=settings.openai_api_model,
            temperature=0,
            http_async_client=http_client,
        )
        graph = _build_orchestrator_graph(llm)
        result = await graph.ainvoke(
            {
                "messages": [
                    SystemMessage(
                        content=(
                            "You are the weather intelligence supervisor. Delegate "
                            "current conditions, forecasts, and Weather application "
                            "FAQ questions to the matching specialist. Use every "
                            "specialist needed for a combined request, then combine "
                            "their findings into one concise response. Do not invent "
                            "facts or alter numeric weather values."
                        )
                    ),
                    HumanMessage(content=query),
                ]
            }
        )

    response = _message_text(result["messages"][-1])
    await redis_cache.set(cache_key, {"raw": response}, ex=3600)
    return response, cache_key
