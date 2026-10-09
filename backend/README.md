# SELVIA Backend

Two independent Python services plus one small shared package. Each service has its own
dependencies, lock file and virtual environment:

```text
backend/
  server/                  # Core API (FastAPI): REST API for the frontend + its own database
    pyproject.toml         # server dependencies only
    uv.lock                # server lock file (commit it)
    requirements.txt       # generated from uv.lock, never edited by hand
    app/                   # imported as `app.*`
      core/security.py       # Keycloak token check: get_current_user, require_roles
      clients/ai_backend.py  # fast AI requests: HTTP call to the AI Backend
      services/ai_jobs.py    # slow AI requests: enqueue an orchestration job
    tests/
  agentic_framework/       # AI Backend (FastAPI + LangGraph) and the Procrastinate worker
    pyproject.toml         # dependencies for ALL agents
    uv.lock                # one lock file for every agent (commit it)
    requirements.txt       # generated from uv.lock, never edited by hand
    app/main.py            # AI Backend app: POST /api/v1/orchestration
    app/orchestrator/      # Main Orchestrator (graph, state, router, executor)
    app/agents/<agent>/    # project_planning, performance_assessment, adaptive_tutor, aegis
    app/agents/registry.py # where each agent is registered with the orchestrator
    app/integrations/      # clients for external systems (MCP, GitHub, scanners)
    app/tasks/             # queue tasks; orchestration_tasks.py sends jobs to the orchestrator
    worker.py
    tests/
  shared/                  # `selvia-shared` package used by both services
    pyproject.toml
    src/shared/contracts/  # Pydantic contracts: AgentRequest/Response, Orchestration*, contexts
    src/shared/queue.py    # Procrastinate job queue
    src/shared/jobs.py     # orchestration job name and queue naming, used by both services
```

The server and the agents never import each other's code. The Core API reaches the Main
Orchestrator in two ways: over HTTP (`POST /api/v1/orchestration`) when the caller waits, or as an
`orchestration.run` queue job when the work is slow (see `docs/AGENT_COMMUNICATION_GUIDE.md`). Both sides use the models in `shared.contracts`. How
members build their agents is in `docs/TEAM_DEVELOPMENT_GUIDE.md`. Database migrations are in
`docs/SERVER_DATABASE_GUIDE.md`.

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/). Set up each service you work on:

```bash
cd backend/server && uv sync              # creates backend/server/.venv
cd backend/agentic_framework && uv sync   # creates backend/agentic_framework/.venv
```

`uv sync` also installs `shared` into each environment as an editable path dependency, so changes
to `backend/shared/` are picked up immediately by both services. Environment variables are read
from `backend/.env` (or the service's own `.env`).

## Dependencies: one lock file per service

- The server and the agentic framework are deployed separately, so each has its own lock file and
  the AI libraries (LangChain, LangGraph, OpenAI, Neo4j) never end up in the server image.
- All agents run in the same worker process and the same LangGraph runtime, so they share
  **one** lock file in `agentic_framework/`. Don't create a `pyproject.toml`, `uv.lock`,
  `requirements.txt` or `.venv` inside an agent folder.
- `shared` declares only what the queue and contracts need (`procrastinate`, `python-dotenv`,
  `pydantic`); both services
  get it through `[tool.uv.sources] selvia-shared = { path = "../shared", editable = true }`.

Run these from the service folder you are changing (`backend/server/` or
`backend/agentic_framework/`):

| Task | Command |
|---|---|
| Add a runtime package | `uv add <package>` |
| Add a dev/test tool | `uv add --dev <package>` |
| Remove a package | `uv remove <package>` |
| Upgrade one package | `uv lock --upgrade-package <package>` |
| Refresh `requirements.txt` | `uv export --format requirements-txt --no-hashes --output-file requirements.txt` |

If you change `backend/shared/pyproject.toml`, run `uv lock` in **both** services.

Rules:

1. Never edit `uv.lock` or `requirements.txt` by hand. Commit `pyproject.toml`, `uv.lock` and the
   regenerated `requirements.txt` of that service together.
2. If a `uv.lock` has a merge conflict, don't fix it line by line. Accept either side, run `uv lock`
   in that service folder, then commit the result.
3. A package only one agent needs still goes in `agentic_framework/pyproject.toml`. If it's large
   and optional, put it in an extra, e.g. `uv add --optional performance <package>`, and install it
   with `uv sync --extra performance`.
4. Docker images and CI install with `uv sync --locked`, which fails if `pyproject.toml` and
   `uv.lock` disagree.

## Run

```bash
# Core API (from backend/server/)
uv run uvicorn app.main:app --reload --port 8002

# AI Backend (from backend/agentic_framework/)
uv run uvicorn app.main:app --reload --port 8003

# Agent worker (from backend/agentic_framework/)
uv run python -m worker
uv run python -m worker --queues performance planning

# Performance assessment agent as its own debug service (from backend/agentic_framework/)
uv run uvicorn app.agents.performance_assessment.server:app --port 8004
```

The Core API reaches the AI Backend at `AI_BACKEND_URL` (default `http://localhost:8003`). The
performance agent's debug server defaults to port 8002 like the Core API, so always pass `--port`
when running both locally.

The performance assessment agent's `Dockerfile` and `docker-compose.yml` live in its protected
folder (only its owner may change them). They still expect a per-agent `requirements.txt`; an update
that builds from `backend/` and installs from `agentic_framework/uv.lock` has been handed to the
owner as a patch.

## Test and lint

Run from each service folder:

```bash
uv run pytest
uv run ruff check .
```

`agentic_framework/tests/test_e2e_server_flow.py` tests both services together. It is skipped unless
the web server is running (default `http://localhost:8002`, override with `SELVIA_SERVER_URL`).
