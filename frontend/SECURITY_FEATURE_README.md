# Frontend Security Feature Implementation

This document records the current implementation of the student/instructor-facing
AEGIS Security portal in the MENTOR frontend. It is intended as a restoration guide
after cloning the repository again.

It is a **frontend-only prototype**: all data comes from an in-memory mock findings
set that mirrors the finding-record schema described in the security subsystem's
project definition (evidence, OWASP/CWE, CVSS, traceability, risk score, fix
pattern, probe question). No real scanner, LLM, or Tutor Agent is called yet.

## What is implemented

Three tabs under **Project Security**, matching the sidebar navigation
(`src/shared/layout/navConfig.js`):

- **Dashboard** (`/security/dashboard`) — KPI stat cards (open findings, critical
  count, average project-context risk, Tutor-verified closed count), an OWASP
  category breakdown, Secure-SDLC phase coverage (Requirements/Implementation/
  Testing/Deployment, with Design merged into Requirements), and the
  highest-risk findings ranked by risk score rather than severity alone.
- **Scan Report** (`/security/scan-report`) — the full findings list with status
  tabs (All / Open / Awaiting review / Awaiting learning check / Closed) and
  live counts, a category filter, live search by title/file path, and a detail
  dialog per finding showing evidence with the vulnerable line highlighted,
  detector/confidence/CWE/OWASP/CVSS, why it matters, and linked
  requirement/commit/sprint-task context (or an honest "could not be linked"
  message). A "Request review" action moves a finding to `Awaiting review`.
- **Remediation** (`/security/remediation`) — a workspace for one finding at a
  time: before/after fix code, the explanation, a "Mark fix applied" action, and
  a Tutor Agent learning-check handoff placeholder (connecting state, probe
  question, and prototype Pass/Retry outcomes). A finding only becomes `Closed`
  after the simulated comprehension check passes — never just from deleting the
  vulnerable line.

Each page fetches data through a TanStack Query hook so the state resets on
refresh; findings edited on the Remediation page (fix applied / learning-check
outcome) live in that page's local component state only.

## Files changed or required

### Data, service and hook layer (`src/modules/security/`)

- `data/mockFindings.js` — `INITIAL_FINDINGS` (six sample findings across all
  five vulnerability categories: Injection, Secrets/sensitive data, Access
  control, Dependencies & CI/CD, Authentication), plus `CATEGORY_OPTIONS` and
  `STATUS_LABELS`.
- `services/securityService.js` — resolves the mock data with a small artificial
  delay. Written to the same shape a future `apiClient`-backed service would
  use, so swapping in real HTTP calls later needs no change in the hook or
  pages (see `docs/API_GUIDELINES.md`).
- `hooks/useSecurityFindings.js` — `useQuery` wrapper, keyed by the active team
  from `useScope()`.

### Shared security components

- `components/FindingBadges.jsx` — `PriorityBadge`, `StatusBadge`,
  `ConfidenceBadge`.
- `components/CodeBlock.jsx` — renders source lines with an optional
  highlighted (vulnerable) line.
- `components/FindingDetailDialog.jsx` — the full evidence dialog used by Scan
  Report.

### Pages

- `pages/Dashboard.jsx`
- `pages/ScanReport.jsx`
- `pages/Remediation.jsx`

### Route registration

`src/modules/security/routes.jsx` mounts three routes, with the module index
redirecting to `dashboard`:

```text
/teams/:teamId/security/dashboard
/teams/:teamId/security/scan-report
/teams/:teamId/security/remediation
```

`src/App.jsx` mounts `security/*` under the team-scoped, authenticated
`DashboardShell` per `docs/ROUTING_GUIDELINES.md`; no changes were needed there.

### Student & instructor navigation

`src/shared/layout/navConfig.js` already listed all three tabs under
**Project Security** (student) / **Security** (instructor) before this change —
only the page implementations were missing. Admin navigation keeps a single
link to the Dashboard and does not expose Scan Report or Remediation.

## Data model used by the prototype

Each item in `INITIAL_FINDINGS` has this shape:

```js
{
  id, category, status, priority,           // open | review | learning | closed
  owasp, cwe, cvss, cvssVector,
  detector, detectionMethod, confidence, confidenceValue,
  title, endpoint, file, line, code, vulnerableLine,
  explanation, whyItMatters,
  context: { linked, requirement, commit, sprintTask, contributor },
  riskScore, learningPriority,
  before, after, probeQuestion,
  verification,                             // present once a finding is closed
}
```

Internal status values map to labels in `STATUS_LABELS`:

| Internal value | Visible label           |
| -------------- | ----------------------- |
| `open`         | Open                    |
| `review`       | Awaiting review         |
| `learning`     | Awaiting learning check |
| `closed`       | Closed                  |

## How to restore after recloning

From the repository root:

```powershell
Set-Location frontend
npm install
npm run dev
```

Sign in and open `Project Security` in the sidebar; it lands on
`/teams/<teamId>/security/dashboard`.

To verify before continuing development:

```powershell
npm run lint
npm run build
```

Manual smoke test:

1. Confirm all three Project Security tabs render for the student account.
2. On the Dashboard, confirm the KPI cards, category breakdown, and top-risk
   findings list populate.
3. On Scan Report, test the status tabs, category filter, and search; open a
   finding and confirm the evidence/context/probe-question dialog renders;
   request review on an open finding and confirm it moves to
   "Awaiting review".
4. On Remediation, select a finding, confirm the before/after code renders,
   mark the fix applied, start the learning check, wait for the connecting
   state, then test both the Pass and Retry outcomes.

## Prototype limitations and next integration work

- All findings are mock data in `data/mockFindings.js`; nothing is fetched
  from a real scanner or LLM pipeline yet.
- Remediation page state (fix applied / learning-check outcome) lives in
  React state only and resets on refresh; it is not shared with Scan Report
  in the same session.
- The learning check is a handoff placeholder; it does not embed a real
  Tutor Agent conversation, and the Pass/Retry buttons exist only to
  demonstrate the intended status transitions.
- "Re-run analysis" on Scan Report only shows a toast notice; it does not
  call a scanner.
- No PDF/report export is implemented in this pass.
- There is no real cross-user data source in this prototype; production code
  must enforce signed-in-student scoping at the API boundary and use
  `X-Team-Id` per `docs/API_GUIDELINES.md`.

When connecting the real services, preserve the current student-facing rules
from the project definition: findings are learning signals, never grade
inputs; no cross-student data; the security subsystem generates the probe
question but never owns the Tutor Agent's verification dialogue; and no claim
that the LLM detected a finding before the deterministic scanner did.
