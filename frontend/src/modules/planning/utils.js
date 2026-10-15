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
  compound: 'warning',
  ambiguous: 'primary',
  structural: 'danger',
  novel: 'neutral',
  insufficient_evidence: 'neutral',
}

export const SUBTASK_STATUS_TONE = {
  Done: 'success',
  'In Progress': 'primary',
  Todo: 'neutral',
}

export const QUALITY_GATE_THRESHOLD = 75

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
  correctness: {
    label: 'Correctness',
    issue: 'The stated behaviour may not be the one the system actually needs.',
    whyItMatters: 'An incorrect requirement sends design, code and tests down the wrong path.',
    suggestion: 'Confirm this is the genuinely intended behaviour and is technically sound for the goal.',
  },
  traceability: {
    label: 'Traceability',
    issue: 'This requirement is hard to identify or link back to a source/goal.',
    whyItMatters: 'Untraceable requirements can’t be tracked through design, test and sign-off.',
    suggestion: 'Give it a unique ID and keep it self-contained so it traces to a clear goal.',
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

export function formatRelativeTime(isoString) {
  const diffMs = Date.now() - new Date(isoString).getTime()
  const minutes = Math.round(diffMs / 60000)
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  return `${days}d ago`
}
