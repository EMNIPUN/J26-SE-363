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
