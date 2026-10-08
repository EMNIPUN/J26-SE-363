# SELVIA Common Foundation — Implementation Report

Branch: `feature/common-foundation` (not committed yet)
Scope: the shared foundation every agent builds on. No agent logic, Neo4j, MCP, authentication or
database schema was implemented. The protected `performance_assessment/` folder and the frontend
were not changed.

## 1. Summary

- Every AI request now reaches an agent **through the Main Orchestrator**, whether the caller waits
  for the answer (HTTP) or not (background job).
- The Core API (`backend/server`) and the AI Backend (`backend/agentic_framework`) speak the same
  language: shared Pydantic contracts in `backend/shared/src/shared/contracts/`.
- Each agent has **one entry point**: `async def handle(AgentRequest) -> AgentResponse`. An agent is
  connected by adding one line to `app/agents/registry.py`.
- No agent is registered yet, so every request currently returns `status: "unavailable"`. The
  pipeline is ready and tested; the agents are the next step for each member.

## 2. Architecture

```text
Frontend (React, port 5173)
   |
   v
Core API  backend/server  (port 8002)
   |                                          \
   | FAST: caller waits                        \ SLOW: caller gets a job id at once
   | AIBackendClient.orchestrate()              \ start_ai_job()
   | HTTP POST /api/v1/orchestration             \ job queue (PostgreSQL, Procrastinate)
   v                                              v
AI Backend  backend/agentic_framework (port 8003)   Worker  (python -m worker)
   | orchestrate()                                    | run_orchestration()  task "orchestration.run"
   \                                                  /
    `--------------> Main Orchestrator <-------------'
                     get_orchestrator()  ->  Orchestrator.handle()
                        route    -> select_agent()           picks the agent from the action prefix
                        execute  -> AgentExecutor.execute()  calls agent.handle()
                        finalize -> builds OrchestrationResponse
                            |
                            v
                     One agent: app/agents/<agent>/   handle(AgentRequest) -> AgentResponse
