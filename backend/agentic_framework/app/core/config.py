from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/agentic_framework/.env (only the AI Backend's own file; the Core API has a separate one)
AI_BACKEND_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """AI Backend settings, read from variables with the AI_BACKEND_ prefix."""

    APP_NAME: str = "SELVIA AI Backend"
    APP_ENV: str = "development"

    model_config = SettingsConfigDict(
        env_prefix="AI_BACKEND_",
        env_file=AI_BACKEND_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
