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
    const rawScore = typeof v === 'object' ? (v?.raw_score ?? Math.round(score / 25)) : Math.round(score / 25)
    const applicability = typeof v === 'object' ? (v?.applicability ?? 'applicable') : 'applicable'
    dimensionScores[key] = score
    dimensionDetails[key] = {
      score,
      rawScore,
      applicability,
      rationale: v?.justification || v?.rationale || '',
      issues: v?.issues || [],
      remedy: v?.remedy || v?.recommended_action || '',
      standardReference: v?.standard_reference || v?.relevant_standard_reference || null,
    }
  }

  const assessmentStatus = q.status || ''
  const overallScore = Math.round(q.overall_score ?? 0)
  const overallScore4 = q.overall_score_4 ?? +(overallScore / 25).toFixed(2)
  const qualityBand = q.quality_band
    || (overallScore4 >= 3.5 ? 'Excellent' : overallScore4 >= 2.5 ? 'Good' : overallScore4 >= 1.5 ? 'Moderate' : overallScore4 >= 0.5 ? 'Poor' : 'Very poor')
  // A provider's textual status alone must never unlock a stage. The
  // persisted numeric assessment is the gate evidence; a malformed/raw
  // response marked "passed" with no score must remain locked.
  const completedOrPassed = !assessmentStatus
    || assessmentStatus === 'completed'
    || assessmentStatus === 'passed'
  const uiStatus = overallScore >= 75 && completedOrPassed
    ? 'Passing'
    : (BACKEND_STATUS_MAP[assessmentStatus] || 'Needs Review')

  const rawConf = (q?.confidence !== undefined && q?.confidence !== null) ? q.confidence : q?.confidence_level
  let confidenceVal = 0.85
  if (typeof rawConf === 'number' && !Number.isNaN(rawConf)) {
    confidenceVal = rawConf <= 1.0 ? rawConf : rawConf / 100.0
  } else if (typeof rawConf === 'string') {
    const parsed = parseFloat(rawConf)
    if (!Number.isNaN(parsed)) {
      confidenceVal = parsed <= 1.0 ? parsed : parsed / 100.0
    } else {
      const lower = rawConf.trim().toLowerCase()
      if (lower === 'high') confidenceVal = 0.90
      else if (lower === 'low') confidenceVal = 0.45
      else confidenceVal = 0.75
    }
  }

  return {
    id: q.id,
    title: extra.title || titleFromText(text),
    description: text || q.text || '',
    priority: extra.priority || 'Medium',
    status: uiStatus,
    decompositionAuthorized: Boolean(q.decomposition_authorized),
    effortAuthorized: Boolean(q.effort_authorized),
    overallScore,
    overallScore4,
    qualityBand,
    dimensionScores,
    dimensionDetails,
    applicableDimensions: q.applicable_dimensions || Object.keys(dimensionScores),
    naDimensions: q.na_dimensions || [],
    cannotAssessDimensions: q.cannot_assess_dimensions || [],
    smells: q.smells || [],
    retrieval: q.retrieval || { standards: [], exemplars: [], cross_req_hits: [] },
    suggestedRewrite: q.suggested_rewrite || null,
    confidence: confidenceVal,
    diagnosis: q.diagnosis || null,
    recommendedAction: q.recommended_action || null,
    toolOutputs: q.tool_outputs || [],
    toolsUsed: q.tools_used || q.tools_invoked || (q.tool_outputs || []).map((tool) => tool.tool_name),
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
