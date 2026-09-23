// Local demo fixtures for the Requirements Analysis & Intelligent Project Planning
// component. There is no backend yet, so every planning page reads from this one
// file (via PlanningDataContext for anything the student can edit) to stay
// internally consistent end-to-end: SRS Quality -> Decomposition -> Effort
// Estimation -> Sprint Management.

export const QUALITY_DIMENSIONS = [
  { key: 'clarity', label: 'Clarity' },
  { key: 'completeness', label: 'Completeness' },
  { key: 'consistency', label: 'Consistency' },
  { key: 'testability', label: 'Testability' },
  { key: 'feasibility', label: 'Feasibility' },
  { key: 'scope', label: 'Scope Alignment' },
]

export const AGENTS = {
  quality: { key: 'quality', label: 'Quality Analysis Agent', short: 'Quality', color: '#2563eb' },
  decomposition: { key: 'decomposition', label: 'Decomposition Agent', short: 'Decomposition', color: '#7c3aed' },
  estimation: { key: 'estimation', label: 'Estimation Agent', short: 'Estimation', color: '#0891b2' },
}

export const QUALITY_GATE_THRESHOLD = 70

export const PROJECT_INFO = {
  name: 'NexaPlan — Adaptive Tutor Framework',
  batch: 'Y4.2',
  groupId: 'g03',
  supervisor: 'Dr. Amara Silva',
  sprintNumber: 5,
  totalSprints: 8,
  sprintName: 'Sprint 5',
  sprintStartDate: '2026-09-15',
  sprintEndDate: '2026-09-28',
}

export const TEAM_MEMBERS = [
  { id: 'u1', name: 'Nimal Perera', initials: 'NP', role: 'You · Requirements & Planning', capacity: 20 },
  { id: 'u2', name: 'Ishara Fernando', initials: 'IF', role: 'Backend Engineer', capacity: 20 },
  { id: 'u3', name: 'Ruwan Silva', initials: 'RS', role: 'Frontend Engineer', capacity: 20 },
  { id: 'u4', name: 'Dilani Wickrama', initials: 'DW', role: 'QA & DevOps', capacity: 15 },
]

export const REQUIREMENTS = [
  {
    id: 'REQ-101',
    title: 'Student can submit a functional requirement in natural language',
    description:
      'The system shall allow a student to enter a requirement as free-form text and receive a structured requirement object in return.',
    priority: 'High',
    status: 'Passing',
    overallScore: 93,
    dimensionScores: { clarity: 95, completeness: 92, consistency: 90, testability: 94, feasibility: 96, scope: 91 },
    suggestedRewrite: null,
    lastChecked: '2026-09-20T09:12:00Z',
  },
  {
    id: 'REQ-102',
    title: 'System shall notify supervisors of at-risk groups weekly',
    description:
      'The system shall send a weekly digest to the supervising instructor summarizing groups whose quality gate pass rate has dropped.',
    priority: 'Medium',
    status: 'Passing',
    overallScore: 88,
    dimensionScores: { clarity: 90, completeness: 85, consistency: 88, testability: 84, feasibility: 92, scope: 89 },
    suggestedRewrite: null,
    lastChecked: '2026-09-19T14:32:00Z',
  },
  {
    id: 'REQ-103',
    title: 'The app should be fast and easy to use for everyone',
    description: 'The app should be fast and easy to use for everyone involved in the project.',
    priority: 'Low',
    status: 'Failing',
    overallScore: 41,
    dimensionScores: { clarity: 28, completeness: 35, consistency: 40, testability: 22, feasibility: 70, scope: 51 },
    suggestedRewrite:
      'The system shall render the dashboard in under 2 seconds on a standard broadband connection, and a first-time user shall be able to submit a requirement without external help within 3 minutes.',
    lastChecked: '2026-09-21T08:05:00Z',
  },
  {
    id: 'REQ-104',
    title: 'System shall auto-decompose a requirement and simultaneously lock its scope',
    description:
      'The system shall generate a sub-task breakdown for a requirement while also preventing any further edits to that requirement once decomposition starts.',
    priority: 'High',
    status: 'Needs Review',
    overallScore: 63,
    dimensionScores: { clarity: 74, completeness: 70, consistency: 45, testability: 66, feasibility: 58, scope: 65 },
    suggestedRewrite:
      'Split into two requirements: (1) auto-decomposition of a requirement into sub-tasks, and (2) a separate scope-lock rule triggered once decomposition is accepted.',
    lastChecked: '2026-09-21T11:47:00Z',
  },
  {
    id: 'REQ-105',
    title: 'Effort estimation shall include a confidence interval per requirement',
    description:
      'The system shall predict effort in story points for each requirement and report a confidence interval alongside the point estimate.',
    priority: 'Medium',
    status: 'Passing',
    overallScore: 90,
    dimensionScores: { clarity: 92, completeness: 88, consistency: 91, testability: 87, feasibility: 93, scope: 89 },
    suggestedRewrite: null,
    lastChecked: '2026-09-18T16:20:00Z',
  },
  {
    id: 'REQ-106',
    title: 'System shall support offline mode with full AI agent functionality',
    description:
      'The system shall allow students to use every AI agent (quality, decomposition, estimation) while fully offline with no network connection.',
    priority: 'Low',
    status: 'Failing',
    overallScore: 34,
    dimensionScores: { clarity: 60, completeness: 40, consistency: 35, testability: 20, feasibility: 15, scope: 34 },
    suggestedRewrite:
      'Scope down to: the system shall cache the last-fetched agent results for read-only viewing while offline; live agent inference requires connectivity.',
    lastChecked: '2026-09-21T07:58:00Z',
  },
  {
    id: 'REQ-107',
    title: 'Instructor shall be able to override an unresolved DART arbitration decision',
    description:
      'The system shall let a supervising instructor review a DART arbitration case and confirm or override its resolution, with the override logged.',
    priority: 'High',
    status: 'Needs Review',
    overallScore: 71,
    dimensionScores: { clarity: 80, completeness: 75, consistency: 68, testability: 62, feasibility: 78, scope: 63 },
    suggestedRewrite:
      'Clarify what "logged" means: specify that an override records instructor id, timestamp, and justification text in the case history.',
    lastChecked: '2026-09-20T13:10:00Z',
  },
  {
    id: 'REQ-108',
    title: 'System shall generate a six-dimension quality radar for every submitted requirement',
    description:
      'The system shall score every submitted requirement against six quality dimensions and visualize the result as a radar chart.',
    priority: 'Medium',
    status: 'Passing',
    overallScore: 95,
    dimensionScores: { clarity: 96, completeness: 94, consistency: 95, testability: 93, feasibility: 97, scope: 95 },
    suggestedRewrite: null,
    lastChecked: '2026-09-17T10:00:00Z',
  },
]

