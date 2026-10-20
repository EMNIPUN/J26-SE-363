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

# 4. Run the tests with the real scanners (slow, on request only: CodeQL builds a database per test)
docker run --rm -v "$PWD:/app" selvia-security-assistant-tools \
  sh -c "pip install -q pydantic pyyaml pytest && git config --global --add safe.directory '*' && python -m pytest -m integration app/agents/security_assistant/tools/tests"
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


## Scan and read the findings (`scan.py`)

```powershell
python -m app.agents.security_assistant.scan <folder | https://github.com/owner/repo> [--out DIR] [--skip a,b] [--ref SHA]
```

Prints a per-tool status table, a **coverage** check per category V1-V5, and a findings table, and writes
`findings.json` (all findings, secrets masked) and `report.md` (grouped by V1-V5 with tool, rule, CWE, file:line,
severity, message and a masked code snippet) to `--out` (default `scan_output/<name>_<time>/`, git-ignored).

- A tool that failed, timed out or is not installed is shown as such and the result line says INCOMPLETE (exit code 2).
- `--skip codeql` (comma separated or repeated; names: codeql, config-scan, gitleaks, trufflehog, osv-scanner, npm-audit,
  pip-audit, actionlint, zizmor) runs without them. The output lists the skipped tools and the categories they leave
  uncovered: **NONE** = no tool that finds this category ran, so "0 findings" says nothing; **REDUCED** = some did.
  Without CodeQL, V1 and V2 are uncovered and V3 is reduced (config-scan still runs).
