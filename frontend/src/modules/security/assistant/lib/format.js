// Pure helpers for the Security Assistant pages: wording and colours of statuses, kept apart from the components so they are easy to test.
// The rule behind most of them: a check that failed, was skipped or did not run must never look like "no findings".

export const CATEGORIES = [
  { id: 'V1', label: 'Access control' },
  { id: 'V2', label: 'Injection' },
  { id: 'V3', label: 'Authentication' },
  { id: 'V4', label: 'Secrets' },
  { id: 'V5', label: 'Dependencies & CI/CD' },
]

export const STAGE_ORDER = ['fetch', 'scan', 'governance', 'interpret', 'trace', 'risk', 'guidance', 'questions']

export const STAGE_LABEL = {
  fetch: 'Fetch',
  scan: 'Scan',
  governance: 'Governance',
  interpret: 'LLM interpretation',
  trace: 'Traceability',
  risk: 'Risk ranking',
  guidance: 'Fix guidance',
  questions: 'Probe questions (mock Tutor)',
}

// Tones are those of shared/components/Badge.jsx: neutral | primary | success | warning | danger.
export function stageTone(status) {
  return { completed: 'success', partial: 'warning', skipped: 'warning', failed: 'danger' }[status] ?? 'neutral'
}

export function toolTone(status) {
  return { succeeded: 'success', not_applicable: 'neutral', unavailable: 'warning', failed: 'danger', timed_out: 'danger' }[status] ?? 'neutral'
}

export const TOOL_STATUS_LABEL = {
  succeeded: 'succeeded',
  failed: 'failed',
  timed_out: 'timed out',
  unavailable: 'unavailable',
  not_applicable: 'not applicable',
}

export function coverageTone(level) {
  return { FULL: 'success', REDUCED: 'warning', NONE: 'danger', 'NOTHING TO SCAN': 'neutral' }[level] ?? 'neutral'
}

export function statusTone(status) {
  return { confirmed: 'danger', dismissed: 'neutral', uncertain: 'warning', 'not interpreted': 'warning' }[status] ?? 'neutral'
}

export function toolStatusLabel(status) {
  return TOOL_STATUS_LABEL[status] ?? String(status ?? 'unknown')
}

export const CHECKOUT_LABEL = {
  'clone-tempdir': 'Cloned into a temporary folder (read-only use), deleted when the run ended',
  'docker-mount-ro': 'Mounted read-only in a container',
  'local-folder': 'A local folder, opened in place and only read',
  unknown: 'Not recorded by this run',
}

export function checkoutLabel(checkout) {
  if (!checkout) return CHECKOUT_LABEL.unknown
  return CHECKOUT_LABEL[checkout.kind] ?? CHECKOUT_LABEL.unknown
}

export const TRIGGER_LABEL = { manual: 'Manual', push: 'Push', merged_pr: 'Merged pull request' }
export const SCAN_TYPE_LABEL = { full: 'Full scan', 'reused-scan': 'Saved scan reused (nothing scanned now)' }

export function triggerLabel(trigger) {
  return TRIGGER_LABEL[trigger] ?? 'Not recorded'
}

export function scanTypeLabel(type) {
  return SCAN_TYPE_LABEL[type] ?? 'Not recorded'
}

export function shortSha(sha) {
  return sha ? String(sha).slice(0, 7) : null
}

// "2026-10-21T09:30:00Z" -> "21 Oct 2026, 09:30 UTC". Anything else is shown as it is (never invented).
export function formatWhen(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(iso ?? '')
  if (!m) return iso ?? 'Not recorded'
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  return `${Number(m[3])} ${months[Number(m[2]) - 1]} ${m[1]}, ${m[4]}:${m[5]} UTC`
}

export function totalOf(row) {
  return Object.values(row ?? {}).reduce((sum, n) => sum + (Number(n) || 0), 0)
}

// What "0 findings" in a category really means, given how well the category was covered.
export function categoryState(coverage, row) {
  const level = coverage?.level ?? 'NONE'
  const total = totalOf(row)
  if (level === 'NOTHING TO SCAN') return { tone: 'neutral', text: 'Nothing in this project for these tools to scan.' }
  if (level === 'NONE') {
    return { tone: 'danger', text: total ? 'Not checked by the tools; the findings shown come from elsewhere.' : 'Not checked: 0 findings here means nothing.' }
  }
  if (level === 'REDUCED') return { tone: 'warning', text: total ? 'Checked with reduced coverage.' : 'Reduced coverage: 0 findings does not mean clean.' }
  return { tone: total ? 'danger' : 'success', text: total ? `${total} finding${total === 1 ? '' : 's'} reported.` : 'Full coverage and no findings.' }
}

// The tool runs that did not do their job (a failed or missing check is not a "clean" check).
export function problemRuns(toolRuns) {
  return (toolRuns ?? []).filter((r) => !['succeeded', 'not_applicable'].includes(r.status))
}

export function headline(run) {
  return run?.complete ? 'COMPLETE' : 'INCOMPLETE'
}

export function llmFacts(llm) {
  if (!llm) return []
  return [
    ['Model', llm.model ?? 'none (the LLM stages did not run)'],
    ['Temperature', llm.temperature ?? 'not recorded'],
    ['Seed', llm.seed ?? 'not recorded'],
    ['Interpreter prompt', llm.interpreter_prompt ?? 'not recorded'],
    ['Link prompt', llm.trace_prompt ?? 'not recorded'],
    ['Risk ranking version', llm.risk_version ?? 'not recorded'],
    ['Comprehension threshold', llm.threshold ?? 'not recorded'],
  ]
}

