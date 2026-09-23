#use lowercase Python field names and let Pydantic read the uppercase environment variables.

from pathlib import Path
import sys

from pydantic_settings import BaseSettings, SettingsConfigDict
import logging

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


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

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
print("Loaded settings from %s", settings)


def validate_settings() -> None:

    # ---------------------------------------------
    # Development
    # ---------------------------------------------
    print("Validating settings for environment: %s", settings.environment)
    if settings.environment == "development":

        if not ENV_FILE.exists():
            print(f"ERROR: .env file is not present: {ENV_FILE}")
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
        print(
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
        print("ERROR: Missing required configuration:")

        for name in missing:
            print(f"  - {name}")

        sys.exit(1)


validate_settings()