# Use lowercase Python field names and let Pydantic read uppercase environment variables.

from io import StringIO
import logging
import os
from pathlib import Path
import sys

from dotenv import dotenv_values
from pydantic_settings import BaseSettings, SettingsConfigDict
from google.cloud import secretmanager

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

SECRET_NAMES = [
    "OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
]


def load_secrets(project_id):
    client = secretmanager.SecretManagerServiceClient()
    for secret_id in SECRET_NAMES:
        name = (
            f"projects/{project_id}/secrets/"
            f"{secret_id}/versions/latest"
        )

        response = client.access_secret_version(
            request={"name": name}
        )
        os.environ[secret_id] = (
            response.payload.data.decode("UTF-8")
        )
        print(f"Loaded secret: {secret_id} = {os.environ[secret_id]}")

# Prod [ENVIRONMENT=production GOOGLE_CLOUD_PROJECT=workspace-prod-511311 DEPLOY_TYPE=app-engine uvicorn app.main:app]
# Dev [app.main:app --reload]

environment = os.getenv("ENVIRONMENT", "development").lower()
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
DEPLOY_TYPE = os.getenv("DEPLOY_TYPE", "local").lower()

print(f"Environment: {environment} GOOGLE_CLOUD_PROJECT: {GOOGLE_CLOUD_PROJECT} DEPLOY_TYPE: {DEPLOY_TYPE}")

# GCP APP Engine: Load secrets from Secret Manager using google.cloud python library. This is required for production deployment on GCP App Engine.
# GCP Kubernates & Cloud Run: Enviromnment variables & Secrete Keys are automatically injected from Secret Manager. No need to load secrets using google.cloud python library.
# Local Development: Load secrets from .env file using dotenv library. This is required for local development.
if environment == "production" and GOOGLE_CLOUD_PROJECT != "" and DEPLOY_TYPE == "app-engine":
    load_secrets(GOOGLE_CLOUD_PROJECT)


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
    weather_timeout_seconds: float = 6.0
    waqi_api_url: str = "https://api.waqi.info"
    waqi_api_token: str | None = None

    # Redis
    redis_enabled: bool = True
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl_seconds: int = 3600

    # Langfuse
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_base_url: str = "https://cloud.langfuse.com"

     # Vector DB Settings
    vector_store: str = "faiss"
    pinecone_api_key: str | None = None
    pinecone_env: str | None = None
    
    # Paths
    data_dir: str = str(BASE_DIR / "data")
    faq_dir: str = str(BASE_DIR / "data" / "faq")
    prompts_dir: str = str(BASE_DIR / "data" / "prompts")

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
print("Loaded settings for environment: %s", settings)


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
        }
        if settings.redis_enabled:
            required["REDIS_URL"] = settings.redis_url

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
        
    if settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    if settings.google_api_key:
        os.environ["GOOGLE_API_KEY"] = settings.google_api_key



validate_settings()