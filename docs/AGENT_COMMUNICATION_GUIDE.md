# Server & Agentic Framework Communication Guide

This guide details the PostgreSQL-backed job queue architecture connecting the **FastAPI Web Server** (`backend/server/`) and the **Multi-Agent Framework** (`backend/agentic_framework/`) using **Procrastinate**.

> **Use the orchestration job for new work.** Background AI requests are now one task,
> `orchestration.run`, whose payload is an `OrchestrationRequest`. The Core API enqueues it with
> `start_ai_job()` (`backend/server/app/services/ai_jobs.py`); the worker runs
> `run_orchestration()` (`backend/agentic_framework/app/tasks/orchestration_tasks.py`), which passes
> it to the Main Orchestrator, the same one behind `POST /api/v1/orchestration`. The per-agent
> tasks shown below (`performance.assess_student`, ...) are the older direct path and return mock
> data. Procrastinate stores only the job status, not the task's return value, and the tasks don't
> configure retries. See `docs/TEAM_DEVELOPMENT_GUIDE.md`.

---

## 1. Why Do We Need a Job Queue?

In an AI-driven multi-agent platform, agent tasks are fundamentally different from standard database CRUD operations:

1. **Long-Running Execution vs. HTTP Timeouts**:
   - Standard HTTP requests expect responses within milliseconds. Browsers, mobile apps, load balancers, and reverse proxies (NGINX, Cloudflare) enforce strict gateway timeouts (typically 30–60 seconds).
   - Agent workflows involve heavy computations, external tool invocations, multiple LLM reasoning chains, and graph iterations that take anywhere from **15 seconds to several minutes**.
   - Holding a synchronous HTTP connection open for this duration leads to dropped client connections, `504 Gateway Timeout` errors, and wasted server resources.

2. **Decoupling and Asynchronous Non-Blocking Server**:
   - The FastAPI web server stays fast and responsive. When an incoming request triggers an agent, the server immediately records the job, returns `HTTP 202 Accepted` with a `job_id`, and frees the request thread to handle other users.

3. **Fault Tolerance, Retries, and Crash Resilience**:
   - If an external AI API experiences rate limits, network blips, or an agent worker restarts mid-execution, synchronous requests crash and lose the entire computation.
   - With a persistent PostgreSQL queue, job state is safely stored in Supabase. Unfinished jobs remain safely recorded and can be retried or inspected without data loss.

4. **Independent Horizontal Scalability & Worker Isolation**:
   - Web traffic and AI tasks require vastly different compute profiles. The web server is lightweight and I/O-bound; agent workers are heavy and CPU/memory-bound.
   - A job queue allows running web servers and worker instances on completely independent machines or containers, scaling agent workers dynamically based on queue depth.
   - Multiple worker instances pull jobs concurrently using PostgreSQL's atomic row locking without race conditions or duplicate execution.

5. **Granular Multi-Stage Observability**:
   - Rather than staring at a frozen loading spinner, the client receives live status updates (`todo` ➔ `doing` ➔ `succeeded` / `failed`) via `GET /api/v1/jobs/{job_id}`.

6. **Strict Rate Limiting & Concurrency Control**:
   - Prevents sudden traffic spikes from exhausting third-party AI rate limits or overwhelming the host system. The worker processes jobs according to available capacity.

---

## 2. Architecture & Components

```
FastAPI Server (Producer)
       │
       │ POST /api/v1/jobs  (or task.defer_async)
       ▼
Supabase PostgreSQL (procrastinate_jobs table)
       │  • id (int)
       │  • queue_name ('performance', 'planning', etc.)
       │  • task_name ('performance.assess_student')
       │  • args (JSONB payload)
       │  • status ('todo' ➔ 'doing' ➔ 'succeeded' / 'failed')
       │  • attempts
       │
       ▼
Agentic Framework Worker Daemon (Consumer)
       └── uv run python -m worker   (from backend/agentic_framework/)
             ├── @app.task("performance.assess_student")
             ├── @app.task("performance.parse_rubric")
             ├── @app.task("performance.generate_ownership_quiz")
             └── @app.task("performance.ingest_git_commits")
```

---

## 3. How to Use It: Complete End-to-End Walkthrough

### Part A: Server Side — Incoming REST Request Enqueues Task

When a client hits `POST /api/v1/jobs`, the server enqueues the task in Supabase and returns `HTTP 202 Accepted` immediately:

```bash
# HTTP Request from Frontend / Client:
POST /api/v1/jobs
Content-Type: application/json

{
  "task_name": "performance.assess_student",
  "queue": "performance",
  "payload": {
    "student_id": "IT21098765",
    "batch_id": "2026-REG-Y4S1",
    "sprint_id": "sprint-2"
  }
}
```

**FastAPI Implementation (`backend/server/app/api/v1/jobs.py`):**
```python
from fastapi import APIRouter, status
from pydantic import BaseModel
from shared.queue import app as procrastinate_app

router = APIRouter(prefix="/jobs", tags=["Agent Jobs"])

@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def publish_job(body: JobPublishRequest):
    # Enqueue task non-blockingly into Supabase PostgreSQL
    job_id = await (
        procrastinate_app
        .configure_task(name=body.task_name, queue=body.queue)
        .defer_async(payload=body.payload)
    )
    return {
        "job_id": job_id,
        "task_name": body.task_name,
        "queue": body.queue,
        "status": "todo"
    }
```

**Response (HTTP 202 Accepted):**
```json
{
  "job_id": 6,
  "task_name": "performance.assess_student",
  "queue": "performance",
  "status": "todo"
}
```

---

### Part B: Agentic Framework Side — Worker Consumes and Executes

The agentic framework worker listens to the queue and executes the registered `@app.task`:

**Task Definition (`backend/agentic_framework/app/tasks/performance_tasks.py`):**
```python
from shared.queue import app

@app.task(name="performance.assess_student", queue="performance")
async def assess_student(payload: dict) -> dict:
    """Executes the agentic evaluation when claimed by the worker."""
    student_id = payload.get("student_id")
    sprint_id = payload.get("sprint_id")
    
    # Run the real LangGraph com_agent evaluation & AHP fusion pipeline:
    # result = await run_evaluation(student_id=student_id, sprint_id=sprint_id)
    
    return {
        "student_id": student_id,
        "sprint_id": sprint_id,
        "final_score": 87.5,
        "factor_scores": {
            "effort": 88.0,
            "consistency": 85.0,
            "code_ownership": 90.0
        }
    }
```

**Start the Worker Daemon:**
```powershell
cd backend/agentic_framework
uv sync
uv run python -m worker
```
Or consume only specific queues:
```powershell
uv run python -m worker --queues performance
```

---

### Part C: Checking Job Status

The client checks status and retrieves parameters at any time:

```bash
GET /api/v1/jobs/6
```

**Response:**
```json
{
  "job_id": 6,
  "task_name": "performance.assess_student",
  "queue": "performance",
  "status": "succeeded",
  "attempts": 1,
  "input_payload": {
    "student_id": "IT21098765",
    "batch_id": "2026-REG-Y4S1",
    "sprint_id": "sprint-2"
  }
}
```

Possible statuses:
- `"todo"`: Waiting in queue for worker to claim.
- `"doing"`: Worker is currently processing the job.
- `"succeeded"`: Job finished successfully.
- `"failed"`: Retries exhausted or unhandled exception.
