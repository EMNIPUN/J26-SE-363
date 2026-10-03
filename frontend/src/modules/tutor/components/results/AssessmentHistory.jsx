import { Link } from 'react-router-dom'
import { ChevronRight, History } from 'lucide-react'
import Badge from '@/shared/components/Badge.jsx'
import ContextSection from '../layout/ContextSection.jsx'
import QueryState from '../common/QueryState.jsx'
import LoadingState from '../common/LoadingState.jsx'
import { useAssessmentHistory } from '../../hooks/useResults.js'
import { useTutorPaths } from '../../utils/tutorPaths.js'
import { ACTIVITY_KIND, PERFORMANCE_BAND, getMeta } from '../../utils/statusMeta.js'
import { formatDateTime } from '../../utils/format.js'

function HistoryItem({ item }) {
  const paths = useTutorPaths()
  const kind = getMeta(ACTIVITY_KIND, item.assessmentType)
  const band = getMeta(PERFORMANCE_BAND, item.band)
  const KindIcon = kind.icon

  return (
    <Link
      to={paths.results(item.assessmentId)}
      className="group flex items-center gap-3 rounded-lg border border-border/60 p-3 transition-colors hover:border-primary/40 hover:bg-primary/5 focus-visible:outline-2 focus-visible:outline-ring"
    >
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
        {KindIcon && <KindIcon className="h-4 w-4" aria-hidden="true" />}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-semibold text-foreground">{item.title}</span>
        <span className="block text-[11px] text-muted-foreground">
          {kind.label} · {item.primaryConcept.name} · {formatDateTime(item.completedAt)}
        </span>
        <span className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
          <Badge tone={band.tone}>{band.label}</Badge>
          {item.primaryGain > 0 && (
            <span className="font-medium tabular-nums text-emerald-700 dark:text-emerald-400">
              +{item.primaryGain}% {item.primaryConcept.name}
            </span>
          )}
          {item.gapsClosed > 0 && (
            <span className="font-medium text-foreground">
              {item.gapsClosed === 1 ? '1 gap closed' : `${item.gapsClosed} gaps closed`}
            </span>
          )}
        </span>
      </span>
      <span className="text-right">
        <span className="block text-base font-bold tabular-nums text-foreground">{item.score}%</span>
        <span className="block text-[10px] text-muted-foreground">score</span>
      </span>
      <ChevronRight
        className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5"
        aria-hidden="true"
      />
    </Link>
  )
}

export default function AssessmentHistory() {
  const historyQuery = useAssessmentHistory()

  return (
    <ContextSection icon={History} title="Completed Activities" description="Each result became new learning evidence">
      <QueryState
        query={historyQuery}
        loading={<LoadingState rows={4} label="Loading your results" />}
        errorTitle="Could not load your results"
        emptyIcon={History}
        emptyTitle="No results yet"
        emptyDescription="Complete a learning activity, coding exercise or adaptive quiz from Sprint Guidance and your results will appear here."
      >
        {(items) => (
          <ul className="space-y-2">
            {items.map((item) => (
              <li key={item.assessmentId}>
                <HistoryItem item={item} />
              </li>
            ))}
          </ul>
        )}
      </QueryState>
    </ContextSection>
  )
}
