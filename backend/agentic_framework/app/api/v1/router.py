from fastapi import APIRouter

from app.api.v1.orchestration import router as orchestration_router

api_router = APIRouter()
api_router.include_router(orchestration_router)
