"""Background AI jobs: every job goes through the Main Orchestrator.

Queue: any ("default", or the action's area such as "planning", "tutor")
Task name: orchestration.run

The payload is an OrchestrationRequest. The Core API enqueues it with
`app.services.ai_jobs.start_ai_job()`; this task hands it to the same
orchestrator the HTTP route uses, so agents only implement `handle()`.
"""

import logging
from typing import Any

from shared.contracts import OrchestrationRequest
from shared.jobs import DEFAULT_QUEUE, ORCHESTRATION_TASK_NAME
from shared.queue import app

from app.orchestrator.factory import get_orchestrator

logger = logging.getLogger(__name__)


@app.task(name=ORCHESTRATION_TASK_NAME, queue=DEFAULT_QUEUE)
async def run_orchestration(payload: dict[str, Any]) -> dict[str, Any]:
    request = OrchestrationRequest.model_validate(payload)
    response = await get_orchestrator().handle(request)
    logger.info(
        "Orchestration job %s (%s) finished with status %s",
        request.request_id,
        request.action,
        response.status.value,
    )
    return response.model_dump(mode="json")
