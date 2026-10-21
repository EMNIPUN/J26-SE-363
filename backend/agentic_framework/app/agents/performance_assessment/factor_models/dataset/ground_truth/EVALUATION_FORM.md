# Student Contribution Assessment — Evaluator Form

**Purpose.** Your ratings are the independent reference for checking SELVIA's automatic assessment. Please rate what the evidence shows, not what the student might have done.

**How to rate.** Read one candidate at a time. For each factor, rate every criterion from 1 to 5 using the scale below, then choose the behaviour pattern that fits best and give an overall mark out of 100. Students and teams are anonymised (STU-xxx, Txx). Candidates are in random order.

| Score | Meaning |
|---|---|
| 1 | No evidence, or clearly inadequate |
| 2 | Below what the team needed |
| 3 | What a reasonable team member would do |
| 4 | Clearly more than expected |
| 5 | Exceptional; rare — reserve it for work that stands out across the whole cohort |

Most students are 2–4 on most criteria. A student can be strong on one factor and weak on another.

## Criteria

**Effort**
- *Responsibility engagement* — Took up and worked on the tasks assigned to them.
- *Work investment* — Amount and substance of the work, not just how often they committed.
- *Responsibility fulfilment* — Finished what they took on.
- *Initiative* — Went beyond the assignment: picked up unowned work, unblocked others.
- *Persistence* — Kept working through the sprint and through problems.

**Consistency**
- *Steady engagement* — Worked on many days, not one or two.
- *Early contribution* — Started early rather than near the deadline.
- *Continuity* — No long idle stretches inside the sprint.
- *Predictable rhythm* — Similar amounts of work across the sprint rather than spikes.

**Requirement fulfilment**
- *Task alignment* — The work matches the tasks they were assigned.
- *Acceptance criteria* — The delivered work meets the stated criteria.
- *Completeness* — Tasks are finished, not left partial or done by others.

**Collaboration**
- *Review engagement* — Reviewed or merged teammates' work.
- *Discussion substance* — Wrote useful comments, not just 'ok'.
- *Team interaction* — Worked on shared parts of the code with others; integrated others' work.
- *Follow-through* — Got their own work reviewed and merged; resolved feedback.

**Task complexity**
- *Technical difficulty* — How hard the assigned work was to build.
- *Scope and breadth* — How many parts of the system it covered.
- *Dependency impact* — How much other code depends on what they changed.
- *Architectural impact* — Whether it shaped the structure others build on.
- *Uncertainty* — How much had to be worked out rather than followed.

**Code ownership**
- *Authorship depth* — Wrote substantial original code of their own.
- *Code durability* — Their code is still in the final product.
- *Self-maintenance* — They fixed and extended their own code; others did not have to rewrite it.

**Behaviour pattern** (choose one): consistent deep contributor · last-minute rusher · burst worker · reviewer or coordinator · free rider · no specific pattern.

**Overall mark** (0–100): your overall judgement of this student's contribution in this sprint.

### Evaluator
- Name or identifier: ____________________
- Role: ____________________
- Date: ____________________

---

## Candidate C01

**Student** STU-008 · **Team** T08 (E-commerce microservices, 4 members) · **Sprint** S1 (2026-02-16 to 2026-03-01)

**Tasks on the sprint board**
- *Repository and service scaffold* (1 pts): **Done**. Criteria: 1. Repository created; 2. Frontend scaffold; 3. Service folders. — Dummy files only for the services.
- *User service with authentication* (5 pts): **Done**. Criteria: 1. Register and log in; 2. User CRUD; 3. Health endpoint; 4. Docker Compose and CI. — CI step added then removed the same day; all work on one day.

**Activity in the repository**
- Worked on 3 of the 14 days: `······■ ■····■·` (■ = day with commits, week 1 then week 2).
- Wrote a substantial amount of code (around a thousand lines); made 12 of the team's 115 commits this sprint (10%).
- Example commit messages: “Initial commit”; “Add frontend React/Vite scaffold and backend packages”; “Scaffold backend microservices & dummy files”; “Logo update”; “feat: implement user service with authentication and CRUD operations”; “Add docker-compose configuration for user service and MongoDB”; “Add build and push steps for user service in CI/CD workflow”; “Add health check endpoint and routes for user service”.

**Working with the team**
- Opened 6 pull request(s); 6 merged.
- Merged 0 pull request(s) or branches from teammates; wrote 1 review(s).
- Review text: “No issues.”.
- Some of the files they changed were also changed by teammates.

**Their code later on**
- Of the code they wrote this sprint, most of it is still in the final version of the project.
- In the final version they are the main author of nearly all of the files they worked on.
- The comprehension interview could not be held for past students, so no answers are available.

**Effort**

| Criterion | Code | Rating |
|---|---|---|
| Responsibility engagement | `E_responsibility_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Work investment | `E_work_investment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Responsibility fulfilment | `E_responsibility_fulfillment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Initiative | `E_initiative` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Persistence | `E_persistence` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Consistency**

| Criterion | Code | Rating |
|---|---|---|
| Steady engagement | `C_steady_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Early contribution | `C_early_contribution` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Continuity | `C_continuity` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Predictable rhythm | `C_predictable_rhythm` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Requirement fulfilment**

| Criterion | Code | Rating |
|---|---|---|
| Task alignment | `RF_task_alignment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Acceptance criteria | `RF_acceptance_criteria` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Completeness | `RF_completeness` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Collaboration**

| Criterion | Code | Rating |
|---|---|---|
| Review engagement | `Co_review_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Discussion substance | `Co_discussion_substance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Team interaction | `Co_team_interaction` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Follow-through | `Co_follow_through` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Task complexity**

| Criterion | Code | Rating |
|---|---|---|
| Technical difficulty | `TC_technical_difficulty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Scope and breadth | `TC_scope_breadth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Dependency impact | `TC_dependency_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Architectural impact | `TC_architectural_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Uncertainty | `TC_uncertainty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Code ownership**

| Criterion | Code | Rating |
|---|---|---|
| Authorship depth | `KO_authorship_depth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Code durability | `KO_code_durability` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Self-maintenance | `KO_self_maintenance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Behaviour pattern:** [ ] consistent deep contributor &nbsp; [ ] last-minute rusher &nbsp; [ ] burst worker &nbsp; [ ] reviewer or coordinator &nbsp; [ ] free rider &nbsp; [ ] no specific pattern

**Overall mark (0–100):** ________ &nbsp;&nbsp; **Comment:** ____________________________________

<div style='page-break-after: always;'></div>

## Candidate C02

**Student** STU-001 · **Team** T09 (Tourism platform, 4 members) · **Sprint** S1 (2025-03-10 to 2025-03-23)

**Tasks on the sprint board**
- *Project and environment setup* (2 pts): **Done**. Criteria: 1. Project runs; 2. Environment configuration; 3. Base page structure. — Many commits named 'update' or 'test 2'.
- *Dashboard layout and sidebar* (3 pts): **Done**. Criteria: 1. Sidebar; 2. Dashboard pages.
- *AI chat bot and RFID dashboard* (5 pts): **Partially Done**. Criteria: 1. Chat bot page answers questions; 2. RFID dashboard shows scans. — RFID dashboard shows sample data only.
- *Backend endpoints for the dashboard* (3 pts): **Done**. Criteria: 1. Endpoints for dashboard data. — Commit messages are all 'update'.

**Activity in the repository**
- Worked on 10 of the 14 days: `·■·■■■■ ■■·■■■·` (■ = day with commits, week 1 then week 2).
- Wrote a large amount of code (several thousand lines); made 19 of the team's 51 commits this sprint (37%).
- Example commit messages: “Initial commit”; “environment setup”; “clear project folder”; “Update index.css”; “initial commit”; “Update App.jsx”; “test 2”; “env update”.

**Working with the team**
- Opened 5 pull request(s); 4 merged.
- Merged 0 pull request(s) or branches from teammates; wrote 0 review(s).
- No written review comments.
- Some of the files they changed were also changed by teammates.

**Their code later on**
- Of the code they wrote this sprint, only a small part of it is still in the final version of the project.
- In the final version they are the main author of nearly all of the files they worked on.
- The comprehension interview could not be held for past students, so no answers are available.

**Effort**

