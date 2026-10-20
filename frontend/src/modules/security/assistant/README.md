# Security Assistant frontend: plan

Status: **plan only, no code written.** On approval this file is saved as `frontend/src/modules/security/assistant/README.md` and the build starts at step 0.
Decisions already taken with you: the API is a **Core API router that reads result files**; the pages are a **sub-section of `modules/security`**;
a student sees **the team run plus a "mine" filter**; results are **folders on disk** (no database change).

---

## 1. Repo review: what exists and where each part belongs

| Area | What I found | Where the Security Assistant part goes |
|---|---|---|
| Frontend stack | React 19, Vite, **plain JS**, react-router v7, TanStack Query, axios, Tailwind v4 + shadcn/radix (`src/components/ui/`: tabs, table, dialog, sheet, tooltip, progress, skeleton, badge, card ...), recharts, lucide, sonner. Tests: **vitest only**, using `renderToStaticMarkup` (no jsdom, no testing-library). | Reuse all of it. No new dependency. |
| Routing / layout | `App.jsx`: `RequireAuth` > `RequireAccount` > `DashboardShell` > `/teams/:teamId` (`TeamScopeGuard`: unknown or foreign team = 404) > `security/*` -> `modules/security/routes.jsx`. Per-role nav in `shared/layout/navConfig.js` ("Project Security" group for students, "Security & Quality" for lecturers). | New pages mount at `/teams/:teamId/security/assistant/*` inside the existing guard. |
| Auth / roles | Keycloak (`keycloak-js`), `useAuth().user.role` = `student` / `instructor` (shown as Lecturer) / `admin`; `RequireRole`. Backend: `get_onboarded_account`, `require_account_role(...)`, team visibility = members only (others get 404), `{team}` = id or code. | Reuse both as they are. |
| API client | `shared/api/apiClient.js` (axios, Bearer token, `X-Team-Id`, error toasts), paths in `shared/api/endpoints.js`, one service file per module, TanStack hooks. The Vite proxy sends `/api/*` to the **Core API** (`/api/v1/*`). | `securityAssistantService.js` + hooks inside the new folder; one new block in `endpoints.js`. |
| Existing `modules/security` | 4 pages (Dashboard, ScanReport, Remediation, RemediationDetail) + 3 components on **mock data** (`data/mockFindings.js`); `securityService.js` says its signatures are meant to be swapped for real calls. Nav group "Project Security". | **Left untouched.** The new section lives beside it; I may import (not edit) its `CodeBlock`. |
| Core API | FastAPI in `backend/server`: routers in `app/api/v1/`, `protected_router` in `api/v1/router.py` (every route needs a token; `tests/test_route_protection.py` fails otherwise), services, schemas. `app/modules/security/` exists as an **empty README placeholder**. | New router package there (`router.py`, `schemas.py`, `reader.py`). |
| DB models | `users` (keycloak_sub, role, name, email, student_number, institution, github_username), `groups` (code, term, `repo_url`, leader), `group_members` (user, group, term), `projects`, `agent_runs` (JSON `response`, unused by security). **No scan/finding tables.** | Read-only: `users`, `groups`, `group_members`. Nothing else is touched. |
| Registered students | Rows appear only when a person signs in through Keycloak and finishes onboarding (`accounts.provision`). **No seed data exists.** Tests build users with `onboard()` helpers on in-memory SQLite. | See section 6: the demo uses real sign-ins plus a results seed; tests use the existing helpers. |
| AI Backend | Internal only (token), not reachable from the browser. `agent.py` and the registry are empty: **the Security Assistant is not wired into the orchestrator.** Webhook handling calls `pipeline.run_pipeline` (fetch + scan) and does not produce an `assess` report. | The UI reads files; it does not call the AI Backend. |
| Security Assistant outputs | `assess` writes **`report.json`** (everything folded in: stages, scan + coverage, findings with verdict, links, risk breakdown, guidance, probe, decision trails, governance, llm_usage, limitations), `report.md`, **`audit.jsonl`** (hashes only), and local-only `trace_mapping.local.json` / `pii_mapping.local.json`. It does **not** write separate `traced/risk/questions.json` (those are the standalone commands). Diagrams: `docs/*.mmd`. RQ1: `rq1_results/*.csv`. | The API reads `report.json` as the source; extra files only where listed. |

