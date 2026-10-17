# `com_agent` Implementation Board
**Project:** J26-SE-363 (CEAI)  
**Agent:** Individual Student Performance Assessment  
**Reference Plan:** [PLAN.md](./PLAN.md)  
**Status:** Planning Complete — Ready for Implementation

---

## How to Read This Board

- **Phases** are sequential. Each phase must be complete before the next begins.
- **Tasks** within a phase are independent unless explicitly marked with a dependency.
- **Subtasks** are atomic coding units — one focused session each.
- **Refs** link to the exact section in [PLAN.md](./PLAN.md) where the design lives.
- Status markers: `[ ]` not started · `[/]` in progress · `[x]` done

> **Scope boundary:** Everything stays inside `backend/app/agents/performance_assessment/`.
> No other folders are touched. All external services are mocked.
> See [PLAN.md §12.8](./PLAN.md#128-external-connector-mock-strategy--all-connectors-mocked-for-development).

---

## Phase Overview

| Phase | Name | Primary Goal |
|---|---|---|
| **0** | Foundation & Scaffolding | Directory tree, YAML configs, env vars, mock fixtures |
| **1** | State & Schema Layer | `AssessmentState` TypedDict + all Pydantic models |
| **2** | Ingestion Layer | Evidence adapters, retry policy, git sandbox runner |
| **3** | Fusion Engine | Deterministic calculator, weights, fallbacks, discrepancy rules |
| **4** | Prompt System | YAML schema, loader, `prompts.yaml` content |
| **5** | Graph Nodes | All 16 LangGraph nodes implemented and individually testable |
| **6** | Graph Assembly | `StateGraph` wired with all edges, interrupts, and checkpointer |
| **7** | Public Entrypoints | `agent.py` four triggers, `schemas.py` export contracts |
| **8** | Test Suite | Full automated coverage across all 8 test categories |
| **9** | End-to-End Validation | Full mock run, LangSmith trace review, output verification |

---

## Phase 0 — Foundation & Scaffolding

> **Ref:** [PLAN.md §10](./PLAN.md#10-directory-structure) · [PLAN.md §12.1](./PLAN.md#121-authorization-layer--mock-via-json-context-injection) · [PLAN.md §12.8](./PLAN.md#128-external-connector-mock-strategy--all-connectors-mocked-for-development)

---

### T0.1 — Create Directory Skeleton

- [x] **T0.1.1** `com_agent/__init__.py`
- [x] **T0.1.2** `com_agent/state.py` (empty placeholder)
- [x] **T0.1.3** `com_agent/graph.py` (empty placeholder)
- [x] **T0.1.4** `com_agent/nodes/__init__.py` + empty stubs:
  `validation_node.py`, `passive_runner_node.py`, `active_quiz_node.py`,
  `behavioral_node.py`, `fusion_node.py`, `discrepancy_node.py`,
  `review_node.py`, `memory_node.py`, `sanitizer_node.py`,
  `explanation_node.py`, `export_node.py`
- [x] **T0.1.5** `com_agent/ingestion/__init__.py` + empty stubs:
  `scrum_mcp_client.py`, `github_client.py`, `git_sandbox_runner.py`, `cohort_baseline.py`
- [x] **T0.1.6** `com_agent/fusion_engine/__init__.py` + empty stubs:
  `calculator.py`, `weights_config.py`
- [x] **T0.1.7** `com_agent/policies/__init__.py` + empty stubs:
  `fallback_policies.py`, `discrepancy_rules.py`, `retry_policy.py`
- [x] **T0.1.8** `com_agent/prompts/__init__.py` + empty stubs:
  `prompt_loader.py`, `prompts.yaml`
- [x] **T0.1.9** `com_agent/config/__init__.py` + empty stubs:
  `settings_loader.py`, `weights_config.yaml`, `quiz_timeout_settings.yaml`
- [x] **T0.1.10** `com_agent/mock_context/__init__.py` + fixture stubs:
  `student_context.json`,
  `mock_github_responses/commits.json`,
  `mock_github_responses/pull_requests.json`,
  `mock_github_responses/issues.json`,
  `mock_scrum_responses/sprint_details.json`,
  `mock_scrum_responses/student_tasks.json`,
  `mock_scrum_responses/task_acceptance_criteria.json`,
  `mock_scrum_responses/task_status_history.json`
- [x] **T0.1.11** `com_agent/mock_context/output/` directory (exported JSON written here in dev mode)
- [x] **T0.1.12** `com_agent/tests/__init__.py` + empty test stubs for all 8 test files
  from [PLAN.md §11](./PLAN.md#11-verification-plan)

---

### T0.2 — Configuration YAML Files

> **Ref:** [PLAN.md §12.5](./PLAN.md#125-ahp-factor-weights--yaml-configuration-file-lecturer-configurable) · [PLAN.md §12.2](./PLAN.md#122-quiz-timeout-policy--two-chance-system-with-configurable-cap) · [PLAN.md §12.7](./PLAN.md#127-github-api-rate-limiting--per-student-cap-with-sandbox-fallback)

- [x] **T0.2.1** Write `config/weights_config.yaml`
  Weights: `effort:0.20, consistency:0.15, requirement_fulfillment:0.25, collaboration:0.15,
  task_complexity:0.10, code_ownership:0.15`. Include `version`, `last_updated_by`, `last_updated_at`.
  Sum must equal `1.0` exactly.

- [x] **T0.2.2** Write `config/quiz_timeout_settings.yaml`
  Two blocks — `code_ownership_quiz`: (`time_window_hours: 48`, `extra_time_hours: 48`,
  `capped_score_ceiling: 0.50`) and `github_api`: (`max_calls_per_student: 30`).

---

### T0.3 — Settings Loader (`config/settings_loader.py`)

> **Ref:** [PLAN.md §12.5](./PLAN.md#125-ahp-factor-weights--yaml-configuration-file-lecturer-configurable)

- [x] **T0.3.1** Pydantic models: `QuizTimeoutSettings`, `GitHubAPISettings`, `FactorWeightsConfig`, `AppSettings`
- [x] **T0.3.2** Load both YAML files at module import; expose `settings: AppSettings` singleton
- [x] **T0.3.3** Validate `sum(factor_weights.values()) == 1.0` within `1e-6`; raise `ValueError` with descriptive message on failure
- [x] **T0.3.4** Read `COM_AGENT_ENV` env var (`"development"` | `"production"`); export `IS_DEV_MODE: bool`

---

### T0.4 — Mock Context Fixture Files

> **Ref:** [PLAN.md §12.1](./PLAN.md#121-authorization-layer--mock-via-json-context-injection)

- [x] **T0.4.1** `student_context.json` — one student: `student_id`, `student_name`,
  `student_github_username`, `student_git_emails` (two emails), `team_id`, `sprint_id`,
  `repo_url`, `sprint_start`, `sprint_end`, `assigned_tasks` (3 tasks with story points)

- [x] **T0.4.2** `mock_github_responses/commits.json` — 12 commits for the mock student spanning the sprint.
  Each: `sha`, `author.login`, `author.email`, `commit.author.date`,
  `stats.additions`, `stats.deletions`, `files[]`, `parents[]` (length 1, non-merge).
  Include 2 teammate commits to test filtering.

- [x] **T0.4.3** `mock_github_responses/pull_requests.json` — 4 PRs:
  2 authored by mock student (with teammate reviews), 2 by teammates (with mock student reviews).

- [x] **T0.4.4** `mock_github_responses/issues.json` — 6 comments:
  3 by mock student on teammates' issues (with reaction counts and timestamps); 3 by others.

- [x] **T0.4.5** `mock_scrum_responses/sprint_details.json` — sprint name, `sprint_id`, `start_date`, `end_date`

- [x] **T0.4.6** `mock_scrum_responses/student_tasks.json` — 3 tasks: 2 completed, 1 in-progress.
  Each: `task_id`, `title`, `story_points`, `subtask_count`, `status`

- [x] **T0.4.7** `mock_scrum_responses/task_acceptance_criteria.json` — keyed by `task_id`;
  each has `description` and `acceptance_criteria: List[str]`

- [x] **T0.4.8** `mock_scrum_responses/task_status_history.json` — keyed by `task_id`;
  each is a list of `{column, timestamp}` transitions:
  e.g. `[{column:"Todo",...},{column:"In Progress",...},{column:"Done",...}]`

---

### T0.5 — Dependency Setup

- [x] **T0.5.1** Add to `requirements.txt`:
  `langgraph>=0.2`, `langchain-core`, `langsmith`, `pydantic>=2.0`, `pyyaml`, `python-dotenv`, `pytest`, `pytest-asyncio`
- [x] **T0.5.2** Create `com_agent/.env.example`:
  `COM_AGENT_ENV=development`, `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY=`, `LANGCHAIN_PROJECT=performance_assessment_com_agent`

---

## Phase 1 — State & Schema Layer

> **Ref:** [PLAN.md §8](./PLAN.md#8-langgraph-state-schema-assessmentstate) · [PLAN.md §12.2](./PLAN.md#122-quiz-timeout-policy--two-chance-system-with-configurable-cap) · [PLAN.md §12.3](./PLAN.md#123-output-api-schema--assessment-result-contract) · [PLAN.md §12.7](./PLAN.md#127-github-api-rate-limiting--per-student-cap-with-sandbox-fallback)
> **Depends on:** Phase 0 complete.

---

### T1.1 — Internal Pydantic Models (`com_agent/state.py`)

- [x] **T1.1.1** `FactorOutput` — `score: float [0,1]`, `features: Dict`,
  `evidence_traces: List[Dict]`, `status: Literal["completed","missing","fallback_applied"]`,
  `error_message: Optional[str]`

- [x] **T1.1.2** `ActiveVerificationState` — all fields from [PLAN.md §8](./PLAN.md#8-langgraph-state-schema-assessmentstate)
  plus Section 12.2 additions: `is_extended: bool`, `quiz_extension_deadline: Optional[str]`,
  `is_double_timed_out: bool`

- [x] **T1.1.3** `DiscrepancyAlert` — `alert_code: Literal["GHOSTWRITER_SUSPICION","DEADLINE_PANIC","FREE_RIDER","UNRECORDED_WORK"]`,
  `severity: Literal["INFO","WARNING","CRITICAL"]`, `description: str`, `recommended_action: str`

- [x] **T1.1.4** `CohortBaseline` — `metric_means: Dict[str,float]`, `metric_stds: Dict[str,float]`,
  `student_count: int`, `sprint_count_used: int`, `computed_at: str`

---

### T1.2 — `AssessmentState` TypedDict (`com_agent/state.py`)

**Depends on: T1.1**

- [x] **T1.2.1** Implement base `AssessmentState` with all sections 1-10 from [PLAN.md §8](./PLAN.md#8-langgraph-state-schema-assessmentstate)
- [x] **T1.2.2** Add Section 12.2 timeout fields:
  `ko_raw_score: Optional[float]`, `ko_fusion_score: Optional[float]`,
  `quiz_is_extended: bool`, `quiz_is_double_timed_out: bool`, `quiz_extension_deadline: Optional[str]`
- [x] **T1.2.3** Add Section 12.7 API-tracking fields:
  `github_api_call_count: int`, `github_sandbox_mode: bool`
- [x] **T1.2.4** Confirm `factor_scores` is `Annotated[Dict[str, FactorOutput], operator.ior]` for parallel fan-in merge

---

### T1.3 — Public Output Schemas (`performance_assessment/schemas.py`)

> **Ref:** [PLAN.md §12.3](./PLAN.md#123-output-api-schema--assessment-result-contract)

- [x] **T1.3.1** `FactorScoreOutput` — public, UI-friendly: `score`, `label`, `evidence_summary`, `status`
- [x] **T1.3.2** `AssessmentResultSchema` — full lecturer-facing output contract per [PLAN.md §12.3](./PLAN.md#123-output-api-schema--assessment-result-contract)
- [x] **T1.3.3** `StudentFeedbackSchema` — student-portal subset; strips evidence traces and instructor-only fields
- [x] **T1.3.4** Apply `model_config = ConfigDict(frozen=True)` to both schemas

---

## Phase 2 — Ingestion Layer

> **Ref:** [PLAN.md §4](./PLAN.md#4-evidence-gathering-layer-scrum-mcp--github-hybrid-strategy) · [PLAN.md §12.6](./PLAN.md#126-factor-tool-error--retry-policy) · [PLAN.md §12.7](./PLAN.md#127-github-api-rate-limiting--per-student-cap-with-sandbox-fallback) · [PLAN.md §12.8](./PLAN.md#128-external-connector-mock-strategy--all-connectors-mocked-for-development)
> **Depends on:** Phase 1 complete. Phases 2, 3, 4 run in parallel.

---

### T2.1 — Retry Policy (`policies/retry_policy.py`)

> Build first — all adapters depend on it.

- [x] **T2.1.1** `@retry_with_backoff(max_attempts=3, base_delay_seconds=2)` async decorator
  — catches transient network/timeout/5xx errors
  — waits `base_delay * 2^(attempt-1)` between retries
  — raises original exception after all attempts exhausted
- [x] **T2.1.2** `RetryExhaustedError` custom exception class
- [x] **T2.1.3** Unit test: verify 3 attempts fire, correct backoff timing, exception raised on final failure

---

### T2.2 — GitHub Client (`ingestion/github_client.py`)

**Depends on: T2.1, T0.4.2-T0.4.4, T1.2.3**

- [x] **T2.2.1** `GitHubClientProtocol` ABC — 4 methods:
  `get_commits(repo_url, author_username, author_emails, since, until)`,
  `get_pull_requests(repo_url, author_username, since, until)`,
  `get_review_comments(repo_url, pr_ids, reviewer_username)`,
  `get_issue_comments(repo_url, author_username, since, until)`

- [x] **T2.2.2** `MockGitHubClient(GitHubClientProtocol)` — reads fixture JSON, applies author filtering in-memory,
  always excludes merge commits (`len(parents) > 1`) per [PLAN.md §5](./PLAN.md#5-seven-factor-responsibilities--clean-student-isolation)

- [x] **T2.2.3** `RealGitHubClient(GitHubClientProtocol)` — stub only; all methods `raise NotImplementedError`

- [x] **T2.2.4** `CountingGitHubClientWrapper` — wraps any client; increments `state["github_api_call_count"]` per call;
  when count reaches `settings.github_api.max_calls_per_student`, sets `state["github_sandbox_mode"] = True`
  and routes further calls to `GitSandboxRunner`

- [x] **T2.2.5** Factory `get_github_client(is_dev) → GitHubClientProtocol`

---

### T2.3 — Git Sandbox Runner (`ingestion/git_sandbox_runner.py`)

> **Ref:** [PLAN.md §12.7](./PLAN.md#127-github-api-rate-limiting--per-student-cap-with-sandbox-fallback)

- [x] **T2.3.1** `ALLOWED_GIT_COMMANDS = ["log", "diff", "show", "shortlog", "blame"]`
- [x] **T2.3.2** `async run_git_command(repo_path, subcommand, args, author_filter) → str`
  — validates subcommand against whitelist (raises `PermissionError` otherwise)
  — always injects `--author=<author_filter>`
  — runs via `asyncio.create_subprocess_exec`; raises on non-zero exit
- [x] **T2.3.3** `parse_git_log_to_commits(raw) → List[Dict]` — normalized to same schema as `MockGitHubClient` output
- [x] **T2.3.4** `parse_git_diff_to_files(raw) → List[Dict]`
- [x] **T2.3.5** Apply `@retry_with_backoff(max_attempts=2)` to `run_git_command`

---

### T2.4 — Scrum MCP Client (`ingestion/scrum_mcp_client.py`)

**Depends on: T2.1**

- [x] **T2.4.1** `ScrumMCPClientProtocol` ABC — 4 tools per [PLAN.md §4.1](./PLAN.md#41-custom-scrum-board-mcp-server):
  `get_sprint_details(sprint_id)`, `get_student_tasks(sprint_id, student_id)`,
  `get_task_acceptance_criteria(task_id)`, `get_task_status_history(task_id)`
- [x] **T2.4.2** `MockScrumMCPClient` — reads fixture JSON; filters by ID fields
- [x] **T2.4.3** `RealScrumMCPClient` — stub only; `raise NotImplementedError`
- [x] **T2.4.4** Apply `@retry_with_backoff` to all four methods
- [x] **T2.4.5** Factory `get_scrum_client(is_dev) → ScrumMCPClientProtocol`

---

### T2.5 — Cohort Baseline Calculator (`ingestion/cohort_baseline.py`)

> **Ref:** [PLAN.md §12.4](./PLAN.md#124-cohort-baseline--rolling-sprint-average)  
> **Depends on: T1.1.4**

- [x] **T2.5.1** `compute_current_sprint_raw_baseline(commits_by_student) → Dict`
  — per-metric mean and std across all students for the current sprint
- [x] **T2.5.2** `load_historical_baselines(store, team_id) → List[Dict]`
  — queries LangGraph Store at `("cohort", team_id, "sprint_baselines")`; returns `[]` on Sprint 1
- [x] **T2.5.3** `compute_rolling_average_baseline(historical, current) → CohortBaseline`
  — averages across all N+1 sprints; sets `sprint_count_used`
- [x] **T2.5.4** `save_sprint_baseline(store, team_id, sprint_id, raw_baseline) → None`
  — writes current sprint entry; in dev `store` is a plain `dict`

---

## Phase 3 — Fusion Engine

> **Ref:** [PLAN.md §9 nodes 8-9](./PLAN.md#9-nodes-and-graph-flow-specification) · [PLAN.md §12.5](./PLAN.md#125-ahp-factor-weights--yaml-configuration-file-lecturer-configurable) · [PLAN.md §12.6](./PLAN.md#126-factor-tool-error--retry-policy)
> **Depends on:** Phase 1 complete. Runs in parallel with Phases 2 and 4.
> **Zero LLM calls. Pure deterministic math.**

---

### T3.1 — Score Calculator (`fusion_engine/calculator.py`)

- [x] **T3.1.1** `compute_additive_score(factor_scores, weights) → Tuple[float, Dict]`
  — uses `ko_fusion_score` (capped) from `factor_scores["code_ownership"]`
  — calls `redistribute_weights()` for any `fallback_applied` factors before multiplying
  — audit trail records every `factor * weight * score` step
  — returns `(additive_score, audit_trail)`
- [x] **T3.1.2** `apply_behavioral_modifier(additive_score, bp_modifier) → float`
  — `S = bp_modifier * additive_score`; clamps to `[0.0, 1.0]`
- [x] **T3.1.3** `build_radar_chart_data(factor_scores) → Dict[str, float]`
  — `{"effort": 0.74, "consistency": 0.61, ...}` for frontend radar chart
- [x] **T3.1.4** Validate `sum(effective_weights) == 1.0` after redistribution; include in audit trail

---

### T3.2 — Weights Bridge (`fusion_engine/weights_config.py`)

**Depends on: T0.3**

- [x] **T3.2.1** `load_weights() → FactorWeightsConfig` — thin wrapper around `settings.factor_weights`
- [x] **T3.2.2** `get_weights_as_dict() → Dict[str, float]` — flat dict for calculator

---

### T3.3 — Fallback Policies (`policies/fallback_policies.py`)

> **Ref:** [PLAN.md §9 node 3](./PLAN.md#9-nodes-and-graph-flow-specification) · [PLAN.md §12.6](./PLAN.md#126-factor-tool-error--retry-policy)

- [x] **T3.3.1** `get_fallback_for_factor(factor_code) → FactorOutput`
  — returns `FactorOutput(score=0.0, status="fallback_applied", evidence_traces=[], features={})`
- [x] **T3.3.2** `redistribute_weights(weights, failed_factors) → Dict`
  — removes failed keys; distributes their total proportionally across remaining
- [x] **T3.3.3** `handle_zero_review_comments() → FactorOutput`
  — valid zero case for Factor 4 (no PR reviews is legitimate, not an error)

---

### T3.4 — Discrepancy Rules (`policies/discrepancy_rules.py`)

> **Ref:** [PLAN.md §9 node 9](./PLAN.md#9-nodes-and-graph-flow-specification)

- [x] **T3.4.1** `check_ghostwriter_suspicion(effort, ko_raw)` — CRITICAL when `effort > 0.75` and `ko_raw < 0.35`
- [x] **T3.4.2** `check_deadline_panic(consistency, effort)` — WARNING when `consistency < 0.30` and `effort > 0.60`
- [x] **T3.4.3** `check_free_rider(effort, collaboration)` — WARNING when both `< 0.25`
- [x] **T3.4.4** `check_unrecorded_work(effort, ko_raw, consistency)` — INFO when `ko_raw > 0.80` but effort and consistency `< 0.40`
- [x] **T3.4.5** `run_all_discrepancy_checks(factor_scores) → List[DiscrepancyAlert]` — runs all four
- [x] **T3.4.6** `REQUIRES_HUMAN_REVIEW_SEVERITIES = ["CRITICAL"]` constant used by graph router

---

## Phase 4 — Prompt System

> **Ref:** [PLAN.md §6](./PLAN.md#6-prompt-management-via-yaml-schema)
> **Depends on:** Phase 1 complete. Runs in parallel with Phases 2 and 3.

---

### T4.1 — Pydantic Prompt Schema (`prompts/prompt_loader.py`)

> **Ref:** [PLAN.md §6.1](./PLAN.md#61-pydantic-prompt-schema-prompt_loaderpy)

- [x] **T4.1.1** `PromptDefinition` Pydantic model — all fields:
  `prompt_id`, `version`, `role`, `objective`, `strict_constraints: List[str]`,
  `input_variables: List[str]`, `output_schema_format`, `model_parameters: Dict`,
  `system_prompt_template`, `user_prompt_template`
- [x] **T4.1.2** `PromptLibrary` — `version: str`, `prompts: Dict[str, PromptDefinition]`
- [x] **T4.1.3** `load_prompt_library(yaml_path) → PromptLibrary`
  — reads and validates YAML; raises `ValidationError` on any schema mismatch
- [x] **T4.1.4** `render_prompt(prompt_def, variables) → Tuple[str, str]`
  — returns `(system_prompt, user_prompt)` with all placeholders filled
  — raises `KeyError` if any declared `input_variable` is missing from the passed dict

---

### T4.2 — `prompts.yaml` Content

> **Ref:** [PLAN.md §6.2](./PLAN.md#62-yaml-prompt-schema-definition-com_agentpromptspromptsyaml)  
> **Depends on: T4.1**

- [x] **T4.2.1** Write `instructor_assessment_dossier` prompt — senior evaluator role, NEVER-modify-scores constraint,
  all 10 input variables, `temperature: 0.15`, `max_tokens: 1500`
- [x] **T4.2.2** Write `student_formative_feedback` prompt — supportive pedagogical mentor role,
  6 input variables, `temperature: 0.30`, `max_tokens: 1000`
- [x] **T4.2.3** Unit test `tests/test_prompt_yaml.py`:
  — YAML parses without `ValidationError`
  — both prompt IDs present
  — all `input_variables` have matching `{placeholder}` in both template strings
  — `render_prompt` raises `KeyError` when a required variable is missing
  — `strict_constraints` list is non-empty for both prompts

---

## Phase 5 — Graph Nodes

> **Ref:** [PLAN.md §9](./PLAN.md#9-nodes-and-graph-flow-specification) · [PLAN.md §1](./PLAN.md#1-langgraph-stategraph-workflow)
> **Depends on:** Phases 2, 3, and 4 all complete.
> All node tasks within this phase are independent and can be built in parallel.
> Each node is an `async` function, unit-testable by direct call with a mock `AssessmentState` dict.

---

### T5.1 — `validate_context_node` (`nodes/validation_node.py`)

> **Ref:** [PLAN.md §9 node 1](./PLAN.md#9-nodes-and-graph-flow-specification) · [PLAN.md §12.1](./PLAN.md#121-authorization-layer--mock-via-json-context-injection)

- [x] **T5.1.1** Load student context from `mock_context/student_context.json` (dev) or DB (prod)
- [x] **T5.1.2** Validate required fields: `student_id`, `student_github_username`, `team_id`, `sprint_id`, `repo_url`, `assigned_tasks`
- [x] **T5.1.3** Validate `student_git_emails` is non-empty (identity mapping per [PLAN.md §5](./PLAN.md#5-seven-factor-responsibilities--clean-student-isolation))
- [x] **T5.1.4** Verify local clone dir `/repos/{team_id}/` exists (skip check in dev mode)
- [x] **T5.1.5** Call `compute_rolling_average_baseline()`; inject `CohortBaseline` into state
- [x] **T5.1.6** On failure: append to `state["errors"]`, set `current_step = "validation_failed"`, return partial update

---

### T5.2 — Parallel Passive Factor Tools (`nodes/passive_runner_node.py`)

> **Ref:** [PLAN.md §9 nodes 2-3](./PLAN.md#9-nodes-and-graph-flow-specification) · [PLAN.md §5](./PLAN.md#5-seven-factor-responsibilities--clean-student-isolation) · [PLAN.md §12.6](./PLAN.md#126-factor-tool-error--retry-policy)

All five tools run concurrently in LangGraph parallel fan-out. Each returns `{"factor_scores": {"<code>": FactorOutput}}`.
On persistent adapter failure: return `FactorOutput(status="fallback_applied")`.

- [x] **T5.2.1** `run_effort_tool(state)` — features: CC, LOC_net, FC, CT, RD
  — GitHub (author-filtered, no merge commits) + Scrum — z-score via `cohort_baselines`
  — calls `factor_models/01_effort/` public interface `compute_effort_score(features) → float`

- [x] **T5.2.2** `run_consistency_tool(state)` — features: AWR, DC, LI_norm, CV_norm
  — GitHub commit timestamps only — calls `factor_models/02_consistency/` interface

- [x] **T5.2.3** `run_req_fulfillment_tool(state)` — task ACs + per-task commit diffs
  — Scrum `get_task_acceptance_criteria` + GitHub diffs for student's commits
  — calls `factor_models/03_requirement_fulfillment/` interface

- [x] **T5.2.4** `run_collaboration_tool(state)` — PRC_depth, IC_depth, MC, PCount, CCount, IR
  — GitHub: student's reviews/comments on teammates' PRs and issues only
  — calls `factor_models/04_collaboration/` interface

- [x] **T5.2.5** `run_complexity_tool(state)` — SP, SC, FI, DR, CB
  — Scrum (SP, SC) + Git sandbox runner (pre-sprint DAG traversal for DR, CB)
  — calls `factor_models/05_task_complexity/` interface

- [x] **T5.2.6** `join_passive_factors_node(state)` — fan-in: collects all 5 results (merged via `operator.ior`),
  identifies `fallback_applied` factors, calls `redistribute_weights()`, stores `weights_used`,
  sets `current_step = "passive_complete"`

---

### T5.3 — AST Quiz Generator (`nodes/active_quiz_node.py`)

> **Ref:** [PLAN.md §9 node 4](./PLAN.md#9-nodes-and-graph-flow-specification)

- [x] **T5.3.1** `ast_quiz_generator_node(state)` — calls `factor_models/07_code_ownership/`
  `select_highest_signal_snippet(commits)` and `generate_ast_question(snippet)`
  — populates `state["active_verification"]` with snippet, file_path, line_range, question, ast_metadata
  — sets `current_step = "quiz_generated"`

---

### T5.4 — Quiz Interrupt & Timeout Handling (`nodes/active_quiz_node.py`)

> **Ref:** [PLAN.md §9 node 5](./PLAN.md#9-nodes-and-graph-flow-specification) · [PLAN.md §12.2](./PLAN.md#122-quiz-timeout-policy--two-chance-system-with-configurable-cap)

- [x] **T5.4.1** `await_quiz_response_node(state)` — computes `initial_deadline = sprint_end + time_window_hours`
  — calls `interrupt({"question": ..., "deadline": initial_deadline_iso})`
  — resumes via `Command(resume={"student_response": "...", "response_timestamp": "..."})`

- [x] **T5.4.2** Post-resume timeout routing:
  — within initial window: proceed normally
  — first timeout but `quiz_is_extended == False`: set `quiz_is_extended = True`,
    compute `extension_deadline`, issue second `interrupt()` — thread pauses again
  — after second resume: if past `extension_deadline`, set `quiz_is_double_timed_out = True`

---

### T5.5 — Code Ownership Evaluation (`nodes/active_quiz_node.py`)

> **Ref:** [PLAN.md §9 node 6](./PLAN.md#9-nodes-and-graph-flow-specification) · [PLAN.md §12.2](./PLAN.md#122-quiz-timeout-policy--two-chance-system-with-configurable-cap)

- [x] **T5.5.1** `evaluate_ownership_tool(state)` — calls `factor_models/07_code_ownership/`
  `evaluate_response(snippet, question, answer) → float`
  — stores raw result as `state["ko_raw_score"]` (always uncapped, always preserved)
  — cap logic: normal → `ko_fusion_score = raw`; extended → `ko_fusion_score = min(raw, capped_score_ceiling)`;
    double timeout → `ko_fusion_score = 0.0`
  — stores `FactorOutput` using `ko_fusion_score` in `state["factor_scores"]["code_ownership"]`

---

### T5.6 — Behavioral Pattern Node (`nodes/behavioral_node.py`)

> **Ref:** [PLAN.md §9 node 7](./PLAN.md#9-nodes-and-graph-flow-specification)

- [x] **T5.6.1** `run_behavioral_pattern_node(state)` — collects effort, consistency, collaboration,
  `ko_raw_score` (RAW, not capped), untracked commit ratio
  — calls `factor_models/06_behavioral_pattern/` `classify_persona(signals) → Tuple[str, float]`
  — sets `state["behavioral_persona"]` and `state["behavioral_modifier"] ∈ [0.80, 1.20]`

---

### T5.7 — Deterministic Fusion Node (`nodes/fusion_node.py`)

> **Ref:** [PLAN.md §9 node 8](./PLAN.md#9-nodes-and-graph-flow-specification)
> **⚠️ Zero LLM. Pure math.**

- [x] **T5.7.1** `deterministic_fusion_node(state)` — `get_weights_as_dict()` → `compute_additive_score()`
  → `apply_behavioral_modifier()` → `build_radar_chart_data()`
  — writes `additive_score`, `final_score`, `weights_used`, `calculation_audit_trail`, `radar_chart_data` to state
  — sets `current_step = "fusion_complete"`

---

### T5.8 — Discrepancy Detection Node (`nodes/discrepancy_node.py`)

> **Ref:** [PLAN.md §9 node 9](./PLAN.md#9-nodes-and-graph-flow-specification)

- [x] **T5.8.1** `discrepancy_detection_node(state)` — calls `run_all_discrepancy_checks(factor_scores)`
  — stores `state["discrepancy_flags"]`
  — sets `state["requires_human_review"] = True` if any flag has severity in `REQUIRES_HUMAN_REVIEW_SEVERITIES`
  — sets `current_step = "discrepancy_checked"`

---

### T5.9 — Lecturer Review Node (`nodes/review_node.py`)

> **Ref:** [PLAN.md §9 node 10](./PLAN.md#9-nodes-and-graph-flow-specification) · [PLAN.md §2 Trigger 4](./PLAN.md#21-the-four-execution-triggers)

- [x] **T5.9.1** `lecturer_review_node(state)` — `interrupt({"flags": ..., "scores": ..., "final_score": ...})`
  — resumes via `Command(resume={"override_score": float|None, "reason": str, "lecturer_id": str})`
  — if `override_score is not None`: update `state["final_score"]` and `state["lecturer_override_score"]`
  — always sets `lecturer_reviewed = True`, `lecturer_id`, `review_timestamp`

---

### T5.10 — Cross-Sprint Memory Nodes (`nodes/memory_node.py`)

> **Ref:** [PLAN.md §9 nodes 11, 15](./PLAN.md#9-nodes-and-graph-flow-specification) · [PLAN.md §7.3](./PLAN.md#73-two-tier-memory-management) · [PLAN.md §12.4](./PLAN.md#124-cohort-baseline--rolling-sprint-average)

- [x] **T5.10.1** `load_cross_sprint_memory_node(state, store)` — queries Store `("students", student_id, "sprint_history")`
  — injects `state["historical_trajectory"]`; returns `[]` on first sprint
- [x] **T5.10.2** `update_cross_sprint_memory_node(state, store)` — builds sprint snapshot, appends to Store,
  calls `save_sprint_baseline()` from cohort_baseline.py

---

### T5.11 — PII Sanitization Nodes (`nodes/sanitizer_node.py`)

> **Ref:** [PLAN.md §7.1](./PLAN.md#71-pii-redaction--sanitization) · [PLAN.md §9 nodes 12, 14](./PLAN.md#9-nodes-and-graph-flow-specification)

- [x] **T5.11.1** `pii_redaction_sanitizer_node(state)` — builds substitution map, applies to all LLM-bound fields,
  stores map in `state["pii_substitution_map"]`
- [x] **T5.11.2** `pii_restore_node(state)` — reverses substitutions in both markdown fields,
  clears `state["pii_substitution_map"]`

---

### T5.12 — Explanation Generation Node (`nodes/explanation_node.py`)

> **Ref:** [PLAN.md §9 node 13](./PLAN.md#9-nodes-and-graph-flow-specification) · [PLAN.md §6](./PLAN.md#6-prompt-management-via-yaml-schema)

- [x] **T5.12.1** `generate_explanation_node(state)` — loads `PromptLibrary`, renders `instructor_assessment_dossier`
  with anonymized state vars, calls LLM (temp 0.15), stores in `state["instructor_report_markdown"]`;
  renders `student_formative_feedback`, calls LLM (temp 0.30), stores in `state["student_feedback_markdown"]`

---

### T5.13 — Export Results Node (`nodes/export_node.py`)

> **Ref:** [PLAN.md §9 node 16](./PLAN.md#9-nodes-and-graph-flow-specification) · [PLAN.md §12.3](./PLAN.md#123-output-api-schema--assessment-result-contract)

- [x] **T5.13.1** `export_results_node(state)` — validates against `AssessmentResultSchema` (raises `ValidationError` if incomplete),
  writes `assessment_result_{student_id}_{sprint_id}.json` to `mock_context/output/` (dev),
  writes filtered `StudentFeedbackSchema` JSON separately,
  sets `current_step = "export_complete"`

---

## Phase 6 — Graph Assembly

> **Ref:** [PLAN.md §1](./PLAN.md#1-langgraph-stategraph-workflow) · [PLAN.md §2](./PLAN.md#2-graph-triggers--execution-lifecycle)
> **Depends on:** Phase 5 complete.

---

### T6.1 — StateGraph Construction (`com_agent/graph.py`)

- [x] **T6.1.1** `StateGraph(AssessmentState)` initialized; all 16 nodes added via `graph.add_node()`
- [x] **T6.1.2** `START → validate_context_node`
- [x] **T6.1.3** Fan-out: `validate_context_node → [run_effort_tool, run_consistency_tool, run_req_fulfillment_tool, run_collaboration_tool, run_complexity_tool]`
- [x] **T6.1.4** Fan-in: all 5 parallel tools → `join_passive_factors_node`
- [x] **T6.1.5** Sequential: `join_passive → ast_quiz_generator → await_quiz_response → evaluate_ownership_tool`
- [x] **T6.1.6** Sequential: `evaluate_ownership → behavioral_pattern → deterministic_fusion → discrepancy_detection`
- [x] **T6.1.7** Conditional edge from `discrepancy_detection_node`:
  `requires_human_review == True` → `lecturer_review_node` else → `load_cross_sprint_memory_node`
- [x] **T6.1.8** `lecturer_review_node → load_cross_sprint_memory_node`
- [x] **T6.1.9** Sequential: `load_cross_sprint_memory → pii_redaction → generate_explanation → pii_restore → update_cross_sprint_memory → export_results → END`
- [x] **T6.1.10** Checkpointer: `MemorySaver()` when `IS_DEV_MODE`; `PostgresSaver(conn)` in prod
- [x] **T6.1.11** Compile: `compiled_graph = graph.compile(checkpointer=checkpointer)`

---

### T6.2 — Thread & State Helpers

- [x] **T6.2.1** `make_thread_config(sprint_id, student_id) → dict`
  — `{"configurable": {"thread_id": f"sprint_{sprint_id}_student_{student_id}"}}`
  per [PLAN.md §3](./PLAN.md#3-per-student-isolation-model--cohort-baselines)
- [x] **T6.2.2** `build_initial_state(student_context: dict) → AssessmentState`
  — safe defaults for all fields; injects student context; `factor_scores={}`, `errors=[]`,
  `github_api_call_count=0`, `github_sandbox_mode=False`, etc.

---

## Phase 7 — Public Entrypoints

> **Ref:** [PLAN.md §2.1](./PLAN.md#21-the-four-execution-triggers)
> **Depends on:** Phase 6 complete.

---

### T7.1 — Four Triggers (`performance_assessment/agent.py`)

- [x] **T7.1.1** `async trigger_sprint_end(sprint_id, student_ids) → List[str]`
  **Trigger 1.** Loads mock contexts, runs cohort baseline pre-pass, spawns one `ainvoke` per student concurrently.
  Returns list of thread IDs paused at quiz interrupt.

- [x] **T7.1.2** `async submit_quiz_response(thread_id, student_response) → str`
  **Trigger 2.** `ainvoke(Command(resume={"student_response": ...}), config)`.
  Returns `"pending_lecturer_review"` or `"evaluation_complete"`.

- [x] **T7.1.3** `async trigger_on_demand(sprint_id, student_id) → str`
  **Trigger 3.** Fresh full assessment run for one student. Returns `thread_id`.

- [x] **T7.1.4** `async submit_lecturer_review(thread_id, override_score, reason, lecturer_id) → str`
  **Trigger 4.** Resumes lecturer review interrupt. Returns `"finalized"` when export completes.

---

### T7.2 — Schema Export (`performance_assessment/schemas.py`)

- [x] **T7.2.1** `AssessmentResultSchema` and `StudentFeedbackSchema` importable from `performance_assessment.schemas`
- [x] **T7.2.2** `__all__ = ["AssessmentResultSchema", "StudentFeedbackSchema", "FactorScoreOutput"]`

---

## Phase 8 — Test Suite

> **Ref:** [PLAN.md §11](./PLAN.md#11-verification-plan)
> **Depends on:** Phase 7 complete (tests can be written in parallel with Phases 5-7; run after Phase 7).
> All tests use mock clients, `MemorySaver`, and fixture JSON. Zero real external calls.

---

### T8.1 — Trigger & Lifecycle (`tests/test_com_agent_triggers.py`)

- [x] **T8.1.1** Trigger 1 → all 5 passive factors complete → thread paused at quiz interrupt
- [x] **T8.1.2** Trigger 2 within initial window → KO scored normally → fusion runs → `final_score` in state
- [x] **T8.1.3** Trigger 2 after initial window but within extension → `ko_fusion_score <= capped_score_ceiling`; `quiz_is_extended == True`
- [x] **T8.1.4** Both windows expired → `ko_fusion_score == 0.0`; `quiz_is_double_timed_out == True`
- [x] **T8.1.5** CRITICAL discrepancy injected → thread pauses at `lecturer_review_node`
- [x] **T8.1.6** Trigger 4 with `override_score=0.45` → `final_score == 0.45`; `lecturer_reviewed == True`
- [x] **T8.1.7** Trigger 4 with `override_score=None` → original `final_score` preserved

---

### T8.2 — Evidence Isolation (`tests/test_evidence_isolation.py`)

- [x] **T8.2.1** Mock client returns only commits matching `student_git_emails` (not teammate commits)
- [x] **T8.2.2** Merge commits excluded from all results
- [x] **T8.2.3** Student with two emails — commits from both captured
- [x] **T8.2.4** `CountingGitHubClientWrapper` increments `github_api_call_count` correctly
- [x] **T8.2.5** At `max_calls_per_student` → `github_sandbox_mode == True`
- [x] **T8.2.6** `run_git_command` raises `PermissionError` on non-whitelisted subcommand
- [x] **T8.2.7** `run_git_command` always includes `--author` flag in executed command

---

### T8.3 — Fusion Calculator (`tests/test_fusion_calculator.py`)

- [x] **T8.3.1** Known inputs → exact `final_score` matches manual calculation
- [x] **T8.3.2** All 6 factors present → `sum(effective_weights) == 1.0`
- [x] **T8.3.3** One factor missing → weight redistributed → sum still `1.0`
- [x] **T8.3.4** `BP_modifier = 0.80` applied → correct multiplication verified
- [x] **T8.3.5** Result clamped to `[0.0, 1.0]` even when product exceeds 1
- [x] **T8.3.6** Capped KO: `ko_fusion_score = 0.50` in formula; `ko_raw_score = 0.90` in state but not in formula
- [x] **T8.3.7** Audit trail contains all factor×weight×score entries

---

### T8.4 — Fallback Policies (`tests/test_fallback_policies.py`)

- [x] **T8.4.1** Factor 4 missing → weight redistributed proportionally; sum stays `1.0`
- [x] **T8.4.2** `get_fallback_for_factor()` returns `FactorOutput(score=0.0, status="fallback_applied")`
- [x] **T8.4.3** `handle_zero_review_comments()` returns valid `FactorOutput` (not an error)
- [x] **T8.4.4** All 5 passive factors fallback → pipeline completes without exception

---

### T8.5 — PII Redaction (`tests/test_pii_sanitizer.py`)

- [x] **T8.5.1** `student_name` absent from all LLM-bound fields after redaction node
- [x] **T8.5.2** `[STUDENT_A]` token present in rendered prompts
- [x] **T8.5.3** Real student name restored in `instructor_report_markdown` after restore node
- [x] **T8.5.4** `pii_substitution_map` empty after `pii_restore_node` runs

---

### T8.6 — Cross-Sprint Memory (`tests/test_cross_sprint_memory.py`)

- [x] **T8.6.1** Sprint 1 → Store entry created at `("students", student_id, "sprint_history")`
- [x] **T8.6.2** Sprint 2 → Sprint 1 entry loaded into `state["historical_trajectory"]`
- [x] **T8.6.3** `historical_trajectory` values visible in rendered explanation prompt
- [x] **T8.6.4** Rolling average: Sprint 2 baseline is average of Sprint 1 and Sprint 2 raw metrics
- [x] **T8.6.5** `sprint_count_used` equals number of prior sprints + 1

---

### T8.7 — Prompt YAML (`tests/test_prompt_yaml.py`)

- [x] **T8.7.1** `prompts.yaml` parses into `PromptLibrary` without error
- [x] **T8.7.2** Both prompt IDs present
- [x] **T8.7.3** All `input_variables` have matching `{placeholder}` in both templates
- [x] **T8.7.4** `render_prompt` raises `KeyError` on missing variable
- [x] **T8.7.5** `strict_constraints` non-empty for both prompts

---

### T8.8 — Explanation Guardrails (`tests/test_explanation_guardrails.py`)

- [x] **T8.8.1** Exact `final_score` value appears verbatim in `instructor_report_markdown`
- [x] **T8.8.2** No factor score in report contradicts `state["factor_scores"]` values
- [x] **T8.8.3** `strict_constraints` guardrail text present in rendered system prompt
- [x] **T8.8.4** `student_feedback_markdown` contains no raw evidence trace data

---

## Phase 9 — End-to-End Validation

> **Depends on:** Phase 8 complete (all tests passing).

---

### T9.1 — Happy Path Mock Run

- [x] **T9.1.1** `await trigger_sprint_end("sprint-01", ["STU-001"])` — thread pauses at quiz interrupt;
  `state["active_verification"]` has snippet, question, deadline
- [x] **T9.1.2** `await submit_quiz_response(thread_id, "The function initializes the session by setting the auth token...")` within window
  — `ko_raw_score` set; `quiz_is_extended == False`; all 6 factor scores present; `final_score ∈ [0.0, 1.0]`
- [x] **T9.1.3** Inspect `mock_context/output/assessment_result_STU-001_sprint-01.json`
  — parses as `AssessmentResultSchema` without error; `lecturer_override_applied == False`;
  `radar_chart_data` has all 6 keys
- [x] **T9.1.4** Inspect `mock_context/output/student_feedback_STU-001_sprint-01.json`
  — parses as `StudentFeedbackSchema`; `calculation_audit_trail` absent; `discrepancy_flags` absent

---

### T9.2 — Discrepancy & Override Path

- [x] **T9.2.1** Modify fixture to trigger `GHOSTWRITER_SUSPICION` (high effort + low KO)
  — thread pauses at `lecturer_review_node`; flag present in state
- [x] **T9.2.2** `await submit_lecturer_review(thread_id, override_score=0.45, reason="Confirmed via oral viva", lecturer_id="LEC-001")`
  — `final_score == 0.45`; `lecturer_override_applied == True`; `lecturer_comments` set correctly

---

### T9.3 — Quiz Extension Path

- [x] **T9.3.1** Simulate Trigger 2 arriving after `time_window_hours` but before `time_window_hours + extra_time_hours`
  — `quiz_is_extended == True`; `ko_fusion_score <= capped_score_ceiling`;
  `ko_raw_score` unchanged; behavioral persona classification uses raw score

---

### T9.4 — LangSmith Trace Review

- [x] **T9.4.1** Project appears in LangSmith under `performance_assessment_com_agent`
- [x] **T9.4.2** Full trace: all 16 nodes as named spans; 5 passive tools concurrent;
  both `interrupt()` events as checkpoints; token usage logged for both LLM calls
- [x] **T9.4.3** No PII tokens (`student_name`, `student_id`, real email) visible in any LangSmith prompt span

---

### T9.5 — Configuration Smoke Tests

- [x] **T9.5.1** Weights summing to `0.99` → `ValueError` raised before any graph execution
- [x] **T9.5.2** Restore correct weights → clean startup; `IS_DEV_MODE == True` confirmed

---

## Dependency Map

```
Phase 0 (Foundation)
    |
Phase 1 (State & Schema)
    |
  --+----------+----------+
  |            |           |
Phase 2     Phase 3     Phase 4
(Ingestion) (Fusion)   (Prompts)
  |            |           |
  --+----------+-----------+
               |
           Phase 5 (Nodes — all independent within)
               |
           Phase 6 (Graph Assembly)
               |
           Phase 7 (Public Entrypoints)
               |
           Phase 8 (Tests — write in parallel with 5-7, run after 7)
               |
           Phase 9 (E2E Validation)
```

---

## File to Task Reference

| File | Phase | Tasks |
|---|---|---|
| `config/weights_config.yaml` | 0 | T0.2.1 |
| `config/quiz_timeout_settings.yaml` | 0 | T0.2.2 |
| `config/settings_loader.py` | 0 | T0.3.1–T0.3.4 |
| `mock_context/student_context.json` | 0 | T0.4.1 |
| `mock_context/mock_github_responses/` | 0 | T0.4.2–T0.4.4 |
| `mock_context/mock_scrum_responses/` | 0 | T0.4.5–T0.4.8 |
| `state.py` | 1 | T1.1, T1.2 |
| `performance_assessment/schemas.py` | 1 | T1.3 |
| `policies/retry_policy.py` | 2 | T2.1 |
| `ingestion/github_client.py` | 2 | T2.2 |
| `ingestion/git_sandbox_runner.py` | 2 | T2.3 |
| `ingestion/scrum_mcp_client.py` | 2 | T2.4 |
| `ingestion/cohort_baseline.py` | 2 | T2.5 |
| `fusion_engine/calculator.py` | 3 | T3.1 |
| `fusion_engine/weights_config.py` | 3 | T3.2 |
| `policies/fallback_policies.py` | 3 | T3.3 |
| `policies/discrepancy_rules.py` | 3 | T3.4 |
| `prompts/prompt_loader.py` | 4 | T4.1 |
| `prompts/prompts.yaml` | 4 | T4.2 |
| `nodes/validation_node.py` | 5 | T5.1 |
| `nodes/passive_runner_node.py` | 5 | T5.2 |
| `nodes/active_quiz_node.py` | 5 | T5.3–T5.5 |
| `nodes/behavioral_node.py` | 5 | T5.6 |
| `nodes/fusion_node.py` | 5 | T5.7 |
| `nodes/discrepancy_node.py` | 5 | T5.8 |
| `nodes/review_node.py` | 5 | T5.9 |
| `nodes/memory_node.py` | 5 | T5.10 |
| `nodes/sanitizer_node.py` | 5 | T5.11 |
| `nodes/explanation_node.py` | 5 | T5.12 |
| `nodes/export_node.py` | 5 | T5.13 |
| `graph.py` | 6 | T6.1, T6.2 |
| `performance_assessment/agent.py` | 7 | T7.1 |
| `tests/test_com_agent_triggers.py` | 8 | T8.1 |
| `tests/test_evidence_isolation.py` | 8 | T8.2 |
| `tests/test_fusion_calculator.py` | 8 | T8.3 |
| `tests/test_fallback_policies.py` | 8 | T8.4 |
| `tests/test_pii_sanitizer.py` | 8 | T8.5 |
| `tests/test_cross_sprint_memory.py` | 8 | T8.6 |
| `tests/test_prompt_yaml.py` | 8 | T8.7 |
| `tests/test_explanation_guardrails.py` | 8 | T8.8 |