| Criterion | Code | Rating |
|---|---|---|
| Responsibility engagement | `E_responsibility_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Work investment | `E_work_investment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Responsibility fulfilment | `E_responsibility_fulfillment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Initiative | `E_initiative` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Persistence | `E_persistence` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Consistency**

| Criterion | Code | Rating |
|---|---|---|
| Steady engagement | `C_steady_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Early contribution | `C_early_contribution` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Continuity | `C_continuity` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Predictable rhythm | `C_predictable_rhythm` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Requirement fulfilment**

| Criterion | Code | Rating |
|---|---|---|
| Task alignment | `RF_task_alignment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Acceptance criteria | `RF_acceptance_criteria` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Completeness | `RF_completeness` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Collaboration**

| Criterion | Code | Rating |
|---|---|---|
| Review engagement | `Co_review_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Discussion substance | `Co_discussion_substance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Team interaction | `Co_team_interaction` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Follow-through | `Co_follow_through` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Task complexity**

| Criterion | Code | Rating |
|---|---|---|
| Technical difficulty | `TC_technical_difficulty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Scope and breadth | `TC_scope_breadth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Dependency impact | `TC_dependency_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Architectural impact | `TC_architectural_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Uncertainty | `TC_uncertainty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Code ownership**

| Criterion | Code | Rating |
|---|---|---|
| Authorship depth | `KO_authorship_depth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Code durability | `KO_code_durability` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Self-maintenance | `KO_self_maintenance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Behaviour pattern:** [ ] consistent deep contributor &nbsp; [ ] last-minute rusher &nbsp; [ ] burst worker &nbsp; [ ] reviewer or coordinator &nbsp; [ ] free rider &nbsp; [ ] no specific pattern

**Overall mark (0–100):** ________ &nbsp;&nbsp; **Comment:** ____________________________________

<div style='page-break-after: always;'></div>

## Candidate C03

**Student** STU-016 · **Team** T14 (Waste management system, 4 members) · **Sprint** S1 (2025-10-13 to 2025-10-26)

**Tasks on the sprint board**
- *Container CRUD and sensor simulation* (8 pts): **Done**. Criteria: 1. Container CRUD; 2. Sensor simulation; 3. Location with province; 4. Deactivate and reactivate.
- *Container management dashboard* (5 pts): **Done**. Criteria: 1. Container dashboard; 2. Sidebar link; 3. Deactivation from the dashboard.
- *Container unit tests* (3 pts): **Done**. Criteria: 1. Backend tests; 2. Frontend tests. — 3,700 lines in one test commit.

**Activity in the repository**
- Worked on 2 of the 14 days: `···■■·· ·······` (■ = day with commits, week 1 then week 2).
- Wrote a large amount of code (several thousand lines); made 13 of the team's 112 commits this sprint (12%).
- Example commit messages: “Add waste container CRUD and sensor simulation backend”; “Add location update and status filter to containers API”; “Add automated sensor simulation and error fixing”; “Add container deactivation and improve status logic”; “Add province to container location and enhance location logic”; “Add container management dashboard and related components”; “Add Container Management to admin sidebar”; “Add container deactivation feature to dashboard”.

**Working with the team**
- Opened 4 pull request(s); 4 merged.
- Merged 0 pull request(s) or branches from teammates; wrote 0 review(s).
- No written review comments.
- Some of the files they changed were also changed by teammates.

**Their code later on**
- Of the code they wrote this sprint, only a small part of it is still in the final version of the project.
- In the final version they are the main author of most of the files they worked on.
- The comprehension interview could not be held for past students, so no answers are available.

**Effort**

| Criterion | Code | Rating |
|---|---|---|
| Responsibility engagement | `E_responsibility_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Work investment | `E_work_investment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Responsibility fulfilment | `E_responsibility_fulfillment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Initiative | `E_initiative` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Persistence | `E_persistence` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Consistency**

| Criterion | Code | Rating |
|---|---|---|
| Steady engagement | `C_steady_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Early contribution | `C_early_contribution` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Continuity | `C_continuity` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Predictable rhythm | `C_predictable_rhythm` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Requirement fulfilment**

| Criterion | Code | Rating |
|---|---|---|
| Task alignment | `RF_task_alignment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Acceptance criteria | `RF_acceptance_criteria` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Completeness | `RF_completeness` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Collaboration**

| Criterion | Code | Rating |
|---|---|---|
| Review engagement | `Co_review_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Discussion substance | `Co_discussion_substance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Team interaction | `Co_team_interaction` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Follow-through | `Co_follow_through` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Task complexity**

| Criterion | Code | Rating |
|---|---|---|
| Technical difficulty | `TC_technical_difficulty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Scope and breadth | `TC_scope_breadth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Dependency impact | `TC_dependency_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Architectural impact | `TC_architectural_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Uncertainty | `TC_uncertainty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Code ownership**

| Criterion | Code | Rating |
|---|---|---|
| Authorship depth | `KO_authorship_depth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Code durability | `KO_code_durability` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Self-maintenance | `KO_self_maintenance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Behaviour pattern:** [ ] consistent deep contributor &nbsp; [ ] last-minute rusher &nbsp; [ ] burst worker &nbsp; [ ] reviewer or coordinator &nbsp; [ ] free rider &nbsp; [ ] no specific pattern

**Overall mark (0–100):** ________ &nbsp;&nbsp; **Comment:** ____________________________________

<div style='page-break-after: always;'></div>

## Candidate C04

**Student** STU-027 · **Team** T04 (Healthcare microservices, 4 members) · **Sprint** S2 (2026-03-30 to 2026-04-12)

**Tasks on the sprint board**
- *Container setup for the AI service* (1 pts): **Done**. Criteria: 1. Service in compose; 2. Reachable through the gateway.
- *AI symptom checker screen* (3 pts): **To Do**. Criteria: 1. Symptom input form; 2. Results shown. — Not started; still missing in sprint 3.

**Activity in the repository**
- Worked on 1 of the 14 days: `······■ ·······` (■ = day with commits, week 1 then week 2).
- Wrote a small amount of code (under 150 lines); made 1 of the team's 12 commits this sprint (8%).
- Example commit messages: “feat:configure the docker compose.yml for the ai symptom  service”.

**Working with the team**
- Opened 0 pull request(s); 0 merged.
- Merged 0 pull request(s) or branches from teammates; wrote 0 review(s).
- No written review comments.
- Some of the files they changed were also changed by teammates.

**Their code later on**
- No source code to follow up.
- The comprehension interview could not be held for past students, so no answers are available.

**Effort**

| Criterion | Code | Rating |
|---|---|---|
| Responsibility engagement | `E_responsibility_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Work investment | `E_work_investment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Responsibility fulfilment | `E_responsibility_fulfillment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Initiative | `E_initiative` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Persistence | `E_persistence` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Consistency**

| Criterion | Code | Rating |
|---|---|---|
| Steady engagement | `C_steady_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Early contribution | `C_early_contribution` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Continuity | `C_continuity` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Predictable rhythm | `C_predictable_rhythm` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Requirement fulfilment**

| Criterion | Code | Rating |
|---|---|---|
| Task alignment | `RF_task_alignment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Acceptance criteria | `RF_acceptance_criteria` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Completeness | `RF_completeness` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Collaboration**

| Criterion | Code | Rating |
|---|---|---|
| Review engagement | `Co_review_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Discussion substance | `Co_discussion_substance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Team interaction | `Co_team_interaction` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Follow-through | `Co_follow_through` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Task complexity**

| Criterion | Code | Rating |
|---|---|---|
| Technical difficulty | `TC_technical_difficulty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Scope and breadth | `TC_scope_breadth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Dependency impact | `TC_dependency_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Architectural impact | `TC_architectural_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Uncertainty | `TC_uncertainty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Code ownership**

| Criterion | Code | Rating |
|---|---|---|
| Authorship depth | `KO_authorship_depth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Code durability | `KO_code_durability` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Self-maintenance | `KO_self_maintenance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Behaviour pattern:** [ ] consistent deep contributor &nbsp; [ ] last-minute rusher &nbsp; [ ] burst worker &nbsp; [ ] reviewer or coordinator &nbsp; [ ] free rider &nbsp; [ ] no specific pattern

**Overall mark (0–100):** ________ &nbsp;&nbsp; **Comment:** ____________________________________

<div style='page-break-after: always;'></div>

## Candidate C05

**Student** STU-019 · **Team** T03 (Agricultural marketplace, 5 members) · **Sprint** S3 (2025-04-28 to 2025-05-11)

**Tasks on the sprint board**
- *Finance management updates* (5 pts) (carried over from the previous sprint): **Done**. Criteria: 1. Finance backend endpoints; 2. Payment history page; 3. All payments view. — Vague commit messages; lockfile-only commits.

