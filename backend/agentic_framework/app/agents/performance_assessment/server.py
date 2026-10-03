"""Standalone HTTP Microservice API for the Performance Assessment Agent.

Exposes Triggers 1-4 and status query endpoints as an isolated service.
Can be run via:
    uvicorn app.agents.performance_assessment.server:app --host 0.0.0.0 --port 8002
"""

import logging
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from app.agents.performance_assessment.agent import (
    trigger_sprint_end,
    submit_quiz_response,
    trigger_on_demand,
    submit_lecturer_review,
    get_assessment_status,
    check_expired_quiz_timeouts,
)
from app.agents.performance_assessment.com_agent.db import init_assessment_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize assessment database tables on startup if PostgreSQL is configured
    try:
        init_assessment_db()
    except Exception as e:
        logger.warning(f"Startup DB init non-fatal warning: {e}")
    yield


app = FastAPI(
    title="Performance Assessment Agent API",
    description="Decoupled standalone microservice for automated individual student contribution assessment.",
    version="1.0.0",
    lifespan=lifespan,
)


# Request schemas
class SprintEndRequest(BaseModel):
    sprint_id: str = Field(..., description="Sprint identifier, e.g. sprint-01")
    student_ids: Optional[List[str]] = Field(default=None, description="Optional list of student IDs")
    custom_contexts: Optional[Dict[str, Dict[str, Any]]] = Field(default=None, description="Optional per-student context override")


class QuizResponseRequest(BaseModel):
    thread_id: str = Field(..., description="Execution thread ID for the student assessment")
    student_response: str = Field(..., description="Plain-English explanation submitted by student")


class OnDemandRequest(BaseModel):
    sprint_id: str = Field(..., description="Sprint identifier")
    student_id: str = Field(..., description="Student identifier")
    custom_context: Optional[Dict[str, Any]] = Field(default=None, description="Optional student context")
    force_refresh: bool = Field(default=False, description="Re-ingest live data instead of reusing cached evidence pool")


class LecturerReviewRequest(BaseModel):
    thread_id: str = Field(..., description="Thread ID paused at lecturer review")
    override_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Optional overridden score")
    reason: str = Field(..., description="Justification notes for review/override")
    lecturer_id: str = Field(..., description="Lecturer identifier")


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint for Docker / orchestration probes."""
    return {
        "status": "healthy",
        "service": "performance_assessment_agent",
        "version": "1.0.0",
    }


@app.post("/api/v1/assessment/check-timeouts", status_code=status.HTTP_200_OK)
async def api_check_timeouts():
    """Trigger periodic scan of active quiz threads to resume any that exceeded 48h/96h deadlines."""
    try:
        expired = await check_expired_quiz_timeouts()
        return {
            "status": "checked",
            "expired_threads_count": len(expired),
            "expired_threads": expired,
        }
    except Exception as e:
        logger.error(f"Failed to check expired timeouts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/assessment/triggers/sprint-end", status_code=status.HTTP_202_ACCEPTED)
async def api_trigger_sprint_end(req: SprintEndRequest):
    """Trigger 1: Automated Sprint End Deadline Trigger."""
    try:
        thread_ids = await trigger_sprint_end(
            sprint_id=req.sprint_id,
            student_ids=req.student_ids,
            custom_contexts=req.custom_contexts,
        )
        return {
            "status": "triggered",
            "sprint_id": req.sprint_id,
            "thread_ids": thread_ids,
        }
    except Exception as e:
        logger.error(f"Failed to trigger sprint end: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/assessment/triggers/quiz-response", status_code=status.HTTP_200_OK)
async def api_submit_quiz_response(req: QuizResponseRequest):
    """Trigger 2: Student Active Verification Quiz Submission (Resumption Event)."""
    try:
        outcome = await submit_quiz_response(
            thread_id=req.thread_id,
            student_response=req.student_response,
        )
        return {
            "thread_id": req.thread_id,
            "outcome": outcome,
        }
    except Exception as e:
        logger.error(f"Failed to process quiz submission: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/assessment/triggers/on-demand", status_code=status.HTTP_202_ACCEPTED)
async def api_trigger_on_demand(req: OnDemandRequest):
    """Trigger 3: On-Demand Student Evaluation Trigger."""
    try:
        thread_id = await trigger_on_demand(
            sprint_id=req.sprint_id,
            student_id=req.student_id,
            student_context=req.custom_context,
            force_refresh=req.force_refresh,
        )
        return {
            "status": "triggered",
            "thread_id": thread_id,
            "sprint_id": req.sprint_id,
            "student_id": req.student_id,
        }
    except Exception as e:
        logger.error(f"Failed to trigger on-demand assessment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/assessment/triggers/lecturer-review", status_code=status.HTTP_200_OK)
async def api_submit_lecturer_review(req: LecturerReviewRequest):
    """Trigger 4: Lecturer Review and Override Resumption Trigger."""
    try:
        outcome = await submit_lecturer_review(
            thread_id=req.thread_id,
            override_score=req.override_score,
            reason=req.reason,
            lecturer_id=req.lecturer_id,
        )
        return {
            "thread_id": req.thread_id,
            "outcome": outcome,
        }
    except Exception as e:
        logger.error(f"Failed to submit lecturer review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/assessment/status/{thread_id}", status_code=status.HTTP_200_OK)
async def api_get_status(thread_id: str):
    """Query current thread lifecycle status and assessment state."""
    state = get_assessment_status(thread_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Assessment thread {thread_id} not found.")

    return {
        "thread_id": thread_id,
        "current_step": state.get("current_step"),
        "final_score": state.get("final_score"),
        "behavioral_persona": state.get("behavioral_persona"),
        "requires_human_review": state.get("requires_human_review", False),
        "lecturer_reviewed": state.get("lecturer_reviewed", False),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.agents.performance_assessment.server:app", host="0.0.0.0", port=8002, reload=True)
