from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# Resolve base directory path
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    environment: str = "development"

    # OpenAI Settings
    openai_api_key: str | None = None
    openai_api_model: str = "gpt-4o-mini"

    WEATHER_API_URL: str = "https://wttr.in"
    WEATHER_TIMEOUT_SECONDS: float = 10.0

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

#print(settings.model_dump())