**Activity in the repository**
- Worked on 3 of the 14 days: `······■ ■·■····` (■ = day with commits, week 1 then week 2).
- Wrote a substantial amount of code (around a thousand lines); made 8 of the team's 58 commits this sprint (14%).
- Example commit messages: “Update package-lock.json”; “updated”; “latest updates in finance management”; “Update package-lock.json”; “Update payamenthistory.page.jsx”; “updated”; “all payments update”.

**Working with the team**
- The team did not use pull requests this sprint; work was pushed or merged directly.
- Some of the files they changed were also changed by teammates.

**Their code later on**
- Of the code they wrote this sprint, most of it is still in the final version of the project.
- In the final version they are the main author of about half of the files they worked on.
- The comprehension interview could not be held for past students, so no answers are available.

**Effort**

| Criterion | Code | Rating |
|---|---|---|
| Responsibility engagement | `E_responsibility_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Work investment | `E_work_investment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Responsibility fulfilment | `E_responsibility_fulfillment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Initiative | `E_initiative` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Persistence | `E_persistence` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Consistency**

| Criterion | Code | Rating |
|---|---|---|
| Steady engagement | `C_steady_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Early contribution | `C_early_contribution` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Continuity | `C_continuity` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Predictable rhythm | `C_predictable_rhythm` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Requirement fulfilment**

| Criterion | Code | Rating |
|---|---|---|
| Task alignment | `RF_task_alignment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Acceptance criteria | `RF_acceptance_criteria` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Completeness | `RF_completeness` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Collaboration**

| Criterion | Code | Rating |
|---|---|---|
| Review engagement | `Co_review_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Discussion substance | `Co_discussion_substance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Team interaction | `Co_team_interaction` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Follow-through | `Co_follow_through` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Task complexity**

| Criterion | Code | Rating |
|---|---|---|
| Technical difficulty | `TC_technical_difficulty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Scope and breadth | `TC_scope_breadth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Dependency impact | `TC_dependency_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Architectural impact | `TC_architectural_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Uncertainty | `TC_uncertainty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Code ownership**

| Criterion | Code | Rating |
|---|---|---|
| Authorship depth | `KO_authorship_depth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Code durability | `KO_code_durability` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Self-maintenance | `KO_self_maintenance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Behaviour pattern:** [ ] consistent deep contributor &nbsp; [ ] last-minute rusher &nbsp; [ ] burst worker &nbsp; [ ] reviewer or coordinator &nbsp; [ ] free rider &nbsp; [ ] no specific pattern

**Overall mark (0–100):** ________ &nbsp;&nbsp; **Comment:** ____________________________________

<div style='page-break-after: always;'></div>

## Candidate C06

**Student** STU-010 · **Team** T04 (Healthcare microservices, 4 members) · **Sprint** S3 (2026-04-13 to 2026-04-26)

**Tasks on the sprint board**
- *Notification service* (5 pts): **Done** — completed by a teammate (STU-005). Criteria: 1. Notification service; 2. Sent on booking; 3. Running in Docker. — Branch named for STU-010 but the files were uploaded and fixed by STU-005.
- *Patient service updates* (2 pts): **Partially Done**. Criteria: 1. Patient service matches the final API. — Mostly committed database files; 1,078 lines removed.

**Activity in the repository**
- Worked on 1 of the 14 days: `■······ ·······` (■ = day with commits, week 1 then week 2).
- Wrote a small amount of code (under 150 lines); made 1 of the team's 20 commits this sprint (5%).
- Example commit messages: “Updated patient service changes”.

**Working with the team**
- Opened 0 pull request(s); 0 merged.
- Merged 0 pull request(s) or branches from teammates; wrote 0 review(s).
- No written review comments.
- Most of the files they changed were also changed by teammates in this sprint.

**Their code later on**
- No source code to follow up.
- The comprehension interview could not be held for past students, so no answers are available.

**Effort**

| Criterion | Code | Rating |
|---|---|---|
| Responsibility engagement | `E_responsibility_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Work investment | `E_work_investment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Responsibility fulfilment | `E_responsibility_fulfillment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Initiative | `E_initiative` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Persistence | `E_persistence` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Consistency**

| Criterion | Code | Rating |
|---|---|---|
| Steady engagement | `C_steady_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Early contribution | `C_early_contribution` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Continuity | `C_continuity` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Predictable rhythm | `C_predictable_rhythm` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Requirement fulfilment**

| Criterion | Code | Rating |
|---|---|---|
| Task alignment | `RF_task_alignment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Acceptance criteria | `RF_acceptance_criteria` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Completeness | `RF_completeness` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Collaboration**

| Criterion | Code | Rating |
|---|---|---|
| Review engagement | `Co_review_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Discussion substance | `Co_discussion_substance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Team interaction | `Co_team_interaction` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Follow-through | `Co_follow_through` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Task complexity**

| Criterion | Code | Rating |
|---|---|---|
| Technical difficulty | `TC_technical_difficulty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Scope and breadth | `TC_scope_breadth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Dependency impact | `TC_dependency_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Architectural impact | `TC_architectural_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Uncertainty | `TC_uncertainty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Code ownership**

| Criterion | Code | Rating |
|---|---|---|
| Authorship depth | `KO_authorship_depth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Code durability | `KO_code_durability` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Self-maintenance | `KO_self_maintenance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Behaviour pattern:** [ ] consistent deep contributor &nbsp; [ ] last-minute rusher &nbsp; [ ] burst worker &nbsp; [ ] reviewer or coordinator &nbsp; [ ] free rider &nbsp; [ ] no specific pattern

**Overall mark (0–100):** ________ &nbsp;&nbsp; **Comment:** ____________________________________

<div style='page-break-after: always;'></div>

## Candidate C07

**Student** STU-004 · **Team** T06 (Campus services hub, 4 members) · **Sprint** S1 (2026-03-23 to 2026-04-05)

**Tasks on the sprint board**
- *Notifications and auth profile backend* (5 pts): **Done** — completed by a teammate (STU-015). Criteria: 1. Notifications stored and listed; 2. Profile endpoint; 3. Flyway migrations for PostgreSQL. — Workstream 4 backend was built by STU-015; the assignee made the frontend in sprint 2.

**Activity in the repository**
- No commits in this sprint.

**Working with the team**
- The team did not use pull requests this sprint; work was pushed or merged directly.

**Their code later on**
- No source code to follow up.
- The comprehension interview could not be held for past students, so no answers are available.

**Effort**

| Criterion | Code | Rating |
|---|---|---|
| Responsibility engagement | `E_responsibility_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Work investment | `E_work_investment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Responsibility fulfilment | `E_responsibility_fulfillment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Initiative | `E_initiative` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Persistence | `E_persistence` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Consistency**

| Criterion | Code | Rating |
|---|---|---|
| Steady engagement | `C_steady_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Early contribution | `C_early_contribution` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Continuity | `C_continuity` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Predictable rhythm | `C_predictable_rhythm` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Requirement fulfilment**

| Criterion | Code | Rating |
|---|---|---|
| Task alignment | `RF_task_alignment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Acceptance criteria | `RF_acceptance_criteria` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Completeness | `RF_completeness` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Collaboration**

| Criterion | Code | Rating |
|---|---|---|
| Review engagement | `Co_review_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Discussion substance | `Co_discussion_substance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Team interaction | `Co_team_interaction` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Follow-through | `Co_follow_through` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Task complexity**

| Criterion | Code | Rating |
|---|---|---|
| Technical difficulty | `TC_technical_difficulty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Scope and breadth | `TC_scope_breadth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Dependency impact | `TC_dependency_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Architectural impact | `TC_architectural_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Uncertainty | `TC_uncertainty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Code ownership**

| Criterion | Code | Rating |
|---|---|---|
| Authorship depth | `KO_authorship_depth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Code durability | `KO_code_durability` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Self-maintenance | `KO_self_maintenance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Behaviour pattern:** [ ] consistent deep contributor &nbsp; [ ] last-minute rusher &nbsp; [ ] burst worker &nbsp; [ ] reviewer or coordinator &nbsp; [ ] free rider &nbsp; [ ] no specific pattern

**Overall mark (0–100):** ________ &nbsp;&nbsp; **Comment:** ____________________________________

<div style='page-break-after: always;'></div>

## Candidate C08

