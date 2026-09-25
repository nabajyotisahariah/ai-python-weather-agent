# Use lowercase Python field names and let Pydantic read uppercase environment variables.

from io import StringIO
import logging
import os
from pathlib import Path
import sys

from dotenv import dotenv_values
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
DEFAULT_SECRET_NAME = (
    "projects/1040682241529/secrets/"
    "python-ai-weather-application/versions/latest"
)


def get_secret(secret_name: str) -> str:
    """Read a secret version from Google Secret Manager."""
    from google.cloud import secretmanager

    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(request={"name": secret_name})
    return response.payload.data.decode("UTF-8")


def load_production_secrets() -> None:
    """Load dotenv-style production secrets into the process environment."""
    secret_name = os.getenv("GCP_SECRET_NAME", DEFAULT_SECRET_NAME)
    secret_data = get_secret(secret_name)
    secret_values = dotenv_values(stream=StringIO(secret_data))
    #logger.info("Production secrets loaded successfully. Keys: %s",list(secret_values.keys()))
    print("Production secrets loaded successfully. Keys:", secret_values)
    for name, value in secret_values.items():
        if value is not None:
            os.environ.setdefault(name, value)

    logger.info("Loaded production configuration from Secret Manager")


environment = os.getenv(
    "ENVIRONMENT",
    dotenv_values(ENV_FILE).get("environment", "development"),
).lower()
logger.info(f"Environment: {environment}")

if environment == "production":
    load_production_secrets()


class Settings(BaseSettings):

    environment: str = "development"

    # OpenAI
    openai_api_key: str | None = None
    openai_api_model: str = "gpt-4o-mini"

    # Google
    google_api_key: str | None = None
    google_adk_model: str = "gemini-2.0-flash"

    # Weather
    weather_api_url: str = "https://wttr.in"
    weather_timeout_seconds: float = 10.0

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl_seconds: int = 3600

    # Langfuse
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_base_url: str = "https://cloud.langfuse.com"

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
logger.info("Loaded settings for environment: %s", settings.environment)


def validate_settings() -> None:

    # ---------------------------------------------
    # Development
    # ---------------------------------------------
    logger.info("Validating settings for environment: %s", settings.environment)
    if settings.environment == "development":

        if not ENV_FILE.exists():
            logger.error(f"ERROR: .env file is not present: {ENV_FILE}")
            sys.exit(1)

        required = {
            "OPENAI_API_KEY": settings.openai_api_key,
        }

    # ---------------------------------------------
    # Production
    # ---------------------------------------------
    elif settings.environment == "production":

        # .env is NOT required.
        #
        # Values must come from:
        #
        # GCP Secret Manager
        #       ↓
        # Kubernetes
        #       ↓
        # Environment variables

        required = {
            "OPENAI_API_KEY": settings.openai_api_key,
            "GOOGLE_API_KEY": settings.google_api_key,
            "REDIS_URL": settings.redis_url,
        }

    else:
        logger.error(
            f"ERROR: Unsupported environment: "
            f"{settings.environment}"
        )
        sys.exit(1)

    missing = [
        name
        for name, value in required.items()
        if value is None or (
            isinstance(value, str) and not value.strip()
        )
    ]

    if missing:
        logger.error("ERROR: Missing required configuration:")

        for name in missing:
            logger.error(f"  - {name}")

        sys.exit(1)


validate_settings()