- A URL is cloned with `fetch_repo` (https://github.com only, deleted afterwards); `--ref` picks the commit.
- `--from-json findings.json [folder]` re-renders a saved result without scanning (used by the tests).

The scanners live in the Docker image, so run it there (build the image first, see "How to run it"). The seeded
fixtures need a real git history for the planted secret; `demo_repos` creates scannable copies. Planted bugs per
fixture, to tick off against `report.md`: `tools/tests/fixtures/PLANTED_BUGS.md`.

```powershell
cd backendgentic_framework
# once: create the scannable copies in scan_output/demo_repos
docker run --rm -v "${PWD}:/app" selvia-security-assistant-tools sh -c "pip install -q pydantic pyyaml && cd /app && python -m app.agents.security_assistant.tools.tests.demo_repos /app/scan_output/demo_repos"

# fast tools only (no CodeQL), one fixture each; replace <name> with vuln_py_repo, vuln_js_repo, vuln_java_repo, vuln_java_gradle_repo
docker run --rm -v "${PWD}:/app" selvia-security-assistant-tools sh -c "pip install -q pydantic pyyaml && git config --global --add safe.directory '*' && cd /app && python -m app.agents.security_assistant.scan scan_output/demo_repos/<name> --out scan_output/reports/<name>_fast --skip codeql"

# everything including CodeQL (slow: minutes per language)
docker run --rm -v "${PWD}:/app" selvia-security-assistant-tools sh -c "pip install -q pydantic pyyaml && git config --global --add safe.directory '*' && cd /app && python -m app.agents.security_assistant.scan scan_output/demo_repos/<name> --out scan_output/reports/<name>_full"

# a public repository (clone, scan, delete the clone)
docker run --rm -v "${PWD}:/app" selvia-security-assistant-tools sh -c "pip install -q pydantic pyyaml && git config --global --add safe.directory '*' && cd /app && python -m app.agents.security_assistant.scan https://github.com/octocat/Hello-World --out scan_output/reports/hello_world --skip codeql"
```

Open `scan_output/reports/<name>_fast/report.md` (or `_full`) afterwards. On the host (no Docker) `uv run python -m
app.agents.security_assistant.scan <folder>` also works, but only config-scan is installed there, so the other tools are
reported as unavailable and the result is INCOMPLETE.

## Interpret the findings with the LLM (`interpret.py`)

Takes the `findings.json` of a scan plus the scanned folder. It runs on the host with `uv` (no scanner is needed) and
**sends nothing to an LLM unless `--allow-external-llm` is passed**.

```powershell
cd backend\agentic_framework
# 1. see exactly what would be sent (redacted) and how many calls; calls nothing
uv run python -m app.agents.security_assistant.interpret scan_output/reports/<name>_fast/findings.json scan_output/demo_repos/<name> --dry-run
# 2. the real run (needs SECURITY_ASSISTANT_LLM_API_KEY in .env); --delay is the pause between calls
uv run python -m app.agents.security_assistant.interpret scan_output/reports/<name>_fast/findings.json scan_output/demo_repos/<name> --allow-external-llm --delay 6 --out scan_output/reports/<name>_fast_interpreted
```

Options: `--only-category V1,V4`, `--max-findings N` (limits the number of calls), `--retries N` (bounded retries for
429/500/503, default 2). It writes `interpreted.json` and `report.md` (the normal report plus an "LLM interpretation"
section: scanner-only count versus confirmed / dismissed / uncertain, why answers are uncertain, what was merged, and
per call the status, confidence, evidence ids and rationale).

Before any call (`dedupe.py`): the same advisory for the same package reported by several tools (for example OSV-Scanner and
pip-audit) is merged, then dependency findings are grouped per package, so one call judges a package and answers for
all its advisories. Every merge is listed in the output; no scanner finding is dropped, each stays a member of its group.

The LLM cannot add findings: output with extra fields is rejected, a failed call or rejected output is `uncertain`
(with the reason), and a cited evidence id that is not in the bundle downgrades the answer to `uncertain`.
Exit codes: 0 ok, 2 some calls failed, 3 usage error, 4 refused (no `--allow-external-llm`).

## Personal data (PII) redaction (`pii.py`)

Before anything is sent to the LLM, `PIIRedactor` (next to `redaction.py`, which handles secrets) replaces personal data
with stable placeholders in every evidence item, at the same place as the secret redaction (when the bundle is built, and
once more when the prompt is built, so a hand-made bundle is covered too). `interpret --dry-run` shows the redacted text.

| What | How | Placeholder |
|---|---|---|
| email addresses | pattern | `<EMAIL_1>`, `<EMAIL_2>`, ... |
| phone numbers | pattern with a separator or `+` country code, or 0 + 9 digits (not plain digit strings, versions or IPs) | `<PHONE_n>` |
| student IDs | regex, default `\bIT\d{8}\b`; set `SECURITY_ASSISTANT_STUDENT_ID_REGEX` for another format | `<STUDENT_ID_n>` |
| names | only on labelled lines: `Author:`, `@author`, `Copyright`, `Maintainer`, `Contact`, `Written/Created/Developed by`, `Signed-off-by`, ...; afterwards the same name (and a first or last name of 4+ letters) is redacted wherever it appears in comments, strings and messages; `SECURITY_ASSISTANT_PII_KNOWN_NAMES` adds names | `<NAME_n>` |
| git metadata | author, email and message, when a caller adds them to a bundle (`redact_git_metadata`); the bundle builder does not add commit data by itself | same |
| file paths | kept as they are, except a known name, email or student ID inside the path (for example `submissions/kasun_perera/app.py` becomes `submissions/<NAME_1>/app.py`) | same |

In source code only comments and string literals are changed; identifiers and code structure never are. The mapping
(placeholder to original, and redacted path to real path) stays in memory and, after a real run, in
`pii_mapping.local.json` next to `interpreted.json` (git-ignored). It is never in a prompt and never in `interpreted.json`
or `report.md`. Do not share that file. `findings.json`, `report.md` and the scan output still contain the original
code, paths and names, so treat them like the repository itself.

**Read this before using real student code:**
- **Name detection is label based and incomplete.** A name in a sentence, a variable value, a chat log or a README
  paragraph ("thanks to Priya for the idea") is not found unless it was also seen on a labelled line, in git author data or in
  the known names. Phone and ID patterns can miss unusual formats and can match other numbers. Secret and PII redaction
  reduce the risk; they do not remove it. Always read the `--dry-run` output.
- **Real student code still needs the students' consent and ethics approval before it is used with an external LLM**
  (Google Gemini here). This tool does not replace that approval. Use the synthetic demo repositories until it exists.

## Local setup with uv (the project package manager)

The Python side is managed with [uv](https://docs.astral.sh/uv/) from `backend/agentic_framework/`
(Python 3.11, pinned in `.python-version`). The tools layer adds no Python dependency of its own: it
uses `pydantic`, `pyyaml` and `pytest`, which are already in `pyproject.toml` / `uv.lock`.

```powershell
winget install --id astral-sh.uv -e      # once; open a new terminal afterwards
cd backend\agentic_framework
uv sync                                   # creates .venv from uv.lock
uv run pytest app/agents/security_assistant tests            # the fast suite (see Testing below)
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

## Testing

Fast suite (default; mocked tools, recorded outputs, mocked LLM; no real scanner, no network, no API key):

```powershell
cd backend\agentic_framework
uv run pytest app/agents/security_assistant tests      # about 1 minute; the git based pipeline tests are the slowest
```

`pyproject.toml` deselects two markers by default: `integration` (real CodeQL, Gitleaks, TruffleHog, OSV-Scanner,
npm audit, pip-audit, actionlint, zizmor, in the Docker image; includes the 40-minute CodeQL tests) and `live` (real LLM
call, needs an API key). Run them only on request: `uv run pytest -m live`, and for scanners the Docker command above.
A bare `uv run pytest` also collects other agents' tests; some of the performance_assessment ones fail on a fresh
checkout because their mock fixture folder is git-ignored.

## LLM Semantic Interpreter (`interpreter/`)

Judges ONE finding that a scanner already produced; it cannot create findings. Input: the `Finding` plus an
`EvidenceBundle` of labelled items with ids (E1 finding metadata, E2 code snippet, E3.. context such as where
authorisation, sanitisers or a package are used), all size-limited and redacted. Output (schema-validated):
`status` confirmed / dismissed / uncertain, `rationale`, `evidence_ids`, `confidence`.

| Category | What the model is asked |
|---|---|
| V1 | is there middleware or annotation-based authorisation the scanner missed (authentication alone does not count) |
| V2 | does a custom sanitiser neutralise the input before the sink |
| V3 | is the misconfiguration real, and which is the most critical one |
| V4 | live credential or test / example value (using the redaction hints kind, length, placeholder_like) |
| V5 | is the vulnerable code path reachable |

Built-in safety: secrets are redacted before every call (and again when the prompt is built); output that fails
the schema is rejected (result `uncertain`, `output_rejected`); a cited evidence id that is not in the bundle, or a
verdict without any evidence id, is downgraded to `uncertain`; the prompt declares repository text untrusted data
and fences it in `<evidence>` blocks; an LLM error gives `uncertain` with the error, never a verdict. `hooks.py` has
the single `governance_hook(event, data)` (called before and after the call), a no-op for now.

LLM: Gemini, for this component only (`interpreter/llm.py`, `LLMClient` is a one-method protocol, so another model
is one new class). Settings in `.env.example`: `SECURITY_ASSISTANT_LLM_API_KEY` (or `GEMINI_API_KEY`), `..._MODEL`.

Seeded set for the RQ1 comparison: `interpreter/seeded/cases.json`, one real finding and one deliberate false
positive per category (10 cases, scanner-style findings with hand-written evidence). Run
`uv run python -m app.agents.security_assistant.interpreter.evaluate_seeded` (offline, a mock that answers with the
labels: plumbing only) or add `--live` for a real Gemini run.
