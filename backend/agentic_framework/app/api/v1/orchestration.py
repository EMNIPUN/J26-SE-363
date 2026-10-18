"""Entry point for AI requests coming from the Core API."""

from typing import Annotated

from fastapi import APIRouter, Depends
from shared.contracts import OrchestrationRequest, OrchestrationResponse

from app.api.dependencies import get_orchestrator
from app.core.security import require_internal_token
from app.orchestrator import Orchestrator

router = APIRouter(
    tags=["Orchestration"],
    dependencies=[Depends(require_internal_token)],
)


@router.post("/orchestration", response_model=OrchestrationResponse)
async def orchestrate(
    request: OrchestrationRequest,
    orchestrator: Annotated[Orchestrator, Depends(get_orchestrator)],
) -> OrchestrationResponse:
    return await orchestrator.handle(request)
