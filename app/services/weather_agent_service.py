import logging
import re
from typing import Literal

from app.config import settings
from app.guardrails.input_guardrails import validate_query
from app.orchestrator.crewai.crew import run_weather_orchestrator
from app.orchestrator.langgraph.orchestrator import run_weather_orchestrator_langgraph
from app.schema.weather import AgentResponse
from app.services.interface.weather_agent_interface import WeatherAgentInterface
from app.cache.redis_cache import AsyncRedisCache

logger = logging.getLogger(__name__)
AgentProvider = Literal["crewai", "langgraph"]

class WeatherAgentService(WeatherAgentInterface):

    base_url: str = settings.weather_api_url
    timeout_seconds: float = settings.weather_timeout_seconds

    def __init__(self) -> None:
        self.cache = AsyncRedisCache()

    @staticmethod
    def _report_cache_key(query: str, provider: AgentProvider) -> str:
        normalized_query = re.sub(r"[^a-z0-9]+", "-", query.casefold()).strip("-")
        return f"weather:agent:{provider}:{normalized_query}"

    async def _get_cached_report(
        self,
        query: str,
        provider: AgentProvider,
    ) -> AgentResponse | None:
        cache_key = self._report_cache_key(query, provider)
        cached_report = await self.cache.get(cache_key)
        if cached_report and "status" in cached_report and "message" in cached_report:
            return AgentResponse(
                status=cached_report["status"],
                message=str(cached_report["message"]),
                data=cached_report.get("data"),
                isCached=True,
                cacheKey=cached_report.get("cacheKey", cache_key),
            )
        return None

    async def _cache_report(
        self,
        query: str,
        report: AgentResponse,
        provider: AgentProvider,
    ) -> None:
        await self.cache.set(
            self._report_cache_key(query, provider),
            report.model_dump(),
            ex=3600,
        )

    async def process_weather_query(self, query: str) -> AgentResponse:
        """Process a natural language weather query using the CrewAI agent."""
        query_str = validate_query(query)
        logger.info("Executing process_weather_query with query: %s", query_str)
        
        # Check cache
        cached_report = await self._get_cached_report(query_str, "crewai")
        if cached_report:
            logger.info("Cache hit for query: %s", query_str)
            return cached_report

        # Call orchestrator if not cached
        logger.info("Cache miss for query: %s. Fetching from orchestrator.", query_str)
        response = await run_weather_orchestrator(query_str)
        
        report = AgentResponse(
            status="success",
            message=str(response),
            data=None,
            isCached=False,
            cacheKey=self._report_cache_key(query_str, "crewai"),
        )
        
        # Cache the new report
        await self._cache_report(query_str, report, "crewai")
        
        return report

    async def process_weather_langgraph_query(self, query: str) -> AgentResponse:
        """Process a natural language weather query using LangGraph specialist agents."""
        query_str = validate_query(query)
        logger.info("Executing process_weather_langgraph_query with query: %s", query_str)
        
        # Check cache
        cached_report = await self._get_cached_report(query_str, "langgraph")
        if cached_report:
            logger.info("Cache hit for query: %s", query_str)
            return cached_report

        # Call orchestrator if not cached
        logger.info("Cache miss for query: %s. Fetching from orchestrator.", query_str)
        response, cache_key = await run_weather_orchestrator_langgraph(query_str)
        
        report = AgentResponse(
            status="success",
            message=str(response),
            data=None,
            isCached=False,
            cacheKey=cache_key,
        )
        
        # Cache the new report
        await self._cache_report(query_str, report, "langgraph")
        
        return report