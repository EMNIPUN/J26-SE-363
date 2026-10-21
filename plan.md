# Assessment agent: end-to-end integration plan

> After approval this file is copied to `C:\Users\sadee\OneDrive\Documents\Simultanious Work\J26-SE-363\plan.md` on branch `feature/assessment-agent-integration-sadeesha`.

## Context

The seven factor packages exist (Collaboration, Behavioral Pattern, Code Ownership have production entry points; Effort, Consistency, Task Complexity have trained/validated models but no `evaluate.py`; Requirement Fulfillment has a LangGraph sub-agent that runs on a synthetic benchmark). The `com_agent` graph runs on real LangGraph but almost everything around it is mock: GitHub and Scrum clients are stubs, there is no clone, several features are hard-coded, results are not saved, the checkpointer is in-memory, nothing streams progress, the worker tasks return placeholders, the server has no performance endpoints and the frontend uses mock data with no pipeline view.

**Goal (the finish line for the assessment agent):** a lecturer gives a team (repo link + Scrum board) and starts tracking; the agent collects evidence through the whole sprint, evaluates every student with the factors as tools, checks and debugs suspicious results, asks a human when needed, and produces predicted marks with a justification per factor, a final report, and a day-by-day development view. The frontend shows the live pipeline (every node, its logs, the active node glowing, the glow travelling along edges) and the results for lecturers and students.

**Decisions already taken with the user**
- Scrum board: our own planning module. A small **MCP server script** exposes its data to the agent (not a new board).
- Sandbox: **read only** (git history, diffs, blame, syntax trees). No student code is executed, so no containers.
- Timing: tracking starts at sprint start; continuous cheap evidence sync; nightly staggered provisional snapshots; queued, rate-limited runs; the agent's memory persists in Postgres (one LangGraph thread per team-sprint), not in a long-running process.

## 1. When assessment happens (and lack of data during development)

**Lifecycle per team**
1. `start tracking` (lecturer) creates the team's tracking record (repo URL, board id, sprint calendar, roster, GitHub usernames and commit e-mails).
2. **Sync** (cheap, no LLM): GitHub webhook on push/PR/review, plus a periodic sync every 2 hours as a safety net. Fetches into the cached mirror; stores new commits/PR events. Seconds per team.
3. **Nightly snapshot** (staggered: `hash(team_id) % window`): provisional factor results to date for each student. Only what changed since the last snapshot is recomputed (cache keyed by commit SHA set, task status, PR ids).
4. **Sprint-end run** (deadline or lecturer trigger): final run. Most of the work is already cached, so it is incremental. The Code Ownership quiz is issued here.
5. **Resume events**: quiz answers, quiz timeouts, lecturer review decisions resume the same persisted thread.

**Why no crash at the deadline:** runs are jobs on the existing Procrastinate queue with a fixed number of worker slots (heavy LLM/encoder work on its own queue), a per-team lock (no duplicate runs), and incremental computation. 250 students become 250 queued student sub-runs that drain at the workers' pace; nothing runs unbounded.

**Lack of data during the sprint (the known weakness of starting early), handled explicitly:**
- **Provisional, never final, before sprint end.** Every snapshot result carries `status: provisional`, `as_of`, `sprint_elapsed` (0-1) and a confidence interval that is wide early and narrows.
- **Per-factor evidence gates** (a factor reports "not enough evidence yet" instead of a misleading number):

| Factor | Can be computed during the sprint when | Before that |
|---|---|---|
| Effort | at least 1 working day elapsed; reported as effort-to-date and pace | "no activity yet" |
| Consistency | at least 5 days elapsed (rhythm needs a window) | not available |
| Requirement Fulfillment | per task, once the task is In Review or Done (only those tasks are judged) | tasks in progress listed, not scored |
| Collaboration | as soon as the team has any review; otherwise "not available" (existing gate) | not available |
| Task Complexity | as soon as tasks are assigned (it is measured before the work) | available from day 1 |
| Code Ownership | only at sprint end (quiz) | passive context only (survival, primary-owner share) |
| Behavioral Pattern | only when its inputs are final; during the sprint shown as "tendency" without a modifier | not applied |

