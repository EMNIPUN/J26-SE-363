import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.queue import app as procrastinate_app

from app.api.v1.router import api_router
from app.core.config import settings
from app.database.session import check_db_connection

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Application lifespan — opens Procrastinate connection for job publishing."""
    logger.info("Initializing SELVIA Server...")

    # Open the Procrastinate app for the duration of the server lifetime.
    async with procrastinate_app.open_async():
        logger.info("Procrastinate queue connection open.")
        yield

    logger.info("SELVIA Server shut down.")


app = FastAPI(
    title=settings.APP_NAME,
    description="SELVIA Web Server API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
def health_check():
    """Health check — validates server and database connectivity."""
    db_healthy = check_db_connection()
    return {
        "status": "UP" if db_healthy else "DEGRADED",
        "database_connected": db_healthy,
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }
