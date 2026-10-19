import logging
import re
from typing import Literal

from app.config import settings
from app.guardrails.input_guardrails import validate_query
from app.orchestrator.crewai.crew import CrewAIOrchestrator
from app.orchestrator.langgraph.orchestrator import LangGraphOrchestrator
from app.schema.weather import AgentResponse
from app.services.interface.weather_agent_interface import WeatherAgentInterface
from app.cache.redis_cache import AsyncRedisCache

AgentProvider = Literal["crewai", "langgraph"]

class WeatherAgentService(WeatherAgentInterface):

    base_url: str = settings.weather_api_url
    timeout_seconds: float = settings.weather_timeout_seconds

    def __init__(self) -> None:
        self.cache = AsyncRedisCache()
        self.logger = logging.getLogger(__name__)
        self.crewai_orchestrator = CrewAIOrchestrator()
        self.langgraph_orchestrator = LangGraphOrchestrator()

    async def process_weather_query(self, query: str, session_id: str, user_id: str) -> AgentResponse:
        """Process a natural language weather query using the CrewAI agent."""

        [response, cache_key, is_cached] = await self.crewai_orchestrator.run_weather_orchestrator(query, session_id=session_id, user_id=user_id)
        
        report = AgentResponse(
            status="success",
            message=str(response),
            data=None,
            isCached=is_cached,
            cacheKey=cache_key,
        )
        
        return report

    async def process_weather_langgraph_query(self, query: str) -> AgentResponse:
        """Process a natural language weather query using LangGraph specialist agents."""
        query_str = validate_query(query)
        self.logger.info("Executing process_weather_langgraph_query with query: %s", query_str)
        
        # Call orchestrator if not cached
        self.logger.info("Cache miss for query: %s. Fetching from orchestrator.", query_str)
        [response, cache_key, is_cached] = await self.langgraph_orchestrator.run_weather_orchestrator_langgraph(query_str)
        
        report = AgentResponse(
            status="success",
            message=str(response),
            data=None,
            isCached=is_cached,
            cacheKey=cache_key,
        )
    
        return report