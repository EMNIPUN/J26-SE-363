// Pure helpers for the Agents page: the decision trails, the governance panel, the audit table and the workflow diagram's colours.

export const INDICATOR_NOTE = 'indicator, not proof'

// The three agents in the order of the flow. The trail keys are the names the run uses.
export const AGENTS = [
  { key: 'Analysis Orchestrator', title: 'Analysis Orchestrator', goal: 'A findings report where every category is covered and no dependency gap is open.' },
  { key: 'Question Generation', title: 'Question Agent', goal: 'Each confirmed finding is closed by the (mock) Tutor, or escalated to the lecturer after the follow-ups are used.' },
  { key: 'Governance', title: 'Governance', goal: 'Nothing that must not leave the machine is sent, and a repository that talks to the model gets more scrutiny.' },
]

export function trailAgents(decisionTrail) {
  return AGENTS.map((a) => ({ ...a, entries: decisionTrail?.[a.key] ?? [] }))
}

export function rejectedCount(entries) {
  return (entries ?? []).filter((e) => e.rejected).length
}

// "The policy 'rogue' proposed 'shell:rm -rf /': not one of the valid options. The rules decided instead."
export function describeRejected(rejected) {
  if (!rejected) return ''
  return `The policy "${rejected.policy}" proposed "${rejected.proposed}": ${rejected.problem}. The rules decided instead.`
}

export function optionsLabel(options) {
  return (options ?? []).join(' | ') || 'none'
}

export const SCRUTINY_TONE = { normal: 'success', elevated: 'warning', high: 'danger' }

export function scrutinyTone(level) {
  return SCRUTINY_TONE[level] ?? 'neutral'
}

// What the level means in a sentence, with the thresholds the run used.
export function scrutinyMeaning(scrutiny) {
  if (!scrutiny) return 'Not recorded.'
  const { level, score, elevated_at: elevated, high_at: high } = scrutiny
  if (level === 'high') return `Score ${score} reached ${high}: the run is flagged for human review and every call gets a second, stricter check.`
  if (level === 'elevated') return `Score ${score} reached ${elevated}: every later call gets a second, stricter check.`
  return `Score ${score}: below ${elevated}, so calls get the normal check.`
}

export function indicatorRows(indicators) {
  return (indicators ?? []).map((i) => ({ kind: i.kind, source: i.source, pattern: i.pattern, count: i.count }))
}

// ---- audit lines ----------------------------------------------------------------------------------------------------------------------

const HASH_KEY = /(sha256|hash)$/i

// A line of audit.jsonl as a few readable facts: scalars as they are, hashes cut to 12 characters, nested values only by their size.
// The log holds fingerprints, ids and counts, never the text of a prompt, so there is nothing else to show.
export function auditFacts(line) {
  const facts = []
  for (const [name, value] of Object.entries(line)) {
    if (name === 'seq' || name === 'event') continue
    if (value === null || value === undefined) continue
    if (typeof value === 'string' && HASH_KEY.test(name)) facts.push({ name, value: `${value.slice(0, 12)}…`, hash: true })
    else if (Array.isArray(value)) facts.push({ name, value: `${value.length} item${value.length === 1 ? '' : 's'}` })
    else if (typeof value === 'object') facts.push({ name, value: `${Object.keys(value).length} field${Object.keys(value).length === 1 ? '' : 's'}` })
    else facts.push({ name, value: String(value) })
  }
  return facts
}

export function pageOf(lines, page, size = 25) {
  const pages = Math.max(1, Math.ceil((lines?.length ?? 0) / size))
  const current = Math.min(Math.max(0, page), pages - 1)
  return { rows: (lines ?? []).slice(current * size, (current + 1) * size), page: current, pages, total: lines?.length ?? 0 }
}

export function canSeeAudit(role) {
  return role === 'instructor' || role === 'admin'
}

// ---- the diagram ---------------------------------------------------------------------------------------------------------------------

// Which graph sits inside which node of the workflow: the scan runs the orchestrator, the questions stage runs the question agent, and every
// LLM call (interpret, trace) passes the governance gate.
export const NESTED = { scan: 'orchestrator', questions: 'question', interpret: 'governance', trace: 'governance' }

export const GRAPH_TITLE = { workflow: 'Whole workflow', orchestrator: 'Analysis Orchestrator', question: 'Question Agent', governance: 'Governance gate' }

// Node colour classes by status. A skipped or not-run node is dashed so it never looks like a completed one.
const NODE = {
  completed: ['fill-emerald-50 stroke-emerald-500 dark:fill-emerald-950/40', 'completed'],
  ran: ['fill-emerald-50 stroke-emerald-500 dark:fill-emerald-950/40', 'ran'],
  partial: ['fill-amber-50 stroke-amber-500 dark:fill-amber-950/40', 'partial'],
  failed: ['fill-red-50 stroke-red-500 dark:fill-red-950/40', 'failed'],
  skipped: ['fill-amber-50 stroke-amber-500 dark:fill-amber-950/40 [stroke-dasharray:4_3]', 'skipped'],
  'not run': ['fill-muted stroke-border [stroke-dasharray:4_3]', 'not run'],
}

export function nodeStyle(status) {
  return NODE[status] ?? ['fill-card stroke-border', status ?? '']
}

export function nodeLabel(id, labels = {}) {
  if (id === '__start__') return 'start'
  if (id === '__end__') return 'end'
  return labels[id] ?? id.replace(/_/g, ' ')
}

export const DIAGRAM_LABELS = {
  fetch: 'Fetch', scan: 'Scan', governance: 'Governance', interpret: 'LLM interpretation', trace: 'Traceability', risk: 'Risk ranking',
  guidance: 'Fix guidance', questions: 'Questions (mock Tutor)', report: 'Report',
  plan: 'Plan', execute_action: 'Execute action', update_state: 'Update state', stop: 'Stop',
  ask: 'Ask', score: 'Score', follow_up: 'Follow up', close: 'Close', escalate: 'Escalate',
  check_input: 'Check input', raise_scrutiny: 'Raise scrutiny', allow: 'Allow', block: 'Block',
}
