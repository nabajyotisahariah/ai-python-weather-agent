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
from app.cache.semantic_cache import SemanticCache
from app.guardrails.hitl_guardrails import detect_consequential_action, needs_location_clarification

AgentProvider = Literal["crewai", "langgraph"]

_LOCATION_QUERY_PATTERN = re.compile(
    r"\b(?:in|at|near|for|of)\s+([\w.'-]+(?:\s+[\w.'-]+)?)",
    re.IGNORECASE,
)
_LOCATION_SUFFIXES = {
    "for",
    "right",
    "now",
    "today",
    "tomorrow",
    "tonight",
    "currently",
}
_WEATHER_QUERY_PATTERN = re.compile(
    r"\b(?:weather|rain(?:y|ing|fall)?|umbrella|forecast|temperatures?|"
    r"jackets?|coats?|snow(?:y|ing)?|sunny|hot|cold|wind(?:y|s)?|"
    r"storm(?:y|s)?|cloud(?:y|s)?|aqi|air quality|pollution|pollutant|smog)\b",
    re.IGNORECASE,
)
_AIR_QUALITY_PATTERN = re.compile(
    r"\b(?:aqi|air quality|pollution|pollutant|smog)\b",
    re.IGNORECASE,
)
_FORECAST_PATTERN = re.compile(
    r"\b(?:forecast|tomorrow|tonight|coming days|this week|will\s+(?:it|there)|"
    r"next\s+\d*\s*(?:days?|weeks?))\b",
    re.IGNORECASE,
)


def _semantic_cache_dimensions(query: str) -> tuple[str, str] | None:
    if _WEATHER_QUERY_PATTERN.search(query) is None:
        return None

    if _AIR_QUALITY_PATTERN.search(query) is not None:
        return "air_quality", "current"

    if _FORECAST_PATTERN.search(query) is not None:
        return "weather_forecast", "forecast"

    return "current_weather", "current"


def _query_matches_resolved_city(query: str, resolved_city: str) -> bool:
    match = _LOCATION_QUERY_PATTERN.search(query)
    if match is None:
        return True

    location_parts = match.group(1).casefold().split()
    while location_parts and location_parts[-1] in _LOCATION_SUFFIXES:
        location_parts.pop()

    return " ".join(location_parts) == resolved_city.casefold().strip()


