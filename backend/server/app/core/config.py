import os
from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings for the SELVIA Server backend.
    
    Zero hardcoded credentials: all database URLs, usernames, passwords,
    and secrets must be provided via environment variables.
    """
    APP_NAME: str = "SELVIA Server"
    APP_ENV: str = "development"
    DEBUG: bool = False

    # Server Database Configuration
    # Accepts a full connection URL or discrete connection parameters from environment.
    # Supabase Transaction Pooler (Port 6543):
    #   postgresql+psycopg://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require
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
    KEYCLOAK_SERVER_URL: Optional[str] = None
    KEYCLOAK_REALM: Optional[str] = None
    KEYCLOAK_CLIENT_ID: Optional[str] = None
    KEYCLOAK_CLIENT_SECRET: Optional[str] = None

    # GitHub Ingestion Settings
    GITHUB_TOKEN: Optional[str] = None

    # Agent Job Queue Retention (Clean up finished/failed jobs older than X hours)
    AGENT_JOB_RETENTION_HOURS: int = 24

    model_config = SettingsConfigDict(
        env_file=(
            "backend/server/.env",
            "server/.env",
            "backend/.env",
            ".env",
            ".env.development",
            "../.env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

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


settings = Settings()
