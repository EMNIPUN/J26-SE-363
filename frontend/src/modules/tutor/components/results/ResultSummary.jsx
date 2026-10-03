import { CalendarCheck, CircleCheck, MonitorPlay, Target } from 'lucide-react'
import Badge from '@/shared/components/Badge.jsx'
import { ACTIVITY_KIND, PERFORMANCE_BAND, getMeta } from '../../utils/statusMeta.js'
import { formatDateTime } from '../../utils/format.js'

const RADIUS = 30
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

function ScoreRing({ score, strokeClass }) {
  const clamped = Math.min(100, Math.max(0, score))
  return (
    <div className="relative h-20 w-20 shrink-0">
      <svg viewBox="0 0 72 72" className="h-20 w-20 -rotate-90" aria-hidden="true">
        <circle cx="36" cy="36" r={RADIUS} fill="none" strokeWidth="6" className="stroke-muted" />
        <circle
          cx="36"
          cy="36"
          r={RADIUS}
          fill="none"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={CIRCUMFERENCE * (1 - clamped / 100)}
          className={strokeClass}
        />
      </svg>
      <span className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-lg font-bold tabular-nums leading-none text-foreground">{clamped}%</span>
        <span className="mt-0.5 text-[10px] text-muted-foreground">Score</span>
      </span>
    </div>
  )
}

export default function ResultSummary({ result }) {
  const kind = getMeta(ACTIVITY_KIND, result.assessmentType)
  const band = getMeta(PERFORMANCE_BAND, result.band)
  const KindIcon = kind.icon

  return (
    <div className="flex flex-wrap items-center gap-4">
      <ScoreRing score={result.score} strokeClass={band.strokeClass ?? 'stroke-primary'} />
      <div className="min-w-0 flex-1 space-y-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge tone={kind.tone}>
            {KindIcon && <KindIcon className="h-3 w-3" aria-hidden="true" />}
            {kind.label}
          </Badge>
          <Badge tone="success">
            <CircleCheck className="h-3 w-3" aria-hidden="true" />
            Completed
          </Badge>
          <Badge tone={band.tone}>{band.label}</Badge>
        </div>
        <h2 className="text-base font-semibold leading-snug text-foreground">{result.title}</h2>
        <dl className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <Target className="h-3.5 w-3.5" aria-hidden="true" />
            <dt className="sr-only">Concept</dt>
            <dd className="font-medium text-foreground">{result.primaryConcept.name}</dd>
          </div>
          <div className="flex items-center gap-1.5">
            <MonitorPlay className="h-3.5 w-3.5" aria-hidden="true" />
            <dt className="sr-only">Platform</dt>
            <dd>{result.platform}</dd>
          </div>
          <div className="flex items-center gap-1.5">
            <CalendarCheck className="h-3.5 w-3.5" aria-hidden="true" />
            <dt className="sr-only">Completed</dt>
            <dd>{formatDateTime(result.completedAt)}</dd>
          </div>
        </dl>
      </div>
    </div>
  )
}
