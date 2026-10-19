# Security Assistant Agent

Owner: Security Assistant team member. All security analysis logic lives in this directory.
Orchestrator name: `AgentName.SECURITY_ASSISTANT` (`security_assistant`); actions use the
`security.` prefix (e.g. `security.scan_repository`).

## Languages in scope

Python, Java and JavaScript/TypeScript are all in scope; none is optional. Java is supported for
**Spring Boot** projects (Maven or Gradle) with Spring-aware V1 and V3 checks, details and limits in
[tools/README.md](tools/README.md#java-spring-boot-what-is-covered-and-the-limits).

## What is built so far: the detection tools layer

You give it a folder containing a student project. It runs 9 existing security scanners on that
folder and turns all their different outputs into one common list of findings (category V1-V5,
file, line, CWE, rule, tool and version). It also records whether each scanner worked, failed,
timed out or was not installed, so a broken scanner never looks like a clean project.
No LLM is involved, and the agent is **not yet connected** to the orchestrator
(`agent.py` is empty, nothing is registered in `app/agents/registry.py`).

| File or folder | What it is |
|---|---|
| `schemas.py` | The common finding format (`Finding`), the run record per scanner (`ToolRun`) and the scan result |
| `tools/runner.py` | Entry point: `run_all(repo_path)` runs all the scanners and returns one result |
| `tools/base.py` | Shared safety rules for every scanner: fixed commands, time limits, secrets masked, failures recorded |
| `tools/languages.py` | Works out which languages a project uses (Python, Java, JS, TS) |
| `tools/codeql.py` | Runs CodeQL (injection and similar code issues) for V1, V2, V3 |
| `tools/config_scan.py` | Our own simple checker for weak login settings (V3) |
| `tools/secret_scanners.py` | Runs Gitleaks and TruffleHog for hard-coded secrets (V4) |
| `tools/dependencies.py` | Runs OSV-Scanner, npm audit and pip-audit for vulnerable libraries (V5) |
| `tools/workflow_lint.py` | Runs actionlint and zizmor on GitHub Actions workflows (V5) |
| `tools/check.py` | Command that lists which scanners are installed |
| `tools/queries/` | Our own CodeQL rules for V1 (a handler uses an id without checking the logged-in user), one per language |
| `tools/tests/` | The tests |
| `tools/tests/fixtures/` | Three tiny fake student projects (Python, Java, JS/TS) with deliberately planted vulnerabilities; tests check that the scanners find them. Test data, not real code |
| `Dockerfile` | Builds the image that has all the scanners installed (they run on Linux and are hard to install by hand on Windows) |

More detail: [tools/README.md](tools/README.md) and [tools/queries/README.md](tools/queries/README.md).

## How to run it

```bash
# 1. Build the scanner image once (large download, mainly CodeQL)
docker build -t selvia-security-assistant-tools backend/agentic_framework/app/agents/security_assistant

# 2. From backend/agentic_framework: list which scanners are installed
docker run --rm -v "$PWD:/app" selvia-security-assistant-tools \
  sh -c "pip install -q pydantic pyyaml && python -m app.agents.security_assistant.tools.check"

# 3. Scan a folder
docker run --rm -v "$PWD:/app" -v /path/to/student-repo:/repo:ro selvia-security-assistant-tools \
  sh -c "pip install -q pydantic pyyaml && python -m app.agents.security_assistant.tools.runner /repo"

# 4. Run the tests with the real scanners (slow: CodeQL builds a database per test)
docker run --rm -v "$PWD:/app" selvia-security-assistant-tools \
  sh -c "pip install -q pydantic pyyaml pytest && git config --global --add safe.directory '*' && python -m pytest app/agents/security_assistant/tools/tests"
```

## Entry paths: manual and GitHub webhook (limited)

Both paths end in the same function, which clones with `fetch_repo`, runs the tools and deletes the clone:

```python
from app.agents.security_assistant.pipeline import run_pipeline
result = await run_pipeline("https://github.com/owner/repo")                    # manual: default branch, full scan
result = await run_pipeline(url, sha, scan_type="secrets_only")                  # what the webhook calls
```

`fetch_repo(repo_url, commit_sha)` (`pipeline.py`): https://github.com URLs only; full history; git hooks and the
template directory disabled; no submodules or LFS; symlinks written as plain files; size limit (500 MB) and time
limit (300 s) enforced while cloning; checks out the exact SHA; never executes anything from the repository; deletes
the clone afterwards, also on errors.

`handle_github_event(headers, raw_body)` (`webhook.py`) is a plain async function, not an HTTP route; whatever
receives the HTTP request later passes the headers and the *raw* body to it:

1. verifies `X-Hub-Signature-256` against `SECURITY_ASSISTANT_WEBHOOK_SECRET` (no secret configured = reject everything);
2. classifies: `push` -> `secrets_only` scan of the pushed commit; `pull_request` closed **and merged** -> `full`
   scan of the merge commit; draft PRs, unmerged closes, other actions and other events -> ignored, reason logged;
3. dedupes by commit SHA (in memory, bounded, lost on restart): a repeated delivery does not run twice. A push and
   the merged PR for the same commit run `secrets_only` then `full`; a `full` scan makes a later `secrets_only`
   of the same SHA redundant. A crashed pipeline releases its claim so a GitHub redelivery can retry;
4. accepts only `https://github.com/<owner>/<repo>` repository URLs from the payload, then calls `run_pipeline`.

Demo without network (signs the two sample payloads in `webhook_samples/` and replays them, plus duplicate, draft,
unmerged, tampered and gitlab.com cases, with a stub pipeline that only prints what it would scan):

```powershell
uv run python -m app.agents.security_assistant.replay_webhook          # add --run to really clone and scan
```

Not part of this: an HTTP route, frontend, database tables, queues. Dedupe state is therefore per process.

## Local setup with uv (the project package manager)

The Python side is managed with [uv](https://docs.astral.sh/uv/) from `backend/agentic_framework/`
(Python 3.11, pinned in `.python-version`). The tools layer adds no Python dependency of its own: it
uses `pydantic`, `pyyaml` and `pytest`, which are already in `pyproject.toml` / `uv.lock`.

```powershell
winget install --id astral-sh.uv -e      # once; open a new terminal afterwards
cd backend\agentic_framework
uv sync                                   # creates .venv from uv.lock
uv run pytest app/agents/security_assistant/tools/tests   # unit tests; real-scanner tests skip themselves
```

The scanner binaries (CodeQL, Gitleaks, ...) are not Python packages, so uv cannot install them:
they come from the Docker image above. To run everything with the real scanners, use the Docker
commands in "How to run it".

Settings (optional, in `backend/agentic_framework/.env`): `SECURITY_ASSISTANT_SCAN_DIR`,
`SECURITY_ASSISTANT_TOOL_TIMEOUT[_<TOOL>]`, `SECURITY_ASSISTANT_CODEQL_RAM_MB`,
`SECURITY_ASSISTANT_CODEQL_THREADS`.

## Rules for building the agent on top of this

- Implement an agent class with `name = AgentName.SECURITY_ASSISTANT` and
  `async def handle(request: AgentRequest) -> AgentResponse` (see `app/agents/base.py`).
- The orchestrator routes `security.*` actions here.
- Findings must be evidence-grounded: return scanner output as `Evidence` items; the LLM explains
  and prioritizes verified findings, it does not invent them.
- If a finding needs student learning, return a `NextAction` with
  `target_agent=AgentName.ADAPTIVE_TUTOR`. Never call the tutor directly; the orchestrator
  coordinates Security Assistant -> Tutor -> Security Assistant.
- When ready, register the agent in `app/agents/registry.py`.

See `docs/TEAM_DEVELOPMENT_GUIDE.md`.
