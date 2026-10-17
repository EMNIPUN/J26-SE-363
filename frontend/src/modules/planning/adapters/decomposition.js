// Adapts the Decomposition agent's backend payloads into the shape the planning UI uses.
//
// Backend contract (both POST /planning/decomposition's `assessment` and each
// item of GET /planning/decomposition's `results` use the SAME flat shape —
// see decomposition_service.assessment_to_dict):
//   { requirement_id, gate_status, decomposition_quality_score, quality_band,
//     needs_review_reason, coverage: { coverage_percentage, elements, checks },
//     stories: [{ story_ref, story_ready, independent: {result, note}, ... }],
//     student_feedback: [string], assessed_at }

const CRITERIA = ['independent', 'negotiable', 'valuable', 'estimable', 'small', 'testable']

function emptyCoverage() {
  return { percentage: 0, elements: [], checks: [] }
}

/**
 * Map one backend decomposition assessment into the UI evaluation shape.
 * Returns null when there is simply no analysis yet (falsy input) — distinct
 * from a malformed/unsaved response, which returns an object with
 * `malformed: true` so the UI can show an explicit error instead of a
 * false-positive "no issues flagged" state.
 */
export function mapDecompositionResult(result) {
  if (!result) return null

  if (result.persisted === false && !result.assessment) {
    return {
      malformed: true,
      stale: false,
      persistError: result.persist_error || 'Analysis could not be saved.',
      gateStatus: 'INCOMPLETE',
      score: 0,
      qualityBand: 'Very poor',
      coverage: emptyCoverage(),
      investResults: {},
      studentFeedback: [],
    }
  }

  const r = result.assessment ?? result.result ?? result
  if (!r || typeof r !== 'object' || !('gate_status' in r)) {
    return {
      malformed: true,
      stale: false,
      gateStatus: 'INCOMPLETE',
      score: 0,
      qualityBand: 'Very poor',
      coverage: emptyCoverage(),
      investResults: {},
      studentFeedback: [],
      summary: 'Analysis response was malformed or incomplete.',
    }
  }

  const investResults = {}
  for (const story of r.stories || []) {
    const mapped = {}
    for (const criterion of CRITERIA) {
      const c = story[criterion] || {}
      const result = c.result || 'Cannot Assess'
      mapped[criterion] = {
        result,
        note: c.note || '',
        pass: result === 'Pass' || result === 'Pass with note',
      }
    }
    mapped.storyReady = story.story_ready ?? false
    mapped.coveragePercentage = story.coverage_percentage ?? null
    // overallPass kept for any legacy UI still reading the old boolean shape.
    mapped.overallPass = mapped.storyReady
    if (story.story_ref) investResults[story.story_ref] = mapped
  }

  const cov = r.coverage || {}

  return {
    malformed: false,
    stale: false,
    // True only when the coverage LLM call itself could not run (unavailable
    // or errored) - distinct from a real analysis that concluded INCOMPLETE.
    // The checklist/score below are a mechanical placeholder in this state,
    // not a real finding — the UI must show this as a system error.
    analysisFailed: Boolean(r.analysis_failed),
    failureReason: r.failure_reason || null,
    gateStatus: r.gate_status,
    needsReviewReason: r.needs_review_reason || null,
    score: r.decomposition_quality_score ?? 0,
    qualityBand: r.quality_band || 'Very poor',
    coverage: {
      percentage: cov.coverage_percentage ?? 0,
      elements: cov.elements || [],
      checks: cov.checks || [],
    },
    investResults,
    studentFeedback: r.student_feedback || [],
    diagnosis: r.diagnosis || '',
    recommendedAction: r.recommended_action || null,
    confidence: r.confidence || 'moderate',
    storiesEvaluated: r.stories_evaluated ?? 0,
    storiesNeedingRevision: r.stories_needing_revision ?? 0,
    evaluatedAt: r.assessed_at || new Date().toISOString(),
  }
}

/**
 * Map persisted story rows from GET /planning/stories into the store's
 * userStories map. Returns { [requirementRef]: [story, story, ...] }.
 * decomposition_service.story_to_dict already emits the UI-ready camelCase
 * `investResult` shape directly — the legacy `row.data` JSONB branch is kept
 * one release cycle for any stale cached localStorage data from before the
 * normalized-schema upgrade.
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
      acceptanceCriteria: row.acceptance_criteria,
      student_story_points: row.student_story_points,
      priority: row.priority,
      status: row.status,
      tasks: row.tasks || [],
      investResult: row.investResult ?? row.invest_result,
      db_id: row.db_id,
      editedAt: row.edited_at,
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
 * assessment_to_dict always emits requirement_id as the human ref (injected
 * by the API layer) — see _attach_requirement_refs in planning.py.
 */
export function mapPersistedDecompositions(rows) {
  const map = {}
  for (const row of rows || []) {
    if (!row.requirement_id) continue
    map[row.requirement_id] = mapDecompositionResult(row)
  }
  return map
}