---

## 2. Questions and conflicts

### Conflicts with the existing structure (nothing chosen silently)

1. **Shared files must be touched**, one line or block each, all additive:
   `backend/server/app/api/v1/router.py` (one `include_router`), `backend/server/app/core/config.py` (one setting: results folder),
   `frontend/src/modules/security/routes.jsx` (one `<Route path="assistant/*">`), `frontend/src/shared/layout/navConfig.js` (nav children for student, lecturer, admin),
   `frontend/src/shared/api/endpoints.js` (one `SECURITY_ASSISTANT` block). No existing line is changed or removed.
2. **Overlap with the mock section.** "Project Security > Dashboard / Scan Report / Remediation" show invented findings; the new pages show real runs. Both appear in the nav, so the new entry is named **"Security Assistant (live results)"** to avoid confusion. Your call whether the mock pages should later be retired (not in this plan).
3. **"Request review" is a write, but the API must be read-only.** Default in this plan: the button is client-side only (it copies a prepared review request, with run id and finding key, to the clipboard and shows a toast). Alternative, if you want it recorded: reuse the existing `Notifier` to notify the team's lecturer (writes a row to the existing `notifications` table, no schema change). **Needs your decision.**
4. **Trigger = push / merged PR cannot be real yet.** The webhook path does not produce an `assess` report, so every available run is `manual`. The provenance card shows the trigger from the run manifest; the demo can include one run labelled as a **replayed webhook** (clearly marked), nothing is faked as live.
5. **Starting a scan from the UI is not possible yet** (agent not registered, `agent.py` empty). Default: phase 1 has **no start-scan button** (a disabled control explains why). The gate design for a later step is in section 7. **Needs your decision.**
6. **A registered student cannot be created by the seed script.** Users are created at first Keycloak sign-in, and you said student data is read-only for me. The demo therefore uses real sign-ins of two demo accounts and a lecturer-created team through the existing UI; the seed only writes result folders.
7. **Two services, one folder.** The Core API must be able to read the results folder. In development both run on the host, so a path works; any container deployment needs a mount (not in `docker-compose.yml`, which has no app containers).
8. **`report.json` lacks some fields the UI needs** (section 5). They are added **additively inside `security_assistant/`**, your own folder; the golden snapshot is re-recorded deliberately for them.

### Open questions with my default (confirm or change when you approve)

| # | Question | Default |
|---|---|---|
| Q1 | Start a scan from the UI in this plan? | **No.** Read-only phase; runs come from the CLI and the seed. |
| Q2 | Render the workflow diagram how? | **A small custom SVG** drawn from node/edge data (the graphs are tiny; no `mermaid` package). The `.mmd` text is shown alongside. |
| Q3 | UI tests | **vitest + `renderToStaticMarkup` + pure-function tests**, no new dev dependency. A real browser walk-through is the demo script. |
| Q4 | Additive fields in `report.json` | **Yes**, section 5, in `security_assistant/` only. |
| Q5 | "Request review" | **Clipboard only** (see conflict 3). |
| Q6 | Results folder | `SECURITY_ASSISTANT_RESULTS_DIR`, default `backend/agentic_framework/scan_output/results` (already git-ignored). |
| Q7 | Raw `audit.jsonl` lines | **Lecturer/admin only.** Students see the decision trail and governance summary, not the raw lines. |
| Q8 | Linking a student to commits | By the **verified account e-mail** matched against the run's local mapping file, server-side only. No match = the student sees the team run and an empty "mine" (stated on screen). |

---

## 3. Where results live and how a student is linked to a run

