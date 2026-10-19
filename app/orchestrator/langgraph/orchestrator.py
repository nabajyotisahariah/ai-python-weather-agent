import logging

import httpx
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.config import settings
from app.guardrails.input_guardrails import validate_query
from app.orchestrator.langgraph.agent_graph import AgentState, message_text
from app.orchestrator.langgraph.weather_faq_agent import build_weather_faq_delegate
from app.orchestrator.langgraph.weather_agent import build_current_weather_delegate
from app.orchestrator.langgraph.weather_forecast_agent import (
    build_weather_forecast_delegate,
)
from app.cache.redis_cache import AsyncRedisCache

class LangGraphOrchestrator:

    def __init__(self):
        self.redis = AsyncRedisCache()
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def _build_orchestrator_graph(llm: ChatOpenAI):
        delegation_tools: list[BaseTool] = [
            build_current_weather_delegate(llm),
            build_weather_forecast_delegate(llm),
            build_weather_faq_delegate(llm),
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

    async def run_weather_orchestrator_langgraph(
        self,
        query: str,
    ) -> tuple[str, str, bool]:
        """Run the LangGraph weather supervisor and return its response and cache key."""
        query = validate_query(query)
        cache_key = (
            f"weather:orchestrator:langgraph:"
            f"{query.casefold().replace(' ', '_')}"
        )
        cached_result = await self.redis.get(cache_key)
        if cached_result and isinstance(cached_result.get("raw"), str):
            self.logger.info("LangGraph orchestrator cache hit for query: %s", query)
            return cached_result["raw"], cache_key, True

        self.logger.info("Executing run_weather_orchestrator_langgraph for query: %s", query)
        async with httpx.AsyncClient(
            timeout=settings.weather_timeout_seconds
        ) as http_client:
            llm = ChatOpenAI(
                api_key=settings.openai_api_key,
                model=settings.openai_api_model,
                temperature=0,
                http_async_client=http_client,
            )
            graph = self._build_orchestrator_graph(llm)
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

        response = message_text(result["messages"][-1])
        await self.redis.set(cache_key, {"raw": response}, ex=3600)
        return response, cache_key, False


async def run_weather_orchestrator_langgraph(
    query: str,
) -> tuple[str, str, bool]:
    return await LangGraphOrchestrator().run_weather_orchestrator_langgraph(query)
