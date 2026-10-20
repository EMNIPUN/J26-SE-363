/**
 * Words, bands and colours for the assessment screens, in one place so every page says the same thing.
 * Wording follows the proposal: the score supports the lecturer's decision, so every number comes with what it means.
 */

export const FACTORS = [
  { id: 'effort', label: 'Effort', question: 'How much real work was done?', measures: 'Commits that carry code, net lines of real code, files and tasks finished. Comments, blank lines, formatting and generated files do not count.' },
  { id: 'consistency', label: 'Consistency', question: 'How steadily did the student work?', measures: 'How evenly the work is spread over the sprint, and whether it all came at the last minute.' },
  { id: 'requirement_fulfillment', label: 'Requirement Fulfillment', question: 'Does the code meet the tasks?', measures: "Whether the student's own code changes meet the acceptance criteria of the tasks assigned to them." },
  { id: 'collaboration', label: 'Collaboration', question: "Does the student help the team's work?", measures: "Substantive reviews and discussion of teammates' pull requests." },
  { id: 'task_complexity', label: 'Task Complexity', question: 'How demanding were the tasks?', measures: 'How hard the assigned tasks were, from story points and the size of the code they touch.' },
  { id: 'code_ownership', label: 'Code Ownership', question: 'Does the student understand their code?', measures: 'A question about a function the student wrote, rated against what the code does.' },
]

export const FACTOR_LABEL = Object.fromEntries([...FACTORS.map((f) => [f.id, f.label]), ['behavioral_pattern', 'Working pattern']])

export const RESULT_STATUS = {
  final: { label: 'Final', tone: 'success', help: 'The sprint is over and every part of the assessment is in.' },
  provisional: { label: 'Provisional', tone: 'primary', help: 'The sprint is still running, or a part of the assessment (usually the code question) is still to come. It can change.' },
  pending_review: { label: 'Needs your review', tone: 'warning', help: 'The agent found something a person should look at before this mark is relied on.' },
  under_review: { label: 'Being checked', tone: 'warning', help: 'Your lecturer is checking this result before it is shown.' },
}

export const RUN_STATUS = {
  queued: { label: 'Queued', tone: 'neutral' },
  running: { label: 'Running', tone: 'primary' },
  waiting_human: { label: 'Waiting for you', tone: 'warning' },
  succeeded: { label: 'Finished', tone: 'success' },
  failed: { label: 'Failed', tone: 'danger' },
  cancelled: { label: 'Cancelled', tone: 'neutral' },
}

/** low, medium or high: the same cut points the justification uses. */
export function band(score) {
  if (score == null) return null
  return score < 0.34 ? 'low' : score < 0.67 ? 'medium' : 'high'
}

export const BAND_STYLE = {
  low: { text: 'text-rose-600 dark:text-rose-400', bar: 'bg-rose-500', soft: 'bg-rose-50 dark:bg-rose-950/40', ring: '#f43f5e' },
  medium: { text: 'text-amber-600 dark:text-amber-400', bar: 'bg-amber-500', soft: 'bg-amber-50 dark:bg-amber-950/40', ring: '#f59e0b' },
  high: { text: 'text-emerald-600 dark:text-emerald-400', bar: 'bg-emerald-500', soft: 'bg-emerald-50 dark:bg-emerald-950/40', ring: '#10b981' },
  none: { text: 'text-muted-foreground', bar: 'bg-muted-foreground/40', soft: 'bg-muted', ring: '#94a3b8' },
}

export const markBand = (mark) => (mark == null ? null : band(mark / 100))
export const styleOf = (b) => BAND_STYLE[b] || BAND_STYLE.none

/** What a factor result is called when it has no score. */
export function factorState(f) {
  if (!f) return { kind: 'missing', label: 'Not run' }
  if (f.status === 'completed' && f.score != null) return { kind: 'scored', label: f.provisional ? 'To date' : 'Scored' }
  if (f.status === 'pending') return { kind: 'pending', label: 'Waiting for the answer' }
  if (f.status === 'not_available') return { kind: 'unavailable', label: 'Cannot be measured' }
  if (f.status === 'fallback') return { kind: 'failed', label: 'Did not run' }
  return { kind: 'missing', label: f.status || 'Not run' }
}

export const score100 = (s) => (s == null ? '-' : String(Math.round(s * 100)))
export const markText = (m) => (m == null ? 'n/a' : String(Math.round(m)))
export const rangeText = (r) => (r ? `${Math.round(r[0])} to ${Math.round(r[1])}` : '')

/**
 * What each factor contributed to the mark: weight x score, on the factors that exist (the weight of a missing one is shared out).
 * `weights` come from the run's method; the pattern adjustment is applied afterwards, as in the agent.
 */
export function contributions(factors, weights) {
  const have = Object.entries(weights || {}).filter(([k]) => factors?.[k]?.status === 'completed' && factors[k].score != null)
  const total = have.reduce((a, [, w]) => a + w, 0)
  if (!total) return []
  return have.map(([k, w]) => ({ id: k, label: FACTOR_LABEL[k] || k, weight: w / total, score: factors[k].score, points: (100 * w * factors[k].score) / total }))
}

export function duration(seconds) {
  if (seconds == null) return ''
  const s = Math.round(seconds)
  if (s < 60) return `${s} s`
  const m = Math.floor(s / 60)
  return m < 60 ? `${m} min ${s % 60 ? `${s % 60} s` : ''}`.trim() : `${Math.floor(m / 60)} h ${m % 60} min`
}

export function when(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export function initials(name) {
  return String(name || '?').split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join('')
}

/** The cohort numbers shown above a results table. */
export function summarize(rows) {
  const marks = rows.map((r) => r.effective_mark).filter((m) => m != null)
  return {
    students: rows.length,
    mean: marks.length ? marks.reduce((a, b) => a + b, 0) / marks.length : null,
    lowest: marks.length ? Math.min(...marks) : null,
    highest: marks.length ? Math.max(...marks) : null,
    needReview: rows.filter((r) => r.status === 'pending_review').length,
    provisional: rows.filter((r) => r.status === 'provisional').length,
    waitingForAnswer: rows.filter((r) => r.factors?.code_ownership?.status === 'pending').length,
    flags: rows.reduce((a, r) => a + (r.justification?.flags?.length || 0), 0),
  }
}
