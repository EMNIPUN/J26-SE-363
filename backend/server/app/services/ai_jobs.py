"""Slow AI requests: Core API -> job queue -> worker -> Main Orchestrator.

Use `start_ai_job()` for work that can take minutes (PDF analysis, sprint
assessment, repository scans); the caller gets a job id at once. For quick
requests where the caller waits for the answer (tutor chat), use
`app.clients.ai_backend.AIBackendClient.orchestrate()`. Both reach the same
orchestrator and agents.
"""

from shared.contracts import OrchestrationRequest
from shared.jobs import ORCHESTRATION_TASK_NAME, queue_for
from shared.queue import app as procrastinate_app


async def start_ai_job(request: OrchestrationRequest) -> int:
    """Enqueue the request and return its job id (status: GET /api/v1/jobs/{job_id})."""
    return await procrastinate_app.configure_task(
        name=ORCHESTRATION_TASK_NAME, queue=queue_for(request)
    ).defer_async(payload=request.model_dump(mode="json"))