```
<RESULTS_DIR>/
  _shared/                     copied once by the seed: docs/*.mmd, WORKFLOW.md, rq1_comparison.csv
  <team-code>/                 e.g. J26-SE-363 (the Group.code; same code as in the URL)
    <run-id>/                  e.g. 2026-10-21T0930-manual-a1b2c3d
      run.json                 NEW manifest (provenance), see section 5
      report.json              from assess
      report.md                from assess (offered as a download, not parsed)
      audit.jsonl              from assess (hashes only)
      trace_mapping.local.json from assess: LOCAL ONLY, read server-side for "mine", never returned
```

**Student -> run.** `signed-in user -> group_members -> groups.code -> <RESULTS_DIR>/<code>/`. A student can list and open only runs of the team they belong to
(anyone else gets 404, as for teams today). A lecturer sees runs of their own teams and picks a student **of that team** (`group_members`, read-only) to view
"through" that student; an admin sees every team. The repo scanned is the team's (`groups.repo_url` is shown next to the manifest's repo for comparison).

**"Mine".** The server looks up the viewer's e-mail in the run's `trace_mapping.local.json`, gets their `C-xxxxxxxx`, and filters findings whose introducing commit
has that id. The file, names and e-mails are never returned; the response only carries `my_contributor_id` for the student themselves (a lecturer sees the
pseudonym of the student they selected, no more).

---

## 4. Pages and components (organised by vulnerability type)

Folder `frontend/src/modules/security/assistant/` (own components, hooks, service, tests), mounted at `/teams/:teamId/security/assistant/*`.
A bar at the top of every page holds the **run picker**, the **student selector** (lecturer/admin only; students see their own name) and the **MOCK / INCOMPLETE** badges.
Selection lives in the URL (`?run=...&student=...`) so a panel link reproduces a view.

| Route | Page | Shows (requirement) |
|---|---|---|
| `` | **Overview** | 2 provenance (repo, commit, trigger, scan type, time, clone/mount, tool and model versions, prompt version, temperature, seed) - 3 run overview (stage strip for all 8 stages, COMPLETE / INCOMPLETE banner with reasons, tool run table, coverage per category) |
| `findings` -> `findings/:category` | **Findings by type**: tabs **V1 Access control, V2 Injection, V3 Authentication, V4 Secrets, V5 Dependencies/CI-CD**, each with confirmed / dismissed / uncertain counts, filter "mine", sort by risk | 4 |
| `findings/:category/:groupId` | **Finding detail** (drawer or page) | 4 the full card |
| `learning` | **Learning verification** | 5 |
| `agents` | **Agents and governance** | 6 |
| `evidence` | **Panel evidence** | 7 |

**Components** (reuse `Card`, `Badge`, `PageHeader`, `StatCard`, `EmptyState`, `QueryBoundary`, `LoadingState`, `ui/tabs`, `ui/table`, `ui/sheet`, `ui/progress`, `ui/tooltip`; recharts for the bar charts):

- `RunBar`, `RunPicker`, `StudentPicker`, `MockBadge` (the Tutor label, used everywhere it appears)
- Overview: `ProvenanceCard`, `StageStrip`, `IncompleteBanner` (a failed or skipped check is a **red/amber state with a reason**, visibly different from the green "0 findings"), `ToolRunsTable`, `CoverageGrid` (FULL / REDUCED / NONE / NOTHING TO SCAN per category, with the note)
- Findings: `CategoryTabs` (counts by status), `FindingList`, `FindingCard` made of `ScannerVsVerdict` (scanner evidence beside the LLM verdict, status, confidence, rationale, cited evidence ids, downgrade reason), `RiskBreakdown` (six factors: weight, value, contribution, sums to the score), `TraceLinks` (story, task, introducing commit as `C-xxxxxxxx`; **verified** vs **candidate** chip), `FixGuidance` (steps, safe example, OWASP/CWE links, the tailored note), `MaskedCode` (secrets shown as `[REDACTED ...]`; wraps the existing `CodeBlock` by import), `RequestReviewButton`
- Learning: `ProbeThread` (question per hint level, Tutor score against the threshold bar, closed / escalated), `LearningSummary` (concepts = fix patterns covered, closed vs escalated, attempts)
- Agents: `DecisionTrailTable` (per agent: step, options, chosen, why, outcome, rejected choices highlighted), `GovernancePanel` (level, score, second checks, escalation, injection indicators labelled "indicator, not proof"), `AuditTable` (hashes, ids, counts; lecturer/admin), `WorkflowDiagram` (SVG, node colour = status; nested agent graphs expand beneath their node)
- Evidence: `ScannerVsLlmChart`, `Rq1Table`, `LimitationsPanel`, `CompareView` (two runs of the same repo: findings added / removed / changed status, matched on category + rule + file + line)

