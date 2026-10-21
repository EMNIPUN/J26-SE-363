# PLAN — Requirement Quality Agent (+ Decomposition, + DART)

> Component: **Requirement Analysis & Project Planning** (`project_planning`) · Owner: Rajapaksha R W V C V, IT23152878 · Project J26-SE-363 / SELVIA
> Target: end-of-October viva — **2 core functions working end-to-end + DART as the novelty**.
> **On approval, step 0 is to copy this file to `J26-SE-363/PLAN.md`** (plan mode cannot write there yet).

---

## Context

Students in project-based learning write poor requirements and get slow lecturer feedback. This component turns an uploaded SRS into a sprint-ready backlog by gating the student's own work through specialized ReAct agents, and — the research contribution — arbitrating agent disagreement with **DART** (Diagnostic Arbitration via Reasoning Traces) instead of naive re-voting/averaging.

The SELVIA platform and its common foundation are **already built**: shared Pydantic contracts, a deterministic prefix-router orchestrator, two FastAPI services, Keycloak/Kong, and a **fully-built frontend** for this module running on mock data. The `project_planning` agent slot already exists in the contracts and routing — **the files are just empty**. So this work is: fill one agent folder, add one line to the registry, add Core-API endpoints + persistence, and point the existing frontend at real data. **No shared or teammate code is forked.**

### Decisions locked with the owner
| # | Decision | Choice |
|---|---|---|
| 1 | LLM provider | **Groq** (mirror the repo's working `GroqMultiKeyClient` pattern; the proposal's GPT-4o-mini is substituted — justify in report). |
| 2 | Build fidelity | **Pragmatic MVP on correct foundations** — real spaCy/ChromaDB/SBERT/Groq, but small seed data & LLM-centric scoring; no throwaway stubs. |
| 3 | Quality dimensions | **IEEE 830 six**: clarity, completeness, correctness, testability, consistency, traceability. Update the frontend to match. |
| 4 | Persistence | **Dedicated results table**, done the correct way (Alembic migration, owned & written by the Core API), because research continues after the deadline. |
| 5 | Gate threshold | **75** default, configurable (FR-04). Frontend mock's `70` → `75`. |

---

## Step 1 — Understanding (summary)

### (i) What my component must do (per proposal `IT23152878.pdf` §3.3, §5.1, and `Architecture & Build Guide` §6–13)
- **FR-01** Parse uploaded SRS (`.docx`) → individual requirements (rule-based, python-docx).
- **FR-02** Score each requirement on the six IEEE 830 dimensions; **FR-03** emit structured diagnostic rationales + evidence; **FR-04** enforce a configurable quality gate (default ≥75: pass / block+feedback / low-confidence→DART).
- **FR-05** Evaluate student-written user-story decomposition against parent requirements (INVEST, coverage).
- **FR-07/08/09** DART arbitration on low confidence or disagreement: classify uncertainty (COMPOUND/AMBIGUOUS/STRUCTURAL/NOVEL), pick a resolution (RESOLVE/RETRIEVE/REFINE/ESCALATE), escalate to instructor when unresolvable.
- Everything is **ONE registered agent** (`project_planning`, prefix `planning.`). The three "agents" + DART are internal Python modules behind `handle()` (Build Guide §7 — "the single most important idea").
- *(Out of presentation scope: Effort Estimation agent + XGBoost, FR-06 — post-viva.)*

### (ii) What the current architecture already provides
- **Contracts** `backend/shared/src/shared/contracts/agent.py`: `AgentName.PROJECT_PLANNING` + `ACTION_PREFIX_TO_AGENT["planning"]` **already exist**. `AgentRequest{action, input, scope ids, requester}` → `AgentResponse{status, result, evidence[], next_action, error}`. Component shapes ride inside `input`/`result` — **never fork the contract**.
- **Agent interface** `backend/agentic_framework/app/agents/base.py`: `BaseAgent` protocol = one `async def handle(AgentRequest) -> AgentResponse`.
- **Registry** `.../app/agents/registry.py`: currently `return {}` → every `planning.*` request answers `unavailable`. Register with **one line**.
- **Orchestrator** `.../app/orchestrator/` (`route → execute → finalize`): deterministic prefix routing, no code change needed.
- **Two paths**: fast = Core API `AIBackendClient.orchestrate()` → `POST /api/v1/orchestration` (:8003); slow = `start_ai_job()` → Procrastinate worker → same orchestrator. Poll `GET /api/v1/jobs/{id}`.
- **Reference implementation**: teammate's `performance_assessment/` is a full LangGraph+Groq agent with its own DB/checkpointer — the pattern to imitate (but **do not import** from it; it's CODEOWNERS-protected).
- **Core API** `backend/server/` (:8002): Keycloak JWT auth (`app/core/security.py`), SQLAlchemy 2 + Alembic, models `user/group/project/agent_run`, empty `app/modules/planning/`, `app/api/v1/router.py` to mount new routers.
- **Frontend** `frontend/src/modules/planning/` (React 19 + Vite, JS, shadcn, Tailwind v4, React Query, axios, Keycloak): pages `SRSQuality.jsx`, `Decomposition.jsx`, `Estimation.jsx`, instructor `ArbitrationOversight.jsx` (for DART), components `QualityRadarChart`, `AgentBadge`, `RequirementListPanel`, `HighlightedRequirementText`, `WorkflowStepper`. All on `data/mockData.js`.

