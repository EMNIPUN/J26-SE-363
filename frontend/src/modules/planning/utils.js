export const GATE_STATUS_TONE = {
  Passing: 'success',
  'Needs Review': 'warning',
  Failing: 'danger',
}

export const RISK_TONE = {
  Low: 'success',
  Medium: 'warning',
  High: 'danger',
}

export const ARBITRATION_CATEGORY_TONE = {
  COMPOUND: 'warning',
  AMBIGUOUS: 'primary',
  STRUCTURAL: 'danger',
  NOVEL: 'neutral',
}

export const SUBTASK_STATUS_TONE = {
  Done: 'success',
  'In Progress': 'primary',
  Todo: 'neutral',
}

export const QUALITY_GATE_THRESHOLD = 70

export const DIMENSION_ISSUE = {
  clarity: {
    label: 'Clarity',
    issue: 'The wording is vague or open to more than one reading.',
    whyItMatters: 'A developer implementing this may build the wrong thing without realizing it.',
    suggestion: 'Use concrete, unambiguous nouns and verbs — avoid words like "should", "fast" or "easy".',
  },
  completeness: {
    label: 'Completeness',
    issue: 'Not every pre-condition, post-condition or edge case is stated.',
    whyItMatters: 'Missing conditions surface as bugs or scope disputes late in the sprint.',
    suggestion: 'State every pre-condition, post-condition and edge case this requirement must cover.',
  },
  consistency: {
    label: 'Consistency',
    issue: 'This may contradict another requirement, or bundle two obligations into one sentence.',
    whyItMatters: 'Bundled or conflicting requirements can’t be decomposed into one clean unit of work.',
    suggestion: 'Check this doesn’t contradict another requirement or combine two obligations — split if needed.',
  },
  testability: {
    label: 'Testability',
    issue: 'No measurable acceptance condition is defined.',
    whyItMatters: 'The development team cannot objectively determine whether the requirement is complete.',
    suggestion: 'Add a measurable, verifiable threshold — a number, a time limit, an exact behavior.',
  },
  feasibility: {
    label: 'Feasibility',
    issue: 'This may not be achievable within the current architecture or project constraints.',
    whyItMatters: 'Infeasible requirements block downstream decomposition and estimation entirely.',
    suggestion: 'Confirm the current architecture can actually support this within project constraints.',
  },
  scope: {
    label: 'Scope Alignment',
    issue: 'This may reach outside the project’s agreed scope.',
    whyItMatters: 'Out-of-scope requirements inflate effort and dilute the project’s focus.',
    suggestion: 'Keep this requirement inside the agreed project scope — split out anything tangential.',
  },
}

const AMBIGUOUS_PHRASES = [
  'quickly', 'easily', 'easy', 'fast', 'simple', 'user-friendly', 'appropriately',
  'as needed', 'efficiently', 'seamlessly', 'robust', 'intuitive', 'should', 'may',
]

export function findAmbiguousPhrases(text) {
  const found = []
  const lower = text.toLowerCase()
  for (const phrase of AMBIGUOUS_PHRASES) {
    let idx = lower.indexOf(phrase)
    while (idx !== -1) {
      found.push({ phrase, start: idx, end: idx + phrase.length })
      idx = lower.indexOf(phrase, idx + phrase.length)
    }
  }
  return found.sort((a, b) => a.start - b.start)
}

export const STORY_STATUS_TONE = {
  Draft: 'neutral',
  'Needs Revision': 'warning',
  Validated: 'success',
  Accepted: 'primary',
}

const ROLE_GOAL_RE = /as\s+(a|an|the)\s+.+i\s+want/i
const BENEFIT_RE = /(so\s+that|in\s+order\s+to)\s+\S+/i

// Evaluates a student-written user story and returns the issues the
// Decomposition agent found — the agent critiques, it never rewrites. The
// student edits their own text and re-runs this until it comes back clean.
export function evaluateUserStory(title, acceptanceCriteria) {
  const issues = []
  const t = (title || '').trim()
  const ac = (acceptanceCriteria || '').trim()

  if (!ROLE_GOAL_RE.test(t)) {
    issues.push({
      id: 'role-goal',
      dimension: 'Structure',
      problem: 'The story doesn’t clearly state a role and a goal ("As a …, I want …").',
      suggestion: 'Rewrite the title so the role and the goal are both explicit — who is asking, and what do they want to do?',
    })
  } else if (!BENEFIT_RE.test(t) && !BENEFIT_RE.test(ac)) {
    issues.push({
      id: 'benefit',
      dimension: 'Structure',
      problem: 'No benefit or rationale is stated ("… so that …").',
      suggestion: 'Add why the user wants this — the benefit is what lets the team judge if the story is worth doing.',
    })
  }

  if (ac.length < 20) {
    issues.push({
      id: 'ac-missing',
      dimension: 'Testability',
      problem: 'Acceptance criteria is missing or too brief to verify against.',
      suggestion: 'Add at least one Given/When/Then condition, or a short checklist, that says exactly when this story is done.',
    })
  }

  const ambiguous = findAmbiguousPhrases(`${t} ${ac}`)
  const uniquePhrases = [...new Set(ambiguous.map((m) => m.phrase))]
  if (uniquePhrases.length > 0) {
    issues.push({
      id: 'ambiguous',
      dimension: 'Clarity',
      problem: `Vague wording found: ${uniquePhrases.map((p) => `"${p}"`).join(', ')}.`,
      suggestion: 'Replace vague words with something concrete and measurable.',
    })
  }

  if (t.length > 160) {
    issues.push({
      id: 'scope',
      dimension: 'Scope',
      problem: 'This story reads as more than one concern bundled together.',
      suggestion: 'Consider splitting this into two smaller stories, each independently shippable.',
    })
  }

  return issues
}

export function formatRelativeTime(isoString) {
  const diffMs = Date.now() - new Date(isoString).getTime()
  const minutes = Math.round(diffMs / 60000)
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  return `${days}d ago`
}