**Student** STU-011 · **Team** T03 (Agricultural marketplace, 5 members) · **Sprint** S2 (2025-03-24 to 2025-04-06)

**Tasks on the sprint board**
- *Transport manager CRUD* (5 pts) (carried over from the previous sprint): **Partially Done**. Criteria: 1. Vehicle CRUD; 2. Driver CRUD; 3. Transport requests listed. — One 1,500-line commit on one day; most of the transport flow was later built by teammates.

**Activity in the repository**
- Worked on 1 of the 14 days: `··■···· ·······` (■ = day with commits, week 1 then week 2).
- Wrote a substantial amount of code (around a thousand lines); made 1 of the team's 54 commits this sprint (2%).
- Example commit messages: “Implement crud operation”.

**Working with the team**
- The team did not use pull requests this sprint; work was pushed or merged directly.
- Some of the files they changed were also changed by teammates.

**Their code later on**
- Of the code they wrote this sprint, about half of it is still in the final version of the project.
- In the final version they are the main author of most of the files they worked on.
- The comprehension interview could not be held for past students, so no answers are available.

**Effort**

| Criterion | Code | Rating |
|---|---|---|
| Responsibility engagement | `E_responsibility_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Work investment | `E_work_investment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Responsibility fulfilment | `E_responsibility_fulfillment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Initiative | `E_initiative` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Persistence | `E_persistence` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Consistency**

| Criterion | Code | Rating |
|---|---|---|
| Steady engagement | `C_steady_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Early contribution | `C_early_contribution` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Continuity | `C_continuity` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Predictable rhythm | `C_predictable_rhythm` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Requirement fulfilment**

| Criterion | Code | Rating |
|---|---|---|
| Task alignment | `RF_task_alignment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Acceptance criteria | `RF_acceptance_criteria` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Completeness | `RF_completeness` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Collaboration**

| Criterion | Code | Rating |
|---|---|---|
| Review engagement | `Co_review_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Discussion substance | `Co_discussion_substance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Team interaction | `Co_team_interaction` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Follow-through | `Co_follow_through` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Task complexity**

| Criterion | Code | Rating |
|---|---|---|
| Technical difficulty | `TC_technical_difficulty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Scope and breadth | `TC_scope_breadth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Dependency impact | `TC_dependency_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Architectural impact | `TC_architectural_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Uncertainty | `TC_uncertainty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Code ownership**

| Criterion | Code | Rating |
|---|---|---|
| Authorship depth | `KO_authorship_depth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Code durability | `KO_code_durability` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Self-maintenance | `KO_self_maintenance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Behaviour pattern:** [ ] consistent deep contributor &nbsp; [ ] last-minute rusher &nbsp; [ ] burst worker &nbsp; [ ] reviewer or coordinator &nbsp; [ ] free rider &nbsp; [ ] no specific pattern

**Overall mark (0–100):** ________ &nbsp;&nbsp; **Comment:** ____________________________________

<div style='page-break-after: always;'></div>

## Candidate C09

**Student** STU-017 · **Team** T11 (Medical services microservices, 4 members) · **Sprint** S2 (2026-04-06 to 2026-04-19)

**Tasks on the sprint board**
- *Telemedicine service and pages* (8 pts): **Done**. Criteria: 1. Telemedicine APIs; 2. Doctor panel; 3. Patient joins a meeting; 4. Uses appointment data.
- *Notifications for telemedicine* (5 pts) (carried over from the previous sprint): **Done**. Criteria: 1. Notification on consultation events; 2. Secrets for providers.

**Activity in the repository**
- Worked on 5 of the 14 days: `····■·· ■■·■■··` (■ = day with commits, week 1 then week 2).
- Wrote a large amount of code (several thousand lines); made 18 of the team's 116 commits this sprint (16%).
- Example commit messages: “feature/ implement relevent apis for telemedicine management”; “feat/add teleconsultation frontend on doctor panel”; “feat/implemented the telemedicine ui in both patient and doctor view”; “feat/implement patient telemedicine part”; “fix/remove the unused variables”; “refactor/change the ngnx like on the main branch”; “feat/use appoinment apis”; “fix/internal server error”.

**Working with the team**
- Opened 6 pull request(s); 3 merged.
- Merged 0 pull request(s) or branches from teammates; wrote 0 review(s).
- No written review comments.
- Some of the files they changed were also changed by teammates.

**Their code later on**
- Of the code they wrote this sprint, most of it is still in the final version of the project.
- In the final version they are the main author of nearly all of the files they worked on.
- The comprehension interview could not be held for past students, so no answers are available.

**Effort**

| Criterion | Code | Rating |
|---|---|---|
| Responsibility engagement | `E_responsibility_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Work investment | `E_work_investment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Responsibility fulfilment | `E_responsibility_fulfillment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Initiative | `E_initiative` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Persistence | `E_persistence` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Consistency**

| Criterion | Code | Rating |
|---|---|---|
| Steady engagement | `C_steady_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Early contribution | `C_early_contribution` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Continuity | `C_continuity` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Predictable rhythm | `C_predictable_rhythm` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Requirement fulfilment**

| Criterion | Code | Rating |
|---|---|---|
| Task alignment | `RF_task_alignment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Acceptance criteria | `RF_acceptance_criteria` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Completeness | `RF_completeness` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Collaboration**

| Criterion | Code | Rating |
|---|---|---|
| Review engagement | `Co_review_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Discussion substance | `Co_discussion_substance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Team interaction | `Co_team_interaction` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Follow-through | `Co_follow_through` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Task complexity**

| Criterion | Code | Rating |
|---|---|---|
| Technical difficulty | `TC_technical_difficulty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Scope and breadth | `TC_scope_breadth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Dependency impact | `TC_dependency_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Architectural impact | `TC_architectural_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Uncertainty | `TC_uncertainty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Code ownership**

| Criterion | Code | Rating |
|---|---|---|
| Authorship depth | `KO_authorship_depth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Code durability | `KO_code_durability` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Self-maintenance | `KO_self_maintenance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Behaviour pattern:** [ ] consistent deep contributor &nbsp; [ ] last-minute rusher &nbsp; [ ] burst worker &nbsp; [ ] reviewer or coordinator &nbsp; [ ] free rider &nbsp; [ ] no specific pattern

**Overall mark (0–100):** ________ &nbsp;&nbsp; **Comment:** ____________________________________

<div style='page-break-after: always;'></div>

## Candidate C10

**Student** STU-003 · **Team** T13 (Tourism certification platform, 4 members) · **Sprint** S2 (2026-02-16 to 2026-03-01)

**Tasks on the sprint board**
- *Audit management API* (8 pts) (carried over from the previous sprint): **Done**. Criteria: 1. Create audit; 2. Retrieve audits; 3. Review sections; 4. Schemas. — All in one day; a 2,100-line commit titled 'Refactor code structure'.
- *Vector database for audit documents* (3 pts): **Done**. Criteria: 1. Embeddings stored; 2. Similar documents found.

**Activity in the repository**
- Worked on 2 of the 14 days: `······· ···■■··` (■ = day with commits, week 1 then week 2).
- Wrote a large amount of code (several thousand lines); made 6 of the team's 48 commits this sprint (12%).
- Example commit messages: “feat(audit): implement audit management endpoints including creation, retrieval, review, a”; “feat(audit): add audit and section review schemas for hotel certification process”; “Refactor code structure for improved readability and maintainability”; “chore(documentProcessingService): remove unnecessary blank lines for cleaner code”; “chore(geminiService): remove unnecessary blank line in constructor for cleaner code”; “Refactor vector database service to use MongoDB for embeddings”.

**Working with the team**
- Opened 2 pull request(s); 1 merged.
- Merged 0 pull request(s) or branches from teammates; wrote 0 review(s).
- No written review comments.
- Some of the files they changed were also changed by teammates.

**Their code later on**
- Of the code they wrote this sprint, nearly all of it is still in the final version of the project.
- In the final version they are the main author of nearly all of the files they worked on.
- The comprehension interview could not be held for past students, so no answers are available.

**Effort**

| Criterion | Code | Rating |
|---|---|---|
| Responsibility engagement | `E_responsibility_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Work investment | `E_work_investment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Responsibility fulfilment | `E_responsibility_fulfillment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Initiative | `E_initiative` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Persistence | `E_persistence` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Consistency**

| Criterion | Code | Rating |
|---|---|---|
| Steady engagement | `C_steady_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Early contribution | `C_early_contribution` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Continuity | `C_continuity` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Predictable rhythm | `C_predictable_rhythm` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Requirement fulfilment**