Never displayed anywhere: raw secrets (the report is already masked, the API re-checks), names, e-mails, `*.local.json`.

---

## 5. Minimal read-only API (Core API, `/api/v1/security-assistant/...`)

All routes `GET`, authenticated, team-checked with the existing helpers (members only; others 404). Responses are **slices of `report.json`** plus the manifest; the router
validates with permissive Pydantic models (`extra="ignore"`) and never imports agent code.

| Endpoint | Role | Returns |
|---|---|---|
| `/teams/{team}/runs` | any member | `[{run_id, started_at, trigger, scan_type, repo, commit_sha, complete, counts}]` newest first |
| `/teams/{team}/students` | lecturer, admin | `[{id, display_name, github_username}]` of that team (read-only from `users`/`group_members`) |
| `/teams/{team}/runs/{run}` | any member | overview: `manifest` (provenance), `stages[]`, `run{complete, incomplete_reasons}`, `scan{tool_runs, coverage, skipped_tools, coverage_gaps, warnings}`, `counts{category: {confirmed, dismissed, uncertain}}`, `llm{model, prompts, temperature, seed, tokens}`, `my_contributor_id` |
| `.../findings?category=V2&status=&mine=true` | any member | finding summaries (below) |
| `.../findings/{group_id}` | any member | the full card |
| `.../learning?student=` | any member | `{threshold, tutor{label, is_mock:true}, items[{group_id, category, concept, attempts[{attempt, hint_level, text, score, result}], decision, escalation_reason}], summary{concepts, closed, escalated, attempts}}` |
| `.../agents` | any member | `{decision_trail{orchestrator, question, governance}, governance{mode, scrutiny, indicators, second_checks, escalated}}` |
| `.../audit?limit=&offset=` | lecturer, admin | audit lines (event, ids, hashes, counts, decisions) |
| `.../workflow` | any member | `{graphs:{workflow, orchestrator, question, governance}: {nodes, edges, mmd}}`, and `ran[node]` derived from stage statuses and trails |
| `/teams/{team}/evidence` | any member | `{rq1_rows[...], limitations[], mocked[] }` + per run `scanner_only vs scanner+llm` counts |
| `/teams/{team}/compare?a=&b=` | any member | `{added[], removed[], changed[], unchanged_count}` for two runs of the same repo |

**Finding card shape** (existing fields marked `=`, additive ones `+`):
`group_id =, category =, title +(rule + message), tool =, rule_id =, cwe +, severity_tool =, file_path =, line =, snippet + (masked), scanner{message +, members +}, llm{status =, confidence =, rationale =, evidence_ids =, original_status +, downgrade_reason +}, risk{rank =, score =, breakdown[{factor, weight, value, contribution, detail}] =}, links[{kind, id, title, status, methods, evidence, confidence}] =, introducing_commit{sha, date, subject, contributor C-id, how_found} =, fix_guidance{id, title, steps =, example +, references +}, recommendation =, probe{question =, hint-level attempts +, scores =, decision =, escalation_reason =}`.

**Additive changes in `security_assistant/` (step 0):**
`run.json` manifest writer (repo URL, commit sha, trigger, scan type, started and finished time, checkout kind `clone-tempdir` / `docker-mount-ro` / `local-folder`, read-only flag, `deleted_after`, folder label only, never a user path);
`report.json` gets `meta.temperature`, per finding `cwe`, `message`, `snippet` (masked), `llm.original_status`, `llm.downgrade_reason`, `fix_guidance.example` and `.references`, `probe.attempt_log`.

