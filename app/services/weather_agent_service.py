import logging
import re
from typing import Literal

from app.config import settings
from app.guardrails.input_guardrails import validate_query
from app.orchestrator.crewai.crew import CrewAIOrchestrator
from app.orchestrator.langgraph.orchestrator import LangGraphOrchestrator
from app.schema.weather import AgentResponse, Status
from app.services.interface.weather_agent_interface import WeatherAgentInterface
from app.cache.redis_cache import AsyncRedisCache
from app.guardrails.hitl_guardrails import needs_location_clarification, requires_action_approval

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
            status=Status.SUCCESS,
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
            status=Status.SUCCESS,
            message=str(response),
            data=None,
            isCached=is_cached,
            cacheKey=cache_key,
        )
    
        return report

    
    async def process_weather_hitl(self, query: str, session_id: str, user_id: str) -> AgentResponse:
        """Process a natural language weather query using the CrewAI agent."""

        context = await self.crewai_orchestrator.get_user_context(session_id, user_id)
        print("process_weather_hitl ",context)
        
        #Guardrail check over here
        # 1. Require human authorization for consequential actions.
        if requires_action_approval(query):

            self.crewai_orchestrator.set_user_hitl(query, session_id, user_id);

            return AgentResponse(
                    status=Status.PENDING_CLARIFICATION,
                    message=str("This service is not available."),
                    data=None,
                    isCached=False,
                    cacheKey=None,
                )

        
        # 2. Ask for missing information before invoking agents.
        if needs_location_clarification(query, context):

            await self.crewai_orchestrator.set_user_hitl(query, session_id, user_id);
            
            return AgentResponse(
                    status=Status.PENDING_CLARIFICATION,
                    message=str("I need your location to answer accurately."),
                    data=None,
                    isCached=False,
                    cacheKey=None)
    
        [response, cache_key, is_cached] = await self.crewai_orchestrator.run_weather_orchestrator_hitl(query, session_id=session_id, user_id=user_id)
        
        report = AgentResponse(
            status=Status.SUCCESS,
            message=str(response),
            data=None,
            isCached=is_cached,
            cacheKey=cache_key,
        )
        
        return report