### (iii) The gap
| Needed | Status today |
|---|---|
| `project_planning/agent.py`, `schemas.py` | **Empty files** |
| Registry entry | Missing (one line) |
| Component orchestrator, extraction, quality/decomposition sub-agents, DART | **Do not exist** |
| LLM client usable in my folder | Only teammate's (protected). Need **my own** Groq client. |
| spaCy, ChromaDB (vector KB), sentence-transformers/SBERT | **Not installed** anywhere — all net-new deps |
| Core API `planning.py` endpoints + persistence model/migration | **Do not exist** |
| Frontend → real backend wiring; IEEE 830 dimensions; threshold 75 | On mock data; dimensions/threshold mismatched |

---

## Step 2 — Implementation plan: Requirement Quality Agent (build FIRST)

### 2a. Folder layout (all under `backend/agentic_framework/app/agents/project_planning/`)
Mirrors Build Guide §11. Create only what Function 1 needs first; the rest are stubs to grow.
```
project_planning/
├─ agent.py            # ProjectPlanningAgent.handle() — reads request.action, runs component orchestrator
├─ schemas.py          # Pydantic models for input/result (see 2b)
├─ llm/groq_client.py  # OWN Groq client (mirrors teammate pattern; cannot import theirs)
├─ orchestrator/
│  ├─ graph.py         # internal LangGraph: extract → quality → gate (→ decompose → gate … later)
│  ├─ state.py         # shared internal state object
│  └─ gates.py         # ≥75 pass · <75 block+feedback · low-confidence → DART
├─ extraction/extractor.py   # python-docx: SRS .docx → requirement list
├─ subagents/quality/
│  ├─ graph.py         # ReAct loop: reason → execute_tool → reflect → finalize
│  ├─ tools.py         # the 5 tools (2c)
│  └─ prompts.py
├─ knowledge/
│  ├─ vector_store.py  # ChromaDB client + SBERT embedding fn (collections below)
│  └─ seed/            # curated seed docs (IEEE 830, SMART, exemplars)
└─ tests/test_quality_agent.py
```
Add the registry line in `app/agents/registry.py`:
```python
from app.agents.project_planning.agent import ProjectPlanningAgent
def build_agent_registry():
    return {AgentName.PROJECT_PLANNING: ProjectPlanningAgent()}
```

### 2b. Inputs / outputs (example JSON — ride inside `AgentRequest.input` / `AgentResponse.result`)
**Action:** `planning.analyze_quality` (fast) · `planning.extract_requirements` (slow job, SRS upload).

**`AgentRequest.input`:**
```json
{
  "requirements": [
    { "id": "FR-01", "text": "The system shall provide a user-friendly login page.", "type": "functional" }
  ],
  "srs_context": { "all_requirement_texts": ["..."] },
  "options": { "threshold": 75 }
}
```
**`AgentResponse.result`:**
```json
{
  "threshold": 75,
  "requirements": [{
    "id": "FR-01",
    "overall_score": 68,
    "status": "blocked",
    "gate_action": "block",
    "dimension_scores": {
      "clarity":      { "score": 55, "rationale": "...", "issues": ["vague term 'user-friendly'"] },
      "completeness": { "score": 70, "rationale": "..." },
      "correctness":  { "score": 75, "rationale": "..." },
      "testability":  { "score": 60, "rationale": "..." },
      "consistency":  { "score": 80, "rationale": "..." },
      "traceability": { "score": 68, "rationale": "..." }
    },
    "smells": [{ "type": "vague_term", "span": "user-friendly", "suggestion": "specify measurable criteria" }],
    "suggested_rewrite": "The system shall display a login form with email and password fields and validate credentials within 2 seconds.",
    "confidence": 0.78,
    "dart_triggered": false
  }]
}
```
`AgentResponse.evidence[]` carries tool observations as `Evidence(source, description, reference, data)` (e.g. retrieved IEEE 830 clause, matched exemplar, SBERT duplicate pair) — satisfies FR-03 + NFR-05 transparency. This maps cleanly onto the frontend requirement shape (`overallScore`, `dimensionScores`, `status`, `suggestedRewrite`).