**Safety of the reader:** run ids and file names are matched against a whitelist (`report.json`, `run.json`, `audit.jsonl`, `report.md`, `_shared/*`); no path from the request is joined unchecked; every string leaving the API passes the existing secret redaction and a contributor-id check (`^C-[0-9a-f]{8}$`, anything else is dropped).

---

## 6. Demo seeding (a registered student plus the demo repo runs)

1. **Accounts** (existing flows, no code): sign up two accounts in the dev Keycloak realm, a lecturer and a student, finish onboarding for each; the lecturer creates team `J26-SE-363` (already the default code in the app) and adds the student; the team's repository is set to the demo repo URL. This yields the registered student and the team.
2. **`seed_security_demo.py`** (new, in `security_assistant/`, idempotent, never writes to the database): for each of the three demo runs already produced (Python, JS, Java; plus a second Python run for the compare view, produced with the current code) it creates `<RESULTS_DIR>/<team-code>/<run-id>/`, writes `run.json`, and copies the `_shared` files. For the "mine" filter it takes the student's e-mail as an argument and writes it into the local mapping file as the contributor of the demo commits.
3. A **checked-in sample** of one small run (synthetic repo only) under `tests/fixtures/` is what the API and UI tests use, so tests never need the real runs.

No student data is created or changed by the seed; the demo repos are the synthetic ones.

---

## 7. Roles, privacy, safety

| Topic | Rule |
|---|---|
| Student | team runs of their own team only; "mine" filter; own contributor id; trail and governance summary; no raw audit lines |
| Lecturer | runs of the teams they belong to; can select any student **of that team**; raw audit; sees pseudonyms only, never names or e-mails from commits |
| Admin | all teams |
| Contributors | `C-xxxxxxxx` only; the mapping file is read server-side to resolve "mine" and never leaves the server |
| Secrets / PII | masked at source; the API re-redacts strings and drops unknown contributor formats; no free-text field is returned from `*.local.json` |
| Mock Tutor | `MockBadge` next to every score, question result and summary; the Limitations panel lists what is mocked or not built |
| Starting a scan (later, not in this plan) | `POST /security-assistant/teams/{team}/runs` would enqueue through the existing `start_ai_job`, only for the team's own repo, only a public github.com URL or the demo allow-list, `--allow-external-llm` off unless an admin setting enables it, lecturer/admin only. Requires registering the agent (shared `registry.py`) first. |

---

## 8. Build order (small, testable steps)

| # | Step | Tests |
|---|---|---|
| 0 | **Backend prep (agent folder):** `run.json` writer and the additive `report.json` fields; re-record the golden snapshot for them | extend `tests/test_assess.py` and the golden test: new fields present, no secret or name in them, existing assertions unchanged |
| 1 | **Reader** (`reader.py`) + results-dir setting: list teams' runs, load a run, whitelist and path safety, redaction and contributor check | pytest: path traversal refused, unknown file refused, bad contributor id dropped, secret in a field redacted |
| 2 | **Runs + overview routes** with team access | `api` fixture: student of the team 200, student of another team 404, lecturer 200, no token 401 (the existing route-protection test must still pass) |
| 3 | **Findings routes** + "mine" | category filter, status counts equal the report, "mine" resolves via the mapping file and never returns it, no e-mail/name in any response (assert on the full JSON text) |
| 4 | **Learning, agents, audit, workflow, evidence, compare routes** | audit 403 for a student; compare of a run with itself = no changes; workflow `ran` matches stage statuses |
| 5 | **Seed script** + fixture sample | the seeded folder loads through the reader; running twice changes nothing |
| 6 | **Frontend skeleton:** service, hooks, endpoints block, route line, nav entries, `RunBar`, **Overview** page | pure-function tests (mapping, status styles), `renderToStaticMarkup` tests: INCOMPLETE banner shows reasons, a failed tool is not rendered like "no findings" |
| 7 | **Findings by type:** tabs, list, card pieces | static-markup tests: counts per tab, masked snippet shows the marker and never a secret pattern, verified vs candidate chip, risk breakdown sums to the score |
| 8 | **Learning page** | MockBadge present wherever a score shows; escalated vs closed; threshold bar |
| 9 | **Agents page + SVG diagram** | node status classes from stage statuses; rejected choices highlighted; audit table hidden for students |
| 10 | **Evidence page:** RQ1 table, counts, limitations, compare | compare diff function unit tests; limitations list equals the report |
| 11 | **Role and privacy sweep** | student/lecturer/admin matrix on both API and nav; text search of every rendered page fixture for `@`, names, secret patterns |
| 12 | **Viva rehearsal** | run the demo script below end to end; fix only what fails |

