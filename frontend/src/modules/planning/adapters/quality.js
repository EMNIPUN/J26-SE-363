// Adapts the Quality agent's backend payloads into the shape the planning UI uses.
// One mapping, one set of six IEEE 830 keys — reused by upload, re-check, and DB hydration.

const BACKEND_STATUS_MAP = { passed: 'Passing', needs_review: 'Needs Review', blocked: 'Failing' }

function titleFromText(text) {
  const t = (text || '').trim()
  if (!t) return ''
  return t.length > 72 ? `${t.slice(0, 72)}…` : t
}

/**
 * Map one backend quality assessment to a UI requirement.
 * Handles both the agent's raw JSONB shape (from POST /quality)
 * and the normalized shape (from GET /quality's assessment_to_dict).
 */
export function mapQualityResult(q, text, extra = {}) {
  const dims = q?.dimension_scores || {}
  const dimensionScores = {}
  const dimensionDetails = {}
  for (const [key, v] of Object.entries(dims)) {
    const score = typeof v === 'object' ? (v?.score ?? 0) : (v ?? 0)
    dimensionScores[key] = score
    dimensionDetails[key] = {
      score,
      rationale: v?.justification || v?.rationale || '',
      issues: v?.issues || [],
      standardReference: v?.standard_reference || null,
    }
  }

  const assessmentStatus = q.status || ''
  const uiStatus = BACKEND_STATUS_MAP[assessmentStatus]
    || (q.overall_score >= 75 ? 'Passing' : 'Needs Review')

  return {
    id: q.id,
    title: extra.title || titleFromText(text),
    description: text || q.text || '',
    priority: extra.priority || 'Medium',
    status: uiStatus,
    overallScore: q.overall_score,
    dimensionScores,
    dimensionDetails,
    smells: q.smells || [],
    retrieval: q.retrieval || { standards: [], exemplars: [], cross_req_hits: [] },
    suggestedRewrite: q.suggested_rewrite || null,
    confidence: q.confidence,
    diagnosis: q.diagnosis || null,
    recommendedAction: q.recommended_action || null,
    toolOutputs: q.tool_outputs || [],
    dartTriggered: q.dart_triggered,
    lastChecked: extra.lastChecked || q.assessed_at || q.created_at || new Date().toISOString(),
    stale: false,
  }
}

/** Map the ExtractRequirementsResult (upload) into a list of UI requirements. */
export function mapExtractResult(result) {
  const textById = Object.fromEntries((result?.requirements || []).map((r) => [r.id, r.text]))
  const scored = result?.quality?.requirements || []
  return scored.map((q) => mapQualityResult(q, textById[q.id]))
}

/** Map a single analyze_quality result for a known requirement text. */
export function mapAnalyzeResult(result, text, extra = {}) {
  const q = result?.requirements?.[0]
  return q ? mapQualityResult(q, text, extra) : null
}

/**
 * Map persisted rows from GET /planning/quality into UI requirements.
 * Handles both old shape (row.result wrapper) and new normalized shape.
 */
export function mapPersistedRows(rows) {
  return (rows || []).map((row) => {
    if (row.result) {
      return mapQualityResult(row.result, row.requirement_text, { lastChecked: row.created_at })
    }
    return mapQualityResult(row, row.text, { lastChecked: row.created_at || row.assessed_at })
  })
}

/** Map a quality gate decision response. */
export function mapGateDecision(gate) {
  if (!gate) return null
  return {
    decision: gate.decision,
    passed: gate.decision === 'pass',
    compositeScore: gate.composite_score,
    threshold: gate.threshold,
    totalRequirements: gate.total_requirements,
    aboveThreshold: gate.above_threshold,
    belowThreshold: gate.below_threshold,
    summary: gate.gate_summary,
    decidedAt: gate.decided_at,
  }
}