### 2c. Quality criteria/metrics & scoring (proposal §3.2.3, §3.3.1)
- **Six dimensions**, each scored **0–100** by `dimension_scorer` (Groq, structured JSON with per-dimension rationale), **grounded** by the deterministic smell output + retrieved standards/exemplars (not free-floating LLM guesses).
- **Composite** = mean of the six (equal weights initially; weights configurable — proposal leaves them experimental).
- **Gate** (`gates.py`): `≥75 → pass`; `<75 → block + actionable feedback`; **confidence < threshold → trigger DART**.
- **Confidence (calibrated reliability, §3.6)**: MVP = self-consistency — run scoring over **N independent passes with temperature variation**, measure agreement across diagnosis/scores; low agreement ⇒ low confidence ⇒ DART. Correct, extensible foundation for the later full 4-dimension calibration.

### 2d. LLM / NLP approach (per decisions)
- **LLM**: own `llm/groq_client.py` (multi-key round-robin like the reference; env `GROQ_API_KEYS`/`GROQ_MODEL`), structured-JSON prompts in `prompts.py`.
- **ReAct** via LangGraph `StateGraph` (nodes `reason → execute_tool → reflect → finalize`, conditional edges per proposal §3.2.2). Safety: **max 10 iterations + per-agent timeout → fallback to direct scoring**.
- **Five tools** (`subagents/quality/tools.py`):
  | Tool | Impl (MVP, correct) |
  |---|---|
  | `smell_detector` | **spaCy** `en_core_web_sm` + regex: vague terms, passive voice, unbounded quantifiers, missing conditions. Deterministic. |
  | `standard_retriever` | **ChromaDB** collection `ieee830_smart`, SBERT-embedded, seeded with curated clauses. |
  | `exemplar_retriever` | **ChromaDB** `exemplars` (graded high/med/low requirement examples). |
  | `dimension_scorer` | **Groq** LLM, one structured call scoring all six dims with rationale. |
  | `cross_req_checker` | **SBERT** (`all-MiniLM-L6-v2`, 384-d) cosine across the SRS → duplicates/contradictions/overlap (feeds consistency + traceability). |
  > SBERT serves **both** `cross_req_checker` and the ChromaDB embedding function — one dependency, two uses (efficient + correct).

### 2e. Where it fits / files to add or modify
- **Add** (my agent): the whole `project_planning/` tree above. **Modify (1 line):** `app/agents/registry.py`.
- **Core API — add** `backend/server/app/api/v1/planning.py`; **modify** `app/api/v1/router.py` (mount router); **add** `app/modules/planning/service.py` (persistence/business logic).
- **Reuse (no change):** `app/clients/ai_backend.py` (`orchestrate`), `app/services/ai_jobs.py` (`start_ai_job`), `app/core/security.py` (auth).

### 2f. API endpoints, data models, DB schema (Core API)
**Endpoints** (`planning.py`, all `Depends(get_current_user)`; build `requester` from the token, never the body):
| Method | Path | Mode | Action |
|---|---|---|---|
| POST | `/planning/quality` | fast → `orchestrate()` | `planning.analyze_quality` |
| POST | `/planning/srs` (or `/projects/{id}/srs`) | slow → `start_ai_job()` | `planning.extract_requirements` (+quality) |
| GET  | `/planning/quality/{project_id}` | — | read persisted results/history |
| GET  | `/api/v1/jobs/{id}` | — | **existing** job polling (reuse) |

