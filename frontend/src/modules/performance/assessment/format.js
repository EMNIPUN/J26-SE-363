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
  { id: 'code_ownership', label: 'Code Ownership', question: 'Does the student understand their code?', measures: 'A question about a function the student wrote, rated against what the code does.', perSprint: false, why: 'It is measured by questions at the end of a sprint and answered by hand, so one sprint is not comparable with the next.' },
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
  if ((f.status === 'completed' || f.state === 'scored') && f.score != null) return { kind: 'scored', label: f.provisional ? 'To date' : 'Scored' }
  if (f.status === 'pending' || f.state === 'pending') return { kind: 'pending', label: 'Waiting for the answer' }
  if (f.status === 'not_available' || f.state === 'unavailable') return { kind: 'unavailable', label: 'Cannot be measured' }
  if (f.status === 'fallback' || f.state === 'failed') return { kind: 'failed', label: 'Did not run' }
  return { kind: 'missing', label: f.status || f.state || 'Not run' }
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

const WORD = { high: 'a strong contribution', medium: 'a moderate contribution', low: 'a weak contribution' }
const PRIORITY = ['strong', 'weak', 'flag', 'out', 'override', 'range', 'pattern', 'provisional']
const LEAD = { strong: 'Biggest strength', weak: 'Held back by', flag: 'To check', out: 'Left out', override: 'Lecturer mark', range: 'Confidence', pattern: 'Working pattern', provisional: 'Still running' }

/**
 * Why this student got this mark, short enough to scan: a headline, the three things that matter most (`key`), and the rest (`more`).
 * Each line is `{ kind, lead, text }`: a bold lead word and one short sentence. Everything comes from the result itself; nothing is guessed.
 */
export function explainMark(result, weights) {
  if (!result) return { headline: '', key: [], more: [] }
  const j = result.justification || {}
  const mark = result.effective_mark ?? result.mark
  const parts = contributions(result.factors, weights)
  const total = parts.reduce((a, p) => a + p.points, 0)
  const lines = []
  const add = (kind, text) => lines.push({ kind, lead: LEAD[kind], text })

  const top = [...parts].sort((a, b) => b.points - a.points)[0]
  if (top) add('strong', `${top.label}: ${Math.round(top.points)} of ${Math.round(total)} points (score ${score100(top.score)})`)
  const weakest = [...parts].sort((a, b) => a.score - b.score)[0]
  if (weakest && parts.length > 1 && weakest.score < 0.67) add('weak', `${weakest.label}: score ${score100(weakest.score)}, ${weakest.score < 0.34 ? 'low' : 'middling'}`)

  const scoredIds = new Set(parts.map((p) => p.id))
  const out = FACTORS.filter((f) => !scoredIds.has(f.id))
  if (out.length) {
    const why = (f) => ((j.factors?.[f.id]?.reasons || []).filter(Boolean)[0] || factorState(result.factors?.[f.id]).label).replace(/\.$/, '')
    add('out', `${out.map((f) => f.label).join(', ')}. Their weight goes to the other factors${out.length === 1 ? ` (${why(out[0]).toLowerCase()})` : ''}`)
  }

  const flags = (j.flags || []).length
  if (flags) add('flag', `${flags} point${flags === 1 ? '' : 's'} need a person to look (see Points to check)`)

  const pattern = result.factors?.behavioral_pattern
  if (pattern?.persona) add('pattern', pattern.applied && pattern.modifier != null && pattern.modifier !== 1 ? `${pattern.persona}: adjusted the total by ${Number(pattern.modifier).toFixed(2)}` : `${pattern.persona}. Counts only once the sprint is final`)
  if (result.override?.mark != null) add('override', `Set to ${markText(result.override.mark)}; the agent predicted ${markText(result.mark)}`)

  const interval = result.mark_interval
  if (interval) add('range', `Likely ${rangeText(interval)}. ${interval[1] - interval[0] >= 30 ? 'Wide: some evidence is missing' : 'Narrow: the evidence is steady'}`)
  if (parts.some((p) => result.factors[p.id]?.provisional)) add('provisional', 'Scores are to date; the mark can still move')

  lines.sort((a, b) => PRIORITY.indexOf(a.kind) - PRIORITY.indexOf(b.kind))
  return { headline: mark == null ? 'No mark yet' : `${markText(mark)} out of 100: ${WORD[markBand(mark)] || ''}`.trim(), key: lines.slice(0, 3), more: lines.slice(3) }
}

/** One sentence for a factor card: what its score means and what it did to the mark. */
export function explainFactor(meta, result, part) {
  const state = factorState(result)
  if (state.kind === 'scored') {
    const b = band(result.score)
    const base = `Scored ${score100(result.score)} out of 100, which is ${b}.`
    return part ? `${base} It counts for ${Math.round(part.weight * 100)}% of the mark and added ${part.points.toFixed(1)} points.` : base
  }
  if (state.kind === 'pending') return 'Waiting for the student\'s answer. The mark is provisional until it arrives.'
  return `${state.label}. It is left out of the mark, and its weight is shared among the other factors.`
}

