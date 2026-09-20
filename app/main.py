from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.route import health, weather
import logging
from app.utils.logger import setup_logging
from app.config import settings

# Setup structured logging
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Weather Assistant API",
    description="Weather Assistant API provides current weather information for specified cities using the get_weather tool.",
    version="0.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info(f"Initializing API routes")
logger.info(f"Environment: {settings.environment}")
logger.info(f"OpenAI Model: {settings.openai_api_model}")

# Include Routers
app.include_router(weather.router, prefix="/api/v1", tags=["Weather"])
app.include_router(health.router, prefix="/api/v1", tags=["System"])