Fast suites only for backend steps (existing rule); no live LLM calls and no CodeQL anywhere in this plan.

---

## 9. Viva demo script (about 10 minutes)

1. **Login as the registered student**, open *Project Security > Security Assistant (live results)*. Point at the run bar: team run, own contributor id, MOCK and INCOMPLETE badges. (req 1)
2. **Overview.** Provenance card: repo, commit, trigger `manual`, scan type, when, clone/mount (read-only, deleted afterwards), tool versions, model, prompt version, temperature 0, seed. Stage strip, banner, tool runs, coverage grid; open the Java run to show a *failed/INCOMPLETE* check that is clearly not "no findings". (2, 3)
3. **Findings by type.** Walk V1 to V5 with the counts; open one V2 finding: scanner evidence beside the LLM verdict and cited evidence ids, risk breakdown adding up, verified vs candidate links, the introducing commit as a `C-` id, fix steps with the safe example and OWASP/CWE links, the tailored note. Open a V4 finding: masked value only. Toggle **mine**. (4, 8)
4. **Learning.** One finding closed on attempt 2 and one escalated after the limit, hint levels, scores against the threshold, the MOCK label, the per-student summary. (5)
5. **Agents and governance.** Decision trails of the orchestrator, question agent and governance; the rejected-choice row; the repo's README injection indicators (labelled "indicator, not proof") and the scrutiny level; the audit table (log in as lecturer) showing hashes only; the workflow diagram with the nodes that ran highlighted. (6)
6. **Evidence.** Scanner-only vs scanner+LLM counts, the RQ1 table, the limitations panel, then the **compare** of the two Python runs. (7)
7. **Privacy check on screen:** log in as the lecturer, select the student, show that only pseudonyms appear; log in as a student of another team to show a 404. (1, 8)

---

## 9b. Approved decisions and amendments (supersede anything above)

Answers: Q1 no scan button (a disabled control states the reason); Q2 custom SVG; Q3 vitest as proposed; Q4 yes; Q5 clipboard only; Q6 default folder; Q7 raw audit lecturer/admin only; Q8 as proposed.

1. **Read-only demo mode (flag).** `SECURITY_ASSISTANT_DEMO_MODE` (backend) serves the checked-in sample run when Keycloak or the Core API is unavailable; the frontend has a matching explicit flag. A persistent **"demo data"** label shows whenever it is on. It never turns on silently (no automatic fallback on errors; an error shows as an error).
2. **Step 0 golden re-record:** list exactly which fields changed (a diff of keys/paths) and confirm that no verdict, score, count or status moved. Report it before committing.
3. The learning summary is titled **"comprehension check results (mock)"**; no wording implies a real assessment.
4. Every page has a one-sentence **"how to read this page"** strip.
5. Demo runs are seeded **only from the final code, one model, after the RQ1 rerun**. Until then the checked-in sample is used.
6. Only the **five shared files** are touched, additively; I show the diff of each before committing it.
7. **After step 6, stop**: show the Overview running on the sample run (screenshots or exact steps), then continue.
8. One commit per step, fast suites only, no live LLM, no CodeQL; a brief report after each step.

---

## 10. Out of scope here (listed so nothing is assumed)

Starting scans from the browser; webhook to `assess` wiring; registering the agent with the orchestrator; any database table or column; retiring the mock security pages; real Tutor; persisting "request review"; new frontend dependencies.
