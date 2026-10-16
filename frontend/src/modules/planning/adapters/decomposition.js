// Adapts the Decomposition agent's backend payloads into the shape the planning UI uses.

const BACKEND_STATUS_MAP = { passed: 'Validated', needs_review: 'Needs Revision', blocked: 'Needs Revision' }

/**
 * Map one backend DecompositionResult to the UI decomposition evaluation shape.
 * Handles both agent raw JSONB (from POST /decomposition) and normalized shape
 * (from GET /decomposition's assessment_to_dict).
 */
export function mapDecompositionResult(result) {
  if (!result) return null
  const r = result.result || result

  const investResults = {}
  for (const story of r.stories || []) {
    const mapped = {}
    for (const criterion of ['independent', 'negotiable', 'valuable', 'estimable', 'small', 'testable']) {
      const c = story[criterion] || {}
      mapped[criterion] = {
        pass: c.is_satisfied ?? c.passed ?? true,
        score: c.score ?? (c.passed ? 1 : 0),
        note: c.justification || c.note || '',
      }
    }
    mapped.overallPass = story.overall_pass ?? true
    investResults[story.story_id] = mapped
  }

  const cov = r.coverage || {}
  const covered = cov.covered_aspects || (r.aspects || []).filter((a) => a.covered).map((a) => ({ id: a.id, label: a.label }))
  const gaps = cov.uncovered_gaps || (r.gaps || []).map((a) => ({ id: a.id, label: a.label }))

  const coveragePct = cov.overall_coverage_percentage ?? r.coverage_score ?? r.coverage ?? 0
  const score = r.composite_score ?? r.overall_score ?? 0
  const status = r.status || r.assessment_status || ''
  const verdict = BACKEND_STATUS_MAP[status] || (score >= 75 ? 'Validated' : 'Needs Revision')

  return {
    coverage: coveragePct,
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
    summary: r.diagnosis || r.summary || '',
    recommendedAction: r.recommended_action || null,
    confidence: r.confidence ?? 1,
    dartTriggered: r.dart_triggered ?? false,
    retrieval: r.retrieval || {},
    toolOutputs: r.tool_outputs || [],
    storiesEvaluated: r.stories_evaluated ?? 0,
    storiesNeedingRevision: r.stories_needing_revision ?? 0,
    evaluatedAt: r.assessed_at || new Date().toISOString(),
  }
}

/**
 * Map persisted story rows from GET /planning/stories into the store's userStories map.
 * Returns { [requirementRef]: [story, story, ...] }.
 * Handles both old shape (row.data JSONB) and new normalized shape (proper columns).
 */
export function mapStoryRows(rows) {
  const map = {}
  for (const row of rows || []) {
    const reqRef = row.requirement_ref
    if (!map[reqRef]) map[reqRef] = []

    const story = row.data || {
      id: row.id || row.story_ref,
      story_ref: row.story_ref,
      title: row.title,
      as_a: row.as_a,
      i_want: row.i_want,
      so_that: row.so_that,
      description: row.description,
      acceptance_criteria: row.acceptance_criteria,
      student_story_points: row.student_story_points,
      priority: row.priority,
      invest_result: row.invest_result,
      db_id: row.db_id,
      created_at: row.created_at,
      updated_at: row.updated_at,
    }
    map[reqRef].push(story)
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
    map[row.requirement_id || row.requirement_ref] = mapDecompositionResult(row)
  }
  return map
}
