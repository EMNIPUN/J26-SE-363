"""
Agent Job Queue API endpoints — backed by Procrastinate on PostgreSQL.

POST   /api/v1/jobs              — publish a job to the queue
GET    /api/v1/jobs/{job_id}     — get job status + parameters
"""

from typing import Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from shared.queue import app as procrastinate_app

router = APIRouter(prefix="/jobs", tags=["Agent Jobs"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class JobPublishRequest(BaseModel):
    """Body for publishing a new job to the queue."""
    task_name: str = Field(
        ...,
        examples=["performance.assess_student"],
        description="Fully-qualified task name registered in the agentic framework.",
    )
    queue: str = Field(
        default="default",
        examples=["performance"],
        description="Queue name the worker is listening on.",
    )
    payload: dict[str, Any] = Field(
        default={},
        description="Arbitrary input parameters forwarded to the task function as `payload`.",
    )


class JobPublishResponse(BaseModel):
    """Returned immediately after a job is enqueued (HTTP 202)."""
    job_id: int
    task_name: str
    queue: str
    status: str = "todo"


class JobStatusResponse(BaseModel):
    """Current state of a job in the Procrastinate queue."""
    job_id: int
    task_name: str
    queue: str
    status: str          # "todo" | "doing" | "succeeded" | "failed"
    attempts: int
    input_payload: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=JobPublishResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Publish a job to the agent queue",
)
async def publish_job(body: JobPublishRequest) -> JobPublishResponse:
    """Enqueue any registered task by name. Returns immediately (non-blocking)."""
    job_id = await (
        procrastinate_app
        .configure_task(name=body.task_name, queue=body.queue)
        .defer_async(payload=body.payload)
    )
    return JobPublishResponse(
        job_id=job_id,
        task_name=body.task_name,
        queue=body.queue,
    )


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job status",
)
async def get_job(job_id: int) -> JobStatusResponse:
    """Return current status of a queued job.

    Status values:
      todo       — waiting to be picked up
      doing      — worker is executing it right now
      succeeded  — finished successfully
      failed     — all retry attempts exhausted
    """
    jobs = await procrastinate_app.job_manager.list_jobs_async(id=job_id)
    if not jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found.",
        )

    job = jobs[0]
    payload = job.task_kwargs.get("payload") if isinstance(job.task_kwargs, dict) else None

    return JobStatusResponse(
        job_id=job.id,
        task_name=job.task_name,
        queue=job.queue,
        status=str(job.status),
        attempts=job.attempts,
        input_payload=payload,
    )
