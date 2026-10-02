from crewai import Crew
from redis.asyncio import Redis
#from dotenv import load_dotenv

from app.services.interface.weather_agent_interface import WeatherAgentInterface
from app.orchestrator.crewai.crew import run_weather_orchestrator
from app.config import settings
import logging

from app.schema.weather import AgentResponse
from app.utils.redis_cache import AsyncRedisCache

logger = logging.getLogger(__name__)

class WeatherAgentService(WeatherAgentInterface):

    base_url: str = settings.weather_api_url
    timeout_seconds: float = settings.weather_timeout_seconds

    def __init__(self, redis_client: Redis | None = None) -> None:
        self.cache = AsyncRedisCache(redis_client)

    @staticmethod
    def _report_cache_key(query: str) -> str:
        return f"weather:agent:{query.casefold()}"

    async def _get_cached_report(self, query: str) -> AgentResponse | None:
        cached_report = await self.cache.get(self._report_cache_key(query))
        if cached_report and "status" in cached_report and "message" in cached_report:
            return AgentResponse(
                status=cached_report["status"],
                message=str(cached_report["message"]),
                data=cached_report.get("data"),
                isCached=True,
            )
        return None

    async def _cache_report(self, query: str, report: AgentResponse) -> None:
        await self.cache.set(self._report_cache_key(query), report.model_dump(), ex=3600)

    async def process_weather_query(self, query: str) -> AgentResponse:
        """Process a natural language weather query using the CrewAI agent."""
       
        query_str = query.strip()
        logger.info("Executing process_weather_query with query: %s", query_str)
        
        # Check cache
        cached_report = await self._get_cached_report(query_str)
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
            isCached=False
        )
        
        # Cache the new report
        await self._cache_report(query_str, report)
        
        return report