// One line to tell runs apart in the picker.
export function runLabel(run) {
  return `${formatWhen(run.started_at)} · ${triggerLabel(run.trigger)} · ${run.repo ?? 'unknown repository'}${run.complete ? '' : ' · incomplete'}`
}

// The run shown when none is chosen: the newest complete run, else the newest run. `runs` is newest first (as the API lists them).
export function defaultRunId(runs) {
  const list = runs ?? []
  return (list.find((r) => r.complete) ?? list[0])?.run_id ?? null
}

export const SECRET_LINE_NOTE = 'Code line hidden for secrets'

// Findings of one vulnerability type, optionally one status, optionally only the viewer's ("mine").
export function filterFindings(findings, { category, status, mine } = {}) {
  return (findings ?? []).filter((f) => (!category || f.category === category) && (!status || f.status === status) && (!mine || f.mine))
}

// {V1: {confirmed, dismissed, uncertain, 'not interpreted'}, ...} for a list of findings (used for the "mine" counts).
export function countByCategory(findings) {
  const out = Object.fromEntries(CATEGORIES.map((c) => [c.id, { confirmed: 0, dismissed: 0, uncertain: 0, 'not interpreted': 0 }]))
  for (const f of findings ?? []) {
    const row = (out[f.category] ??= { confirmed: 0, dismissed: 0, uncertain: 0, 'not interpreted': 0 })
    row[f.status in row ? f.status : 'uncertain'] += 1
  }
  return out
}

export function whereLabel(f) {
  if (f.file_path) return f.line ? `${f.file_path}:${f.line}` : f.file_path
  return f.package ?? 'not located'
}

// The factors of a risk score add up to the score: this is the sum the page shows next to it.
export function riskTotal(breakdown) {
  return Math.round((breakdown ?? []).reduce((sum, b) => sum + (Number(b.contribution) || 0), 0) * 10) / 10
}

export function referenceLabel(url) {
  if (/cheatsheetseries\.owasp\.org/.test(url)) return 'OWASP Cheat Sheet'
  const cwe = /cwe\.mitre\.org\/data\/definitions\/(\d+)/.exec(url)
  if (cwe) return `CWE-${cwe[1]}`
  return url.replace(/^https?:\/\//, '').split('/')[0]
}

export const LINK_STATUS_NOTE = {
  verified: 'Verified: a simple rule supports it (commit message names it, or the file appears in one story or task).',
  candidate: 'Candidate: proposed, not verified. Treat it as a suggestion.',
}

export function linkTone(status) {
  return status === 'verified' ? 'success' : 'warning'
}

// What "request review" copies: enough for a lecturer to find the finding again. No code, no names.
export function reviewRequestText({ team, run, finding }) {
  return [
    `Review request: Security Assistant finding ${finding.group_id}`,
    `Team: ${team}`,
    `Run: ${run}`,
    `Type: ${finding.category}, ${finding.rule_id} (${finding.tool})`,
    `Where: ${whereLabel(finding)}`,
    `Status in the run: ${finding.status}`,
    'Please look at my understanding of this finding.',
  ].join('\n')
}

export function probeSummary(probe) {
  if (!probe) return 'No probe question was made for this finding.'
  if (!probe.attempts) return `Not asked (${probe.decision}).`
  return `${probe.decision} after ${probe.attempts} question${probe.attempts === 1 ? '' : 's'}`
}

// The tab to open when none is in the address: the first type that has findings, else V1.
export function firstCategoryWithFindings(counts) {
  return CATEGORIES.find((c) => totalOf(counts?.[c.id]) > 0)?.id ?? 'V1'
}

export const LEARNING_TITLE = 'Comprehension check results (mock)'
export const MOCK_NOTICE =
  'The Tutor is a mock: no student answered anything and nothing was graded. Every score here is simulated to show how the flow works. None of it is an assessment of anyone.'

// The summary the page shows for the checks it lists (the same rule as the Core API). Every check ends closed or escalated: the question
// agent has no other end, so there is no "still open" count.
export function learningSummary(items) {
  const list = items ?? []
  return {
    concepts: new Set(list.map((i) => i.concept_id).filter(Boolean)).size,
    closed: list.filter((i) => i.decision === 'closed').length,
    escalated: list.filter((i) => i.decision === 'escalated').length,
    attempts: list.reduce((sum, i) => sum + (i.attempts?.length ?? 0), 0),
  }
}

export function decisionTone(decision) {
  return { closed: 'success', escalated: 'warning' }[decision] ?? 'neutral'
}

export function decisionLabel(decision) {
  return { closed: 'closed', escalated: 'escalated to the lecturer' }[decision] ?? String(decision ?? 'unknown')
}

// 0..100 for a bar; a score outside 0..1 is clamped, a missing one is 0.
export function scorePercent(score) {
  const n = Number(score)
  return Number.isFinite(n) ? Math.round(Math.min(1, Math.max(0, n)) * 100) : 0
}

// One row per concept (the kind of fix the finding needs): how many checks, how many closed or escalated.
export function conceptRows(items) {
  const rows = new Map()
  for (const i of items ?? []) {
    const key = i.concept_id ?? 'none'
    const row = rows.get(key) ?? { id: key, concept: i.concept ?? 'No standard concept', checks: 0, closed: 0, escalated: 0, attempts: 0 }
    row.checks += 1
    if (i.decision in row) row[i.decision] += 1
    row.attempts += i.attempts?.length ?? 0
    rows.set(key, row)
  }
  return [...rows.values()].sort((a, b) => a.concept.localeCompare(b.concept))
}
