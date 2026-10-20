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

## Fix advice for students (`guidance.py`)

Every finding comes with advice on how to fix it, from two sources:

1. **Standard advice (always, no LLM).** `guidance.py` has one entry per type of issue, written by the team: why it
   matters, 2-4 fix steps, a short corrected example in the language of the affected file (Python, JavaScript/TypeScript,
   Java, or `ci` for workflow files) and a link (an OWASP cheat sheet, plus the CWE page). The entry is chosen by rule id,
   then by CWE, then by a general entry for the category, so no finding is left without advice. `report.md` (from `scan` and
   from `interpret`) shows it as a section "How to fix (by type of issue)" with the locations it applies to, and every
   finding links to its entry; `findings.json` records the entry id in `fix_pattern`.
2. **A tailored note from the LLM, for confirmed findings only.** The verdict has a `recommendation` field (2-3 sentences
   about this code, at most 6 lines of example, based on the evidence and the standard advice, no invented APIs). It is
   dropped for dismissed and uncertain findings, and for answers that were downgraded; secrets in it are masked. It
   appears in `interpreted.json` and in the report section "How to fix the confirmed findings", marked as a suggestion
   to review and test, not a patch.
   Models invent concrete values (a "fixed in 2.0.0" that is wrong, a commit SHA), so the prompt forbids them and the code
   enforces it: a note that contains a version number, 40-character SHA or URL that appears nowhere in the evidence, the
   finding or the standard advice is not kept (`recommendation_dropped` says why) and the report falls back to the standard
   advice. The standard dependency examples therefore use placeholders such as `<fixed version>`.
   OSV-Scanner reports the versions that fix each advisory; they are read from the affected package's own ecosystem ranges
   (SEMVER or ECOSYSTEM, same name and ecosystem; GIT ranges list commit hashes and are ignored), stored in
   `Finding.fixed_versions`, shown in `report.md` ("Fixed in") and given to the LLM as evidence, so its upgrade advice can
   name a real version and the guard above accepts it.

To add or change advice, edit the table in `guidance.py` (the tests check that every rule the tools can produce has
specific advice, that examples are short and hold no secret, and that the links are the ones that were checked).

## Traceability: from a finding to its commit, story and task (`trace.py`)

```
python -m app.agents.security_assistant.trace <interpreted.json> <repo> [--requirements F] [--tasks F]
        [--propose-links --allow-external-llm [--dry-run] [--delay S] [--retries N]] [--out DIR]
```

It traces the **confirmed** findings of `interpreted.json` and writes `traced.json` plus a "Traceability" section in
`report.md` (replaced on every run, the rest of the report is kept).

- **Introducing commit** = the commit that added the line, found read-only with `git log -L<line>,<line>:<file>` (the oldest
  entry). For a secret that was deleted (history only) the search starts at the commit the scanner reported. A dependency
  without a line uses the first commit that added the package name to the file (`git log -S`). If nothing is found the
  output says "no introducing commit found". The wording is deliberately "introducing commit", never "blame".
- **Contributors** appear only as `C-xxxxxxxx`, a keyed hash of the author's email. The real name and email are only in
  `trace_mapping.local.json` (git-ignored, next to the outputs, never in a prompt, report or JSON). Reuse the output folder or set
  `SECURITY_ASSISTANT_PSEUDONYM_SALT` to keep ids stable between runs. Commit subjects go through the PII redactor and the
  author's name is removed from them too.
- **Input files** (local JSON, the working contract with the future Requirements agent; samples in `traceability_samples/`):
  `requirements.json` = `{"stories": [{"id", "title", "acceptance_criteria": []}]}`,
  `tasks.json` = `{"tasks": [{"id", "title", "sprint", "story_id", "commits": [sha]}]}`. Both are optional; a wrong format
  stops the run (exit 3). Without a requirements file the report says so and findings are linked to commits only.
- **Verified or candidate.** A link is `verified` only when a rule supports it: the introducing commit's message names the
  story/task id (0.95), the task lists the commit (0.95), the task's story (0.90), or the file/endpoint appears in exactly one
  story or one task (0.70; if several mention it the match is too vague and stays unverified). Anything else is a `candidate`.
  Ids that do not exist are rejected and listed. Each link records its methods, evidence and confidence.
- **LLM proposals** (`--propose-links`): per confirmed finding the model proposes one candidate story and task, citing evidence
  ids (E1 finding, E2 introducing commit without author, E3 stories, E4 tasks). Same safety rules as `interpret`: labelled
  bundle, secrets and personal data redacted, strict schema, fake evidence ids or malformed output = no link, a failed call =
  no link (exit 2), a story/task id not in the files = rejected. It needs `--allow-external-llm`; `--dry-run` shows what would
  be sent.

