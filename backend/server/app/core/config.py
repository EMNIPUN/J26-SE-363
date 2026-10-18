from pathlib import Path
from typing import Literal, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/server/.env (only the Core API's own file; the AI Backend has a separate one)
SERVER_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Application settings for the SELVIA Server backend.
    
    Zero hardcoded credentials: all database URLs, usernames, passwords,
    and secrets must be provided via environment variables.
    """
    APP_NAME: str = "SELVIA Server"
    APP_ENV: str = "development"
    DEBUG: bool = False
    # HTTP listen port for uvicorn (local default 8020; avoids clashing with Kong/Keycloak on 8000).
    PORT: int = 8020

    # Server Database Configuration
    # Accepts a full connection URL or discrete connection parameters from environment.
    # Supabase Transaction Pooler (Port 6543); Supabase URLs must use verify-full (app/database/safety.py):
    #   postgresql+psycopg://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=verify-full&sslrootcert=../certs/supabase-ca.crt
    # Local Docker PostgreSQL:
    #   postgresql+psycopg://[USER]:[PASSWORD]@[HOST]:[PORT]/[DB]
    SERVER_DATABASE_URL: Optional[str] = None
    SERVER_DIRECT_URL: Optional[str] = None

    # Individual database parameters (used if SERVER_DATABASE_URL is not set directly)
    SERVER_POSTGRES_USER: Optional[str] = None
    SERVER_POSTGRES_PASSWORD: Optional[str] = None
    SERVER_POSTGRES_HOST: Optional[str] = None
    SERVER_POSTGRES_PORT: Optional[int] = None
    SERVER_POSTGRES_DB: Optional[str] = None

    # Supabase Cloud Project Settings (Optional for storage/buckets)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_BUCKET_RUBRICS: str = "project-rubrics"

    # Keycloak IAM Configuration
    # Public URL of Keycloak behind Kong; tokens are issued for
    # {KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}.
    KEYCLOAK_SERVER_URL: str = "http://localhost:8000/auth"
    KEYCLOAK_REALM: str = "mentor"
    KEYCLOAK_CLIENT_ID: Optional[str] = None
    KEYCLOAK_CLIENT_SECRET: Optional[str] = None
    # Override when the server must fetch keys from a different (internal) URL
    # than the public issuer, e.g. http://keycloak:8080/auth/realms/mentor/protocol/openid-connect/certs
    KEYCLOAK_JWKS_URL: Optional[str] = None
    # Clients whose access tokens the Core API accepts (token claim `azp`), as a JSON list.
    KEYCLOAK_ALLOWED_CLIENTS: list[str] = ["mentor-frontend"]

    # Browser origins allowed to call the Core API, as a JSON list.
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Email (invitations and notifications; Keycloak sends its own verification and reset mail,
    # configured separately in the realm, see docker/keycloak/README.md).
    # "console" only logs messages, which is enough for development. "smtp" delivers them
    # through any SMTP provider; backend/server/.env.example lists the variables.
    EMAIL_BACKEND: Literal["console", "smtp"] = "console"
    EMAIL_FROM_ADDRESS: str = "no-reply@selvia.local"
    EMAIL_FROM_NAME: str = "SELVIA"
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    # "starttls" (port 587), "ssl" (port 465) or "none" (a local test server such as Mailpit).
    SMTP_SECURITY: Literal["starttls", "ssl", "none"] = "starttls"
    # The web app that links in emails open when the request does not say which one the person
    # uses. Normally the link follows the request's Origin (localhost in development, the deployed
    # address in production) as long as it is in CORS_ORIGINS; see app/services/email/service.py.
    APP_BASE_URL: str = "http://localhost:5173"
    # How long an invitation link stays valid.
    INVITATION_TTL_DAYS: int = 14
    # Invitations only match an account whose email address Keycloak has verified. Turn this
    # off only for local development, where the realm does not verify addresses.
    REQUIRE_VERIFIED_EMAIL: bool = True

    # GitHub Ingestion Settings
    GITHUB_TOKEN: Optional[str] = None

    # Agent Job Queue Retention (Clean up finished/failed jobs older than X hours)
    AGENT_JOB_RETENTION_HOURS: int = 24

    # AI Backend (internal service that runs the Main Orchestrator)
    AI_BACKEND_URL: str = "http://localhost:8003"
    AI_BACKEND_TIMEOUT_SECONDS: float = 60.0
    # Shared secret sent to the AI Backend as `X-Internal-Token`; must equal the value in
    # backend/agentic_framework/.env (AI_BACKEND_INTERNAL_TOKEN). No default; fail closed.
    AI_BACKEND_INTERNAL_TOKEN: Optional[str] = None

    # SLAP internal tutor-access-token mint (Core API only; never expose to browsers or AI Backend).
    # No default URL or credential: minting fails closed until both are set.
    SLAP_BASE_URL: Optional[str] = None
    INTERNAL_TUTOR_MINT_TOKEN: Optional[str] = None
    SLAP_TUTOR_MINT_TIMEOUT_SECONDS: float = 8.0

    model_config = SettingsConfigDict(
        env_file=SERVER_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator(
        "SERVER_DATABASE_URL",
        "SERVER_DIRECT_URL",
        "SLAP_BASE_URL",
        "INTERNAL_TUTOR_MINT_TOKEN",
        "AI_BACKEND_INTERNAL_TOKEN",
        mode="before",
    )
    @classmethod
    def blank_url_is_unset(cls, value: Optional[str]) -> Optional[str]:
        """Blank or whitespace-only env values mean "not set", not an empty URL/secret."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def smtp_needs_a_host(self) -> "Settings":
        if self.EMAIL_BACKEND == "smtp" and not self.SMTP_HOST:
            raise ValueError("EMAIL_BACKEND=smtp needs SMTP_HOST")
        return self

    @model_validator(mode="after")
    def resolve_database_url(self) -> "Settings":
        """Resolve database URL strictly from env without hardcoding."""
        if not self.SERVER_DATABASE_URL:
            if (
                self.SERVER_POSTGRES_USER
                and self.SERVER_POSTGRES_PASSWORD
                and self.SERVER_POSTGRES_DB
            ):
                host = self.SERVER_POSTGRES_HOST or "localhost"
                port = self.SERVER_POSTGRES_PORT or 5433
                self.SERVER_DATABASE_URL = (
                    f"postgresql+psycopg://{self.SERVER_POSTGRES_USER}:"
                    f"{self.SERVER_POSTGRES_PASSWORD}@{host}:{port}/"
                    f"{self.SERVER_POSTGRES_DB}"
                )
        return self

    @property
    def keycloak_issuer(self) -> str:
        return f"{self.KEYCLOAK_SERVER_URL.rstrip('/')}/realms/{self.KEYCLOAK_REALM}"

    @property
    def keycloak_jwks_url(self) -> str:
        return self.KEYCLOAK_JWKS_URL or f"{self.keycloak_issuer}/protocol/openid-connect/certs"

    @property
    def slap_tutor_mint_configured(self) -> bool:
        """True only when both SLAP base URL and the internal mint credential are set."""
        return bool(self.SLAP_BASE_URL and self.INTERNAL_TUTOR_MINT_TOKEN)

    @property
    def ai_backend_internal_token_configured(self) -> bool:
        """True when the Core→AI Backend shared service credential is set."""
        return bool(self.AI_BACKEND_INTERNAL_TOKEN)


settings = Settings()
