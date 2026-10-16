/**
 * Maps DART backend payloads into the shape the planning UI uses.
 * Handles both the agent's raw JSONB shape and the normalized session_to_dict shape.
 */

const STATUS_LABELS = { active: 'Open', resolved: 'Resolved', escalated: 'Escalated', timed_out: 'Timed Out', circuit_broken: 'Circuit Broken' }
const CATEGORY_LABELS = {
  compound: 'Compound Obligation',
  ambiguous: 'Ambiguous Requirement',
  structural: 'Structural Conflict',
  novel: 'Novel Pattern',
  insufficient_evidence: 'Insufficient Evidence',
}

/**
 * Map a DART session (normalized) or a raw DART case into a UI shape.
 */
export function mapDartCase(raw) {
  if (!raw) return null
  const r = raw.result || raw

  const hypothesis = r.diagnostic_hypothesis || r.category || ''
  const statusKey = r.status || 'active'
  const triggerStage = r.triggering_stage || r.source_stage || 'quality'

  const iterations = (r.iterations || []).map((it) => ({
    number: it.iteration_number ?? 1,
    toolUsed: it.resolution_tool_used || '',
    output: it.resolution_output || '',
    confidenceBefore: it.confidence_before,
    confidenceAfter: it.confidence_after,
    convergenceAchieved: it.convergence_achieved ?? false,
    evidence: (it.evidence || []).map((e) => ({
      type: e.evidence_type || 'unknown',
      sourceTool: e.source_tool || '',
      data: e.evidence_data || null,
      relevanceScore: e.relevance_score,
      supportsHypothesis: e.supports_hypothesis,
      summary: e.evidence_summary || '',
    })),
  }))

  const escalation = r.escalation || null

  // Backward compat: also handle old raw result shape
  const resolution = r.resolution || {}
  const oldHypothesis = r.hypothesis || {}
  const consultation = r.consultation || {}
  const response = r.response || {}

  return {
    id: r.id || r.case_id || raw.case_ref || '',
    caseRef: raw.case_ref || r.case_id || r.id || '',
    pipelineSessionId: r.pipeline_session_id || '',
    category: hypothesis,
    categoryLabel: CATEGORY_LABELS[hypothesis] || hypothesis || '',
    status: statusKey,
    statusLabel: STATUS_LABELS[statusKey] || 'Open',
    stage: triggerStage,
    triggerReason: r.trigger_reason || '',
    finalDecision: r.final_decision || null,
    resolvedScore: r.resolved_score,
    iterationCount: r.iteration_count ?? iterations.length,
    iterations,
    escalation: escalation ? {
      reason: escalation.escalation_reason || '',
      status: escalation.status || 'pending',
      instructorDecision: escalation.instructor_decision || null,
      instructorNotes: escalation.instructor_notes || null,
    } : null,
    // Backward compat for old raw result fields
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
      category: oldHypothesis.category || hypothesis || '',
      rationale: oldHypothesis.rationale || '',
      supportingEvidence: oldHypothesis.supporting_evidence || [],
      confidence: oldHypothesis.confidence ?? 0.5,
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
      action: resolution.action || r.final_decision || '',
      rationale: resolution.rationale || '',
      evidenceSummary: resolution.evidence_summary || [],
      confidenceAgreement: resolution.confidence_agreement ?? 0,
      actionableFeedback: resolution.actionable_feedback || '',
    },
    createdAt: r.created_at || raw.created_at || '',
    startedAt: r.started_at || '',
    resolvedAt: r.resolved_at || '',
    title: `DART: ${CATEGORY_LABELS[hypothesis] || 'Analysis'}`,
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
  if (dartCase.iterations?.length) {
    return dartCase.iterations.flatMap((it) =>
      it.evidence.map((e) => ({
        agent: e.sourceTool || it.toolUsed,
        assessment: e.summary,
        confidence: e.relevanceScore ?? 0.5,
      })),
    )
  }
  return dartCase.traces.map((t) => ({
    agent: t.agentName,
    assessment: t.diagnosis,
    confidence: t.confidence,
  }))
}
