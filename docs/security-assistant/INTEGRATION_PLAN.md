# Security Assistant: full integration with the teammates' code (plan)

Status: **plan only, no code, nothing changed in your repository.** On approval this file is saved as `docs/security-assistant/INTEGRATION_PLAN.md` on the new branch.
How I looked: the teammates' remote branches were read through GitHub's public API and downloaded as snapshots into my scratchpad (outside the repo). I ran no `git fetch`, switched no branch and edited no file in the repo.

Decisions you already made: base = **`feature/assessment-models-sadeesha`**; my 62 commits come in by **merging `feature/init-security-agent`**; the webhook gets **its own route and secret**; the external-LLM gate is **an env setting that is off, plus an allow-list of public demo repositories**.

---

## 1. Discovery report

### 1.1 The teammates' branches (20 Oct)

| Branch | Tip | What it holds |
|---|---|---|
| `dev` | d4bf278 (PR 32) | teams, onboarding, notifications, queue, worker (what my branch already contains) |
| **`feature/assessment-models-sadeesha`** | 4787c07 | dev + the **performance assessment module**: `/performance/*` API, **GitHub webhook**, worker tasks, `perf_*` tables, code-ownership. **Chosen base.** |
| `feat/req-rag`, `feat/req-novelty` | bc90e67, c74a828 | requirements agents: `rqa_*` tables (requirements, user stories, tasks, sprints, backlog). **Older core: no teams, no `repo_url`, no webhook.** |
| others | | models, adaptive tutor, collaboration: not relevant |

`dev` has no webhook and no requirement tables. The "finished project initialisation" is the **teams flow** (in dev) plus the **requirements pipeline** (only on the `feat/req-*` line, not merged).

### 1.2 How a project is initialised (Core API, tables owned by teammates)

- `groups`: `code` (e.g. J26-SE-363, used in URLs), `name`, `term`, `status`, **`repo_url`** (String 1024), `created_by_id`, `leader_id`.
- `group_members`: `group_id`, `user_id`, `role` (`lecturer` or `member`), `term`. The leader is `groups.leader_id`.
- `users`: `keycloak_sub`, `role`, `name`, **`email`**, `student_number`, **`github_username`** (asked at onboarding), `institution`.
- `projects`: `group_id`, `title`, `description`. Requirement documents point to `project_documents`.
- Requirements, stories, tasks (**only on `feat/req-*`**): `rqa_requirements` (`requirement_ref`, `requirement_text`, `project_id`, `group_id`), `rqa_user_stories` (`story_ref`, `title`, `as_a/i_want/so_that`, `acceptance_criteria`, `jira_issue_key`, `requirement_id`), `rqa_user_story_tasks` (`user_story_id`, `title`, `description`, `jira_subtask_key`), `rqa_sprints`, `rqa_sprint_backlog_items` (`assigned_to`, `status`). **No commits table**: commits are never stored in a Core table.
- Performance module (base branch): `perf_tracked_teams` (`team_ref`, `repo_url`, roster with logins/emails/names, sprints), `perf_runs`, `perf_run_events`, `perf_assessment_results`, `perf_reviews`, ... created by one migration from `shared/performance/schema.sql`. Not mine; I do not read or write them.

### 1.3 How the repo URL is used today

Only `groups.repo_url` (team page, leader or lecturer sets it) and the performance tracking record. The team validator accepts **any URL starting with `https://`** (`schemas/team.py`), not only github.com, so my own gate must enforce github.com. The performance worker clones it into a read-only mirror.

### 1.3b The GitHub webhook that exists

`POST /api/v1/performance/webhooks/github` (public, HMAC `X-Hub-Signature-256`, secret `GITHUB_WEBHOOK_SECRET`). For push, pull_request and review events it finds tracked teams with the same repository and enqueues `performance.sync_team` on the **`performance`** queue. **It does not touch my component.** My own webhook code (`security_assistant/webhook.py`: classify push -> `secrets_only`, merged PR -> `full`, in-memory dedupe) is a plain function, not wired to any route.

### 1.4 Agents, jobs and the worker