| Criterion | Code | Rating |
|---|---|---|
| Task alignment | `RF_task_alignment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Acceptance criteria | `RF_acceptance_criteria` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Completeness | `RF_completeness` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Collaboration**

| Criterion | Code | Rating |
|---|---|---|
| Review engagement | `Co_review_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Discussion substance | `Co_discussion_substance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Team interaction | `Co_team_interaction` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Follow-through | `Co_follow_through` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Task complexity**

| Criterion | Code | Rating |
|---|---|---|
| Technical difficulty | `TC_technical_difficulty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Scope and breadth | `TC_scope_breadth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Dependency impact | `TC_dependency_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Architectural impact | `TC_architectural_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Uncertainty | `TC_uncertainty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Code ownership**

| Criterion | Code | Rating |
|---|---|---|
| Authorship depth | `KO_authorship_depth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Code durability | `KO_code_durability` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Self-maintenance | `KO_self_maintenance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Behaviour pattern:** [ ] consistent deep contributor &nbsp; [ ] last-minute rusher &nbsp; [ ] burst worker &nbsp; [ ] reviewer or coordinator &nbsp; [ ] free rider &nbsp; [ ] no specific pattern

**Overall mark (0–100):** ________ &nbsp;&nbsp; **Comment:** ____________________________________

<div style='page-break-after: always;'></div>

## Candidate C11

**Student** STU-007 · **Team** T09 (Tourism platform, 4 members) · **Sprint** S1 (2025-03-10 to 2025-03-23)

**Tasks on the sprint board**
- *Attractions page with search* (3 pts): **Done**. Criteria: 1. Attractions list; 2. Search; 3. Suggested attractions scroll.
- *Attraction form validation and layout* (2 pts): **Done**. Criteria: 1. Client-side validation; 2. Desktop layout.
- *Attraction CRUD connected to the backend* (5 pts): **Done**. Criteria: 1. CRUD endpoints; 2. Image upload with multer; 3. Frontend uses the API; 4. Search on the backend.

**Activity in the repository**
- Worked on 7 of the 14 days: `····■■■ ■■·■■··` (■ = day with commits, week 1 then week 2).
- Wrote a substantial amount of code (around a thousand lines); made 14 of the team's 51 commits this sprint (27%).
- Example commit messages: “attraction code”; “added img links and search bar”; “fixed horizontall scrolling for suggested”; “changed button color”; “add attraction page”; “updated form to have js inform validations”; “some optimizations for desktop layout”; “Update delete backend search”.

**Working with the team**
- Opened 3 pull request(s); 3 merged.
- Merged 0 pull request(s) or branches from teammates; wrote 0 review(s).
- No written review comments.
- Most of the files they changed were also changed by teammates in this sprint.

**Their code later on**
- Of the code they wrote this sprint, only a small part of it is still in the final version of the project.
- In the final version they are the main author of only a few of the files they worked on.
- The comprehension interview could not be held for past students, so no answers are available.

**Effort**

| Criterion | Code | Rating |
|---|---|---|
| Responsibility engagement | `E_responsibility_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Work investment | `E_work_investment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Responsibility fulfilment | `E_responsibility_fulfillment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Initiative | `E_initiative` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Persistence | `E_persistence` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Consistency**

| Criterion | Code | Rating |
|---|---|---|
| Steady engagement | `C_steady_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Early contribution | `C_early_contribution` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Continuity | `C_continuity` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Predictable rhythm | `C_predictable_rhythm` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Requirement fulfilment**

| Criterion | Code | Rating |
|---|---|---|
| Task alignment | `RF_task_alignment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Acceptance criteria | `RF_acceptance_criteria` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Completeness | `RF_completeness` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Collaboration**

| Criterion | Code | Rating |
|---|---|---|
| Review engagement | `Co_review_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Discussion substance | `Co_discussion_substance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Team interaction | `Co_team_interaction` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Follow-through | `Co_follow_through` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Task complexity**

| Criterion | Code | Rating |
|---|---|---|
| Technical difficulty | `TC_technical_difficulty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Scope and breadth | `TC_scope_breadth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Dependency impact | `TC_dependency_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Architectural impact | `TC_architectural_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Uncertainty | `TC_uncertainty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Code ownership**

| Criterion | Code | Rating |
|---|---|---|
| Authorship depth | `KO_authorship_depth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Code durability | `KO_code_durability` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Self-maintenance | `KO_self_maintenance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Behaviour pattern:** [ ] consistent deep contributor &nbsp; [ ] last-minute rusher &nbsp; [ ] burst worker &nbsp; [ ] reviewer or coordinator &nbsp; [ ] free rider &nbsp; [ ] no specific pattern

**Overall mark (0–100):** ________ &nbsp;&nbsp; **Comment:** ____________________________________

<div style='page-break-after: always;'></div>

## Candidate C12

**Student** STU-022 · **Team** T05 (Car rental system, 3 members) · **Sprint** S3 (2025-10-06 to 2025-10-19)

**Tasks on the sprint board**
- *Payment for bookings* (5 pts): **To Do**. Criteria: 1. Payment form; 2. Payment recorded against the booking. — No commits this sprint.

**Activity in the repository**
- No commits in this sprint.

**Working with the team**
- Opened 0 pull request(s); 0 merged.
- Merged 0 pull request(s) or branches from teammates; wrote 0 review(s).
- No written review comments.

**Their code later on**
- No source code to follow up.
- The comprehension interview could not be held for past students, so no answers are available.

**Effort**

| Criterion | Code | Rating |
|---|---|---|
| Responsibility engagement | `E_responsibility_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Work investment | `E_work_investment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Responsibility fulfilment | `E_responsibility_fulfillment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Initiative | `E_initiative` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Persistence | `E_persistence` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Consistency**

| Criterion | Code | Rating |
|---|---|---|
| Steady engagement | `C_steady_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Early contribution | `C_early_contribution` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Continuity | `C_continuity` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Predictable rhythm | `C_predictable_rhythm` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Requirement fulfilment**

| Criterion | Code | Rating |
|---|---|---|
| Task alignment | `RF_task_alignment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Acceptance criteria | `RF_acceptance_criteria` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Completeness | `RF_completeness` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Collaboration**

| Criterion | Code | Rating |
|---|---|---|
| Review engagement | `Co_review_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Discussion substance | `Co_discussion_substance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Team interaction | `Co_team_interaction` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Follow-through | `Co_follow_through` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Task complexity**

| Criterion | Code | Rating |
|---|---|---|
| Technical difficulty | `TC_technical_difficulty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Scope and breadth | `TC_scope_breadth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Dependency impact | `TC_dependency_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Architectural impact | `TC_architectural_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Uncertainty | `TC_uncertainty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Code ownership**

| Criterion | Code | Rating |
|---|---|---|
| Authorship depth | `KO_authorship_depth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Code durability | `KO_code_durability` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Self-maintenance | `KO_self_maintenance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Behaviour pattern:** [ ] consistent deep contributor &nbsp; [ ] last-minute rusher &nbsp; [ ] burst worker &nbsp; [ ] reviewer or coordinator &nbsp; [ ] free rider &nbsp; [ ] no specific pattern

**Overall mark (0–100):** ________ &nbsp;&nbsp; **Comment:** ____________________________________

<div style='page-break-after: always;'></div>

## Candidate C13

**Student** STU-021 · **Team** T01 (Learning platform (web), 4 members) · **Sprint** S2 (2025-09-15 to 2025-09-28)

**Tasks on the sprint board**
- *Admin authentication and approval workflow* (8 pts) (carried over from the previous sprint): **Partially Done**. Criteria: 1. Admin login; 2. Approve and reject endpoints; 3. Pending accounts screen; 4. Actions logged. — Audit log of actions not found.
- *Backend - audit log for approvals* (3 pts) (carried over from the previous sprint): **To Do**. Criteria: 1. Log admin id, target account, action and time; 2. Logs queryable by admins. — On the sprint 1 backlog; never done.

**Activity in the repository**
- Worked on 1 of the 14 days: `······· ·····■·` (■ = day with commits, week 1 then week 2).
- Wrote a large amount of code (several thousand lines); made 3 of the team's 13 commits this sprint (23%).
- Example commit messages: “Add admin authentication and approval system”; “fix 1.1”.

**Working with the team**
- The team did not use pull requests this sprint; work was pushed or merged directly.
- They worked mostly in files nobody else touched this sprint.