class WeatherAgentService(WeatherAgentInterface):

    base_url: str = settings.weather_api_url
    timeout_seconds: float = settings.weather_timeout_seconds

    def __init__(self) -> None:
        self.cache = AsyncRedisCache()
        self.semantic_cache = SemanticCache()
        self.logger = logging.getLogger(__name__)
        self.crewai_orchestrator = CrewAIOrchestrator()
        self.langgraph_orchestrator = LangGraphOrchestrator()
        self._semantic_cache_initialized = False

    async def _initialize_semantic_cache(self) -> None:
        if self._semantic_cache_initialized:
            return

        await self.semantic_cache.initialize_semantic_cache()
        self._semantic_cache_initialized = True

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
    ) -> AgentResponse:

        query = validate_query(query)

        #Caching Keys:
        # weather:context:{session_id}:{user_id}    - Session & User specific context history
        # weather:approval:{approval_id}            - Pending approval for consequential actions
        # weather:location:{session_id}:{user_id}   - location information for the user (resolved city)

        resolved_city = await self.crewai_orchestrator.get_resolved_city(
            session_id,
            user_id,
        )
        self.logger.info("process_weather_hitl resolved_city %s",resolved_city)

        # 2. Check for consequential actions.
        #Ex: Please broadcast an alert to all users about the weather warning
        action_intent = detect_consequential_action(query)      #action: broadcast_alert or bulk_notification
        self.logger.info("process_weather_hitl action_intent %s", action_intent)

        if action_intent:
            approval = await self.crewai_orchestrator.create_pending(
                session_id=session_id,
                user_id=user_id,
                action=action_intent.action,
                payload={"query": query},
            )

            return AgentResponse(
                status=Status.PENDING_APPROVAL,
                message="Raised a pending approval for the action: {}".format(action_intent.action),
                data={"approval_id": approval["approval_id"]},
                isCached=False,
                cacheKey=None,
            )

        # 3. Ask for missing location information.
        #Ex: "What's the weather like?" or "Will it rain tomorrow?" or "Do I need an umbrella?"
        #    "Should I wear a jacket"
        if needs_location_clarification(query, resolved_city=resolved_city):

            clarification_msg = "Which city would you like the weather forecast for?"
            await self.crewai_orchestrator.set_user_hitl(query, clarification_msg, session_id, user_id)

            return AgentResponse(
                status=Status.PENDING_CLARIFICATION,
                message=clarification_msg,
                data=None,
                isCached=False,
                cacheKey=None,
            )

        # 4. Execute only after the checks have passed.
        response, cache_key, is_cached = (
            await self.crewai_orchestrator.run_weather_orchestrator_hitl(
                query,
                session_id=session_id,
                user_id=user_id,
            )
        )

        return AgentResponse(
            status=Status.SUCCESS,
            message=str(response),
            data=None,
            isCached=is_cached,
            cacheKey=cache_key,
        )

    async def process_weather_hitl_semantic(
        self,
        query: str,
        session_id: str,
        user_id: str,
    ) -> AgentResponse:
        print("process_weather_hitl_semantic query: ", query)

        query = validate_query(query)
        resolved_city = await self.crewai_orchestrator.get_resolved_city(
            session_id,
            user_id,
        )
        self.logger.info(
            "process_weather_hitl_semantic resolved_city %s",
            resolved_city,
        )

        action_intent = detect_consequential_action(query) #broadcast_alert, bulk_notification
        if action_intent:
            approval = await self.crewai_orchestrator.create_pending(
                session_id=session_id,
                user_id=user_id,
                action=action_intent.action,
                payload={"query": query},
            )
            return AgentResponse(
                status=Status.PENDING_APPROVAL,
                message=(
                    "Raised a pending approval for the action: "
                    f"{action_intent.action}"
                ),
                data={"approval_id": approval["approval_id"]},
                isCached=False,
                cacheKey=None,
            )

        if needs_location_clarification(query, resolved_city=resolved_city):
            clarification_msg = (
                "Which city would you like the weather forecast for?"
            )
            await self.crewai_orchestrator.set_user_hitl(
                query,
                clarification_msg,
                session_id,
                user_id,
            )
            return AgentResponse(
                status=Status.PENDING_CLARIFICATION,
                message=clarification_msg,
                data=None,
                isCached=False,
                cacheKey=None,
            )

        cache_dimensions = _semantic_cache_dimensions(query)
        print("process_weather_hitl_semantic cache_dimensions: ", cache_dimensions)

        location_matches = (
            resolved_city is not None
            and _query_matches_resolved_city(query, resolved_city)
        )
        print("process_weather_hitl_semantic location_matches: ", location_matches," resolved_city ",resolved_city  )

        if (
            cache_dimensions is not None
            and resolved_city is not None
            and location_matches
        ):
            await self._initialize_semantic_cache()
            intent, scope = cache_dimensions
            cached_response = await self.semantic_cache.get_semantic_cache(
                query,
                intent=intent,
                location=resolved_city,
                scope=scope,
            )
            if cached_response is not None:
                await self.crewai_orchestrator.set_user_hitl(
                    query,
                    cached_response,
                    session_id,
                    user_id,
                )
                return AgentResponse(
                    status=Status.SUCCESS,
                    message=cached_response,
                    data=None,
                    isCached=True,
                    cacheKey=None,
                )

        response, cache_key, is_cached = (
            await self.crewai_orchestrator.run_weather_orchestrator_hitl(
                query,
                session_id=session_id,
                user_id=user_id,
            )
        )

        if cache_dimensions is not None:
            cache_city = await self.crewai_orchestrator.get_resolved_city(
                session_id,
                user_id,
            )
            if (
                cache_city is not None
                and _query_matches_resolved_city(query, cache_city)
            ):
                await self._initialize_semantic_cache()
                intent, scope = cache_dimensions
                await self.semantic_cache.set_semantic_cache(
                    query,
                    str(response),
                    intent=intent,
                    location=cache_city,
                    scope=scope,
                )

        return AgentResponse(
            status=Status.SUCCESS,
            message=str(response),
            data=None,
            isCached=is_cached,
            cacheKey=cache_key,
        )