// DART — Diagnostic Arbitration via Reasoning Traces. Folded inline into SRS
// Quality / Decomposition (rather than a standalone page) so it surfaces exactly
// where the agents actually disagree on a given requirement.
export const ARBITRATION_CASES = [
  {
    id: 'DART-1001',
    requirementId: 'REQ-104',
    category: 'COMPOUND',
    stage: 'decomposition',
    title: 'Auto-decomposition requirement bundles a scope-lock rule',
    status: 'Open',
    confidenceAgreement: 58,
    createdAt: '2026-09-21T11:50:00Z',
    agentRationale: {
      quality: {
        verdict: 'Flag as compound',
        confidence: 81,
        rationale:
          'Detected two independent obligations ("decompose" and "lock scope") joined by "while also" — this violates the atomicity check under Consistency and Scope Alignment.',
      },
      decomposition: {
        verdict: 'Treat as one requirement',
        confidence: 47,
        rationale:
          'A single sub-task tree can represent both behaviors as sibling nodes; splitting would fragment traceability to one user story.',
      },
      estimation: {
        verdict: 'Flag as compound',
        confidence: 66,
        rationale:
          'Combined effort estimate has an unusually wide interval versus similar single-obligation requirements, suggesting two distinct units of work.',
      },
    },
    resolution:
      'Split into REQ-104a (auto-decomposition) and REQ-104b (scope-lock rule) — 2 of 3 agents and the wide estimation interval support a compound requirement.',
    resolvedBy: null,
  },
  {
    id: 'DART-1002',
    requirementId: 'REQ-107',
    category: 'AMBIGUOUS',
    stage: 'quality',
    title: '"Logged" is interpreted differently by Quality and Decomposition agents',
    status: 'Open',
    confidenceAgreement: 64,
    createdAt: '2026-09-20T13:15:00Z',
    agentRationale: {
      quality: {
        verdict: 'Needs clarification',
        confidence: 72,
        rationale:
          'The term "logged" has no defined fields (who/when/why), so Testability cannot be scored above 65 — the requirement is not independently verifiable as written.',
      },
      decomposition: {
        verdict: 'Assume audit-log entity',
        confidence: 58,
        rationale:
          'Generated a generic "AuditLogEntry" sub-task by default, since most override-style requirements in this project map to an existing audit trail pattern.',
      },
      estimation: {
        verdict: 'Needs clarification',
        confidence: 60,
        rationale:
          'Effort varies 2x depending on whether a new audit entity is required or an existing one is reused — cannot commit to one estimate yet.',
      },
    },
    resolution:
      'Clarification requested from the student: define the exact fields an override log entry must contain before decomposition/estimation proceed.',
    resolvedBy: null,
  },
  {
    id: 'DART-1003',
    requirementId: 'REQ-103',
    category: 'STRUCTURAL',
    stage: 'quality',
    title: 'Non-measurable performance requirement conflicts with the estimation model input schema',
    status: 'Resolved',
    confidenceAgreement: 89,
    createdAt: '2026-09-21T08:10:00Z',
    agentRationale: {
      quality: {
        verdict: 'Reject as unmeasurable',
        confidence: 92,
        rationale: '"Fast and easy" contains no acceptance threshold; Clarity and Testability both score below 30.',
      },
      decomposition: {
        verdict: 'Cannot decompose',
        confidence: 88,
        rationale: 'No sub-task tree can be derived without a measurable target.',
      },
      estimation: {
        verdict: 'Cannot estimate',
        confidence: 85,
        rationale: 'No comparable historical requirement exists for an unbounded, unmeasurable performance goal.',
      },
    },
    resolution:
      'All three agents agree (89% confidence) — returned to the student with the suggested rewrite before re-entering the pipeline.',
    resolvedBy: 'Dr. Amara Silva',
  },
  {
    id: 'DART-1004',
    requirementId: 'REQ-106',
    category: 'NOVEL',
    stage: 'quality',
    title: 'Full offline AI functionality has no comparable prior case',
    status: 'Open',
    confidenceAgreement: 41,
    createdAt: '2026-09-21T08:02:00Z',
    agentRationale: {
      quality: {
        verdict: 'Flag as infeasible as written',
        confidence: 70,
        rationale: 'Feasibility scores 15/100 — running LLM-backed agents fully offline is not supported by the current architecture.',
      },
      decomposition: {
        verdict: 'No close prior pattern',
        confidence: 35,
        rationale: 'No requirement in the project history resembles "full offline AI parity".',
      },
      estimation: {
        verdict: 'Wide, low-trust estimate',
        confidence: 30,
        rationale: 'Effort interval is the widest in the project; the model is essentially guessing given no comparable precedent.',
      },
    },
    resolution:
      'Marked NOVEL — routed to instructor review rather than auto-resolved, since agent confidence agreement (41%) falls below the auto-resolution threshold.',
    resolvedBy: null,
  },
]

