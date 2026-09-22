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
}

export const SUBTASK_STATUS_TONE = {
  Done: 'success',
  'In Progress': 'primary',
  Todo: 'neutral',
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
