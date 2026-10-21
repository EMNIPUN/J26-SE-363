# Assessment agent

Takes a team (repository link + Scrum board), follows the sprint, assesses every student with the seven factors, checks its own results, and explains each mark. Design: `plan.md` at the repository root.

## How a run works

```
Core API  --create run, defer job-->  queue (Postgres)  -->  worker: performance.assess_team
                                                                |
   team graph (graph.py, TeamGraph)                              v
   load_run_context -> prepare_workspace -> collect_scrum (MCP) -> collect_github -> build_team_evidence
        -> evidence_quality_gate (the only interrupt: lecturer maps unknown authors)
        -> dispatch_students (bounded parallelism) -> team_cross_check -> team_report -> publish
   student graph (StudentPipeline, one per student)
   evidence check -> 5 factors in parallel -> join -> audit (+ one retry of a failed factor) -> Code Ownership quiz state
        -> Behavioral Pattern -> fusion -> explain (audit reasoning, justification) -> export
```

| File | Role |
|---|---|
| `graph.py` | team and student graphs; `shared/performance/topology.py` holds the same shape as data for the frontend |
| `runner.py` | `run_assessment` (start/resume), `refuse_student` (re-compose one student after a quiz answer or expiry), `answer_quiz`, `sweep_quizzes` |
| `factors.py` | the factors as tools: one call each through `com_agent/factor_bridge.py`; result status `completed`, `not_available` (left out of the mark, never 0) or `fallback` (failed) |
| `audit.py` | deterministic findings, optional language-model reasoning (accept, retry or escalate; it can never set a score), default rules without a model |
| `fusion.py` | `S = BP modifier x sum(w x score)` over the factors that exist, weights shared out, conservative band |
| `justify.py` | per-factor reasons built only from results and factor cards; optional rewording whose numbers are checked |
| `quiz_flow.py` | Code Ownership question: one per student and sprint, 48 h + 48 h windows, cap 0.50 in the second window, 0 after both |
| `events.py` | node start/end/error/wait and log events (what the live pipeline shows); no secrets or student text |
| `services.py` | what a run needs: store, read-only workspace, Scrum MCP client, GitHub, language model; `RunData` keeps evidence on disk so a waiting run survives a restart |
| `report.py` | lecturer report (markdown) |

Quiz answers and lecturer reviews never hold a thread: a student without an answer is `provisional` with Code Ownership `pending`, and is composed again when the answer arrives (`performance.refuse_student`).

## Running it

```
cd backend/agentic_framework
uv run python -m worker                 # consumes the queue: assess_team, resume_run, refuse_student, sync_team, and the periodic jobs
```

Environment (worker): `SERVER_DIRECT_URL` (database), `GITHUB_TOKEN` (private repositories, review data), `ASSESSMENT_GROQ_API_KEYS` (Requirement Fulfillment and the auditor; without it RF is "not available"), `ASSESSMENT_WORKSPACE` (folder for the read-only clones and run data), `SCRUM_DATA_DIR` (optional; Scrum MCP data folder).
Core API: `GITHUB_WEBHOOK_SECRET` for `POST /api/v1/performance/webhooks/github`.
Schema: `uv run alembic upgrade head` in `backend/server` (revision `a7c3d5e91f02`). Not applied by any code path automatically.

Periodic jobs: `performance.sync_all` every 2 hours, `performance.snapshot_all` nightly (each team at its own offset inside a 3-hour window), `performance.quiz_sweep` hourly.

## Tests

```
cd backend/agentic_framework && ../.venv/Scripts/python.exe -m pytest app/agents/performance_assessment/assessment tests/test_performance_tasks.py tests/test_performance_store.py
```

`tests/test_pipeline.py` runs the whole pipeline on a throwaway git repository with the real Scrum MCP server as a subprocess, a fake GitHub and a scripted model. The store tests need the local PostgreSQL (`SELVIA_TEST_DSN`, default `postgresql://postgres:test@localhost:55432/selvia`) and skip without it.

## Limits to keep in view

- All factor validation used ratings written by an assistant, not teaching staff.
- The board export keeps only a task's final status, so a snapshot judges tasks by their status now, not as they were on the snapshot day.
- Requirement Fulfillment has no finished held-out evaluation; its band is rough.
- Audit of a re-composed student (after a quiz answer) runs without the evidence (it is not stored with the result), so the "silent but visible" check is skipped there.
- The Requirement Fulfillment sub-agent's inner steps appear as log lines of its node, not as separately lit nodes.
