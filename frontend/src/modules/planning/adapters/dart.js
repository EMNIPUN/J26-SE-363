/**
 * Maps DART backend payloads into the shape the planning UI uses.
 */

const STATUS_LABELS = { open: 'Open', resolved: 'Resolved', escalated: 'Escalated' }
const CATEGORY_LABELS = {
  compound: 'Compound Obligation',
  ambiguous: 'Ambiguous Requirement',
  structural: 'Structural Conflict',
  novel: 'Novel Pattern',
  insufficient_evidence: 'Insufficient Evidence',
}

export function mapDartCase(raw) {
  if (!raw) return null
  const r = raw.result || raw

  const resolution = r.resolution || {}
  const hypothesis = r.hypothesis || {}
  const consultation = r.consultation || {}
  const response = r.response || {}

  return {
    id: r.case_id || raw.case_ref || '',
    caseRef: raw.case_ref || r.case_id || '',
    requirementId: r.requirement_ref || raw.requirement_ref || '',
    category: r.category || raw.category || 'ambiguous',
    categoryLabel: CATEGORY_LABELS[r.category || raw.category] || r.category || '',
    status: r.status || raw.status || 'open',
    statusLabel: STATUS_LABELS[r.status || raw.status] || 'Open',
    stage: r.source_stage || raw.source_stage || 'quality',
    triggerReason: r.trigger_reason || '',
    confidenceAgreement: resolution.confidence_agreement ?? 0,
    traces: (r.traces || []).map((t) => ({
      agentName: t.agent_name || '',
      diagnosis: t.diagnosis || '',
      evidence: t.evidence || [],
      criteriaUsed: t.criteria_used || [],
      confidence: t.confidence ?? 0.5,
      recommendedAction: t.recommended_action || '',
      uncertaintyType: t.uncertainty_type || '',
    })),
    hypothesis: {
      category: hypothesis.category || '',
      rationale: hypothesis.rationale || '',
      supportingEvidence: hypothesis.supporting_evidence || [],
      confidence: hypothesis.confidence ?? 0.5,
    },
    consultation: {
      targetAgent: consultation.target_agent || '',
      question: consultation.question || '',
      context: consultation.context || {},
      category: consultation.category || '',
    },
    response: {
      agentName: response.agent_name || '',
      answer: response.answer || '',
      evidence: response.evidence || [],
      confidence: response.confidence ?? 0.5,
      recommendedResolution: response.recommended_resolution || '',
    },
    resolution: {
      action: resolution.action || '',
      rationale: resolution.rationale || '',
      evidenceSummary: resolution.evidence_summary || [],
      confidenceAgreement: resolution.confidence_agreement ?? 0,
      actionableFeedback: resolution.actionable_feedback || '',
    },
    iteration: r.iteration ?? 1,
    createdAt: r.created_at || raw.created_at || '',
    resolvedBy: raw.resolved_by || '',
    resolvedAt: raw.resolved_at || '',
    title: `DART: ${CATEGORY_LABELS[r.category || raw.category] || 'Analysis'}`,
  }
}

export function mapDartCases(rows) {
  return (rows || []).map(mapDartCase).filter(Boolean)
}

export function getDartCasesForRequirement(cases, reqId) {
  return cases.filter((c) => c.requirementId === reqId)
}

export function buildAgentRationale(dartCase) {
  if (!dartCase) return []
  return dartCase.traces.map((t) => ({
    agent: t.agentName,
    assessment: t.diagnosis,
    confidence: t.confidence,
  }))
}
