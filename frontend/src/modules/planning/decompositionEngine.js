// Mock implementation of the Decomposition Agent's tool suite (Table 3.4):
// coverage_analyzer (SBERT-style similarity), invest_validator (rule-based +
// LLM), pattern_retriever (RAG), decomposition_scorer (LLM). The agent
// evaluates what the student already wrote — it never generates or rewrites
// stories. Everything here is deterministic (no real ML backend yet), but the
// tool-selection sequence is genuinely adaptive: pattern_retriever only fires
// when there's a real gap to illustrate.
import { findAmbiguousPhrases } from './utils.js'

export const INVEST_CRITERIA = [
  { key: 'independent', label: 'Independent' },
  { key: 'negotiable', label: 'Negotiable' },
  { key: 'valuable', label: 'Valuable' },
  { key: 'estimable', label: 'Estimable' },
  { key: 'small', label: 'Small' },
  { key: 'testable', label: 'Testable' },
]

const COVERAGE_HIGH_THRESHOLD = 0.8

const ROLE_GOAL_RE = /as\s+(a|an|the)\s+.+i\s+want/i
const BENEFIT_RE = /(so\s+that|in\s+order\s+to)\s+\S+/i
const DEPENDENCY_RE = /\b(after|once|depends on|requires that|only once|prerequisite)\b/i
const IMPLEMENTATION_RE = /\b(api|endpoint|database|sql|react|button color|css|json payload|http)\b/i

// invest_validator — rule-based + LLM. Runs once per story, independent of
// the others; called on every analysis regardless of coverage, since knowing
// whether the *existing* stories are well-formed is cheap and always useful.
export function runInvestValidator(story) {
  const title = (story.title || '').trim()
  const ac = (story.acceptanceCriteria || '').trim()
  const combined = `${title} ${ac}`

  const independent = DEPENDENCY_RE.test(combined)
    ? { pass: false, note: 'Wording implies this depends on another story finishing first ("after", "once", "depends on").' }
    : { pass: true, note: 'No hard dependency language found — this can plausibly be built on its own.' }

  const negotiable = IMPLEMENTATION_RE.test(combined)
    ? { pass: false, note: 'Locks in an implementation detail (a specific API/tech term) instead of describing the outcome.' }
    : { pass: true, note: 'Describes the outcome, not a fixed implementation.' }

  const valuable = ROLE_GOAL_RE.test(title) && BENEFIT_RE.test(combined)
    ? { pass: true, note: 'States who wants this and why.' }
    : { pass: false, note: 'Missing a clear role/goal or a stated benefit ("so that …").' }

  const ambiguousMatches = findAmbiguousPhrases(combined)
  const ambiguousPhrases = [...new Set(ambiguousMatches.map((m) => m.phrase))]
  const estimable = ambiguousPhrases.length > 0
    ? { pass: false, note: `Vague wording makes this hard to size: ${ambiguousPhrases.map((p) => `"${p}"`).join(', ')}.` }
    : { pass: true, note: 'Concrete enough to size with reasonable confidence.' }

  const small = title.length > 140 || /\band\b.*\band\b/i.test(title)
    ? { pass: false, note: 'Reads like more than one concern bundled together — consider splitting.' }
    : { pass: true, note: 'Scoped to a single, shippable unit of work.' }

  const testable = ac.length >= 20
    ? { pass: true, note: 'Acceptance criteria gives a concrete condition to verify against.' }
    : { pass: false, note: 'Acceptance criteria is missing or too brief to verify against.' }

  const criteria = { independent, negotiable, valuable, estimable, small, testable }
  const overallPass = Object.values(criteria).every((c) => c.pass)
  return { ...criteria, overallPass }
}