export function getArbitrationForRequirement(reqId) {
  return ARBITRATION_CASES.filter((c) => c.requirementId === reqId)
}

// ---------------------------------------------------------------------------
// Decomposition: Requirement -> User Story -> Task -> Sub-task / Bug.
// Stories are student-authored — the agent only evaluates and lists issues,
// it never rewrites. Only requirements that pass the quality gate are
// decomposable; seeded here only for the requirements that already pass in
// REQUIREMENTS above.
// ---------------------------------------------------------------------------
export const USER_STORIES_SEED = {
  'REQ-101': [
    {
      id: 'US-101-1',
      title: "As a student, I want to type my requirement in plain English so I don't need special syntax",
      acceptanceCriteria:
        'Given the intake form, when I submit free text, then the system stores it verbatim before parsing.',
      investResult: null,
      status: 'Draft',
      tasks: [],
      bugs: [],
    },
    {
      id: 'US-101-2',
      title:
        'As the system, I want to parse free text into a structured requirement object so that it can be scored immediately',
      acceptanceCriteria:
        'Given raw text, when parsed, then priority, description and dimension scores are populated.',
      investResult: {
        independent: { pass: true, note: 'No hard dependency language found — this can plausibly be built on its own.' },
        negotiable: { pass: true, note: 'Describes the outcome, not a fixed implementation.' },
        valuable: { pass: true, note: 'States who wants this and why.' },
        estimable: { pass: true, note: 'Concrete enough to size with reasonable confidence.' },
        small: { pass: true, note: 'Scoped to a single, shippable unit of work.' },
        testable: { pass: true, note: 'Acceptance criteria gives a concrete condition to verify against.' },
        overallPass: true,
      },
      status: 'Accepted',
      tasks: [
        {
          id: 'T-101-2-1',
          title: 'Parse free text into schema',
          status: 'In Progress',
          subtasks: [
            { id: 'ST-101-2-1-1', title: 'Extract title + description', done: true },
            { id: 'ST-101-2-1-2', title: 'Infer priority from keywords', done: false },
          ],
        },
        { id: 'T-101-2-2', title: 'Persist structured requirement', status: 'Todo', subtasks: [] },
      ],
      bugs: [
        { id: 'BUG-101-2-1', title: 'Confirmation toast sometimes shows a stale requirement ID', severity: 'Medium', status: 'Open' },
      ],
    },
  ],
  'REQ-102': [],
  'REQ-105': [
    {
      id: 'US-105-1',
      title: 'As a student, I want an effort estimate for my requirement so that I can plan my sprint',
      acceptanceCriteria: 'The system should quickly show a point estimate and a confidence interval for the requirement.',
      investResult: null,
      status: 'Draft',
      tasks: [],
      bugs: [],
    },
  ],
  'REQ-108': [],
}