/** The questions of a student's code check as a list, whether the API sent one question or several. */
export function questionsOf(quiz) {
  if (!quiz) return []
  const list = Array.isArray(quiz.questions) ? quiz.questions : Array.isArray(quiz.items) ? quiz.items : [quiz]
  return list.map((q, i) => ({ ...q, n: q.n ?? i + 1 }))
}

/** How the code check went, in numbers. */
export function quizSummary(questions) {
  const answered = questions.filter((q) => q.status === 'answered')
  const rated = answered.filter((q) => q.rating != null)
  return {
    total: questions.length,
    answered: answered.length,
    open: questions.filter((q) => q.status === 'open' || q.status === 'extended').length,
    expired: questions.filter((q) => q.status === 'expired').length,
    average: rated.length ? rated.reduce((a, q) => a + Number(q.rating), 0) / rated.length : null,
  }
}

/** The factors a student can be followed on from one sprint to the next. Code Ownership cannot: it is a few questions at the end of each sprint. */
export const TRACKED = FACTORS.filter((f) => f.perSprint !== false)

/** The team average of each factor in a set of results, 0 to 1 (null when nobody was scored). */
export function teamAverage(rows) {
  return Object.fromEntries(FACTORS.map((f) => {
    const scores = (rows || []).map((r) => r.factors?.[f.id]).filter((x) => x?.status === 'completed' && x.score != null).map((x) => x.score)
    return [f.id, scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null]
  }))
}

/** The points of a radar chart: one spoke per factor, the student's score and the team average (0 to 100). A factor with no score sits at 0 and is marked as not measured. */
export function radarData(result, average) {
  return FACTORS.map((f) => {
    const state = factorState(result?.factors?.[f.id])
    const avg = average?.[f.id]
    return { id: f.id, factor: f.label, short: f.label.replace('Requirement Fulfillment', 'Requirements').replace('Task Complexity', 'Complexity').replace('Code Ownership', 'Ownership'), score: state.kind === 'scored' ? Math.round(result.factors[f.id].score * 100) : 0, average: avg == null ? null : Math.round(avg * 100), measured: state.kind === 'scored', state: state.label }
  })
}

/**
 * Sprint by sprint: for each sprint, the student's mark and each factor's score, and how much a factor moved since the last sprint in which it was scored.
 * `sprints` is oldest first; `resultOf(id)` is that sprint's result for the student (null when there is none, undefined while it loads).
 * Factors that cannot be followed from sprint to sprint (Code Ownership) come back with `tracked: false` and the reason, and no cells.
 */
export function factorHistory(sprints, resultOf) {
  const results = sprints.map((s) => ({ id: s.id, result: resultOf(s.id) }))
  const marks = results.map(({ id, result }) => ({ sprint: id, loading: result === undefined, mark: result ? (result.effective_mark ?? result.mark) : null }))
  const rows = FACTORS.map((f) => {
    if (f.perSprint === false) return { id: f.id, label: f.label, tracked: false, why: f.why, cells: [] }
    let last = null
    const cells = results.map(({ id, result }) => {
      if (result === undefined) return { sprint: id, kind: 'loading', score: null, delta: null }
      const state = factorState(result?.factors?.[f.id])
      const score = state.kind === 'scored' ? Math.round(result.factors[f.id].score * 100) : null
      const delta = score != null && last != null ? score - last : null
      if (score != null) last = score
      return { sprint: id, kind: result ? state.kind : 'missing', score, delta, label: state.label }
    })
    return { id: f.id, label: f.label, tracked: true, cells }
  })
  return { marks, rows, sprints: sprints.map((s) => s.id), enough: results.filter((r) => r.result).length >= 2 }
}

const EVIDENCE_KINDS = [
  ['commit', /\bcommits?\b/i],
  ['task', /\btasks?\b|\bstory points?\b|\bacceptance\b|\bsubtasks?\b/i],
  ['code', /\bfiles?\b|\blines?\b|\bfunction\b|\bsource\b/i],
  ['review', /\breview|\bcomment|\bpull request|\bPRs?\b/i],
]

/**
 * The evidence behind a mark, factor by factor: the lines each factor says its score rests on (counted commits, tasks and criteria, reviews, files), each tagged with what kind of evidence it is.
 * A factor with nothing to show is left out.
 */
export function evidenceOf(result) {
  if (!result) return []
  const blocks = result?.justification?.factors || {}
  return FACTORS.map((f) => {
    const lines = (blocks[f.id]?.reasons || []).filter(Boolean).map((text) => ({ text, kind: (EVIDENCE_KINDS.find(([, re]) => re.test(text)) || ['note'])[0] }))
    return { id: f.id, label: f.label, scored: factorState(result.factors?.[f.id]).kind === 'scored', lines }
  }).filter((g) => g.lines.length > 0)
}

/** The agent's own short explanation of the mark: the friendly summary when there is one, else the first two sentences of the summary. */
export function briefOf(result) {
  const j = result?.justification || {}
  if (j.friendly_summary) return j.friendly_summary
  return String(j.summary || '').split(/(?<=\.)\s+/).slice(0, 2).join(' ')
}
