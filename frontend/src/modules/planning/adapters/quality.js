// Adapts the Quality agent's backend payloads into the shape the planning UI uses.
// One mapping, one set of six IEEE 830 keys — reused by upload, re-check, and DB hydration.

const BACKEND_STATUS_MAP = { passed: 'Passing', needs_review: 'Needs Review', blocked: 'Failing' }

function titleFromText(text) {
  const t = (text || '').trim()
  if (!t) return ''
  return t.length > 72 ? `${t.slice(0, 72)}…` : t
}

/**
 * Map one backend RequirementQualityResult (+ its source text) to a UI requirement.
 * Keeps both flat dimension scores (for the radar) and per-dimension details
 * (rationale/issues) plus smells and retrieval evidence (for the evidence panel).
 */
export function mapQualityResult(q, text, extra = {}) {
  const dims = q?.dimension_scores || {}
  const dimensionScores = {}
  const dimensionDetails = {}
  for (const [key, v] of Object.entries(dims)) {
    dimensionScores[key] = v?.score ?? 0
    dimensionDetails[key] = { score: v?.score ?? 0, rationale: v?.rationale || '', issues: v?.issues || [] }
  }
  return {
    id: q.id,
    title: extra.title || titleFromText(text),
    description: text || '',
    priority: extra.priority || 'Medium',
    status: BACKEND_STATUS_MAP[q.status] || 'Needs Review',
    overallScore: q.overall_score,
    dimensionScores,
    dimensionDetails,
    smells: q.smells || [],
    retrieval: q.retrieval || { standards: [], exemplars: [], cross_req_hits: [] },
    suggestedRewrite: q.suggested_rewrite || null,
    confidence: q.confidence,
    dartTriggered: q.dart_triggered,
    lastChecked: extra.lastChecked || new Date().toISOString(),
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

/** Map persisted rows from GET /planning/quality into UI requirements. */
export function mapPersistedRows(rows) {
  return (rows || []).map((row) =>
    mapQualityResult(row.result, row.requirement_text, { lastChecked: row.created_at }),
  )
}