- **Pace instead of totals early on.** Effort and activity are compared with the expected curve at the same point of the sprint: the student's own earlier sprints (cross-sprint memory) and the cohort's typical curve at that day fraction. This gives early warnings ("behind own usual pace", "no commits for 5 days", "task in progress for 8 days without commits") without pretending to know the final mark.
- **First sprint of a student:** no history, so only absolute indicators and "insufficient data" labels.
- The **day-by-day view** plots provisional results with their bands; the final mark appears only after the sprint-end run.

## 2. What data each factor needs (team context vs one student)

Evidence is collected **once per team** (one clone, one GitHub fetch, one board read) and turned into one `evidence/1` per student. Scoring is per student. A student's result only contains their own data plus aggregate counts about the team.

| Factor | Needs other members' code/data? | Why |
|---|---|---|
| Effort | No (own commits); repo needed for file classification and line stats | |
| Consistency | No (own commit timestamps) | |
| Requirement Fulfillment | Reads the surrounding repo code as context; scores only the student's own changes | judging whether a criterion is met needs the code around the change |
| Collaboration | Team review counts only (no other student's text exposed) | evidence gate: did the team review at all |
| Task Complexity | **Yes**: whole-repo import graph before the task | dependency reach is a property of the codebase |
| Code Ownership | **Yes**: blame over the whole repo | who owns surviving lines needs everyone's history |
| Behavioral Pattern | No (the student's other factor scores) | |

So the unit of a run is **a team-sprint**, with per-student sub-runs inside it.

## 3. Architecture

```
Frontend (React)  --REST/SSE-->  Core API (FastAPI :8002, /api/v1/performance)
                                   |  enqueue jobs (Procrastinate on Postgres), read results/events
                                   v
                          Postgres (server DB): performance tables, run events, LangGraph checkpoints/store, queue
                                   ^
                                   |  worker (backend/agentic_framework/worker.py, queues: performance, performance_heavy)
                          Assessment agent (LangGraph): team graph -> student subgraph -> RF sub-agent
                                   |               |                    |
                         Workspace manager    GitHub REST          Scrum MCP server script (stdio)
                         (git mirror+worktree) (PRs, reviews)       (planning module data)
                                   |
                         factor_models/* (evaluate.py per factor)
```

Agent code stays in `backend/agentic_framework/app/agents/performance_assessment/` (owned by the user, CI-guarded). Server code goes in `backend/server/app/modules/performance/`.

## 4. Workspace (sandbox) manager: read-only git

New module `performance_assessment/workspace/` (reuses `com_agent/ingestion/git_sandbox_runner.py` whitelisted read-only commands):
- `WorkspaceManager(root, max_total_bytes, ttl)`.
- `ensure_mirror(repo_url)`: `git clone --mirror --filter=blob:none` once, `git fetch --prune` afterwards; token passed through `GIT_ASKPASS`/env, never written to disk.
- `checkout(repo, ref, as_of) -> Worktree` (context manager): `git worktree add --detach` at the sprint-end commit or at the snapshot time; removed after the run.
- Size limits, TTL cleanup, one lock per mirror, path containment checks.
- Only read operations: log/numstat/patch, show, blame `-w`, `ls-tree`, file reads for syntax trees. No build, no install, no execution.
- Open-source: plain `git` CLI (already used). If code execution is ever needed later: `llm-sandbox` (Docker) or E2B; not part of this plan.

## 5. Ingestion and MCP

- **Scrum MCP server script** `performance_assessment/mcp_servers/scrum_board_server.py` (Python `mcp` SDK, FastMCP, stdio). Tools match the existing `ScrumMCPClientProtocol` plus two more: `list_sprints(team)`, `get_sprint_details(sprint)`, `get_student_tasks(student, sprint)`, `get_task_acceptance_criteria(task)`, `get_task_status_history(task)`, `get_team_roster(team)`. Data source behind it is pluggable: JSON/CSV fixtures now (from `dataset/scrum_board`), the planning module's tables later. The agent side implements `RealScrumMCPClient` with the `mcp` client (stdio).
- **GitHub**: `RealGitHubClient` over the REST API with `httpx` (PRs, reviews, review comments, issue comments, merged-by), ETag caching, rate-limit handling. Repository content comes from the workspace, not the API.
- **Evidence builder** (`ingestion/evidence_builder.py`): replaces the hard-coded features. From the worktree + GitHub + board it builds `evidence/1` per student using the existing pieces: `evidence/lines.py` (counted lines), the dataset scripts' logic (`dataset/scripts/01_extract_evidence.py`, `09_clean_commit_stats.py`, `11_clean_blame_real.py`, `repo_analysis.py` for import-graph reach and ownership), and `synthetic_students/to_evidence.py` as the schema reference.
- **Identity resolution**: commit e-mails/usernames mapped to students from the roster; unmapped authors are reported, and the run pauses for a lecturer mapping when they hold a meaningful share of the code.
- **Evidence store**: evidence is saved per student-sprint with `as_of` and a hash of its inputs (incremental reuse).

## 6. Agent graph

Three levels. Every node emits events (section 9), so the frontend can draw the same graph.

**6.1 Team run graph `team_assessment`** (one persisted thread per team-sprint; `thread_id = team:{team}:sprint:{sprint}`)
1. `load_run_context`: team, sprint window, roster, config, mode (snapshot or final).
2. `prepare_workspace`: mirror fetch, worktree at the right point in time.
3. `collect_scrum`: MCP calls.
4. `collect_github`: PRs, reviews, comments.
5. `build_team_evidence`: `evidence/1` per student, blame, reach, data-quality report.
6. `evidence_quality_gate`: deterministic checks (unmapped authors, empty sprint, history rewrites, clock skew). It can interrupt for identity mapping.
7. `dispatch_students`: LangGraph `Send` to one `student_assessment` subgraph per student, run in parallel, bounded by the worker.
8. `team_cross_check`: duplicate credit, co-authored commits, tasks claimed by two students, team-level anomalies.
9. `team_review_gate`: one interrupt collecting all open review items for the lecturer.
10. `team_report`: team summary and lecturer report.
11. `publish`: persist, notify the lecturer and students.

**6.2 Student subgraph `student_assessment`**
1. `student_evidence_check`
2. In parallel: `factor_effort`, `factor_consistency`, `factor_collaboration`, `factor_task_complexity`, `rf_subagent` (subgraph)
3. `join_factors`
4. `factor_audit` (the agent's judgement, see 6.4), which can go to `factor_debug` and re-run, at most 2 times per factor.
5. `ownership_quiz_generate`, then `await_quiz_answer` (interrupt, existing 48 h + 48 h extension + 0.50 cap + double-timeout policy), then `ownership_quiz_score`. Final runs only.
6. `behavioral_pattern`
7. `fusion`: `S = BP_modifier * sum(w_k * factor_k)`, with redistribution for factors that are not available, and an interval propagated from the factor intervals.
8. `discrepancy_check`, then `human_review` (interrupt) when a CRITICAL flag or an audit escalation occurs.
9. `explain`: LLM, grounded only in factor results (features, removed, warnings, citations); PII redacted before and restored after.
10. `student_result_export`

**6.3 Requirement Fulfillment sub-agent** (reuse `03_requirement_fulfillment/experiments/agent_critic.py`): `map_commits → decide ↔ act (tools) → record → check → critique → revise`, per task and criterion. New adapter: `Scope` over the real `evidence/1` + worktree (`list_commits`, `search_changes`, `read_hunk`, `read_file_context`) with the same rule that only the student's own changes can be cited. LLM through the existing `GroqPool` (keys from env, budgets per run). Verdicts are cached by `(task, criterion, commit-set hash)`.

**6.4 The agent knows the factors, checks results and debugs**
- **Factor cards**: each factor folder gets `FACTOR_CARD.md` plus `card.json`, generated from its README/PROTOCOL. They cover what it measures, inputs, formula, validation results and limits, what each warning means, typical failure causes and remedies. The audit node and the explanation node read them.
- **`factor_audit`**: deterministic checks first (range, versions, `extrapolated` flags, warnings, gate status, internal contradictions such as high Effort with zero commits, or a jump against yesterday's snapshot or the student's history). Then an LLM auditor with constrained tools: `get_factor_card`, `inspect_evidence(student, factor)`, `compare_with_history`, `rerun_factor(factor, fix)` (allowed fixes only: identity mapping, excluding commits flagged as generated or vendored, re-fetching evidence), `mark_not_available(reason)`, `escalate_to_human(reason)`.
- **The LLM can never set a score.** Scores come only from the factor packages. Every audit decision is logged with its reason and shown in the UI and the report.

**6.5 Human in the loop**: identity mapping (6.1 step 6), student-level review (6.2 step 8), the team review gate (6.1 step 9). The lecturer can accept, override with a reason, or request a re-run. Overrides are stored next to the model's value and never replace it silently.

## 7. Factor integration work

- `evaluate.py` for Effort, Consistency and Task Complexity: `schema.validate → cleaning.featurize → model.predict` from the chosen experiment results (`training/experiments/*/results/model_choice.json`), with intervals and gates. Saved artifacts go in each factor's `model/` (as done for Code Ownership).
- Requirement Fulfillment `evaluate.py`: runs the sub-agent through the adapter; `simulate.py` stays as a fallback.
- Code Ownership: already production (CodeBERT + SVR head, final test MAE 0.137, Spearman 0.88 on assistant-written data). Needs torch, transformers, scikit-learn and joblib in the agent's environment, and the encoder weights cached.
- Collaboration and Behavioral Pattern: done (merge their branches).
- `factor_bridge.py`: pass the `evidence/1` reference, check `versions`, add the "provisional mode" flag, and return `not available` as its own status (not 0) everywhere.

## 8. Persistence (server Postgres, alembic, schema `performance`)

`tracked_teams` (repo, board, schedule, status) · `sprints` (team, number, start, end, board id) · `identity_map` · `evidence` (student-sprint, as_of, inputs hash, json) · `assessment_runs` (extends `agent_runs`: team, sprint, mode, thread id, status, current node) · `run_events` (run, seq, ts, node path, type, payload) · `factor_results` (run, student, factor, score, interval, status, features, warnings, versions, audit decision) · `assessment_results` (final per student-sprint, mark, interval, justification, overrides) · `snapshots` (daily provisional per student) · `reviews` (open/decided, decision, reason) · `quizzes` (snippet, question, deadlines, answer, score).

LangGraph `PostgresSaver` and `PostgresStore` (`langgraph-checkpoint-postgres`) in the same database replace the in-memory saver. The separate `assessment_db` on port 5434 is retired.

## 9. Job queue, events and live progress

**Procrastinate tasks** (`app/tasks/performance_tasks.py`, which already has placeholders):
- `performance.sync_team`: periodic every 2 h, and on webhook.
- `performance.snapshot_team`: nightly cron, staggered.
- `performance.assess_team`: final or on demand, queue `performance_heavy`.
- `performance.resume_run`: quiz answer, review decision, identity mapping.
- `performance.quiz_timeout_sweep`: periodic.

Locks are per team (`lock=team_id`, `queueing_lock`). Worker concurrency is configurable. The encoder model is loaded once per worker process.

**Events**: the worker runs the graph with `astream(stream_mode=["updates", "custom", "debug"], subgraphs=True)`. An event writer stores node start/finish, logs, tool calls, LLM calls (redacted), interrupts and errors in `run_events`, with `pg_notify`. The graph topology comes from `graph.get_graph(xray=True)` and is exported as JSON, so the UI draws exactly the real graph.

## 10. FastAPI endpoints (`/api/v1/performance`, lecturer/admin unless noted)

Every route is protected through the existing deps (`require_account_role`).

| Method and path | Purpose |
|---|---|
| `POST /teams/{team}/tracking` · `GET` · `DELETE` | start, read or stop tracking (repo, board, schedule, roster mapping) |
| `POST /teams/{team}/sync` | manual sync (202 + job id) |
| `POST /teams/{team}/runs` | start a run `{sprint, mode: snapshot or final}`; returns 202 + run id |
| `GET /runs/{run}` · `POST /runs/{run}/cancel` | run status, current node, timings |
| `GET /runs/{run}/graph` | topology (nodes, edges, subgraph groups) |
| `GET /runs/{run}/events?after=seq` · `GET /runs/{run}/stream` | polling, and SSE (Last-Event-ID resume) |
| `GET /runs/{run}/nodes/{path}` | logs, inputs/outputs summary, tool calls of one node |
| `GET /teams/{team}/sprints/{sprint}/results` | all students: marks, factor scores, flags |
| `GET /teams/{team}/students/{student}/results?sprint=` | one student: mark, interval, per-factor justification, evidence links |
| `GET /teams/{team}/students/{student}/trajectory?sprint=` | day-by-day provisional snapshots |
| `GET /reviews?status=open` · `POST /reviews/{id}/decision` | review queue and decisions |
| `POST /teams/{team}/identity-map` | resolve unmapped authors |
| `GET /runs/{run}/report` | lecturer report (markdown; PDF later) |
| student `GET /me/performance?sprint=` | own results and feedback only |
| student `GET /me/quizzes` · `POST /me/quizzes/{id}/answer` | pending quiz and answer |
| `POST /webhooks/github` | HMAC-verified (the documented exception to the auth rule) |

## 11. Frontend (`frontend/src/modules/performance/`)

**Live pipeline** (`pages/instructor/RunPipeline.jsx`): `@xyflow/react` with `elkjs` layout.
- **Node states:** idle, active, done, failed, waiting for a human.
- **Active node:** a rotating glow border (CSS conic-gradient animated with `@property`).
- **Moving glow:** a custom "comet" edge (SVG `animateMotion` along the edge path) shows the glow travelling from the finished node to the next active one.
- **Layout:** student sub-runs are collapsible lanes, and the RF sub-agent is an expandable group.
- **Node drawer:** click a node to see its logs (virtualised), inputs/outputs summary, tool calls, duration and errors.
- **Controls:** cancel and re-run.
- **Data:** `GET /graph` once, then the SSE stream (fetch-based so the auth header is sent), with react-query polling of `/events?after=` as the fallback.

**Lecturer pages**
- **Team results:** students × factors table with provisional/final badges, flags and intervals.
- **Student detail:** mark with interval; a factor card per factor with its justification, evidence links (commits, PRs, tasks), warnings and audit decisions; a "what changed since yesterday" view.
- **Development view:** a day-by-day chart (recharts) of the provisional mark and each factor, with bands.
- **Review queue:** accept, override with a reason, or re-run.
- **Tracking setup:** repo, board, roster mapping.
- **Report download.**

**Student pages**
- **My progress:** own provisional and final results and feedback, never peers' data.
- **Quiz:** the code snippet, the question, a countdown and submission.

## 12. Delivery phases

| Phase | Content | Done when |
|---|---|---|
| P0 Foundations | dependency approvals; Postgres checkpointer and store; performance tables (alembic); fix known bugs (validation edge ignored, undeclared state keys, timeout sweep reading `.storage`, Dockerfile requirements path) | graph resumes from Postgres after a restart |
| P1 Workspace and evidence | workspace manager, GitHub REST, Scrum MCP server script and client, evidence builder, identity map | `evidence/1` for every student of a real team repo, matching the dataset scripts on a known team |
| P2 Factors | `evaluate.py` for E, C, TC, RF (adapter), merge CO, Co and BP; factor cards; provisional mode and gates | each factor returns score, interval, status and warnings from real evidence |
| P3 Agent graph | team graph, student subgraph, RF subgraph, audit/debug, HITL, quiz flow, explanation, export | full run on a fixture team with scripted LLM, and on a real repo |
| P4 Queue, API, events | tasks, locks, endpoints, event writer, SSE | run started from the API; events visible live |
| P5 Frontend | pipeline canvas, results, review, student quiz | lecturer watches a run node by node and reads the results |
| P6 Development phase | webhooks, periodic sync, nightly snapshots, trajectory, early warnings; load test with 250 simulated students at one deadline | no worker crash; queue drains; deadline run is incremental |
| P7 Acceptance | end-to-end on a real team (repo link and board) | marks with justification, report, development view |

## 13. Dependencies needing approval (nothing installed without asking)

- **Agent:** `langgraph-checkpoint-postgres`, `mcp` (Python SDK), and `torch`/`transformers`/`scikit-learn`/`joblib` in the agent's environment (Code Ownership), plus the CodeBERT weights (about 500 MB).
- **Frontend:** `@xyflow/react`, `elkjs`, and optionally `@microsoft/fetch-event-source`.

## 14. Verification

- **Unit tests:** per new module (workspace, MCP client and server, evidence builder against the dataset scripts on one known team, each `evaluate.py`, audit rules, fusion, event writer).
- **Graph tests:** with `ScriptedLLM` and a fixture repo: normal path, quiz timeout and extension, review interrupt and resume, audit re-run, Collaboration not available, restart from the Postgres checkpointer mid-run.
- **Server tests:** the existing route-protection test plus endpoint tests; the job is enqueued and a run is created.
- **Load test:** 250 simulated students sharing one deadline. Check worker memory, queue drain time, and no duplicate runs.
- **End to end:** a real repo link and the Scrum MCP script. Start tracking, sync, snapshot over several days, final run, answer the quiz, decide a review, read the report and the development view. Watch the pipeline animation in the browser.

## 15. Known limits to keep visible in the product

- **Weak validation:** factor models were validated on small, mostly assistant-labelled data. None is validated against instructors yet. The UI and report say so.
- **Code Ownership scope:** the scorer is trained on Python only. Other languages give "not available" unless the lecturer enables unvalidated scoring.
- **Groq limits:** the RF sub-agent depends on Groq rate limits. Budgets per run and caching matter, and the held-out RF results are still incomplete.
- **Behavioral Pattern gaps:** Last-minute rusher and Burst worker rarely fire (see its README).

## 16. Implementation status (branch `feature/assessment-agent-integration-sadeesha`)

Built and tested:

| Phase | What exists | Tests |
|---|---|---|
| P0 Foundations | Postgres tables `perf_*` (one DDL file, alembic `a7c3d5e91f02`, checked on a throwaway local database), `PerformanceStore`, in-memory twin, LangGraph Postgres checkpointer helper | store tests on local Postgres |
| P1 Workspace and evidence | read-only git workspace, GitHub REST, Scrum MCP server and client, evidence builder, identity map | workspace 35, MCP 7, GitHub 7, builder 7 |
| P2 Factors | `evaluate.py` for Effort, Consistency, Task Complexity (ridge cards), Requirement Fulfillment (sub-agent on real evidence), Code Ownership (production), Collaboration, Behavioral Pattern; factor cards; provisional mode | linear 13, RF 9, factor tests |
| P3 Agent graph | team graph, student pipeline, audit/retry/escalate, fusion, justification, Code Ownership quiz flow with 48 h + 48 h windows, report | 25 tests incl. end to end on a real repo |
| P4 Queue, API, events | jobs `assess_team`, `resume_run`, `refuse_student`, `sync_team`, `sync_all`, `snapshot_all`, `quiz_sweep`; `/api/v1/performance/*` incl. SSE and the GitHub webhook | 13 API tests, 3 task tests, route-protection test |
| P5 Frontend | pipeline canvas (own SVG layout, rotating glow, comet along the edge into the active node, node log drawer), team hub, tracking form, results, day-by-day chart, review queue, identity-mapping form, student page with the code question | model, SSE and roster unit tests; lint and build clean |

Decisions made while building:
- No new frontend packages: the pipeline view uses plain SVG and CSS instead of `@xyflow/react` and `elkjs` (the graph is small and fixed).
- The graph topology lives in `shared/performance/topology.py` so the agent and the Core API share it.
- Checkpoints use one thread per run (`team:{team}:sprint:{sprint}:{run id}`); the cross-run memory is in the result tables.
- A lecturer's override is stored beside the model's mark and never replaces it.

Not done, or not verified:
- P6 and P7: the 250-student load test and a run on a real team repository with the real board have not been done. Only throwaway repositories and a fake GitHub were used.
- The pipeline view and the quiz page have not been looked at in a browser here (no Keycloak login in this environment); they are covered by unit tests, lint and a production build only.
- The alembic migration was applied and reverted on a throwaway local PostgreSQL only; it has not been applied to the shared Supabase database.
- `GITHUB_WEBHOOK_SECRET`, `GITHUB_TOKEN` and `ASSESSMENT_GROQ_API_KEYS` must be set for webhooks, private repositories and Requirement Fulfillment.
- Code Ownership needs the CodeBERT weights on the worker (about 500 MB, loaded once per process).
