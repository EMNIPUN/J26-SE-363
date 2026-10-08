# SELVIA Team Development Guide

How the four members build their agents in parallel on the common foundation without breaking
each other's work. Read this before you start on your agent.

## 1. Request flow

```text
Frontend (React)
  -> Core API          backend/server             (port 8002)  auth, users, groups, projects, DB
  -> AI Backend        backend/agentic_framework  (port 8003)  POST /api/v1/orchestration
  -> Main Orchestrator app/orchestrator/                       route -> execute -> finalize
  -> one agent         app/agents/<agent>/                     returns an AgentResponse
```

- The frontend only talks to the Core API. It never calls the AI Backend or an agent directly.
- Every AI request reaches the agent through the Main Orchestrator. Agents have no HTTP endpoints
  or queue tasks of their own; they only implement `handle()`.

The Core API chooses one of two paths, depending on whether the caller should wait:

```text
Fast (caller waits, e.g. tutor chat):
  Core API -> AIBackendClient.orchestrate() -> POST /api/v1/orchestration -> Orchestrator -> agent

Slow (caller gets a job id at once, e.g. PDF analysis, sprint assessment, repository scan):
  Core API -> start_ai_job() -> job queue -> worker -> orchestration.run -> Orchestrator -> agent
```

| Path | Core API code | AI Backend code |
|---|---|---|
| Fast | `server/app/clients/ai_backend.py` (`AIBackendClient.orchestrate`) | `app/api/v1/orchestration.py` (`orchestrate`) |
| Slow | `server/app/services/ai_jobs.py` (`start_ai_job`) | `app/tasks/orchestration_tasks.py` (`run_orchestration`) |

Both paths send the same `OrchestrationRequest` and use the same orchestrator
(`app/orchestrator/factory.py`, `get_orchestrator`), so an agent behaves the same either way.
Slow jobs go to the queue named after the action's area (`planning`, `tutor`, `performance`,
`security`, otherwise `default`); `uv run python -m worker --queues tutor` serves only tutor jobs.

The per-agent mock tasks in `app/tasks/planning_tasks.py`, `tutor_tasks.py`, `security_tasks.py`
and `performance_tasks.py` are the older direct path. Don't build on them; they will be removed once
the agents are registered with the orchestrator.

Folder names: the project vision calls the services `core-api` and `ai-backend`. In this
repository they are `backend/server` and `backend/agentic_framework`.

## 2. Where each member works

| Agent | Folder (inside `backend/agentic_framework/app/agents/`) | Action prefix | `AgentName` |
|---|---|---|---|
| Project Planning | `project_planning/` | `planning.` | `project_planning` |
| Adaptive Tutor | `adaptive_tutor/` | `tutor.` | `adaptive_tutor` |
| Performance Assessment | `performance_assessment/` (protected, owner only) | `performance.` | `performance_assessment` |
| AEGIS (security) | `aegis/` | `security.` | `aegis` |

Rules:

1. Agent-specific logic (prompts, graphs, tools, models, tests) stays inside your agent folder.
2. Do not edit another member's agent folder. `performance_assessment/` is protected by CI; only
   its owner may change it.
3. Do not create a `pyproject.toml`, `uv.lock`, `requirements.txt` or `.venv` inside an agent
   folder. Add packages with `uv add <package>` from `backend/agentic_framework/`
   (see `backend/README.md`).
4. Shared code lives outside agent folders and changes go through review:

   | Folder | Contains |
   |---|---|
   | `backend/shared/src/shared/contracts/` | Pydantic contracts used by both services |
   | `backend/agentic_framework/app/orchestrator/` | Main Orchestrator (graph, state, router, executor) |
   | `backend/agentic_framework/app/agents/base.py`, `registry.py` | Agent interface and registration |
   | `backend/agentic_framework/app/integrations/` | Clients for external systems (MCP, GitHub, scanners) |
   | `backend/agentic_framework/app/services/` | Services used by more than one agent |
   | `backend/server/` | Core API: users, groups, projects, persistence |

## 3. Shared contracts

All contracts are in `backend/shared/src/shared/contracts/`; import them from `shared.contracts`.

### Context

`StudentContext`, `GroupContext`, `ProjectContext`, `SprintContext` and `TaskContext` are grouped
in `SelviaContext`. Every field is optional, so send only what the request needs.

- A group is a first-class entity. Project titles are not unique, so always identify a project by
  `project_id` (and its `group_id`), never by title.
- Requests carry `student_id`, `group_id`, `project_id`, `sprint_id` and `task_id` at the top
  level. A missing id is filled from `context`; an id that contradicts `context` is rejected.

### AgentRequest (orchestrator -> agent)

| Field | Meaning |
|---|---|
| `request_id` | Correlation id; the same value as the orchestration request |
| `student_id`, `group_id`, `project_id`, `sprint_id`, `task_id` | Scope ids |
| `context` | `SelviaContext` |
| `action` | `"<area>.<action>"`, e.g. `tutor.chat`, `planning.generate_plan` |
| `requester` | `RequesterContext(user_id, role)` of the user who started the request |
| `input` | Action-specific payload (agent-defined) |

### AgentResponse (agent -> orchestrator)

