from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """AI Backend settings. Variables use the AI_BACKEND_ prefix because
    backend/.env is shared with the Core API."""

    APP_NAME: str = "SELVIA AI Backend"
    APP_ENV: str = "development"

    model_config = SettingsConfigDict(
        env_prefix="AI_BACKEND_",
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