Exit codes: 0 ok, 2 some proposals failed, 3 usage error, 4 refused (no `--allow-external-llm`).

## Risk prioritisation (`risk.py`)

```
python -m app.agents.security_assistant.risk <interpreted.json> [repo folder] [--out DIR]
```

A transparent rule engine, **no LLM scoring**. `score = 100 x sum(weight x factor)` over six factors between 0 and 1:

| factor | weight | value |
|---|---|---|
| severity | 0.30 | the tool's own severity: critical or CVSS 9+ 1.0, high / 7+ 0.8, medium or moderate / 4+ 0.5, low 0.2, none given 0.4 (a package group uses its highest advisory) |
| category | 0.15 | V1 1.0, V2 1.0, V4 0.9, V3 0.8, V5 0.7 |
| llm_status | 0.20 | confirmed 1.0, uncertain 0.4 (the down-weight); **dismissed findings are not ranked** and are listed under "Not ranked" |
| llm_confidence | 0.10 | the model's confidence in its own status |
| exposure | 0.15 | by type of issue (a public workflow trigger 1.0, ownership check / injection 0.9, ... dependency 0.5); a named HTTP endpoint or function raises it to at least 0.9 |
| presence | 0.10 | in the current files 1.0, only in the git history 0.6 (a secret whose file is gone or whose line no longer holds it; needs the repo folder, otherwise it is counted as current and the report says so) |

Each factor is stored with its weight, value, contribution (`100 x weight x value`, rounded to 2 decimals) and the reason; the
score is the sum of the rounded contributions, so the breakdown adds up exactly. Ties are broken by category, rule id, group
id, so the order never depends on the input order. Outputs: `risk.json` (weights, ranked list with the breakdown, excluded list)
and a ranked table with the breakdown in `report.md`. The weights are a starting point for the team to review, not a
measured probability.

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
  (Groq here). This tool does not replace that approval. Use the synthetic demo repositories until it exists.

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

LLM: Groq, for this component only: its own small client in `interpreter/llm.py` (plain httpx against Groq's
OpenAI-compatible `chat/completions`), behind the one-method `LLMClient` protocol, so another provider is one new class.
Nothing from performance_assessment is imported or changed. Settings (in `.env`, never printed): `SECURITY_ASSISTANT_LLM_API_KEY`
(a Groq key, `gsk_...`; any other key is refused so it is never sent to Groq) and `SECURITY_ASSISTANT_LLM_MODEL` (**required, no
default**, because models get retired; if either is missing the command stops with a clear message), optional
`SECURITY_ASSISTANT_LLM_TIMEOUT` and `SECURITY_ASSISTANT_LLM_MAX_TOKENS` (default 4096, reasoning models also spend it on thinking).

Output format (Groq docs, structured outputs): for `openai/gpt-oss-20b`, `openai/gpt-oss-120b`, `qwen/qwen3.8-27b` and
`meta-models/muse-spark-open` the request uses `json_schema` with `strict: true` (output constrained to the verdict schema);
every other model gets JSON Object Mode. Both are validated again by the interpreter. Retries are bounded (`--retries`),
waits follow `retry-after` (seconds, capped at 60 s: a longer one is reported, not waited out). Every call keeps a call
record in `interpreted.json` (model, format, attempts, HTTP status, finish reason, output length, token usage; never the
model's text), and a rejected answer says in its reason, for example, `finish_reason=length` (cut off by the output limit).

Evidence for secret findings (V4): besides the code snippet, the bundle has an item "details about the secret (its value
is never shown)": the masked value from the scanner, the kind and length of the value and whether it looks like a
placeholder (measured by reading the line locally, only the measurement is kept), whether it is in the current files or
only in the git history (a file that was deleted later), the introducing commit's date and message (personal data
redacted) and, for a history-only secret, the masked line as it was in that commit. History is read with read-only
`git show` on the scanned folder, using only the commit id and path from the finding after checking their format. If the
folder has no history, or the commit cannot be read, the item says "unknown" instead of guessing.

Every call uses temperature 0.0, the lowest Groq accepts (range 0 to 2), which makes the answers as repeatable as
Groq allows but does not guarantee identical output. `interpreted.json` records the model, prompt version and temperature
in `meta`, and each result's `call` record also holds the temperature.

Seeded set for the RQ1 comparison: `interpreter/seeded/cases.json`, one real finding and one deliberate false
positive per category (10 cases, scanner-style findings with hand-written evidence). Run
`uv run python -m app.agents.security_assistant.interpreter.evaluate_seeded` (offline, a mock that answers with the
labels: plumbing only) or add `--live` for a real Groq run.