- Contract (`shared.contracts`): `AgentName.SECURITY_ASSISTANT` and the action prefix `security` already exist (my rename). An agent implements `async handle(AgentRequest) -> AgentResponse`.
- `app/agents/registry.py::build_agent_registry()` returns `{}`: **my agent is not registered** (shared file, one entry to add).
- `start_ai_job(OrchestrationRequest)` (`server/app/services/ai_jobs.py`) enqueues the Procrastinate job `orchestration.run` on the queue named by the action prefix (`security`); the worker task `run_orchestration` calls the Main Orchestrator, which routes to the registered agent. Job status: `GET /api/v1/jobs/{id}` is **admin only**; Procrastinate **does not keep return values**.
- Worker: `backend/agentic_framework/worker.py` (`python -m worker --queues security`). Core API and worker share Postgres through `shared.queue` (`SERVER_DIRECT_URL`).
- The performance module bypasses the orchestrator (own queue, own tables, own status API). I follow the **`start_ai_job` pattern** as you required.
- `tasks/security_tasks.py` (queue `security`) holds three **stub tasks returning fake "safe" results** (`is_safe: True`, score 96.5). Nothing calls them; they stay untouched and are listed in CONFLICTS.md.
- Scanner tools: the Linux image `backend/agentic_framework/app/agents/security_assistant/Dockerfile` (pinned CodeQL, Gitleaks, TruffleHog, OSV-Scanner, actionlint, zizmor, pip-audit). Its last comment says the worker code is added "by the team's worker image build", which does not exist yet. There is no worker container in `docker-compose.yml` (only postgres, keycloak, kong, mailpit). The teammates' `agentic_framework/pyproject.toml` pulls torch and transformers: too heavy for a scanner worker.

### 1.5 Roles and team checks

Keycloak role -> `UserRole` student / lecturer / admin. `teams.team_for(db, ref, user, is_admin)`: members only, others 404; `{team}` = id or code. `require_account_role(...)` and `get_onboarded_account` in `api/deps.py`. My `app/modules/security/router.py` already uses all of this.

### 1.6 What can replace my mocks

| Mock today | Real source |
|---|---|
| requirements and stories (`traceability_samples/requirements.json`) | `rqa_requirements` + `rqa_user_stories` (id = `jira_issue_key` or `story_ref`) |
| sprint tasks (`tasks.json`) | `rqa_user_story_tasks` (id = `jira_subtask_key`, else `T-` + 8 characters of the uuid) |
| repository URL | `groups.repo_url` |
| registered student | `users.email`, `users.github_username` (GitHub noreply addresses contain the username) |
| commits and contributors | still from the repository itself (git history), as now |
| Tutor channel | stays a **labelled mock** |

### 1.7 Merge picture (checked by comparing the base snapshot with dev and my branch)

My branch is 62 commits ahead of dev. Of the teammates' files I changed (the AEGIS rename, my 5 shared edits), **only three also changed on the base branch** and will conflict: `server/app/api/v1/router.py`, `frontend/src/shared/layout/navConfig.js`, `agentic_framework/pyproject.toml`. All the others merge cleanly (`shared/contracts/agent.py`, `config.py`, `endpoints.js`, docs, tests, mock-data strings).

---

## 2. Conflicts with the existing structure and my decisions

1. **Two unmerged teammate lines.** Base = performance line; requirement tables are not in it. Decision: the Core API reads them through **lightweight read-only table definitions of only the columns I need** (my own metadata, not their ORM classes); a missing table means "no requirements in the database" and the run says so. If their branch merges later, nothing changes.
2. **Different queues** (`performance` vs `security`): the worker needs `--queues security` (documented, no code change).
3. **Stub tasks with fake results** in `security_tasks.py`: untouched; deleting them is a SHARED commit proposed for after the viva.
4. **`repo_url` accepts any https host:** my gate is github.com only, in the Core API **and again in the worker**. The scan **never takes a URL from the request**, only from the team's row.
5. **Two webhooks:** theirs and mine have different routes and secrets (GitHub supports several webhooks per repository).
6. **Heavy worker dependencies:** a separate trimmed requirements file for the security worker, no edit to their `pyproject.toml` beyond the merge.
7. **Env names:** they use `GROQ_API_KEYS`, I use `GROQ_API_KEY`; both are documented in the worker env, no change to theirs.
8. **`git fetch` is needed** to create the branch (it only updates remote-tracking refs, no working-tree change). I will tell you before I run it.

