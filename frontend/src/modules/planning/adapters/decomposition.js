// Adapts the Decomposition agent's backend payloads into the shape the planning UI uses.

const BACKEND_STATUS_MAP = { passed: 'Validated', needs_review: 'Needs Revision', blocked: 'Needs Revision' }

/**
 * Map one backend DecompositionResult to the UI decomposition evaluation shape.
 */
export function mapDecompositionResult(result) {
  if (!result) return null
  const r = result.result || result

  // INVEST results: backend uses `passed`, UI mock used `pass`
  const investResults = {}
  for (const story of r.stories || []) {
    const mapped = {}
    for (const criterion of ['independent', 'negotiable', 'valuable', 'estimable', 'small', 'testable']) {
      const c = story[criterion] || {}
      mapped[criterion] = { pass: c.passed ?? true, note: c.note || '' }
    }
    mapped.overallPass = story.overall_pass ?? true
    investResults[story.story_id] = mapped
  }

  const covered = (r.aspects || []).filter((a) => a.covered).map((a) => ({ id: a.id, label: a.label }))
  const gaps = (r.gaps || []).map((a) => ({ id: a.id, label: a.label }))

  const coverage = r.coverage ?? 0
  const score = r.overall_score ?? 0
  const verdict = BACKEND_STATUS_MAP[r.status] || 'Needs Revision'

  return {
    coverage,
    gaps,
    covered,
    investResults,
    patternExamples: (r.patterns || []).map((p) => ({
      id: p.id || '',
      title: p.title || '',
      stories: p.stories || [],
      note: p.note || '',
    })),
    score,
    verdict,
    summary: r.summary || '',
    confidence: r.confidence ?? 1,
    dartTriggered: r.dart_triggered ?? false,
    retrieval: r.retrieval || {},
    evaluatedAt: new Date().toISOString(),
  }
}

/**
 * Map persisted story rows from GET /planning/stories into the store's userStories map.
 * Returns { [requirementRef]: [story, story, ...] }.
 */
export function mapStoryRows(rows) {
  const map = {}
  for (const row of rows || []) {
    const reqRef = row.requirement_ref
    if (!map[reqRef]) map[reqRef] = []
    map[reqRef].push(row.data)
  }
  return map
}

/**
 * Map persisted decomposition results from GET /planning/decomposition into
 * the store's decompositionEvaluations map { [requirementRef]: evaluation }.
 */
export function mapPersistedDecompositions(rows) {
  const map = {}
  for (const row of rows || []) {
    map[row.requirement_ref] = mapDecompositionResult(row)
  }
  return map
}
