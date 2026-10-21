# CONFLICTS.md: shared and teammate-owned files touched by the Security Assistant integration

Branch: `integration/security-assistant` (created from `feature/assessment-models-sadeesha`, 4787c07, on 21 Oct 2026).
Plan: [docs/security-assistant/INTEGRATION_PLAN.md](docs/security-assistant/INTEGRATION_PLAN.md).
This file is kept current: **every edit to a shared or teammate-owned file is its own commit whose message starts with `SHARED:`** and gets a row here in the same or the next commit.

List them all at any time:

```
git log --grep='^SHARED:' --oneline
```

## How to read a row

| Column | Meaning |
|---|---|
| File | path of the shared or teammate-owned file |
| Owner | who owns it (common = shared by all, or a teammate's area) |
| Change | what my commit does to it (lines) |
| Why | the reason the file had to change |
| Commit | the `SHARED:` commit (or the commit on my earlier branch) |
| Undo | how to take my change out |
| Re-apply | how to put it back after a merge |
| Conflict risk | how likely a later merge conflict is, and how to resolve it |

Generic resolution when a later merge conflicts on one of these files: take the other side's version of the file, then re-apply my change with `git cherry-pick -n <commit> -- <file>` (or copy the few lines listed in the row), and run the three test suites.

---

## A. The step-0 merge (`008d23a`, "SHARED: merge feature/init-security-agent ...")

My 62 earlier commits were merged into the teammates' latest branch. Files that **both sides changed**:

| File | Owner | Result | Resolution | Conflict risk later |
|---|---|---|---|---|
| `backend/agentic_framework/pyproject.toml` | common | **real conflict**: both sides added settings under `[tool.pytest.ini_options]` | kept every line of both sides: their `norecursedirs`, my `markers` and `addopts` (fast suite excludes `integration` and `live`) | low: if it conflicts again, keep both blocks |
| `backend/server/app/api/v1/router.py` | common | automatic (different hunks) | their `performance_router` and `performance_public_router` lines stay; mine adds one import and one `protected_router.include_router(security_assistant_router)` | low: re-add my 2 lines |
| `frontend/src/shared/layout/navConfig.js` | common | automatic (different hunks) | their changes stay; mine adds one nav entry for each of the three roles ("Security Assistant (live results)") | low: re-add my 3 lines |

Everything else of mine in shared files merged cleanly because the teammates did not change those files (section B).

---

## B. Shared files my branch had already changed before the integration branch existed

These commits are older than the `SHARED:` rule, so their messages have no prefix. Their commit ids are in this branch's history (the merge keeps them).

### B1. Rename "AEGIS" to "Security Assistant" (commit `d838fb9`)

| File | Owner | Change | Undo / re-apply |
|---|---|---|---|
| `backend/shared/src/shared/contracts/agent.py` | common | `AgentName.AEGIS = "aegis"` becomes `SECURITY_ASSISTANT = "security_assistant"`; the `security` action prefix maps to it | `git revert d838fb9` / `git cherry-pick d838fb9` |
| `backend/agentic_framework/tests/test_orchestrator.py`, `tests/test_shared_contracts.py` | common | the same name in 5 + 2 test lines | same commit |
| `backend/agentic_framework/app/agents/aegis/` | the original AEGIS placeholder | folder renamed to `security_assistant/` (the 4 placeholder files moved, its README deleted) | same commit |
| `backend/README.md`, `docs/BACKEND_COMMON_WORKFLOW_PROPOSAL.md`, `docs/COMMON_FOUNDATION_REPORT.md`, `docs/TEAM_DEVELOPMENT_GUIDE.md`, `frontend/README.md`, `frontend/docs/ACADEMIC_SCOPE_GUIDELINES.md` | common | wording: AEGIS -> Security Assistant | same commit (`68536eb` for the guidelines file) |
| `frontend/src/modules/performance/services/performanceService.js`, `planning/data/lmsAcademicData.js`, `planning/data/mockData.js`, `tutor/data/mockTutorData.js`, `shared/constants/academicScope.js`, `shared/constants/modules.js`, `security/data/mockFindings.js`, `security/pages/Dashboard.jsx`, `security/services/securityService.js` | teammates' mock data and my mock pages | one string each ("AEGIS" -> "Security Assistant"); the mock pages keep working | same commit |

Conflict risk: the teammates' new code does not use the name AEGIS (checked on their latest branch), so a merge is clean today. If a teammate adds `AgentName.AEGIS` later, replace it with `SECURITY_ASSISTANT`.

### B2. My shared edits for the read-only frontend (the five agreed files)

| File | Owner | Change | Commit | Undo | Re-apply |
|---|---|---|---|---|---|
| `backend/server/app/core/config.py` | common | +2 settings (`SECURITY_ASSISTANT_RESULTS_DIR`, `SECURITY_ASSISTANT_DEMO_MODE`) and the `security_assistant_results_dir` property | `93233bb` | `git revert 93233bb` | `git cherry-pick 93233bb` |
| `backend/server/app/api/v1/router.py` | common | +1 import, +1 `include_router` | `4f888c4` | `git revert 4f888c4` | `git cherry-pick 4f888c4` |
| `frontend/src/shared/api/endpoints.js` | common | +1 block `SECURITY_ASSISTANT` (11 paths) | `954ed5f` | `git revert 954ed5f` (also reverts the other step-6 files) | copy the block |
| `frontend/src/modules/security/routes.jsx` | my mock pages' routes | +1 import, +1 route `assistant/*` | `954ed5f` | as above | copy the 2 lines |
| `frontend/src/shared/layout/navConfig.js` | common | +3 nav entries "Security Assistant (live results)" (student, lecturer, admin) | `954ed5f` | as above | copy the 3 lines |

### B3. Setup and documentation files

| File | Owner | Change | Commits |
|---|---|---|---|
| `backend/agentic_framework/.env.example` | common | new variables for the scanners, the LLM, the governance and the agent loops (documentation only) | `d838fb9 68536eb 9f07788 3ccfb88 a6bc8b1 4cb3ba9 144952d 78295fb 641229f 6830f6e 7066e51` |
| `backend/.gitignore` | common | ignores `agentic_framework/scan_output/` and `*.local.json` (local scan output and the local name mappings) | `f80eb6e 4cb3ba9` |
| `backend/agentic_framework/.python-version` | common | pins Python 3.11 | `9f07788` |
| `backend/agentic_framework/pyproject.toml` | common | markers and addopts (see section A) | `d838fb9 197907d` |

Conflict risk for B3: low (appended lines). Keep both sides.

---

## C. Edits made on the integration branch (kept current, one row per `SHARED:` commit)

| # | File | Owner | Change | Why | Commit | Undo | Re-apply | Conflict risk |
|---|---|---|---|---|---|---|---|---|
| 1 | `backend/agentic_framework/app/agents/registry.py` | common | +1 import, +1 entry | register the agent | _step 1_ | | | |
| 2 | `backend/shared/src/shared/security_assistant/webhook_rules.py` | common (new file) | add-only | HMAC check and event classification shared by the Core API and the agent | _step 5_ | | | none (new file) |
| 3 | `backend/server/app/core/config.py` | common | + settings for the scan gates | limits, LLM gate, allow-list, webhook secret | _steps 4-5_ | | | |
| 4 | `backend/server/app/api/v1/router.py` | common | +1 line: public webhook router | the signed webhook route | _step 5_ | | | |
| 5 | `backend/server/tests/test_route_protection.py` | common | + allow-list entry | the webhook route is public on purpose | _step 5_ | | | |
| 6 | `backend/agentic_framework/.env.example`, `backend/server/.env.example` | common | + documented variables | worker and gate settings | _steps 2-6_ | | | |

## D. Files I deliberately do not touch

`docker-compose.yml` (the worker goes in a new file `docker-compose.security.yml`), `backend/server/app/api/v1/performance.py`, `backend/server/app/modules/performance/*`, `backend/agentic_framework/app/tasks/performance_tasks.py`, `backend/agentic_framework/app/tasks/security_tasks.py` (three stub tasks that return **fake "safe" results**: nothing calls them; deleting them is proposed for after the viva), `shared/performance/*`, every `perf_*` table, the `agent_runs` table, every `rqa_*` table (read-only if present).

## E. Facts about the teammates' branches (for the later merge)

- `feature/assessment-models-sadeesha` (this branch's base) has the teams flow, the queue, the performance module with the GitHub webhook, and **no requirement, user-story or task tables**.
- `feat/req-rag` and `feat/req-novelty` have the `rqa_*` requirement tables on an **older core** (no teams, no `repo_url`). They have not been merged into the base. When they are, the adapter reads their tables unchanged.
- Pre-existing failures of the teammates' own tests in this environment (41 in `app/agents/performance_assessment`) are identical on their branch tip and are not caused by this merge.
