# Proposal v2: Folder Structure & Common Workflow (aligned with the SELVIA vision)

> **Status: DRAFT, waiting for approval.** No code or folders have been changed for this proposal.
> v2 replaces v1. It follows the SELVIA Master Project Vision. Where it differs from the vision,
> section 3 explains why (as the vision requires for architectural changes).
> Approve or change the decisions in section 10 before work starts.

## 1. Goal

Prepare the shared foundation of SELVIA up to the point where each member works only inside their
own agent:

- One folder layout that matches the vision: **Core Backend**, **AI Backend**, Frontend.
- One way for the Core Backend to call the AI Backend (immediate requests) and one way to run
  long jobs (background).
- One central **Main Orchestrator**; agents never call each other.
- Shared project context (student → group → project → sprint → task) passed to every agent, so the
  student never repeats it.

**Out of scope:** agent logic, UI changes, and anything inside
`backend/agentic_framework/app/agents/performance_assessment/` (protected, see section 9).

## 2. Mapping the vision to this repository

| Vision | Repository today | Proposal |
|---|---|---|
| `backend/core-api` (FastAPI, SQLAlchemy, PostgreSQL) | `backend/server` | Keep folder name, reorganize by business domain |
| `backend/ai-backend` (FastAPI, LangGraph, Neo4j, MCP) | `backend/agentic_framework` | Keep folder name, add internal AI API + orchestrator |
| Main Orchestrator | `app/orchestrator/*.py` (empty files) | Fill as the single coordination point |
| 4 agents | `app/agents/{project_planning,adaptive_tutor,performance_assessment,aegis}` | Keep; tutor gets internal modules (still ONE agent) |
| `neo4j/` | `backend/agentic_framework/neo4j/` (README only) | Keep for Cypher schema/seed; Python access in `app/knowledge_graph/` |
| `mcp/` | `backend/agentic_framework/mcp/` (README only) | Move to `app/integrations/mcp/` (external systems only) |
| `database/` | `backend/server/alembic/` (README only) | Alembic in the Core Backend; no separate top-level folder |
| `tests/` | `tests/README.md` | Keep for future cross-service tests |
| Redis + Celery (considered) | Procrastinate on PostgreSQL (implemented by the team) | Keep Procrastinate, see section 3 |
| Frontend | `frontend/src/modules/{planning,tutor,performance,security}` + `shared/` | No change in this work |

## 3. Differences from the vision (need your approval)

### 3.1 Keep folder names `server` and `agentic_framework`

- **Vision:** `backend/core-api` and `backend/ai-backend`.
- **Proposal:** keep the current names; document them as "Core Backend" and "AI Backend".
- **Why:** the CI guard protects `backend/agentic_framework/app/agents/performance_assessment`
  (path also stored in a GitHub secret). Renaming moves every protected file, so the guard blocks
  whoever commits the rename, and every open teammate branch gets conflicts. The vision says the
  folder structure may change and "do not restructure the entire repository without a reason";
  a rename gives no technical benefit.
- **Affected if you still want the rename:** CI guard + secret, both Dockerfiles/compose files,
  docs, every teammate branch. It must be one coordinated PR with Sadeesha.

### 3.2 Keep Procrastinate (PostgreSQL) instead of Redis + Celery

- **Vision:** Redis + Celery is "currently considered", not fixed.
- **Proposal:** keep Procrastinate, already built and tested by the team on `dev`.
- **Why:** jobs live in the PostgreSQL database SELVIA already has, so no Redis server to run,
  secure and deploy ("do not add more databases/queues"). It supports retries, queues per agent,
  scheduled (periodic) jobs, and async Python, which LangGraph uses. Celery's async support is weak.
- **When to revisit:** if job volume grows far beyond a university cohort.

### 3.3 Immediate vs background requests (this follows the vision)

v1 of this proposal sent every AI request through the queue. The vision (sections 38–39) says
interactive requests must stay responsive. v2 follows the vision:

| Request type | Path | Examples |
|---|---|---|
| **Immediate** | Core → HTTP → AI Backend → Orchestrator → Agent → response | Tutor chat, lecturer orchestrator chat, requirement quality check, INVEST check |
| **Background** | Core → queue → AI worker → Orchestrator/Agent → result saved | GitHub ingestion, performance analysis, security scans, KG ingestion, viva preparation, batch analytics |

## 4. Target architecture

