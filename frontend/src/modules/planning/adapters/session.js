/**
 * Maps pipeline session backend payloads into the shape the planning UI uses.
 */

const STAGE_LABELS = {
  parsing: 'SRS Parsing',
  quality: 'Quality Analysis',
  decomposition: 'Decomposition',
  effort_estimation: 'Effort Estimation',
}

const STATUS_LABELS = {
  active: 'Active',
  completed: 'Completed',
  failed: 'Failed',
}

export function mapSession(raw) {
  if (!raw) return null
  return {
    id: raw.id,
    groupId: raw.group_id,
    projectId: raw.project_id,
    currentStage: raw.current_stage || 'parsing',
    currentStageLabel: STAGE_LABELS[raw.current_stage] || raw.current_stage || 'Parsing',
    status: raw.status || 'active',
    statusLabel: STATUS_LABELS[raw.status] || 'Active',
    version: raw.version ?? 1,
    dartActivationCount: raw.dart_activation_count ?? 0,
    overallCompositeScore: raw.overall_composite_score,
    startedAt: raw.started_at || null,
    completedAt: raw.completed_at || null,
  }
}