// coverage_analyzer — SBERT-style similarity between the requirement and the
// student's full story set. Aspects are the topics a complete decomposition
// of that requirement ought to touch; keyword hits stand in for the
// embedding-similarity match a real SBERT model would compute.
export const COVERAGE_ASPECTS = {
  'REQ-101': [
    { id: 'intake', label: 'Free-text submission', keywords: ['submit', 'free text', 'free-form', 'intake', 'type', 'enter'] },
    { id: 'parse', label: 'Parsing into structured fields', keywords: ['pars', 'structur', 'extract', 'schema field'] },
    { id: 'confirm', label: 'Confirmation of receipt', keywords: ['confirm', 'acknowledge', 'receipt', 'toast'] },
  ],
  'REQ-102': [
    { id: 'detect', label: 'Detect at-risk groups', keywords: ['at-risk', 'at risk', 'detect', 'drop', 'threshold'] },
    { id: 'digest', label: 'Compose weekly digest', keywords: ['digest', 'compose', 'summar', 'weekly'] },
    { id: 'deliver', label: 'Deliver to supervisor', keywords: ['deliver', 'send', 'email', 'notif'] },
  ],
  'REQ-103': [
    { id: 'perf', label: 'Response-time performance', keywords: ['second', 'load', 'render', 'perform', 'speed'] },
    { id: 'usability', label: 'First-time usability', keywords: ['first-time', 'without help', 'usab', 'onboard'] },
  ],
  'REQ-104': [
    { id: 'breakdown', label: 'Generate sub-task breakdown', keywords: ['sub-task', 'subtask', 'breakdown', 'decompos'] },
    { id: 'scopelock', label: 'Lock scope after decomposition', keywords: ['lock', 'scope-lock', 'prevent', 'further edit'] },
  ],
  'REQ-105': [
    { id: 'point', label: 'Compute point estimate', keywords: ['point estimate', 'story point', 'estimate'] },
    { id: 'interval', label: 'Compute confidence interval', keywords: ['confidence', 'interval', 'range'] },
    { id: 'calibrate', label: 'Calibrate against history', keywords: ['histor', 'calibrat', 'similar'] },
  ],
  'REQ-106': [
    { id: 'cache', label: 'Cache results for offline viewing', keywords: ['cache', 'offline', 'stored locally'] },
    { id: 'degrade', label: 'Graceful degradation without connectivity', keywords: ['degrad', 'connectivity', 'fallback', 'no network'] },
  ],
  'REQ-107': [
    { id: 'review', label: 'Instructor review UI', keywords: ['review', 'instructor', 'lecturer'] },
    { id: 'override', label: 'Override action', keywords: ['override', 'confirm', 'resolution'] },
    { id: 'log', label: 'Log override with justification', keywords: ['log', 'justif', 'audit', 'record'] },
  ],
  'REQ-108': [
    { id: 'scores', label: 'Compute six-dimension scores', keywords: ['dimension', 'score', 'six'] },
    { id: 'radar', label: 'Render radar chart', keywords: ['radar', 'chart', 'visualiz'] },
  ],
}

export function analyzeCoverage(requirement, stories) {
  const aspects = COVERAGE_ASPECTS[requirement.id] || []
  if (aspects.length === 0) {
    return { coverage: stories.length > 0 ? 1 : 0, covered: [], gaps: [] }
  }
  const haystack = stories.map((s) => `${s.title} ${s.acceptanceCriteria}`.toLowerCase())
  const covered = []
  const gaps = []
  for (const aspect of aspects) {
    const hit = haystack.some((text) => aspect.keywords.some((kw) => text.includes(kw.toLowerCase())))
    ;(hit ? covered : gaps).push(aspect)
  }
  return { coverage: covered.length / aspects.length, covered, gaps }
}

// pattern_retriever — RAG over a small canned "knowledge base" of prior
// decompositions. Only ever shown to the student when there's an actual gap
// or formedness issue to illustrate (the adaptive shortcut skips it otherwise).
export const PATTERN_EXAMPLES = [
  {
    id: 'profile-mgmt',
    title: 'User Profile Management',
    stories: ['View profile details', 'Edit profile details', 'Delete profile', 'Change password / security settings'],
  },
  {
    id: 'notif-prefs',
    title: 'Notification Preferences',
    stories: ['Enable/disable a notification channel', 'Set notification frequency', 'Preview a sample notification'],
  },
  {
    id: 'data-export',
    title: 'Data Export',
    stories: ['Request an export', 'Choose an export format', 'Receive a download link by email'],
  },
]

// decomposition_scorer — final LLM judgment combining coverage + INVEST into
// one score and a plain-language verdict.
export function computeDecompositionScore(coverage, investResults) {
  const results = Object.values(investResults)
  const investPassRate = results.length ? results.filter((r) => r.overallPass).length / results.length : 0
  const score = Math.round(coverage * 60 + investPassRate * 40)
  const verdict = coverage >= COVERAGE_HIGH_THRESHOLD && investPassRate === 1 ? 'Validated' : 'Needs Revision'

  let summary
  if (verdict === 'Validated') {
    summary = 'Coverage and story quality both look solid — ready to move forward.'
  } else if (coverage < COVERAGE_HIGH_THRESHOLD && investPassRate === 1) {
    summary = 'Your existing stories are individually well-formed, but the decomposition is incomplete.'
  } else if (coverage >= COVERAGE_HIGH_THRESHOLD && investPassRate < 1) {
    summary = 'Coverage looks complete, but at least one story needs to be better-formed first.'
  } else {
    summary = 'Both a coverage gap and story-formation issues need attention.'
  }
  return { score, verdict, summary }
}