**Persistence (correct method)** — follow `docs/SCHEMA_CHANGE_GUIDE.md` exactly:
- **Model** `app/models/requirement_quality.py` → `RequirementQualityResult`: `id`, `project_id` (FK), `requirement_ref` (str), `requirement_text`, `overall_score` (int, nullable), `status` (`string_enum` passed/blocked/needs_review), `dimension_scores` (`JSONType`), `smells` (`JSONType`), `suggested_rewrite` (nullable), `confidence` (float, nullable), `dart_triggered` (bool default in Python), `TimestampMixin`. New columns nullable, **no `server_default`**, naming via `base.py` convention. Multiple rows per requirement = history.
- **Import** it in `app/models/__init__.py` (or Alembic won't see it).
- **Preflight**: add a `TableSpec` to `APP_TABLES` in `scripts/supabase_preflight.py` (test `test_expected_tables_match_the_models` enforces this).
- **Migration**: `uv run alembic -x "db_url=$dev" revision --autogenerate -m "add requirement_quality_result"`, then add the **RLS enable + browser-role REVOKE** block after `op.create_table(...)`. Apply **locally** (`upgrade head`) for the demo; **Supabase apply is a coordinated post-PR step** with the foundation owner (never apply to Supabase solo).
- **Ownership rule honored**: the **Core API** writes this table (AI backend only returns the result); AI backend persists nothing business-level.

### 2g. Frontend changes (`frontend/src/modules/planning/`)
- **`src/shared/api/endpoints.js`**: add `PLANNING.QUALITY`, `PLANNING.SRS`, `PLANNING.QUALITY_RESULTS(projectId)`, `PLANNING.DECOMPOSITION`.
- **`services/qualityService.js`** (mirror `planningService.js`) + **React Query hooks** (`hooks/useQuality.js`, mirror `useProjects.js`): `useAnalyzeQuality()`, `useQualityResults(projectId)`.
- **`pages/student/requirements/SRSQuality.jsx`**: replace mock `rescoreRequirement`/`addRequirement` with the hooks; adapter maps `result.requirements[*]` → existing shape (`overallScore`, `dimensionScores`, `status`, `suggestedRewrite`). Keep all existing components.
- **Dimension/threshold alignment** (decisions 3 & 5): `data/mockData.js` → `QUALITY_DIMENSIONS` to the **IEEE 830 six**, `QUALITY_GATE_THRESHOLD 70 → 75`; `components/QualityRadarChart.jsx` labels; `statusFromScore`/`dimTier` thresholds reviewed. (Keep `mockData.js` as fallback until wiring is verified.)

### 2h. Integration with Decomposition & DART
- **Decomposition** is the next internal sub-agent in the **same component orchestrator** (`extract → quality → gate → decompose → gate`), same ReAct shape, tools `pattern_retriever` (ChromaDB `decomposition_patterns`), `invest_validator` (rules+Groq), `coverage_analyzer` (SBERT coverage gaps), `decomposition_scorer` (Groq) + its own ≥75 gate. Action `planning.analyze_decomposition`.
- **DART** sits beside the sub-agents (`dart/arbiter.py`): a sub-agent returning **low confidence / conflict** hands its structured reasoning to DART (gather → categorize → consult → respond → resolve). `COMPOUND → route to decomposition`; `AMBIGUOUS → retrieve standards+exemplars, re-consult`; `STRUCTURAL → re-check consistency`; `NOVEL → flag instructor`. Convergence: **≤2 loops then escalate**; circuit-breaker at 5+ activations/session. To involve the real instructor/other components, return a `NextAction` — never call another agent directly.

### 2i. Ordered task breakdown with estimates
| # | Task | Files | Est. |
|---|---|---|---|
| 1 | **Skeleton**: `handle()` returns hard-coded `completed`; register; first schemas; confirm routing ≠ unavailable | `agent.py`, `registry.py`, `schemas.py` | 0.5 d |
| 2 | Own **Groq client** + env + a smoke call | `llm/groq_client.py`, `.env` | 0.5 d |
| 3 | **Extraction** (python-docx) + **component orchestrator** (`extract → quality`) + state + gates | `extraction/`, `orchestrator/` | 1 d |
| 4 | **ChromaDB + SBERT** wiring + seed `ieee830_smart` & `exemplars` + one-off ingest | `knowledge/` | 1 d |
| 5 | **Quality ReAct sub-agent** + 5 tools + 6-dim scoring + confidence | `subagents/quality/` | 2 d |
| 6 | **Gate** logic + structured result assembly + evidence | `orchestrator/gates.py`, `agent.py` | 0.5 d |
| 7 | **Core API**: `planning.py` endpoints + router mount + persistence model + **local migration** | `server/app/...`, `alembic/` | 1.5 d |
| 8 | **Frontend wiring** + dimension/threshold alignment | `endpoints.js`, `qualityService.js`, `useQuality.js`, `SRSQuality.jsx`, `mockData.js`, `QualityRadarChart.jsx` | 1 d |
| — | **→ Function 1 demo-ready** | | |
| 9 | **Decomposition sub-agent** + tools + gate + endpoint + `Decomposition.jsx` | `subagents/decomposition/`, FE | 2 d |
| — | **→ Function 2 demo-ready (40% viva bar met)** | | |
| 10 | **DART basic**: gather + categorize + AMBIGUOUS & COMPOUND paths + convergence; trigger from quality low-confidence; wire `ArbitrationOversight.jsx` | `dart/`, FE | 2 d |
| 11 | Seed data polish, **pytest**, end-to-end rehearsal, slides | `tests/`, demo SRS | 1.5 d |
| — | Buffer | | 1 d |

### 2j. Testing / evaluation (how to prove it for the viva)
- **Unit (pytest)**: `smell_detector` flags planted smells; `dimension_scorer` returns valid 6-dim JSON; gate boundaries (74/75/76); confidence→DART trigger; DART categorizer on crafted cases.
- **Integration**: call the orchestrator with `planning.analyze_quality` in `agentic_framework/tests/` and assert `status=completed` + schema.
- **E2E**: upload a prepared SRS `.docx` → gated results render in `SRSQuality.jsx`.
- **Demo script**: a hand-crafted SRS mixing clearly-good, clearly-bad (vague/untestable → blocked), a **compound** requirement (forces DART→COMPOUND→decomposition) and an **ambiguous** one (DART→AMBIGUOUS→retrieve). This visibly demonstrates both functions **and** the novelty.
- **Research metrics** (partial for viva, full post-viva): Cohen's κ vs a small manually-labeled set (NFR-03 ≥0.60); the 4-condition ablation (pipeline / agent / agent+simple-arbitration / agent+DART).

---

## Step 3 — 2-week roadmap (demo milestones)
- **Week 1 → Milestone A (Function 1):** tasks 1–8. SRS in → Quality agent scores six IEEE 830 dims → ≥75 gate blocks/passes → real results in the UI.
- **Week 2a → Milestone B (Function 2):** task 9. Decomposition agent + gate wired end-to-end → **40% viva bar met**.
- **Week 2b → Milestone C (Novelty):** task 10. DART triggers on low confidence/conflict, classifies the category, applies a targeted resolution, shows the reasoning trace in `ArbitrationOversight.jsx`. **This is what demonstrates the novelty** — contrast it live against "re-vote/average" baselines (proposal §3.4.5 Table 3.9).
- **Close:** task 11 — rehearse, seed, test, slides.

---

## Step 4 — My manual tasks (checklist)
> PowerShell on Windows; `py`/`node` confirmed present. `uv` and spaCy model are the likely new installs.

1. **Install toolchain**: `uv` (`pip install uv` or winget), Node already present. Verify: `uv --version`, `node --version`.
2. **Sync deps (each service)**: from `backend/server/`, `backend/agentic_framework/`, `backend/shared/` run `uv sync`.
3. **Add my new deps** (from `backend/agentic_framework/` only): `uv add chromadb sentence-transformers spacy python-docx` then `uv run python -m spacy download en_core_web_sm`. *(sentence-transformers pulls torch — sizable download.)*
4. **Env files**: `cp backend/server/.env.example backend/server/.env`; `cp backend/agentic_framework/.env.example backend/agentic_framework/.env`; `cp .env.example .env.development` + `.env.local`; `cd frontend && cp .env.example .env.development`.
5. **Groq key**: create a free key at console.groq.com → put `GROQ_API_KEYS=...` (and `GROQ_MODEL=openai/gpt-oss-120b`) in `backend/agentic_framework/.env`.
6. **Database (local)**: start the dockerized dev DB `docker compose up -d server-postgres` (port 5433) **or** point `SERVER_DATABASE_URL`/`SERVER_DIRECT_URL` at your DB. Verify: from `backend/server/` → `uv run python -c "from app.database import check_db_connection; print(check_db_connection())"`.
7. **Infra for the frontend login** (Keycloak+Kong): `docker compose --profile infra up -d`. *(See §5 for a no-auth fallback for backend-only demos.)*
8. **Migrate (local)**: from `backend/server/` → `uv run alembic -x "db_url=$dev" upgrade head` (after the new migration exists).
9. **Run services** (3 terminals):
   ```bash
   # Core API      (backend/server/)
   uv run uvicorn app.main:app --reload --port 8002
   # AI Backend    (backend/agentic_framework/)
   uv run uvicorn app.main:app --reload --port 8003
   # Worker        (backend/agentic_framework/)
   uv run python -m worker --queues planning
   ```
10. **Run frontend**: `cd frontend && npm install && npm run dev`.
11. **Verify end-to-end**: open the planning module → upload a sample SRS → confirm gated results; and/or hit AI backend directly (no auth):
    ```bash
    curl -X POST http://localhost:8003/api/v1/orchestration -H "Content-Type: application/json" \
      -d '{"requester":{"user_id":"u-1","role":"student"},"action":"planning.analyze_quality","input":{"requirements":[{"id":"FR-01","text":"The system shall provide a user-friendly login page."}]}}'
    ```
12. **Run tests**: `uv run pytest -q` in `backend/server/` and `backend/agentic_framework/`.

---

## Step 5 — What I need from you

### BLOCKING
1. **Groq API key** (free) — required for any LLM scoring.
2. **Local DB choice** — use the dockerized `server-postgres:5433`, or your own `SERVER_DATABASE_URL`/`SERVER_DIRECT_URL`? Needed before migrations.
3. **Sample SRS `.docx` files** — ideally 1–2 real ones plus permission for me to craft a "demo SRS" with planted good/bad/compound/ambiguous requirements.
4. **Curated seed content** for the knowledge bases (IEEE 830 quality criteria text, SMART definitions, graded exemplars, decomposition patterns, INVEST criteria). I can **draft** these for your review — confirm that's acceptable, or supply your own.
5. **Branch / foundation state** — confirm you're on the branch where the common foundation (shared contracts + orchestrator) is present and green, and that `project_planning/` is yours to fill (Build Guide confirms it is).

### NICE-TO-HAVE
- A small **human-labeled** requirement set for the Cohen's κ metric (NFR-03).
- A **Supabase apply window** coordinated with the foundation owner (only when you want results on the shared DB; local is enough for the viva).
- PROMISE/Deep-SE dataset access — **only** for the Effort agent (post-viva).

### Ambiguities / contradictions found (flagged, not silently resolved)
1. **LLM**: proposal says GPT-4o-mini; repo only has **Groq** working → using Groq (decision 1).
2. **Dimensions**: frontend mock uses *feasibility, scope*; proposal/IEEE 830 uses *correctness, traceability* → aligning to proposal, updating FE (decision 3).
3. **Gate threshold**: proposal `75` vs frontend mock `70` → `75` configurable (decision 5).
4. **Ports**: some docs say Core 8000 / AI 8001 (vision) — **implemented** ports are **8002 / 8003**; using those.
5. **Tooling**: Build Guide assumes ChromaDB/SBERT/spaCy; **none exist in the repo** → net-new deps (expected, planned in task 3–4).
6. **"Three agents"**: proposal/diagram draw them as separate; Build Guide + code = **one** registered agent with internal modules → following the one-agent rule.
7. **Groq client location**: the only working client is inside the **teammate's protected folder** → I build **my own** under `project_planning/llm/` (no cross-agent import).
8. **Redis** (proposal tech stack) — not in compose/code → **skipped** for MVP (not needed).
9. **DART** appears in **no** team/foundation doc — correct, because it's internal to this agent; no shared-contract change needed.

---

## Verification (end-to-end)
1. **Routing**: `planning.analyze_quality` returns `completed` (not `unavailable`) after the registry line — prove before any AI logic.
2. **Backend-only**: the `curl` in manual task 11 returns a valid 6-dimension `result` + `evidence[]`.
3. **Persistence**: after a `/planning/quality` call, a row exists in `requirement_quality_result` (query the local DB); `GET /planning/quality/{project_id}` returns it.
4. **Full E2E**: upload demo SRS in the UI → blocked requirements show feedback, passing ones advance, a compound/ambiguous one triggers DART with a visible reasoning trace.
5. **Tests**: `uv run pytest -q` green in both backend services.
6. **Demo rehearsal**: run the prepared demo script start-to-finish within NFR timings (single requirement <30 s; DART <60 s).