### Open questions, each with the default I will use unless you say otherwise
- **Who may start a scan:** any student member of the team (a **draft**), a lecturer of the team, an admin (**official**). Default as stated.
- **Webhook scans** are drafts (not started by a lecturer).
- **New tables: none requested.** Results, dedupe, rate limit and status use run folders (+ the existing job table, read-only). A table (`security_scans`) would be needed only if the Core API and the worker cannot share a folder (different hosts) or you want cross-run history queries. Not proposed now.
- The existing **`agent_runs`** table (unused) is **not** used.
- The shared webhook rules (HMAC check and event classification) go into **one new file** `backend/shared/src/shared/security_assistant/webhook_rules.py` so the Core API and my agent code share one copy and neither imports the other. This is a SHARED add-only commit (no teammate file edited). If you prefer no new file in `shared/`, the fallback is a copy in the Core API module with a parity test.
- **Private repositories are not supported** (no token is passed to the scanner or the clone): the run fails honestly.

---

## 3. The design in one picture

```
Browser --(team API, Keycloak token)--> Core API  /security-assistant/...
   POST scans        start_scan(): gates -> OrchestrationRequest(action="security.start_scan", input={...})
   GET  scans/{run}  status polling                                  |
   POST webhooks/github (own secret) -> same start_scan()            v
                                              start_ai_job() -> Procrastinate queue "security"  (Postgres, existing)
                                                                     |
                      worker container (tools image + trimmed deps): python -m worker --queues security
                                                                     v
                               run_orchestration -> Main Orchestrator -> SecurityAssistantAgent.handle()
                                                                     v
                         assess.run_pipeline(...)  writes  <RESULTS>/<team>/<run-id>/{status.json, run.json, report.json, audit.jsonl, ...}
                                                                     ^
   Core API reads the same folder (reader.py, existing) <---- shared volume / same path
```
The browser never reaches the AI Backend. The Core API imports no agent code. The agent never reads the Core database: **the Core API builds the whole job input** (repository URL, stories, tasks) and the worker only receives it.

**Job input** (`OrchestrationRequest.input`): `{run_id, team_code, repo_url, ref, trigger: manual|push|merged_pr, scan_type: full|secrets_only, initiated_by: {role: student|lecturer|admin|webhook}, counts_for_evaluation: bool, allow_external_llm: bool, requirements: [...], tasks: [...], requirements_source: database|none|local-demo-file}`. No names, no e-mails, no tokens.

---

## 4. Phases (each is one small, tested commit; shared files in their own `SHARED:` commit)