// Orchestrates the full ReAct-style loop: reason -> execute_tool (repeated,
// adaptively) -> reflect -> finalize. Returns both the final result and the
// visible reasoning trace so the UI can show genuine iterative tool
// selection, not just a single opaque API call.
export function runDecompositionAnalysis(requirement, stories) {
  const trace = []
  let iter = 0

  iter += 1
  const { coverage, covered, gaps } = analyzeCoverage(requirement, stories)
  trace.push({
    iteration: iter,
    phase: 'tool',
    reasoning: 'Coverage is the cheapest, most informative check — comparing what the requirement asks for against the full set of stories first.',
    tool: 'coverage_analyzer',
    toolType: 'SBERT (similarity)',
    result: `Coverage ${Math.round(coverage * 100)}% — ${covered.length}/${covered.length + gaps.length} aspect(s) of the requirement are represented in your stories.`,
  })

  iter += 1
  const investResults = {}
  stories.forEach((s) => {
    investResults[s.id] = runInvestValidator(s)
  })
  const failingCount = Object.values(investResults).filter((r) => !r.overallPass).length
  trace.push({
    iteration: iter,
    phase: 'tool',
    reasoning:
      coverage < COVERAGE_HIGH_THRESHOLD
        ? `Coverage is only ${Math.round(coverage * 100)}% — before flagging the gap, checking whether your existing stories are at least well-formed on their own.`
        : 'Coverage looks strong — confirming each story still holds up individually before finishing.',
    tool: 'invest_validator',
    toolType: 'Rule-based + LLM',
    result:
      failingCount === 0
        ? `All ${stories.length} stor${stories.length === 1 ? 'y passes' : 'ies pass'} every INVEST criterion.`
        : `${failingCount}/${stories.length} stor${stories.length === 1 ? 'y needs' : 'ies need'} attention on at least one INVEST criterion.`,
  })

  const needsExamples = coverage < COVERAGE_HIGH_THRESHOLD || failingCount > 0
  let patternExamples = null
  iter += 1
  if (needsExamples) {
    patternExamples = PATTERN_EXAMPLES.slice(0, 2)
    trace.push({
      iteration: iter,
      phase: 'tool',
      reasoning: "There's a real gap to close (not just a formatting issue) — pulling similar decomposition examples so the feedback includes a concrete reference instead of vague advice.",
      tool: 'pattern_retriever',
      toolType: 'RAG (ChromaDB)',
      result: `Retrieved ${patternExamples.length} similar decomposition(s) from the knowledge base.`,
    })
  } else {
    trace.push({
      iteration: iter,
      phase: 'skip',
      reasoning: 'Coverage is high and every story passes INVEST — nothing to fix, so skipping the pattern lookup and going straight to a final score.',
      tool: null,
      toolType: 'adaptive skip',
      result: 'pattern_retriever skipped — no gap to illustrate.',
    })
  }

  iter += 1
  const { score, verdict, summary } = computeDecompositionScore(coverage, investResults)
  trace.push({
    iteration: iter,
    phase: 'tool',
    reasoning: 'Enough evidence gathered — computing an overall decomposition-quality judgment.',
    tool: 'decomposition_scorer',
    toolType: 'LLM',
    result: `Decomposition score ${score}/100 — ${verdict}.`,
  })

  const investAgrees = (verdict === 'Validated') === (coverage >= COVERAGE_HIGH_THRESHOLD && failingCount === 0)
  trace.push({
    iteration: iter + 1,
    phase: 'reflect',
    reasoning: "Reflect: does the coverage/INVEST evidence agree with the scorer's verdict?",
    tool: null,
    toolType: 'reflect',
    result: investAgrees ? 'Consistent — proceeding with this result.' : 'Inconsistent — flagging for a second pass.',
  })

  return {
    coverage,
    gaps,
    covered,
    investResults,
    patternExamples,
    score,
    verdict,
    summary,
    trace,
    evaluatedAt: new Date().toISOString(),
  }
}