```text
React (student + lecturer)
   │  REST + Keycloak token
   ▼
CORE BACKEND  backend/server  (FastAPI · SQLAlchemy · PostgreSQL)        port 8000
   auth, users, groups, projects, requirements, user stories, sprints, tasks, scrum board,
   stored agent results, dashboards, reports
   │                                         │
   │ immediate: HTTP (internal, service key) │ background: enqueue job (Procrastinate)
   ▼                                         ▼
AI BACKEND  backend/agentic_framework  (FastAPI · LangGraph · Neo4j · MCP)
   app/main.py   internal API          port 8001 (not exposed through Kong)
   worker.py     background jobs       (same code, same environment)
        │
        ▼
   MAIN ORCHESTRATOR  (LangGraph)  ── routes, passes SelviaContext, combines results
        │        │          │           │
        ▼        ▼          ▼           ▼
   Planning   Adaptive   Performance   AEGIS        ← agents never call each other
              Tutor (1 agent, internal modules)
        │
        ├── Neo4j (course + student knowledge graphs)
        └── MCP clients (external learning platform, GitHub/project data)

PostgreSQL (Supabase): business data (Core owns schema) + job queue + agent runs + LangGraph checkpoints
```

Rules:

1. The frontend talks **only** to the Core Backend.
2. The Core Backend never imports AI code and has no LLM libraries.
3. Every AI request enters through the Orchestrator. Known actions route deterministically (no LLM
   needed); open questions (lecturer chat) use the LLM router.
4. Agent-to-agent work (e.g. AEGIS → Tutor → AEGIS) is an Orchestrator workflow.
5. The Core Backend owns the database schema (Alembic). The AI Backend writes only to: agent run
   results, LangGraph checkpoints, and Neo4j.

## 5. Target folder structure

`NEW` = created, `MOVE` = moved, `FILL` = existing empty file filled, `REMOVE` = deleted.
Everything else already exists and is unchanged.

```text
J26-SE-363/
├── frontend/                                  (unchanged)
├── backend/
│   ├── README.md
│   ├── .env.example
│   │
│   ├── server/                                CORE BACKEND
│   │   ├── pyproject.toml, uv.lock
│   │   ├── alembic.ini                        NEW
│   │   ├── alembic/env.py, versions/          NEW
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── core/
│   │   │   │   ├── config.py
│   │   │   │   └── security.py                NEW  Keycloak JWT → CurrentUser, require_role()
│   │   │   ├── database/  (base.py, session.py)
│   │   │   ├── models/__init__.py             imports every module's models (for Alembic)
│   │   │   ├── api/v1/router.py               NEW  mounts all module routers under /api/v1
│   │   │   ├── clients/ai_backend.py          NEW  HTTP client for immediate AI requests
│   │   │   ├── jobs/dispatch.py               NEW  enqueue background AI jobs + agent_runs row
│   │   │   └── modules/                       each: router.py, schemas.py, models.py, service.py
│   │   │       ├── identity/                  NEW  users, students, lecturers (Keycloak mapping)
│   │   │       ├── groups/                    NEW  groups, membership, Excel import
│   │   │       ├── projects/                  NEW  projects, lecturer guidance documents
│   │   │       ├── planning/                  requirements, user stories, estimates, planning AI calls
│   │   │       ├── sprints/                   NEW  sprints, tasks, scrum board
│   │   │       ├── tutor/                     tutor chat sessions, learning evidence, assessments
│   │   │       ├── performance/               performance evidence + results
│   │   │       ├── security/                  security findings + remediation status
│   │   │       ├── orchestrator_chat/         NEW  lecturer chat sessions → AI orchestrator
│   │   │       ├── agent_runs/                NEW  status/result of background AI jobs
│   │   │       └── reports/                   NEW  lecturer dashboard, analytics, viva requests
│   │   │       (current api/v1/jobs.py → dev-only)
│   │   └── tests/
│   │
│   ├── agentic_framework/                     AI BACKEND
│   │   ├── pyproject.toml, uv.lock
│   │   ├── worker.py                          background job worker
│   │   ├── neo4j/                             Cypher constraints + course KG seed data
│   │   ├── app/
│   │   │   ├── main.py                        FILL internal AI API (replaces placeholder)
│   │   │   ├── api/
│   │   │   │   ├── dependencies.py            FILL service-key check, request context
│   │   │   │   └── v1/
│   │   │   │       ├── orchestrator.py        NEW  POST /internal/v1/orchestrator/invoke
│   │   │   │       └── health.py              NEW
│   │   │   ├── core/
│   │   │   │   ├── config.py                  FILL Settings (LLM, DB, Neo4j, LangSmith)
│   │   │   │   ├── logging.py                 FILL logs carry request/run id, agent, action
│   │   │   │   ├── security.py                FILL service key, prompt-injection guards
│   │   │   │   ├── llm.py                     NEW  one place to create LLM clients
│   │   │   │   └── checkpointer.py            NEW  shared LangGraph Postgres checkpointer
│   │   │   ├── orchestrator/
│   │   │   │   ├── state.py                   FILL OrchestratorState (context, request, results)
│   │   │   │   ├── registry.py                NEW  agent actions each agent exposes
│   │   │   │   ├── router.py                  FILL deterministic routing + LLM router for chat
│   │   │   │   ├── nodes.py                   FILL call agent, combine results
│   │   │   │   ├── graph.py                   FILL StateGraph
│   │   │   │   └── workflows/                 NEW  multi-agent flows (e.g. security_learning.py)
│   │   │   ├── agents/
│   │   │   │   ├── project_planning/  agent.py, schemas.py
│   │   │   │   ├── adaptive_tutor/            ONE agent
│   │   │   │   │   ├── agent.py, schemas.py   public entry used by the orchestrator
│   │   │   │   │   └── modules/               NEW  internal modules, NOT agents:
│   │   │   │   │       context, knowledge_identification, evidence, learner_model,
│   │   │   │   │       decision_engine, assessment, feedback, adaptation
│   │   │   │   ├── performance_assessment/    (protected, unchanged)
│   │   │   │   └── aegis/  agent.py, schemas.py
│   │   │   ├── knowledge_graph/               NEW  Neo4j client + course/student graph access
│   │   │   ├── integrations/mcp/              MOVE from agentic_framework/mcp/
│   │   │   ├── tasks/                         background job handlers → orchestrator/agents
│   │   │   ├── schemas/                       NEW  API request/response models
│   │   │   ├── database/, models/, services/  REMOVE (README-only placeholders, unused)
│   │   └── tests/
│   │
│   └── shared/                                used by both backends
│       └── src/shared/
│           ├── queue.py                       Procrastinate app
│           ├── context.py                     NEW  SelviaContext, RunUser
│           ├── contracts/                     NEW  base envelope + one file per agent
│           └── runs.py                        NEW  update agent_runs from the worker
├── docker/  (keycloak, kong)                  kong.yml: add /api → Core Backend
├── docs/
├── tests/                                     future cross-service tests
└── docker-compose.yml
```