| # | Step | What | Tests (fast suites, no live LLM, no CodeQL) |
|---|---|---|---|
| 0 | **Branch** | `git fetch origin`; `git switch -c integration/security-assistant origin/feature/assessment-models-sadeesha`; `git merge feature/init-security-agent` resolving router.py, navConfig.js, pyproject.toml additively; commit message `SHARED: merge ...`; create `CONFLICTS.md` (section 8); never commit to dev or to their branches | both suites run: Core API (all), agent fast suite, frontend; compare counts with today (899 server, 183 frontend) |
| 1 | **Agent registration** | `security_assistant/agent.py`: `SecurityAssistantAgent` (`name=SECURITY_ASSISTANT`, action `security.start_scan`) re-validates the input and calls the pipeline; **SHARED:** one entry in `registry.py` | agent test with a fake pipeline; orchestrator -> executor -> agent in process; invalid input -> `FAILED`/`UNAVAILABLE` never "clean" |
| 2 | **Run folder + status** | the pipeline's `say` callback writes `status.json` (`queued/running/complete/incomplete/failed`, stages so far, timestamps, sanitized error); `run.json` gains `initiated_by`, `counts_for_evaluation`, `requirements_source`, `trigger`, `scan_type`; the folder name is the `run_id` the Core API chose | status written at every stage; a crash leaves `failed` with a short sanitized message; manifest has no names, e-mails or paths; golden snapshots unchanged |
| 3 | **Core input adapter** | `app/modules/security/inputs.py`: repo URL from `groups`, stories and tasks from read-only table definitions; missing table or no rows -> `requirements_source: none` (**local sample files only when the demo flag is on, and labelled**) | SQLite fixtures that create the `rqa_*` columns; no tables; empty tables; ids as in 1.6; student text length-capped |
| 4 | **`start_scan` + scan API** | one function `start_scan(db, team, account|webhook, trigger, scan_type, ref)` -> gates -> `start_ai_job`; routes `GET /teams/{team}/scan-options`, `POST /teams/{team}/scans` (202, body has no URL), `GET /teams/{team}/scans/{run}` (status.json, else the job's status: todo = "queued, waiting for a worker") | every gate below, with a fake enqueue override |
| 5 | **Webhook** | public route `/security-assistant/webhooks/github` (own secret, HMAC, event classification from `shared`), maps the repository to teams by `groups.repo_url`, calls `start_scan(trigger=push|merged_pr)`; **SHARED:** `router.py` public include, the route-protection test allow-list entry; **SHARED (add-only):** `shared/security_assistant/webhook_rules.py` | signed and unsigned bodies, wrong event, deleted branch, draft PR, unknown repo, duplicate delivery, two teams on one repo |
| 6 | **Worker environment** | new files only: `docker/security-worker/Dockerfile` (FROM the tools image; non-root; trimmed `requirements-security-worker.txt`), `docker-compose.security.yml` (service `security_worker`, `--queues security`, results volume, tmpfs workdir, CPU and memory limits, no secrets beyond the queue URL and, only when the gate is on, `GROQ_API_KEY`); a smoke script that runs the agent on the synthetic repo inside the container | image builds; the tools check passes inside; marked `integration` (manual); a fast test checks the compose file for the volume and the queue name |
| 7 | **Student <-> findings** | extend "mine": match the account's e-mail **or** the `github_username` inside a GitHub noreply commit address; flag "unlinked contributors" (counts only) for lecturers; pseudonyms stay `C-xxxxxxxx` | noreply patterns, case, no match, two accounts, no mapping file |
| 8 | **Frontend** | enable the scan control (section 6) | static-markup tests, hook logic as pure functions, screenshots |
| 9 | **Rehearsal and docs** | the viva script, the README update, CONFLICTS.md final | the demo script end to end |

### 4.1 Server-side gates in `start_scan` (all in the Core API, each with a test; the worker repeats the cheap ones)
1. Signed-in account, onboarded, **member of the team** (else 404); admin for any team.
2. Role -> draft or official: students and webhook = **draft** (`counts_for_evaluation=false`); lecturers of the team and admins = official.
3. The repository comes **only** from `groups.repo_url`; it must be `https://github.com/<owner>/<repo>` (no other host, no `file:`, no credentials in the URL, no path tricks); no URL is accepted in the request.
4. **One scan per team at a time**: the latest run folder in `queued/running` (not older than 30 minutes, then it counts as stale) -> 409 with that run's id; plus the Procrastinate `queueing_lock` per team and `lock` per team.
5. **Rate limit** per team and hour, counted from the run manifests (`requested_at`): students 3, lecturer/admin 10, webhook 10 (env-tunable) -> 429 with the time to wait.
6. **Persisted dedupe** (replaces my in-memory store): a run of the same repository, commit and scan type that is queued, running or complete (a full scan covers a secrets-only one) -> 200 with the existing run id, nothing queued.
7. **External LLM gate**: `allow_external_llm` is true only if `SECURITY_ASSISTANT_ALLOW_EXTERNAL_LLM=true` **or** the repository is in `SECURITY_ASSISTANT_LLM_REPO_ALLOWLIST` (public synthetic demo repositories); the worker checks its own env as well. Otherwise the LLM stages are **skipped and the run is INCOMPLETE** (never clean).
8. Demo flag on -> real scans are refused ("demo data").
9. Size and time limits (existing tool timeouts, a clone-size cap); nothing from the repository is executed (CodeQL `build-mode=none`); redaction and PII scrubbing as today; failed or skipped tools show as such.

### 4.2 Where results are stored
Run folders first, exactly as now (`<RESULTS>/<team-code>/<run-id>/`), now written by the worker. `SECURITY_ASSISTANT_RESULTS_DIR` is the same path for the Core API and the worker (shared volume in compose, same host in development). **No table.** If the worker and Core API ever run on different hosts, the answer is a shared volume or object storage, or a table I would propose then.

---

## 5. Agent, worker and job path in detail
- **Registration:** `registry.py` gets `AgentName.SECURITY_ASSISTANT: SecurityAssistantAgent()` (SHARED, 2 lines). The existing orchestrator needs no change.
- **Invocation:** `start_ai_job(OrchestrationRequest(action="security.start_scan", requester=..., group_id=<team id>, input=...))` -> queue `security`.
- **Status polling:** `GET /scans/{run}` returns `status.json` of the run folder; before the worker writes anything it maps the job: `todo` = queued, `doing` = running (the job is found through `procrastinate_app.job_manager`, and only if its `group_id` is the caller's team), `failed` = failed. The Core API never exposes another team's job. The job id itself is not shown to students.
- **Worker environment for the scanners:** a Linux container built from the tools image, non-root, read-only root filesystem where possible, a tmpfs work directory that is deleted after each run, outbound access only to github.com (and the LLM host when the gate is on), CPU and memory limits, the queue URL as its only database credential. Windows hosts run the worker in this container (the tools are Linux binaries).
- **One `start_scan` function** is the single way a scan starts: manual requests and the webhook call it; nothing else enqueues a security job.
- **Tutor Channel B:** stays the `MockTutor`, labelled MOCK everywhere (unchanged).

---

## 6. Frontend changes (my folder only; no teammate file edited beyond what the merge needs)
- `StartScanControl` becomes real: shown for lecturers/admins ("Start an official scan") and students ("Start a draft scan"); a confirm dialog states the repository, that a student scan is a **draft and never counts for evaluation**, and whether the LLM will run (from `scan-options`); disabled with the reason when the team has no github.com repository, a scan is running, the limit is reached, or demo mode is on.
- After starting: polling with TanStack `refetchInterval` (2 s) on `scans/{run}` until a final state; a live stage strip; on completion the runs list, overview and findings refresh and the new run opens.
- Badges: **Draft** / **Official**, trigger (manual, push, merged PR), requirements source (database, none, demo file), INCOMPLETE reasons including "LLM not allowed for this repository".
- Demo mode stays explicit (`VITE_SECURITY_ASSISTANT_DEMO`, server `SECURITY_ASSISTANT_DEMO_MODE`), always labelled "demo data", never a fallback after an error. The existing mock security pages are untouched and keep working.

---

## 7. Tests per step (summary)
Step 1-2: agent and status unit tests, orchestrator in-process, golden snapshots unchanged. Step 3: adapter against SQLite fixtures (real column names). Step 4: one test per gate (non-member 404, student draft, wrong host, URL in body ignored, running scan 409, rate limit 429, dedupe 200, LLM gate on/off, demo refuses) with a fake enqueue, and the route-protection test. Step 5: HMAC and classification matrix. Step 6: compose/Dockerfile checks (fast) and a manual `integration` smoke. Step 7: identity patterns. Step 8: static-markup tests and screenshots. Always: no live LLM, no CodeQL in the fast suites.

---

## 8. CONFLICTS.md (format)

Created in step 0 at the repository root. One row per shared or teammate-owned file I touch (plus a section for the 22 files my earlier AEGIS rename already changed):

| # | File | Owner | What I changed (lines) | Why | Commit (`SHARED:`) | Undo | Re-apply |
|---|---|---|---|---|---|---|---|
| 1 | `backend/agentic_framework/app/agents/registry.py` | common | +1 import, +1 entry | register the agent | `<sha>` | `git revert <sha>` | `git cherry-pick <sha>` |

Rules: every edit to a shared file is its own commit starting with `SHARED:`; `git log --grep='^SHARED:' --oneline` lists them all; the file also states per row whether a later merge conflict is likely and how to resolve it (take theirs, then re-apply my lines). Planned entries: the step-0 merge (router.py, navConfig.js, pyproject.toml), `registry.py`, `config.py` (new settings), `router.py` (public webhook include), `test_route_protection.py` (allow-list), the two `.env.example` files (new variables), `shared/security_assistant/webhook_rules.py` (new file), and **no edit** to `docker-compose.yml`, `performance.py`, `performance_tasks.py` or `security_tasks.py`.

---

## 9. Viva demo script (about 10 minutes, one real scan from the UI)

Prepare: a public synthetic demo repository on github.com whose commits are authored with the demo student's GitHub noreply address; it is the team's `repo_url` and is in the LLM allow-list; the worker container is running; two registered accounts (a lecturer and the student, a member of the team); the two webhooks configured; `GITHUB_WEBHOOK` replay script ready.
1. Log in as the **registered student**: open *Security Assistant (live results)*; the page shows the team's earlier runs and the **Start a draft scan** button with the explanation.
2. Click it, confirm the dialog (repository, **draft, does not count for evaluation**, LLM allowed for this demo repository). Watch the **live stages** (fetch, scan, governance, interpret, trace, risk, guidance, questions) tick through; click again to show **409 "a scan is already running"**.
3. When it finishes the new run opens: **Draft** badge, provenance (commit, trigger manual, read-only clone deleted afterwards), findings by type, **"Only my findings"** works because the introducing commits match the student, a finding card with the V4 line hidden, learning page labelled MOCK.
4. Show a **failed or skipped** state is not clean: start a scan on a repository outside the allow-list (LLM skipped) -> INCOMPLETE with the reason.
5. Log in as the **lecturer**: start an **official** scan; compare the two runs; open the agents page and the audit table (hashes only).
6. Trigger the **webhook** with the signed replay (push, then the merged PR): a `secrets_only` run and a `full` run appear with trigger labels; replay the same delivery again to show dedupe.
7. Privacy: log in as a student of another team (404), show only pseudonyms, and the demo flag page (explicitly labelled "demo data").

---

## 9b. Approved decisions and amendments (supersede anything above)

Approved: students start drafts, lecturers and admins official; webhook scans are drafts; no new tables; `shared/security_assistant/webhook_rules.py` as an add-only file; private repositories unsupported.

1. **Step 0 report before step 1:** show each merge conflict and how it was resolved, plus Core API, agent and frontend test counts against today's (899 passed / 7 skipped server; agent fast suite; 183 frontend). **Stop if any count drops.** Stop after step 0 and show the merge report.
2. **Requirements:** if the `rqa_*` tables are missing on this branch the run says so (`requirements_source: none`). Local sample files only when demo mode is on, labelled. I tell you how to load requirement rows locally (dev DB only, never committed) for a real-traceability demo.
3. **Build order change:** step 6 (worker container smoke test) is done **right after step 2**. The report says how the worker reaches the scanners, Postgres and the results volume.
4. **Extra test:** a crashed worker leaves a stale run (`status.json` stuck in `running`) that stops blocking the team after the timeout.
5. **Webhook demo:** the signed replay is the primary demo path; a tunnel is optional.
Same rules: one commit per step, `SHARED:` prefix for shared files, CONFLICTS.md kept current, fast suites only, no live LLM, no CodeQL in the fast suites.

---

## 10. Verification before I call it done
Core API suite, agent fast suite and frontend suite all green on the integration branch; the step-0 conflict resolutions reviewed against CONFLICTS.md; one end-to-end scan through the real queue and the worker container on the demo repository; `git log --grep='^SHARED:'` matches CONFLICTS.md row for row; no teammate file changed except those rows.

Out of scope (so nothing is assumed): any new table or column, using `agent_runs`, private repositories, a real Tutor, editing the teammates' performance or planning code, and deleting the teammates' stub tasks (proposed for after the viva).
