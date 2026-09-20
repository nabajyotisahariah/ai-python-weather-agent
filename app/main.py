import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import uvicorn
from app.utils.logger import setup_logging
from app.config import settings

setup_logging()
logging.info("Starting Weather Assistant API")

from app.route import health, weather

app = FastAPI(
    title="Weather Assistant API",
    description="Weather Assistant API provides current weather information for specified cities using the get_weather tool.",
    version="0.1.0"
)


@app.exception_handler(Exception)
async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
    """Return a safe response for unexpected application errors."""
    logging.getLogger(__name__).exception(
        "Unhandled application error while processing %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"status": "fail", "message": "Internal server error"},
    )

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.info("Initializing API routes")
logging.info("Environment: %s", settings.environment)
logging.info("OpenAI Model: %s", settings.openai_api_model)

# Include Routers
app.include_router(weather.router, prefix="/api/v1", tags=["Weather"])
app.include_router(health.router, prefix="/api/v1", tags=["System"])


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
