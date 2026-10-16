from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/agentic_framework/.env (only the AI Backend's own file; the Core API has a separate one)
AI_BACKEND_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# Shared with Core API (env name AI_BACKEND_INTERNAL_TOKEN). No default real secret.
MIN_INTERNAL_TOKEN_LENGTH = 32


class Settings(BaseSettings):
    """AI Backend settings, read from variables with the AI_BACKEND_ prefix."""

    APP_NAME: str = "SELVIA AI Backend"
    APP_ENV: str = "development"

    # Core API → AI Backend shared service credential (Bearer). Not Keycloak / tutor tokens.
    INTERNAL_TOKEN: Optional[str] = None

    # Platform MCP resource URL for the Adaptive Tutor (env: AI_BACKEND_TUTOR_MCP_URL).
    # Must match the platform MCP_RESOURCE_URL / tutor-token audience. Unset = fail closed.
    TUTOR_MCP_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_prefix="AI_BACKEND_",
        env_file=AI_BACKEND_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("INTERNAL_TOKEN", "TUTOR_MCP_URL", mode="before")
    @classmethod
    def blank_token_is_unset(cls, value: Optional[str]) -> Optional[str]:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def internal_service_auth_configured(self) -> bool:
        token = self.INTERNAL_TOKEN
        return bool(token and len(token) >= MIN_INTERNAL_TOKEN_LENGTH)

    @property
    def tutor_mcp_configured(self) -> bool:
        return bool(self.TUTOR_MCP_URL)


settings = Settings()