**Their code later on**
- Of the code they wrote this sprint, nearly all of it is still in the final version of the project.
- In the final version they are the main author of nearly all of the files they worked on.
- The comprehension interview could not be held for past students, so no answers are available.

**Effort**

| Criterion | Code | Rating |
|---|---|---|
| Responsibility engagement | `E_responsibility_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Work investment | `E_work_investment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Responsibility fulfilment | `E_responsibility_fulfillment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Initiative | `E_initiative` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Persistence | `E_persistence` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Consistency**

| Criterion | Code | Rating |
|---|---|---|
| Steady engagement | `C_steady_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Early contribution | `C_early_contribution` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Continuity | `C_continuity` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Predictable rhythm | `C_predictable_rhythm` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Requirement fulfilment**

| Criterion | Code | Rating |
|---|---|---|
| Task alignment | `RF_task_alignment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Acceptance criteria | `RF_acceptance_criteria` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Completeness | `RF_completeness` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Collaboration**

| Criterion | Code | Rating |
|---|---|---|
| Review engagement | `Co_review_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Discussion substance | `Co_discussion_substance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Team interaction | `Co_team_interaction` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Follow-through | `Co_follow_through` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Task complexity**

| Criterion | Code | Rating |
|---|---|---|
| Technical difficulty | `TC_technical_difficulty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Scope and breadth | `TC_scope_breadth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Dependency impact | `TC_dependency_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Architectural impact | `TC_architectural_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Uncertainty | `TC_uncertainty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Code ownership**

| Criterion | Code | Rating |
|---|---|---|
| Authorship depth | `KO_authorship_depth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Code durability | `KO_code_durability` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Self-maintenance | `KO_self_maintenance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Behaviour pattern:** [ ] consistent deep contributor &nbsp; [ ] last-minute rusher &nbsp; [ ] burst worker &nbsp; [ ] reviewer or coordinator &nbsp; [ ] free rider &nbsp; [ ] no specific pattern

**Overall mark (0–100):** ________ &nbsp;&nbsp; **Comment:** ____________________________________

<div style='page-break-after: always;'></div>

## Candidate C14

**Student** STU-012 · **Team** T05 (Car rental system, 3 members) · **Sprint** S1 (2025-08-18 to 2025-08-31)

**Tasks on the sprint board**
- *Frontend project setup* (1 pts): **Done**. Criteria: 1. App runs; 2. Folder structure for pages and components.
- *Sign-in and sign-up pages* (3 pts): **Done**. Criteria: 1. Sign-in form; 2. Sign-up form; 3. Validation. — Forms not yet connected to the backend.
- *Add vehicle screen and sidebar* (2 pts): **Done**. Criteria: 1. Add vehicle form; 2. Sidebar navigation. — Committed on the last day.

**Activity in the repository**
- Worked on 3 of the 14 days: `■······ ·····■■` (■ = day with commits, week 1 then week 2).
- Wrote a substantial amount of code (around a thousand lines); made 4 of the team's 6 commits this sprint (67%).
- Example commit messages: “Initial commit folder structure with vite”; “simple check”; “feat:SignIn page”; “Feat:add vehicle,sidebar,signUp”.

**Working with the team**
- The team did not use pull requests this sprint; work was pushed or merged directly.
- They worked mostly in files nobody else touched this sprint.

**Their code later on**
- Of the code they wrote this sprint, nearly all of it is still in the final version of the project.
- In the final version they are the main author of nearly all of the files they worked on.
- The comprehension interview could not be held for past students, so no answers are available.

**Effort**

| Criterion | Code | Rating |
|---|---|---|
| Responsibility engagement | `E_responsibility_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Work investment | `E_work_investment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Responsibility fulfilment | `E_responsibility_fulfillment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Initiative | `E_initiative` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Persistence | `E_persistence` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Consistency**

| Criterion | Code | Rating |
|---|---|---|
| Steady engagement | `C_steady_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Early contribution | `C_early_contribution` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Continuity | `C_continuity` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Predictable rhythm | `C_predictable_rhythm` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Requirement fulfilment**

| Criterion | Code | Rating |
|---|---|---|
| Task alignment | `RF_task_alignment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Acceptance criteria | `RF_acceptance_criteria` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Completeness | `RF_completeness` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Collaboration**

| Criterion | Code | Rating |
|---|---|---|
| Review engagement | `Co_review_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Discussion substance | `Co_discussion_substance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Team interaction | `Co_team_interaction` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Follow-through | `Co_follow_through` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Task complexity**

| Criterion | Code | Rating |
|---|---|---|
| Technical difficulty | `TC_technical_difficulty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Scope and breadth | `TC_scope_breadth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Dependency impact | `TC_dependency_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Architectural impact | `TC_architectural_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Uncertainty | `TC_uncertainty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Code ownership**

| Criterion | Code | Rating |
|---|---|---|
| Authorship depth | `KO_authorship_depth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Code durability | `KO_code_durability` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Self-maintenance | `KO_self_maintenance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Behaviour pattern:** [ ] consistent deep contributor &nbsp; [ ] last-minute rusher &nbsp; [ ] burst worker &nbsp; [ ] reviewer or coordinator &nbsp; [ ] free rider &nbsp; [ ] no specific pattern

**Overall mark (0–100):** ________ &nbsp;&nbsp; **Comment:** ____________________________________

<div style='page-break-after: always;'></div>

## Candidate C15

**Student** STU-025 · **Team** T08 (E-commerce microservices, 4 members) · **Sprint** S2 (2026-03-02 to 2026-03-15)

**Tasks on the sprint board**
- *JWT protection for payments* (3 pts): **Done**. Criteria: 1. Payment routes require a token; 2. Token forwarded by the gateway; 3. Frontend sends the token.
- *Merge order service branches* (1 pts): **Done**. Criteria: 1. Order branches merged. — Reviews were one or two words.

**Activity in the repository**
- Worked on 2 of the 14 days: `·····■■ ·······` (■ = day with commits, week 1 then week 2).
- Wrote a moderate amount of code (a few hundred lines); made 3 of the team's 58 commits this sprint (5%).
- Example commit messages: “Implement JWT authentication for payment service and protect routes”; “Implement Bearer token authentication for payment service and update related components”; “Remove example environment variables for payment service”.

**Working with the team**
- Opened 1 pull request(s); 1 merged.
- Merged 4 pull request(s) or branches from teammates; wrote 4 review(s).
- Review text: “All Good.”; “All good..”; “well done.”; “ok”.
- Some of the files they changed were also changed by teammates.

**Their code later on**
- Of the code they wrote this sprint, most of it is still in the final version of the project.
- In the final version they are the main author of nearly all of the files they worked on.
- The comprehension interview could not be held for past students, so no answers are available.

**Effort**

| Criterion | Code | Rating |
|---|---|---|
| Responsibility engagement | `E_responsibility_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Work investment | `E_work_investment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Responsibility fulfilment | `E_responsibility_fulfillment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Initiative | `E_initiative` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Persistence | `E_persistence` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Consistency**

| Criterion | Code | Rating |
|---|---|---|
| Steady engagement | `C_steady_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Early contribution | `C_early_contribution` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Continuity | `C_continuity` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Predictable rhythm | `C_predictable_rhythm` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Requirement fulfilment**

| Criterion | Code | Rating |
|---|---|---|
| Task alignment | `RF_task_alignment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Acceptance criteria | `RF_acceptance_criteria` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Completeness | `RF_completeness` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Collaboration**

| Criterion | Code | Rating |
|---|---|---|
| Review engagement | `Co_review_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Discussion substance | `Co_discussion_substance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Team interaction | `Co_team_interaction` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Follow-through | `Co_follow_through` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Task complexity**

| Criterion | Code | Rating |
|---|---|---|
| Technical difficulty | `TC_technical_difficulty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Scope and breadth | `TC_scope_breadth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Dependency impact | `TC_dependency_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Architectural impact | `TC_architectural_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Uncertainty | `TC_uncertainty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Code ownership**

| Criterion | Code | Rating |
|---|---|---|
| Authorship depth | `KO_authorship_depth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Code durability | `KO_code_durability` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Self-maintenance | `KO_self_maintenance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Behaviour pattern:** [ ] consistent deep contributor &nbsp; [ ] last-minute rusher &nbsp; [ ] burst worker &nbsp; [ ] reviewer or coordinator &nbsp; [ ] free rider &nbsp; [ ] no specific pattern

**Overall mark (0–100):** ________ &nbsp;&nbsp; **Comment:** ____________________________________

