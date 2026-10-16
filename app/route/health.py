from fastapi import APIRouter, HTTPException
from app.utils.response import generic_api_response
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/health", summary="Health Check", description="Returns the current health status of the API.", tags=["System"], response_model_exclude_none=True)
async def health_check():
    """
    Health check endpoint to verify the API is running.
    Returns a simple JSON response indicating the health status.
    """
    return {"status": "ok"}

@router.get("/health/redis", summary="Health Check", description="Returns the current health status of the API.", tags=["System"], response_model_exclude_none=True)
async def redis_health_check():
    """
    Health check endpoint to verify the Redis connection.
    Returns a simple JSON response indicating the health status.
    """
    from app.config import settings

    if not settings.redis_enabled:
        return {"status": "disabled"}

    import redis

    try:
        logger.info("Checking Redis connection to %s", settings.redis_url)
        redis_client = redis.Redis.from_url(settings.redis_url)
        if not redis_client.ping():
            return generic_api_response(503, "fail", "Redis is not responding.")

        return {"status": "ok"}
    except redis.exceptions.RedisError as exc:
        logger.error("Error occurred while checking Redis connection: %s", exc)
        return generic_api_response(503, "fail", "Redis connection error.")