## 6. Shared project context

The vision requires that every component sees the same context. One model in
`shared/context.py`, built by the Core Backend from its database and sent with every AI request
and background job:

```python
class SelviaContext(BaseModel):
    user_id: str                 # Keycloak id
    role: Literal["student", "lecturer"]
    student_id: str | None       # e.g. ST001
    group_id: str | None         # e.g. G01  (group is first-class)
    project_id: str | None       # project title is NOT unique, always use the id
    project_title: str | None
    sprint_id: str | None
    task_id: str | None
```

Agents trust this context because only the Core Backend (after checking the Keycloak token and
group membership) can call the AI Backend.

## 7. How requests flow

### 7.1 Immediate request (example: tutor chat)

```text
React  POST /api/v1/tutor/sessions/{id}/messages
  → Core: check token + membership, build SelviaContext, save message
  → Core → AI  POST /internal/v1/orchestrator/invoke
           {"action": "tutor.chat", "context": {...}, "input": {"message": "Explain JWT"}}
  → Orchestrator: known action → Adaptive Tutor
  → response → Core saves answer + learning evidence → React
```

Timeout (e.g. 60 s) on the Core → AI call. Streaming (SSE) can be added later without changing the
contract.

### 7.2 Lecturer orchestrator chat (open question)

```text
"What groups are falling behind?"
  → Core (orchestrator_chat module) → AI  {"action": "orchestrator.chat", ...}
  → Orchestrator LLM router chooses agents/data → calls them → combines → answer
```

The router can only choose registered, read-only actions unless the lecturer confirms
(bounded AI actions, vision section 46).

### 7.3 Background job (example: sprint-end performance analysis)

```text
Core: dispatch("performance.assess_sprint", context, input)
  → INSERT agent_runs (queued) → enqueue Procrastinate job → HTTP 202 {run_id}
Worker: @agent_task wrapper → mark running → Orchestrator/Agent → save output → succeeded
React polls GET /api/v1/agent-runs/{run_id}; Core stores the result in its domain tables
```

### 7.4 Agent-to-agent (example: AEGIS finding → Tutor → AEGIS)

```text
AEGIS result says "student must understand SQL injection"
  → Orchestrator workflow security_learning:
       Tutor.create_comprehension_check → (student answers later) → Tutor.evaluate
       → AEGIS.update_finding(remediation_understood=True)
```

