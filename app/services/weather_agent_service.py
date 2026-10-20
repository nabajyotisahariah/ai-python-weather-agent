import logging
import re
from typing import Literal

from app.cache.redis_cache import AsyncRedisCache
from app.config import settings
from app.guardrails.hitl_guardrails import (
    extract_city_answer,
    extract_explicit_city,
    needs_location_clarification,
    requires_action_approval,
)
from app.guardrails.input_guardrails import validate_query
from app.orchestrator.crewai.crew import CrewAIOrchestrator
from app.orchestrator.langgraph.orchestrator import LangGraphOrchestrator
from app.schema.weather import AgentResponse, ClarificationData, Status
from app.services.interface.weather_agent_interface import WeatherAgentInterface

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

    
    async def process_weather_hitl(
        self,
        query: str,
        session_id: str,
        user_id: str,
        clarification_id: str | None = None,
    ) -> AgentResponse:
        """Route weather requests through clarification and action guardrails."""
        query = validate_query(query)
        explicit_city = extract_explicit_city(query)

        if requires_action_approval(query):
            return AgentResponse(
                status=Status.FAIL,
                message=(
                    "Consequential notifications are not supported by this "
                    "service. No action was taken."
                ),
            )

        if clarification_id is not None:
            city = extract_city_answer(query)
            if city is None:
                return AgentResponse(
                    status=Status.PENDING_CLARIFICATION,
                    message="Please reply with the city you want the forecast for.",
                    data=ClarificationData(clarification_id=clarification_id),
                )
            pending_query = (
                await self.crewai_orchestrator.consume_pending_clarification(
                    clarification_id,
                    session_id,
                    user_id,
                )
            )
            if pending_query is None:
                return AgentResponse(
                    status=Status.FAIL,
                    message=(
                        "This clarification is invalid, expired, or belongs "
                        "to a different session."
                    ),
                )
            query = pending_query
            resolved_city = city
        else:
            if explicit_city is not None:
                resolved_city = explicit_city
            elif needs_location_clarification(query, None):
                resolved_city = (
                    await self.crewai_orchestrator.get_resolved_city(
                        session_id,
                        user_id,
                    )
                )
            else:
                resolved_city = None
            if needs_location_clarification(query, resolved_city):
                pending_id = (
                    await self.crewai_orchestrator.create_pending_clarification(
                        query,
                        session_id,
                        user_id,
                    )
                )
                return AgentResponse(
                    status=Status.PENDING_CLARIFICATION,
                    message="Which city would you like the weather forecast for?",
                    data=ClarificationData(clarification_id=pending_id),
                )

        response, cache_key, is_cached = (
            await self.crewai_orchestrator.run_weather_orchestrator_hitl(
                query,
                session_id=session_id,
                user_id=user_id,
                resolved_city=resolved_city,
            )
        )
        if resolved_city and any(
            re.search(rf"\b{term}\b", query.casefold())
            for term in ("weather", "rain", "umbrella", "forecast", "temperature")
        ):
            await self.crewai_orchestrator.set_resolved_city(
                session_id,
                user_id,
                resolved_city,
            )

        return AgentResponse(
            status=Status.SUCCESS,
            message=str(response),
            data=None,
            isCached=is_cached,
            cacheKey=cache_key,
        )
