import { Badge } from '@/components/ui/badge'
import { STATUS_LABELS } from '../data/mockFindings.js'

const PRIORITY_CLASSES = {
  Critical: 'bg-destructive/10 text-destructive border-destructive/20',
  High: 'bg-destructive/10 text-destructive border-destructive/20',
  Medium: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
  Low: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
}

const STATUS_CLASSES = {
  open: 'bg-destructive/10 text-destructive border-destructive/20',
  review: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
  learning: 'bg-violet-500/10 text-violet-600 dark:text-violet-400 border-violet-500/20',
  closed: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
}

export function PriorityBadge({ priority }) {
  return (
    <Badge variant="outline" className={PRIORITY_CLASSES[priority] || ''}>
      {priority}
    </Badge>
  )
}

export function StatusBadge({ status }) {
  return (
    <Badge variant="outline" className={STATUS_CLASSES[status] || ''}>
      {STATUS_LABELS[status] || status}
    </Badge>
  )
}

export function ConfidenceBadge({ confidence }) {
  const tone =
    confidence === 'Confirmed'
      ? 'bg-primary/10 text-primary border-primary/20'
      : confidence === 'Likely'
        ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20'
        : 'bg-muted text-muted-foreground border-border'

  return (
    <Badge variant="outline" className={tone}>
      {confidence}
    </Badge>
  )
}
