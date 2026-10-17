from pathlib import Path
from typing import Optional

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/agentic_framework/.env (only the AI Backend's own file; the Core API has a separate one)
AI_BACKEND_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# Shared with Core API (env name AI_BACKEND_INTERNAL_TOKEN). No default real secret.
MIN_INTERNAL_TOKEN_LENGTH = 32

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


class Settings(BaseSettings):
    """AI Backend settings.

    Prefixed vars use ``AI_BACKEND_``. Neo4j and OpenAI also accept unprefixed names
    matching the local ``.env`` conventions (``NEO4J_*``, ``OPENAI_API_KEY``).
    """

    APP_NAME: str = "SELVIA AI Backend"
    APP_ENV: str = "development"

    # Core API → AI Backend shared service credential (Bearer). Not Keycloak / tutor tokens.
    INTERNAL_TOKEN: Optional[str] = None

    # Platform MCP resource URL for the Adaptive Tutor (env: AI_BACKEND_TUTOR_MCP_URL).
    # Must match the platform MCP_RESOURCE_URL / tutor-token audience. Unset = fail closed.
    TUTOR_MCP_URL: Optional[str] = None

    NEO4J_URI: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("AI_BACKEND_NEO4J_URI", "NEO4J_URI"),
    )
    NEO4J_USERNAME: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("AI_BACKEND_NEO4J_USERNAME", "NEO4J_USERNAME"),
    )
    NEO4J_PASSWORD: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("AI_BACKEND_NEO4J_PASSWORD", "NEO4J_PASSWORD"),
    )
    NEO4J_DATABASE: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("AI_BACKEND_NEO4J_DATABASE", "NEO4J_DATABASE"),
    )

    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("AI_BACKEND_OPENAI_API_KEY", "OPENAI_API_KEY"),
    )
    OPENAI_MODEL: str = Field(
        default=DEFAULT_OPENAI_MODEL,
        validation_alias=AliasChoices("AI_BACKEND_OPENAI_MODEL", "OPENAI_MODEL"),
    )

    model_config = SettingsConfigDict(
        env_prefix="AI_BACKEND_",
        env_file=AI_BACKEND_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator(
        "INTERNAL_TOKEN",
        "TUTOR_MCP_URL",
        "NEO4J_URI",
        "NEO4J_USERNAME",
        "NEO4J_PASSWORD",
        "NEO4J_DATABASE",
        "OPENAI_API_KEY",
        mode="before",
    )
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

    @property
    def neo4j_configured(self) -> bool:
        return bool(
            self.NEO4J_URI
            and self.NEO4J_USERNAME
            and self.NEO4J_PASSWORD
            and self.NEO4J_DATABASE
        )

    @property
    def openai_configured(self) -> bool:
        return bool(self.OPENAI_API_KEY)


settings = Settings()
