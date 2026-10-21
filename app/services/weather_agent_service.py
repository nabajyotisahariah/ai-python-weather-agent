import logging
from typing import Literal
from app.config import settings
from app.guardrails.input_guardrails import validate_query
from app.orchestrator.crewai.crew import CrewAIOrchestrator
from app.orchestrator.langgraph.orchestrator import LangGraphOrchestrator
from app.schema.weather import AgentResponse, Status
from app.services.interface.weather_agent_interface import WeatherAgentInterface
from app.cache.redis_cache import AsyncRedisCache
from app.guardrails.hitl_guardrails import detect_consequential_action, needs_location_clarification

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