```

Folder names: the project vision calls the services `core-api` and `ai-backend`. In this repository
they are `backend/server` and `backend/agentic_framework` (kept on purpose, to avoid moving the
protected performance files).

### When to use which path

| Path | Use for | Caller | Core API function | AI Backend function |
|---|---|---|---|---|
| Fast (HTTP) | Tutor chat, short questions | Waits (timeout 60 s) | `AIBackendClient.orchestrate()` in `server/app/clients/ai_backend.py` | `orchestrate()` in `app/api/v1/orchestration.py` |
| Slow (job) | PDF analysis, sprint assessment, repository scans | Gets a job id immediately | `start_ai_job()` in `server/app/services/ai_jobs.py` | `run_orchestration()` in `app/tasks/orchestration_tasks.py` |

Both paths send the same `OrchestrationRequest` to the same orchestrator, so an agent behaves the
same either way.

## 3. Request flow, step by step

### 3.1 Fast path (example: student asks the tutor a question)

| Step | File | Function | What happens |
|---|---|---|---|
| 1 | Core API endpoint (to build) | — | Builds an `OrchestrationRequest` (`action="tutor.chat"`) |
| 2 | `server/app/clients/ai_backend.py` | `AIBackendClient.orchestrate()` | POSTs to the AI Backend; network errors and invalid replies become `AIBackendError` |
| 3 | `agentic_framework/app/api/v1/orchestration.py` | `orchestrate()` | FastAPI validates the body (422 if invalid) |
| 4 | `app/orchestrator/factory.py` | `get_orchestrator()` | Returns the single orchestrator built from the agent registry |
| 5 | `app/orchestrator/graph.py` | `Orchestrator.handle()` | Runs the LangGraph graph |
| 6 | `app/orchestrator/router.py` | `select_agent()` | `tutor.chat` → Adaptive Tutor |
| 7 | `app/orchestrator/executor.py` | `build_agent_request()`, `AgentExecutor.execute()` | Builds the `AgentRequest` and calls the agent's `handle()` |
| 8 | `app/agents/adaptive_tutor/` (to build) | `handle()` | The agent does the real work |
| 9 | `app/orchestrator/graph.py` | `finalize` node | Wraps the result in an `OrchestrationResponse` |

### 3.2 Slow path (example: lecturer uploads the project guidance PDF)

| Step | File | Function | What happens |
|---|---|---|---|
| 1 | Core API endpoint (to build) | — | Stores the PDF, builds an `OrchestrationRequest` (`action="planning.analyze_guidance"`, `input={"document_id": ...}`) |
| 2 | `server/app/services/ai_jobs.py` | `start_ai_job()` | Enqueues task `orchestration.run` on queue `planning`; returns the job id at once |
| 3 | `shared/src/shared/jobs.py` | `queue_for()` | Chooses the queue from the action's area |
| 4 | `agentic_framework/worker.py` | `main()` | The worker picks up the job |
| 5 | `app/tasks/orchestration_tasks.py` | `run_orchestration()` | Validates the payload as an `OrchestrationRequest`, calls the orchestrator |
| 6–9 | same as fast path | | Orchestrator → Project Planning agent → `OrchestrationResponse` |
| 10 | `server/app/api/v1/jobs.py` | `get_job()` | The caller checks the status (`todo`, `doing`, `succeeded`, `failed`) |

## 4. Shared contracts (`backend/shared/src/shared/contracts/`)

### 4.1 Context (`context.py`)

| Model | Fields |
|---|---|
| `UserRole` | `student`, `lecturer`, `admin` |
| `RequesterContext` | `user_id`, `role` |
| `StudentContext` | `student_id`, `name` |
| `GroupContext` | `group_id`, `name`, `member_ids` |
| `ProjectContext` | `project_id`, `title`, `group_id` |
| `SprintContext` | `sprint_id`, `name`, `number`, `start_date`, `end_date` |
| `TaskContext` | `task_id`, `title`, `sprint_id`, `assignee_ids` |
| `SelviaContext` | `student`, `group`, `project`, `sprint`, `task` (all optional) |
| `ScopedRequest` | `request_id` (generated if missing), `student_id`, `group_id`, `project_id`, `sprint_id`, `task_id`, `context` |

`ScopedRequest` fills a missing id from `context` and rejects an id that contradicts `context`.
Groups are first-class and project titles are not unique, so projects are always identified by
`project_id`.

### 4.2 Agent contract (`agent.py`)

| Model | Fields / purpose |
|---|---|
| `AgentName` | `project_planning`, `adaptive_tutor`, `performance_assessment`, `aegis` |
| `ACTION_PREFIX_TO_AGENT`, `agent_for_action()` | `planning.` / `tutor.` / `performance.` / `security.` → agent; used by the router and the queue naming |
| `ResultStatus` | `completed`, `waiting_for_input`, `unavailable`, `failed` |
| `Evidence` | `source`, `description`, `reference`, `data` |
| `NextAction` | `type`, `description`, `target_agent`, `payload` — how an agent asks for another agent's help |
| `ErrorInfo` | `code`, `message`, `retryable` |
| `AgentRequest` | scope ids + `context`, `action` (`"<area>.<action>"`), `requester`, `input` |
| `AgentResponse` | `request_id`, `agent_name`, `status`, `result`, `evidence`, `next_action`, `error` (required when `failed`) |

### 4.3 Core API ↔ AI Backend contract (`orchestration.py`)

| Model | Fields |
|---|---|
| `OrchestrationRequest` | scope ids + `context`, `requester` (required), `action` or `message` (one is required), `input` |
| `OrchestrationResponse` | `request_id`, `status`, `result`, `evidence`, `next_action`, `error`, `agent_responses` |

### 4.4 Background job names (`backend/shared/src/shared/jobs.py`)

- `ORCHESTRATION_TASK_NAME = "orchestration.run"`, `DEFAULT_QUEUE = "default"`.
- `queue_for(request)`: `planning.*` → `planning`, `tutor.*` → `tutor`, `performance.*` →
  `performance`, `security.*` → `security`, anything else → `default`.

## 5. Main Orchestrator (`backend/agentic_framework/app/orchestrator/`)

| File | Contents |
|---|---|
| `state.py` | `OrchestratorState`: `request`, `target_agent`, `agent_responses`, `response` |
| `router.py` | `select_agent()`: picks the agent from the action prefix; free-text messages are not routed yet |
| `executor.py` | `build_agent_request()`; `AgentExecutor.execute()` returns `unavailable` for an unregistered agent and `failed` (`error.code="agent_error"`) if the agent raises |
| `graph.py` | `build_orchestrator_graph()`: route → execute (only if an agent was chosen) → finalize; `Orchestrator.handle()` |
| `factory.py` | `get_orchestrator()`: the one orchestrator shared by the HTTP route and the worker |

The orchestrator's routing is a dictionary lookup (no LLM call), and it runs in the same process as
the agents, so it adds practically no time to a request.

## 6. Agent directories

| Agent | Folder (`app/agents/`) | Prefix | Status |
|---|---|---|---|
| Project Planning | `project_planning/` | `planning.` | README with instructions |
| Adaptive Tutor | `adaptive_tutor/` | `tutor.` | README; ONE agent with internal modules (context, knowledge identification, course graph, student graph, evidence, learner model, decision engine, assessment, feedback, adaptation) |
| Performance Assessment | `performance_assessment/` | `performance.` | Protected, unchanged (owner only) |
| AEGIS | `aegis/` | `security.` | README with instructions |

Shared agent files:

- `app/agents/base.py`: `BaseAgent` protocol (`name`, `async handle(request) -> AgentResponse`).
- `app/agents/registry.py`: `build_agent_registry()`; each owner adds their agent here.
- `app/integrations/`: clients for external systems (MCP, GitHub, scanners). Not for agent-to-agent
  calls.

### Rules for every member

1. Keep agent logic inside your own folder; don't edit another member's agent.
2. Implement only `handle()`; no separate HTTP endpoints or queue tasks per agent.
3. Agents never call each other. Return a `NextAction` with `target_agent`; the orchestrator decides.
4. The Adaptive Tutor is one agent; its parts are internal modules, not agents.
5. Add packages with `uv add` from `backend/agentic_framework/`; no per-agent `pyproject.toml`.

Full guide: `docs/TEAM_DEVELOPMENT_GUIDE.md`.

## 7. Configuration

| Setting | Where | Default |
|---|---|---|
| `AI_BACKEND_URL` | Core API (`server/app/core/config.py`, `backend/.env`) | `http://localhost:8003` |
| `AI_BACKEND_TIMEOUT_SECONDS` | Core API | `60` |
| `AI_BACKEND_APP_ENV` | AI Backend (`AI_BACKEND_` prefix avoids clashes in the shared `.env`) | `development` |

