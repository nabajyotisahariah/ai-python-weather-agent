from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.utils.logger import setup_logging
from app.config import settings

logger = setup_logging()
logger.info("Starting Weather Assistant API")

from app.route import health, weather

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

logger.info("Initializing API routes")
logger.info("Environment: %s", settings.environment)
logger.info("OpenAI Model: %s", settings.openai_api_model)

# Include Routers
app.include_router(weather.router, prefix="/api/v1", tags=["Weather"])
app.include_router(health.router, prefix="/api/v1", tags=["System"])