// ---------------------------------------------------------------------------
// Effort estimation, keyed by user story id — only meaningful once a story has
// been accepted in Decomposition. The AI side stays blank until the student
// submits their own estimate first (aiRevealed unlocks it) — same shape the
// page seeds automatically for any newly-accepted story.
export const STORY_ESTIMATIONS_SEED = {
  'US-101-2': {
    studentPoints: null,
    aiPoints: null,
    aiConfidence: null,
    aiFactors: null,
    aiRevealed: false,
    finalPoints: null,
    reason: '',
    confirmed: false,
  },
}

export const STORY_POINT_SCALE = [1, 2, 3, 5, 8, 13, 21]

// ---------------------------------------------------------------------------
// Sprint Management — Kanban board, seeded with a few already-confirmed cards
// so the board isn't empty on first load.
// ---------------------------------------------------------------------------
export const KANBAN_SEED = [
  {
    id: 'K-1',
    title: 'Build free-text intake form',
    requirementId: 'REQ-101',
    storyId: 'US-101-1',
    points: 3,
    status: 'Done',
    assigneeId: 'u1',
    dueDate: '2026-09-17',
  },
  {
    id: 'K-2',
    title: 'Compute effort estimate with confidence interval',
    requirementId: 'REQ-105',
    storyId: 'US-105-1',
    points: 8,
    status: 'In Progress',
    assigneeId: 'u3',
    dueDate: '2026-09-23',
  },
  {
    id: 'K-3',
    title: 'Draft weekly supervisor digest job',
    requirementId: 'REQ-102',
    storyId: null,
    points: 5,
    status: 'Todo',
    assigneeId: 'u2',
    dueDate: '2026-09-25',
  },
  {
    id: 'K-4',
    title: 'Render six-dimension radar chart component',
    requirementId: 'REQ-108',
    storyId: null,
    points: 3,
    status: 'Done',
    assigneeId: 'u4',
    dueDate: '2026-09-18',
  },
  {
    id: 'K-5',
    title: 'Send weekly digest email to supervisor',
    requirementId: 'REQ-102',
    storyId: null,
    points: 3,
    status: 'Blocked',
    assigneeId: 'u2',
    blockedReason: 'Depends on K-3 (Draft weekly supervisor digest job), which is still To Do.',
    dependsOn: 'K-3',
    dueDate: '2026-09-27',
  },
]

export const KANBAN_COLUMNS = [
  { key: 'Todo', label: 'To Do' },
  { key: 'In Progress', label: 'In Progress' },
  { key: 'Blocked', label: 'Blocked' },
  { key: 'Done', label: 'Done' },
]

export const VELOCITY_TREND = [
  { sprint: 'Sprint 3', velocity: 9, planned: 11 },
  { sprint: 'Sprint 4', velocity: 11, planned: 12 },
  { sprint: 'Sprint 5', velocity: 12, planned: 12 },
]

export const BURNDOWN_SEED = [
  { day: 'Day 1', ideal: 40, actual: 40 },
  { day: 'Day 2', ideal: 36, actual: 38 },
  { day: 'Day 3', ideal: 32, actual: 33 },
  { day: 'Day 4', ideal: 28, actual: 30 },
  { day: 'Day 5', ideal: 24, actual: 22 },
  { day: 'Day 6', ideal: 20, actual: 19 },
  { day: 'Day 7', ideal: 16, actual: 15 },
  { day: 'Day 8', ideal: 12, actual: null },
  { day: 'Day 9', ideal: 8, actual: null },
  { day: 'Day 10', ideal: 0, actual: null },
]