Dependency changes:

- `backend/shared/pyproject.toml`: added `pydantic`.
- `backend/server/pyproject.toml`: `httpx` moved from dev to runtime dependencies.
- `uv.lock` and `requirements.txt` regenerated in both services.

## 8. Files

### 8.1 Created

| Area | Files |
|---|---|
| Shared | `shared/src/shared/contracts/__init__.py`, `context.py`, `agent.py`, `orchestration.py`; `shared/src/shared/jobs.py` |
| AI Backend | `app/agents/base.py`, `app/agents/registry.py`; `app/api/v1/__init__.py`, `router.py`, `orchestration.py`; `app/orchestrator/executor.py`, `factory.py`; `app/tasks/orchestration_tasks.py`; `app/integrations/__init__.py`, `README.md`; READMEs in `agents/project_planning/`, `agents/adaptive_tutor/`, `agents/aegis/` |
| Core API | `app/clients/__init__.py`, `app/clients/ai_backend.py`; `app/services/ai_jobs.py` |
| Tests | AI Backend: `test_shared_contracts.py`, `test_orchestrator.py`, `test_orchestration_api.py`, `test_orchestration_jobs.py`. Core API: `test_ai_backend_client.py`, `test_app_startup.py`, `test_ai_jobs.py` |
| Docs | `docs/TEAM_DEVELOPMENT_GUIDE.md`, `docs/COMMON_FOUNDATION_REPORT.md` (this file) |

### 8.2 Modified

| Area | Files |
|---|---|
| AI Backend | `app/main.py` (real app instead of placeholder), `app/core/config.py`, `app/api/dependencies.py`, `app/orchestrator/__init__.py`, `graph.py`, `router.py`, `state.py`, `app/tasks/__init__.py`, `app/schemas/README.md`, `app/services/README.md` |
| Core API | `app/core/config.py`, `pyproject.toml` |
| Shared | `pyproject.toml` |
| Lock files | `uv.lock` and `requirements.txt` in `server/` and `agentic_framework/` |
| Docs / config | `backend/README.md`, `backend/.env.example`, `docs/README.md`, `docs/AGENT_COMMUNICATION_GUIDE.md` |