| Field | Meaning |
|---|---|
| `request_id` | Copy of the request's `request_id` |
| `agent_name` | Your `AgentName` |
| `status` | `completed`, `waiting_for_input`, `unavailable` or `failed` |
| `result` | Action-specific output |
| `evidence` | List of `Evidence(source, description, reference, data)` behind the result |
| `next_action` | Optional `NextAction(type, description, target_agent, payload)` |
| `error` | `ErrorInfo(code, message, retryable)`; required when `status` is `failed` |

### OrchestrationRequest / OrchestrationResponse (Core API <-> AI Backend)

- `OrchestrationRequest` has the same scope and context fields, plus a required `requester`, and
  either an `action` or a free-text `message`.
- `OrchestrationResponse` has `request_id`, the final `status` / `result` / `evidence` /
  `next_action` / `error`, and `agent_responses` (every `AgentResponse` produced).

Keep agent-specific shapes inside `input` and `result`. If several agents need a new common field,
propose a change to `shared/contracts/`. Do not fork the contract inside your agent.

## 4. Implementing your agent

Each agent implements the `BaseAgent` protocol from `app/agents/base.py`:

```python
from shared.contracts import AgentName, AgentRequest, AgentResponse, ResultStatus


class AdaptiveTutorAgent:
    name = AgentName.ADAPTIVE_TUTOR

    async def handle(self, request: AgentRequest) -> AgentResponse:
        ...
        return AgentResponse(
            request_id=request.request_id,
            agent_name=self.name,
            status=ResultStatus.COMPLETED,
            result={"reply": "..."},
        )
```

Then register it in `app/agents/registry.py` (the only shared file you need to edit):

```python
def build_agent_registry() -> dict[AgentName, BaseAgent]:
    return {
        AgentName.ADAPTIVE_TUTOR: AdaptiveTutorAgent(),
    }
```

Until an agent is registered, the orchestrator answers its actions with `status: "unavailable"`.
If `handle` raises an exception, the orchestrator returns `status: "failed"` with
`error.code = "agent_error"` instead of crashing the request. Still return a proper `failed`
response yourself for errors you expect.

Internally an agent can use any structure (its own LangGraph graph, tools, prompts), as long as
`handle` accepts an `AgentRequest` and returns an `AgentResponse`.

## 5. Agents never call each other

- Do not import another agent's code, and do not call another agent over HTTP or through the queue.
- To involve another agent, return a `NextAction` with `target_agent` set, for example AEGIS
  suggesting a security lesson:

  ```python
  NextAction(
      type="recommend_learning",
      description="Explain SQL injection to the student",
      target_agent=AgentName.ADAPTIVE_TUTOR,
      payload={"topic": "sql_injection", "finding_id": "F-12"},
  )
  ```

- The orchestrator decides whether and when to run that action. The foundation returns
  `next_action` to the caller; multi-step workflows are added to the orchestrator later.
- MCP is only for external systems (GitHub, scanners, Scrum tools); put those clients in
  `app/integrations/`. It is not a channel between agents.

## 6. The Adaptive Tutor is one agent

The Adaptive Tutor is a single agent (`AgentName.ADAPTIVE_TUTOR`) with internal modules, not
several cooperating tutor agents. Internal modules (context, knowledge identification, course
graph, student graph, evidence, learner model, decision engine, assessment, feedback, adaptation)
are plain Python modules under `adaptive_tutor/` and are not registered as agents. See
`app/agents/adaptive_tutor/README.md`.

## 7. Running and testing

```bash
# Core API (from backend/server/)
uv run uvicorn app.main:app --reload --port 8002

# AI Backend (from backend/agentic_framework/)
uv run uvicorn app.main:app --reload --port 8003

# Worker for slow jobs (from backend/agentic_framework/)
uv run python -m worker
```

The Core API finds the AI Backend through `AI_BACKEND_URL` (default `http://localhost:8003`) and
`AI_BACKEND_TIMEOUT_SECONDS` in `backend/.env`. AI Backend settings use the `AI_BACKEND_` prefix so
they don't collide with Core API settings in the same file.

Try the orchestration endpoint (it returns `unavailable` until the tutor is registered):

```bash
curl -X POST http://localhost:8003/api/v1/orchestration \
  -H "Content-Type: application/json" \
  -d '{"requester": {"user_id": "u-1", "role": "student"}, "action": "tutor.chat",
       "student_id": "S-01", "input": {"message": "What is a sprint?"}}'
```

Tests:

- Put agent tests in your agent folder (or `tests/` under it) and run `uv run pytest` from
  `backend/agentic_framework/`.
- `tests/test_shared_contracts.py`, `tests/test_orchestrator.py`,
  `tests/test_orchestration_api.py` and `tests/test_orchestration_jobs.py` cover the foundation.
  Keep them passing.
- Test your agent through the orchestrator by overriding `get_orchestrator` (see
  `tests/test_orchestration_api.py`), or by calling `handle` directly with an `AgentRequest`.

## 8. Not part of the foundation yet

Saving the results of slow jobs is the most important missing piece: the queue only records
`succeeded` / `failed`, not the `OrchestrationResponse`, so an `agent_runs` table is needed before
the frontend can show a background result.

Authentication, database models for groups/projects/sprints, persistence of agent results, Neo4j,
MCP integrations, LLM-based routing of free-text messages and multi-step orchestration are planned
later steps. Don't build private versions of them inside an agent folder; raise them with the team
so they land in the shared layer.