AEGIS only returns a result; it never imports or calls the Tutor.

## 8. Ownership

| Area | Owner |
|---|---|
| `shared/`, server `core/ database/ api/ clients/ jobs/`, Alembic | Common |
| server modules `identity, groups, projects, sprints, agent_runs, orchestrator_chat, reports` | Common |
| server modules `planning, tutor, performance, security` | Matching agent owner |
| AI `core/ api/ orchestrator/ knowledge_graph/ integrations/`, `worker.py` | Common |
| AI `agents/<agent>/`, `tasks/<agent>_tasks.py`, `shared/contracts/<agent>.py` | Agent owner |
| CI, CODEOWNERS, docs | Common |

| Agent | Owner (from git history; **please confirm**) |
|---|---|
| Performance assessment | Sadeesha Sathsara |
| Adaptive tutor | Nipun Dhananjaya |
| Project planning | ? |
| AEGIS security | ? |

## 9. Protected performance folder

`.github/workflows/performance-assessment-guard.yml` fails CI if anyone except Sadeesha changes
`backend/agentic_framework/app/agents/performance_assessment/`.

- This proposal changes nothing inside it. Performance is connected through
  `app/tasks/performance_tasks.py`, the orchestrator registry and `server/app/modules/performance/`.
- The earlier dependency split (uncommitted) changed 3 files there (`Dockerfile`,
  `docker-compose.yml`, `com_agent/tests/test_dependency_and_env_setup.py`). Proposal: revert them
  on this branch and give Sadeesha a patch. Until it's applied, the performance Docker build and
  that test still expect the old `backend/pyproject.toml`.
- Sadeesha decides whether the performance agent's own `server.py` (port 8002) stays as a debug tool
  once the orchestrator can call it.

## 10. Decisions needed

| # | Decision | Recommendation |
|---|---|---|
| D1 | Folder names (3.1) | Keep `server` / `agentic_framework` |
| D2 | Background jobs (3.2) | Keep Procrastinate; no Redis/Celery |
| D3 | Immediate = HTTP, long jobs = queue (3.3) | Yes |
| D4 | Core Backend modules by business domain (section 5) | Yes |
| D5 | Adaptive Tutor internal `modules/` skeleton | Yes (owner: Nipun) |
| D6 | Agent owners + GitHub usernames (section 8) | Fill in |
| D7 | Ports: Core 8000, AI 8001, performance debug server 8002 | Yes |
| D8 | API prefix `/api/v1`; frontend `VITE_API_BASE_URL=/api/v1` later (tutor Phase 18) | Yes |
| D9 | `POST /api/v1/jobs` dev-only | Yes |
| D10 | Protected files handled as in section 9 | Yes |
| D11 | Commit the dependency split as its own PR first | Yes |

## 11. Implementation phases (each waits for your "proceed")

| Phase | Work | Verification |
|---|---|---|
| 0 | Revert protected files → patch; commit dependency split (PR 1) | Tests same as baseline |
| 1 | Folder restructure only: create/move/remove folders and empty packages with short READMEs; no logic | Imports + all existing tests unchanged |
| 2 | `shared/context.py`, `shared/contracts/`, `shared/runs.py` | Unit tests |
| 3 | Core Backend foundation: Keycloak auth, Alembic, base models (users, groups, memberships, projects, sprints, tasks, agent_runs), `api/v1/router.py` | API tests with fake token; migration on local Postgres |
| 4 | Core ↔ AI communication: AI internal API + service key, `clients/ai_backend.py`, `jobs/dispatch.py`, `@agent_task`, `GET /agent-runs/{id}` | Tests for immediate call, background job, failure + retry, unauthorized calls |
| 5 | Orchestrator skeleton: state, registry, deterministic router, LLM-router stub, `security_learning` workflow with stub agents | Graph tests |
| 6 | Backend CI (uv sync --locked, ruff, pytest per service), CODEOWNERS, Kong route, `docs/AGENT_DEVELOPER_GUIDE.md` | CI green on a test PR |

## 12. What each member does after this

1. Define input/output models in `shared/contracts/<agent>.py`.
2. Register the agent's actions in the orchestrator registry.
3. Implement the agent in `app/agents/<agent>/` (graph, tools, prompts, evidence).
4. Add Core endpoints and result storage in `server/app/modules/<domain>/`.
5. Add agent-only packages with `uv add` in `backend/agentic_framework`.
6. Open a PR to `dev`; CI + CODEOWNERS review must pass.
