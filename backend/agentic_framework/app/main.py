"""SELVIA AI Backend. Internal service: only the Core API calls it.

This starts the HTTP server only. The job worker (the part that really runs the assessment agent) is a separate command:

    uv run --active --no-sync uvicorn app.main:app --port 8003
    uv run python -m worker
"""

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="Main Orchestrator and specialized agents for SELVIA",
    version="0.1.0",
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    return {"status": "UP", "service": settings.APP_NAME, "environment": settings.APP_ENV}