<div style='page-break-after: always;'></div>

## Candidate C16

**Student** STU-009 · **Team** T01 (Learning platform (web), 4 members) · **Sprint** S1 (2025-08-18 to 2025-08-31)

**Tasks on the sprint board**
- *Backend - donor registration APIs* (3 pts): **Done**. Criteria: 1. CRUD for donors; 2. Query donors; 3. Validation and error handling. — Donor model, controller and routes added; querying not visible.
- *Frontend - donor registration form* (3 pts): **Done** — completed by a teammate (STU-014). Criteria: 1. Multi-step form with progress; 2. Required fields validated; 3. Submits to donor API. — The registration page in the codebase was written by STU-014, not the assignee.
- *Backend - donor dashboard create donation* (3 pts): **Done**. Criteria: 1. Donor can create a donation; 2. Donation stored and linked to the donor; 3. Validation.
- *Frontend - create donation form* (3 pts): **Done**. Criteria: 1. Donor can open the form; 2. Required fields validated; 3. Success and error messages. — Closed on the tracker on the last day of the sprint; all work landed in two days.

**Activity in the repository**
- Worked on 2 of the 14 days: `······· ·■···■·` (■ = day with commits, week 1 then week 2).
- Wrote a large amount of code (several thousand lines); made 3 of the team's 17 commits this sprint (18%).
- Example commit messages: “feat: implement comprehensive donor system”; “feat: Add donation and impact components for educational support  - Implement MakeDonation”; “feat: Add donation and impact components for educational support  - Implement MakeDonation”.

**Working with the team**
- Opened 0 pull request(s); 0 merged.
- Merged 0 pull request(s) or branches from teammates; wrote 0 review(s).
- No written review comments.
- Most of the files they changed were also changed by teammates in this sprint.

**Their code later on**
- Of the code they wrote this sprint, most of it is still in the final version of the project.
- In the final version they are the main author of nearly all of the files they worked on.
- The comprehension interview could not be held for past students, so no answers are available.

**Effort**

| Criterion | Code | Rating |
|---|---|---|
| Responsibility engagement | `E_responsibility_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Work investment | `E_work_investment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Responsibility fulfilment | `E_responsibility_fulfillment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Initiative | `E_initiative` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Persistence | `E_persistence` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Consistency**

| Criterion | Code | Rating |
|---|---|---|
| Steady engagement | `C_steady_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Early contribution | `C_early_contribution` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Continuity | `C_continuity` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Predictable rhythm | `C_predictable_rhythm` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Requirement fulfilment**

| Criterion | Code | Rating |
|---|---|---|
| Task alignment | `RF_task_alignment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Acceptance criteria | `RF_acceptance_criteria` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Completeness | `RF_completeness` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Collaboration**

| Criterion | Code | Rating |
|---|---|---|
| Review engagement | `Co_review_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Discussion substance | `Co_discussion_substance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Team interaction | `Co_team_interaction` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Follow-through | `Co_follow_through` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Task complexity**

| Criterion | Code | Rating |
|---|---|---|
| Technical difficulty | `TC_technical_difficulty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Scope and breadth | `TC_scope_breadth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Dependency impact | `TC_dependency_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Architectural impact | `TC_architectural_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Uncertainty | `TC_uncertainty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Code ownership**

| Criterion | Code | Rating |
|---|---|---|
| Authorship depth | `KO_authorship_depth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Code durability | `KO_code_durability` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Self-maintenance | `KO_self_maintenance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Behaviour pattern:** [ ] consistent deep contributor &nbsp; [ ] last-minute rusher &nbsp; [ ] burst worker &nbsp; [ ] reviewer or coordinator &nbsp; [ ] free rider &nbsp; [ ] no specific pattern

**Overall mark (0–100):** ________ &nbsp;&nbsp; **Comment:** ____________________________________

<div style='page-break-after: always;'></div>

## Candidate C17

**Student** STU-018 · **Team** T07 (Real-estate GIS, 4 members) · **Sprint** S2 (2026-03-30 to 2026-04-12)

**Tasks on the sprint board**
- *Hazard map and property UI* (8 pts): **Done**. Criteria: 1. Hazard map; 2. Property list and details; 3. Map icons display. — Very large commits titled 'UI updates' and 'minor'; work in the last three days.
- *Controller updates for hazards* (2 pts): **Done**. Criteria: 1. Controllers support the UI.
- *Final deployment and README* (2 pts): **Done**. Criteria: 1. Deployment branch merged; 2. README.

**Activity in the repository**
- Worked on 3 of the 14 days: `······· ····■■■` (■ = day with commits, week 1 then week 2).
- Wrote a large amount of code (several thousand lines); made 15 of the team's 32 commits this sprint (47%).
- Example commit messages: “minor”; “controllor updates”; “UI updates”; “UI Updates”; “UI updates”; “Ui updates for hazard”; “UI Updates”; “minor”.

**Working with the team**
- Opened 5 pull request(s); 5 merged.
- Merged 0 pull request(s) or branches from teammates; wrote 0 review(s).
- No written review comments.
- Most of the files they changed were also changed by teammates in this sprint.

**Their code later on**
- Of the code they wrote this sprint, most of it is still in the final version of the project.
- In the final version they are the main author of most of the files they worked on.
- The comprehension interview could not be held for past students, so no answers are available.

**Effort**

| Criterion | Code | Rating |
|---|---|---|
| Responsibility engagement | `E_responsibility_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Work investment | `E_work_investment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Responsibility fulfilment | `E_responsibility_fulfillment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Initiative | `E_initiative` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Persistence | `E_persistence` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Consistency**

| Criterion | Code | Rating |
|---|---|---|
| Steady engagement | `C_steady_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Early contribution | `C_early_contribution` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Continuity | `C_continuity` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Predictable rhythm | `C_predictable_rhythm` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Requirement fulfilment**

| Criterion | Code | Rating |
|---|---|---|
| Task alignment | `RF_task_alignment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Acceptance criteria | `RF_acceptance_criteria` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Completeness | `RF_completeness` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Collaboration**

| Criterion | Code | Rating |
|---|---|---|
| Review engagement | `Co_review_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Discussion substance | `Co_discussion_substance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Team interaction | `Co_team_interaction` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Follow-through | `Co_follow_through` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Task complexity**

| Criterion | Code | Rating |
|---|---|---|
| Technical difficulty | `TC_technical_difficulty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Scope and breadth | `TC_scope_breadth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Dependency impact | `TC_dependency_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Architectural impact | `TC_architectural_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Uncertainty | `TC_uncertainty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Code ownership**

| Criterion | Code | Rating |
|---|---|---|
| Authorship depth | `KO_authorship_depth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Code durability | `KO_code_durability` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Self-maintenance | `KO_self_maintenance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Behaviour pattern:** [ ] consistent deep contributor &nbsp; [ ] last-minute rusher &nbsp; [ ] burst worker &nbsp; [ ] reviewer or coordinator &nbsp; [ ] free rider &nbsp; [ ] no specific pattern

**Overall mark (0–100):** ________ &nbsp;&nbsp; **Comment:** ____________________________________

<div style='page-break-after: always;'></div>

## Candidate C18

**Student** STU-006 · **Team** T13 (Tourism certification platform, 4 members) · **Sprint** S2 (2026-02-16 to 2026-03-01)

**Tasks on the sprint board**
- *Hotel search with auth and Swagger* (2 pts) (carried over from the previous sprint): **Done**. Criteria: 1. Search hotels; 2. Swagger auth.
- *Hotel feedback system* (3 pts): **Done**. Criteria: 1. Feedback CRUD; 2. Validation; 3. Linked to hotels.
- *AI hotel recommendations* (5 pts): **Done**. Criteria: 1. Recommend hotels; 2. Summaries from feedback; 3. Best-hotel search.
- *Vercel deployment and merges* (2 pts): **Done**. Criteria: 1. API deployed; 2. Branches merged.

**Activity in the repository**
- Worked on 5 of the 14 days: `····■·■ ■··■■··` (■ = day with commits, week 1 then week 2).
- Wrote a large amount of code (several thousand lines); made 13 of the team's 48 commits this sprint (27%).
- Example commit messages: “feat/add auth api for swagger and hotel display user”; “feat(feedback): implement hotel feedback system with CRUD operations and validation”; “refactor(feedback): Implement hotel feedback system with CRUD operations and integrate fee”; “feat(recommendations): Add AI-powered hotel recommendations and best hotel search function”; “feat(search): Implement hotel contact search by location with sorting by certificate level”; “feat(AI-Reccomondation): Enhance hotel recommendation system with feedback summaries and s”; “refactor(logging): Enhance logging in hotel search and feedback services for better tracea”; “feat(deployment): Add Vercel configuration and API entry point for serverless deployment”.