### 8.3 Intentionally not changed

- `backend/agentic_framework/app/agents/performance_assessment/` (protected).
- `frontend/` (AI features go through the Core API with the existing `apiClient`).
- The older per-agent mock tasks (`planning_tasks.py`, `tutor_tasks.py`, `security_tasks.py`,
  `performance_tasks.py`); they still work and are marked in the docs as the old path.
- `worker.py`, `app/orchestrator/nodes.py` (empty), Core API `app/database`, `app/models`.

## 9. Tests

Commands (from each service folder): `uv run pytest -q`, `uv run ruff check <files>`.

| Suite | Result | Notes |
|---|---|---|
| AI Backend foundation tests (31 new) | 31 passed | Contracts, router, executor, orchestrator graph, HTTP endpoint, background job (including a real worker run with an in-memory queue) |
| AI Backend full suite | 243 passed, 1 skipped, 32 failed | All 32 failures are the known ones inside `performance_assessment/`, unchanged from before this work |
| Core API new tests (13) | 13 passed | Client success and error cases, settings, startup and health, job enqueueing, queue naming |
| Core API full suite | 13 passed, 1 failed | `test_jobs_api` needs a running PostgreSQL database (failed before this work too) |
| Ruff on new/changed files | Clean | Existing style warnings in the Core API's `config.py` were left untouched |

What the tests prove:

- Valid requests are accepted; requests without `requester`, without `action`/`message`, with a
  malformed action, or with ids that contradict the context are rejected (422).
- A request reaches the right agent with its scope and context, over HTTP and through the queue.
- Missing agents return `unavailable`; crashing agents return `failed` instead of breaking the request.
- `failed` responses must carry an error.

## 10. How to run

```bash
# Core API (from backend/server/)
uv sync
uv run uvicorn app.main:app --reload --port 8002

# AI Backend (from backend/agentic_framework/)
uv sync
uv run uvicorn app.main:app --reload --port 8003

# Worker for slow jobs (from backend/agentic_framework/)
uv run python -m worker
uv run python -m worker --queues tutor planning
```

Quick check of the AI Backend:

```bash
curl -X POST http://localhost:8003/api/v1/orchestration \
  -H "Content-Type: application/json" \
  -d '{"requester": {"user_id": "u-1", "role": "student"}, "action": "tutor.chat", "student_id": "S-01", "input": {"message": "What is a sprint?"}}'
```

Expected now: `status: "unavailable"` with `agent_responses[0].agent_name = "adaptive_tutor"`.

## 11. Open items

| # | Item | Why it matters | Suggested owner |
|---|---|---|---|
| 1 | Save results of slow jobs (`agent_runs` table + `GET /api/v1/agent-runs/{id}`) | The queue only stores `succeeded`/`failed`, not the answer | Common (with database models) |
| 2 | Authentication (Keycloak) in the Core API | Needed to fill `requester`; `POST /api/v1/jobs` and CORS are open today | Common |
| 3 | Database models: users, groups, projects, sprints, tasks (Alembic) | Needed to build real context and store results | Common |
| 4 | Core API feature endpoints (e.g. guidance PDF upload, tutor chat) | Nothing in the Core API calls the AI side yet | Common + agent owners |
| 5 | Each agent's `handle()` and registry entry | Agents are not implemented | Each member |
| 6 | Remove the old per-agent mock tasks | Avoid two entry points per agent | Common; performance after Sadeesha |
| 7 | Performance agent patch (Dockerfile, compose, one test) | Its Docker build and one test still expect the old layout | Sadeesha |
| 8 | Performance debug server default port 8002 clashes with the Core API | Must pass `--port` locally | Sadeesha |
| 9 | Free-text routing (LLM router), multi-step workflows acting on `next_action`, streaming chat replies | Lecturer chat, agent teamwork, word-by-word tutor replies | Common |
| 10 | Retries for background jobs | Today one error marks a job `failed` | Common |
| 11 | Procrastinate schema setup documented (`procrastinate schema --apply`) | New machines need the queue tables | Common |
| 12 | Backend CI (uv sync --locked, ruff, pytest per service) | No automatic checks on PRs | Common |
| 13 | Commit this branch and open a PR to `dev` | Teammates can't see this work yet | You |