export const ACTIVITY_FEED = [
  {
    id: 1,
    tone: 'primary',
    text: 'SRS Quality Gate re-scored REQ-103 — still failing (41%), rewrite suggested.',
    time: '18 minutes ago',
  },
  {
    id: 2,
    tone: 'warning',
    text: 'DART flagged REQ-104 as a compound requirement — see SRS Quality feedback panel.',
    time: '2 hours ago',
  },
  {
    id: 3,
    tone: 'success',
    text: 'Estimation agent completed REQ-108 at 8 SP with a tight confidence interval.',
    time: 'Yesterday',
  },
  {
    id: 4,
    tone: 'danger',
    text: 'DART flagged REQ-106 as NOVEL — confidence agreement only 41%, routed to instructor review.',
    time: '2 days ago',
  },
]

export const QUALITY_GATE_TREND = [
  { sprint: 'Sprint 3', passRate: 66 },
  { sprint: 'Sprint 4', passRate: 74 },
  { sprint: 'Sprint 5', passRate: 79 },
]

export const GROUPS = [
  {
    id: 'g07',
    name: 'Group 07',
    project: 'AEGIS — Security Vulnerability Assistant',
    batch: 'Y4.1',
    members: 4,
    qualityGate: 92,
    risk: 'Low',
    openArbitrations: 0,
    status: 'On Track',
    requirementIds: ['REQ-101', 'REQ-105', 'REQ-108'],
  },
  {
    id: 'g12',
    name: 'Group 12',
    project: 'TrackWise — Performance Analytics Platform',
    batch: 'Y4.1',
    members: 5,
    qualityGate: 74,
    risk: 'Medium',
    openArbitrations: 2,
    status: 'Needs Attention',
    requirementIds: ['REQ-104', 'REQ-107'],
  },
  {
    id: 'g03',
    name: 'Group 03',
    project: 'NexaPlan — Adaptive Tutor Framework',
    batch: 'Y4.2',
    members: 4,
    qualityGate: 58,
    risk: 'High',
    openArbitrations: 2,
    status: 'At Risk',
    requirementIds: REQUIREMENTS.map((r) => r.id),
  },
  {
    id: 'g09',
    name: 'Group 09',
    project: 'CivicPulse — Community Reporting App',
    batch: 'Y4.1',
    members: 4,
    qualityGate: 81,
    risk: 'Low',
    openArbitrations: 0,
    status: 'On Track',
    requirementIds: ['REQ-102'],
  },
  {
    id: 'g15',
    name: 'Group 15',
    project: 'MedTrack — Clinical Scheduling System',
    batch: 'Y4.2',
    members: 5,
    qualityGate: 69,
    risk: 'Medium',
    openArbitrations: 1,
    status: 'Needs Attention',
    requirementIds: ['REQ-104'],
  },
  {
    id: 'g21',
    name: 'Group 21',
    project: 'HarvestLink — Agri Supply Chain Tracker',
    batch: 'Y4.2',
    members: 4,
    qualityGate: 87,
    risk: 'Low',
    openArbitrations: 0,
    status: 'On Track',
    requirementIds: ['REQ-108', 'REQ-105'],
  },
]

export function getRequirement(id) {
  return REQUIREMENTS.find((r) => r.id === id)
}

export function getGroup(id) {
  return GROUPS.find((g) => g.id === id)
}

// Builds the {requirements, userStories, estimations, kanbanTasks} shape that
// computeStageStats() and the instructor GroupWorkspace expect, filtered down
// to one group's requirements — from the static seed data. Group 03 is the
// one group the student pipeline actually lives in; callers should use the
// live usePlanningData() store for that group instead of this static view.
export function getGroupPipelineData(group) {
  const requirements = REQUIREMENTS.filter((r) => group.requirementIds.includes(r.id))
  const userStories = Object.fromEntries(
    group.requirementIds.map((id) => [id, USER_STORIES_SEED[id] || []]),
  )
  const storyIds = new Set(Object.values(userStories).flat().map((s) => s.id))
  const estimations = Object.fromEntries(
    Object.entries(STORY_ESTIMATIONS_SEED).filter(([storyId]) => storyIds.has(storyId)),
  )
  const kanbanTasks = KANBAN_SEED.filter((t) => group.requirementIds.includes(t.requirementId))
  return { requirements, userStories, estimations, kanbanTasks }
}