**Working with the team**
- Opened 11 pull request(s); 9 merged.
- Merged 0 pull request(s) or branches from teammates; wrote 0 review(s).
- No written review comments.
- Some of the files they changed were also changed by teammates.

**Their code later on**
- Of the code they wrote this sprint, most of it is still in the final version of the project.
- In the final version they are the main author of most of the files they worked on.
- The comprehension interview could not be held for past students, so no answers are available.

**Effort**

| Criterion | Code | Rating |
|---|---|---|
| Responsibility engagement | `E_responsibility_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Work investment | `E_work_investment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Responsibility fulfilment | `E_responsibility_fulfillment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Initiative | `E_initiative` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Persistence | `E_persistence` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Consistency**

| Criterion | Code | Rating |
|---|---|---|
| Steady engagement | `C_steady_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Early contribution | `C_early_contribution` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Continuity | `C_continuity` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Predictable rhythm | `C_predictable_rhythm` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Requirement fulfilment**

| Criterion | Code | Rating |
|---|---|---|
| Task alignment | `RF_task_alignment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Acceptance criteria | `RF_acceptance_criteria` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Completeness | `RF_completeness` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Collaboration**

| Criterion | Code | Rating |
|---|---|---|
| Review engagement | `Co_review_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Discussion substance | `Co_discussion_substance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Team interaction | `Co_team_interaction` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Follow-through | `Co_follow_through` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Task complexity**

| Criterion | Code | Rating |
|---|---|---|
| Technical difficulty | `TC_technical_difficulty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Scope and breadth | `TC_scope_breadth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Dependency impact | `TC_dependency_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Architectural impact | `TC_architectural_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Uncertainty | `TC_uncertainty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Code ownership**

| Criterion | Code | Rating |
|---|---|---|
| Authorship depth | `KO_authorship_depth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Code durability | `KO_code_durability` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Self-maintenance | `KO_self_maintenance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Behaviour pattern:** [ ] consistent deep contributor &nbsp; [ ] last-minute rusher &nbsp; [ ] burst worker &nbsp; [ ] reviewer or coordinator &nbsp; [ ] free rider &nbsp; [ ] no specific pattern

**Overall mark (0–100):** ________ &nbsp;&nbsp; **Comment:** ____________________________________

<div style='page-break-after: always;'></div>

## Candidate C19

**Student** STU-029 · **Team** T06 (Campus services hub, 4 members) · **Sprint** S1 (2026-03-23 to 2026-04-05)

**Tasks on the sprint board**
- *Ticket workflow with attachments* (8 pts): **Done** — completed by a teammate (STU-015). Criteria: 1. Create a ticket; 2. Ownership rules for updates; 3. Attach images; 4. Status workflow. — Workstream 3 was built by STU-015, not the assignee.

**Activity in the repository**
- No commits in this sprint.

**Working with the team**
- The team did not use pull requests this sprint; work was pushed or merged directly.

**Their code later on**
- No source code to follow up.
- The comprehension interview could not be held for past students, so no answers are available.

**Effort**

| Criterion | Code | Rating |
|---|---|---|
| Responsibility engagement | `E_responsibility_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Work investment | `E_work_investment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Responsibility fulfilment | `E_responsibility_fulfillment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Initiative | `E_initiative` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Persistence | `E_persistence` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Consistency**

| Criterion | Code | Rating |
|---|---|---|
| Steady engagement | `C_steady_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Early contribution | `C_early_contribution` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Continuity | `C_continuity` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Predictable rhythm | `C_predictable_rhythm` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Requirement fulfilment**

| Criterion | Code | Rating |
|---|---|---|
| Task alignment | `RF_task_alignment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Acceptance criteria | `RF_acceptance_criteria` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Completeness | `RF_completeness` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Collaboration**

| Criterion | Code | Rating |
|---|---|---|
| Review engagement | `Co_review_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Discussion substance | `Co_discussion_substance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Team interaction | `Co_team_interaction` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Follow-through | `Co_follow_through` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Task complexity**

| Criterion | Code | Rating |
|---|---|---|
| Technical difficulty | `TC_technical_difficulty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Scope and breadth | `TC_scope_breadth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Dependency impact | `TC_dependency_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Architectural impact | `TC_architectural_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Uncertainty | `TC_uncertainty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Code ownership**

| Criterion | Code | Rating |
|---|---|---|
| Authorship depth | `KO_authorship_depth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Code durability | `KO_code_durability` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Self-maintenance | `KO_self_maintenance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Behaviour pattern:** [ ] consistent deep contributor &nbsp; [ ] last-minute rusher &nbsp; [ ] burst worker &nbsp; [ ] reviewer or coordinator &nbsp; [ ] free rider &nbsp; [ ] no specific pattern

**Overall mark (0–100):** ________ &nbsp;&nbsp; **Comment:** ____________________________________

<div style='page-break-after: always;'></div>

## Candidate C20

**Student** STU-013 · **Team** T07 (Real-estate GIS, 4 members) · **Sprint** S2 (2026-03-30 to 2026-04-12)

**Tasks on the sprint board**
- *Guideline pages and home page* (5 pts): **Done**. Criteria: 1. Home page with feature cards; 2. Edit and view guidelines; 3. Generative AI dependency set up. — Most work in the final day.

**Activity in the repository**
- Worked on 3 of the 14 days: `······· ···■■·■` (■ = day with commits, week 1 then week 2).
- Wrote a large amount of code (several thousand lines); made 4 of the team's 32 commits this sprint (12%).
- Example commit messages: “feat: Implement HomePage component with navigation and feature cards”; “feat: Add @google/generative-ai dependency and improve database connection handling”; “Refactor GuidelinesPages and SuggestGuidelinePage for improved UI and functionality”; “feat: add EditGuidelines and ViewGuidelines components for managing disaster guidelines”.

**Working with the team**
- Opened 1 pull request(s); 1 merged.
- Merged 0 pull request(s) or branches from teammates; wrote 0 review(s).
- No written review comments.
- Most of the files they changed were also changed by teammates in this sprint.

**Their code later on**
- Of the code they wrote this sprint, most of it is still in the final version of the project.
- In the final version they are the main author of about half of the files they worked on.
- The comprehension interview could not be held for past students, so no answers are available.

**Effort**

| Criterion | Code | Rating |
|---|---|---|
| Responsibility engagement | `E_responsibility_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Work investment | `E_work_investment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Responsibility fulfilment | `E_responsibility_fulfillment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Initiative | `E_initiative` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Persistence | `E_persistence` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Consistency**

| Criterion | Code | Rating |
|---|---|---|
| Steady engagement | `C_steady_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Early contribution | `C_early_contribution` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Continuity | `C_continuity` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Predictable rhythm | `C_predictable_rhythm` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Requirement fulfilment**

| Criterion | Code | Rating |
|---|---|---|
| Task alignment | `RF_task_alignment` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Acceptance criteria | `RF_acceptance_criteria` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Completeness | `RF_completeness` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Collaboration**

| Criterion | Code | Rating |
|---|---|---|
| Review engagement | `Co_review_engagement` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Discussion substance | `Co_discussion_substance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Team interaction | `Co_team_interaction` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Follow-through | `Co_follow_through` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Task complexity**

| Criterion | Code | Rating |
|---|---|---|
| Technical difficulty | `TC_technical_difficulty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Scope and breadth | `TC_scope_breadth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Dependency impact | `TC_dependency_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Architectural impact | `TC_architectural_impact` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Uncertainty | `TC_uncertainty` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Code ownership**

| Criterion | Code | Rating |
|---|---|---|
| Authorship depth | `KO_authorship_depth` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Code durability | `KO_code_durability` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |
| Self-maintenance | `KO_self_maintenance` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |

**Behaviour pattern:** [ ] consistent deep contributor &nbsp; [ ] last-minute rusher &nbsp; [ ] burst worker &nbsp; [ ] reviewer or coordinator &nbsp; [ ] free rider &nbsp; [ ] no specific pattern

**Overall mark (0–100):** ________ &nbsp;&nbsp; **Comment:** ____________________________________

<div style='page-break-after: always;'></div>
