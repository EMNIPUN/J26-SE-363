import { Link } from 'react-router-dom'
import { ArrowRight, Clock, Lightbulb, Target } from 'lucide-react'
import { Button } from '@/components/ui/button'
import Badge from '@/shared/components/Badge.jsx'
import ContextSection from '../layout/ContextSection.jsx'
import QueryState from '../common/QueryState.jsx'
import LoadingState from '../common/LoadingState.jsx'
import RecommendationReasons from './RecommendationReasons.jsx'
import { useRecommendation } from '../../hooks/useTutorOverview.js'
import { getActionPath, useTutorPaths } from '../../utils/tutorPaths.js'
import { ACTIVITY_KIND, getMeta } from '../../utils/statusMeta.js'

export function RecommendationDetails({ recommendation }) {
  const paths = useTutorPaths()
  const { type, title, summary, conceptName, estimatedMinutes, reasons, action } = recommendation
  const meta = getMeta(ACTIVITY_KIND, type)
  const TypeIcon = meta.icon
  const actionPath = getActionPath(paths, action)

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-primary/15 bg-primary/5 p-3">
        <Badge tone={meta.tone} className="uppercase tracking-wide">
          {TypeIcon && <TypeIcon className="h-3.5 w-3.5" aria-hidden="true" />}
          {meta.label}
        </Badge>
        <h3 className="mt-2 text-sm font-semibold leading-snug text-foreground">{title}</h3>
        {summary && <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{summary}</p>}
        <dl className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
          {conceptName && (
            <div className="flex items-center gap-1.5">
              <Target className="h-3.5 w-3.5" aria-hidden="true" />
              <dt className="sr-only">Concept</dt>
              <dd className="font-medium text-foreground">{conceptName}</dd>
            </div>
          )}
          {estimatedMinutes != null && (
            <div className="flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5" aria-hidden="true" />
              <dt className="sr-only">Estimated time</dt>
              <dd>About {estimatedMinutes} min</dd>
            </div>
          )}
        </dl>
      </div>

      <RecommendationReasons reasons={reasons} />

      {actionPath && (
        <Button asChild className="w-full">
          <Link to={actionPath}>
            {action.label}
            <ArrowRight aria-hidden="true" />
          </Link>
        </Button>
      )}
    </div>
  )
}

export default function RecommendationCard() {
  const recommendationQuery = useRecommendation()

  return (
    <ContextSection
      icon={Lightbulb}
      title="Recommended Next Action"
      description="Chosen by the Tutor from your gaps and progress"
      className="border-primary/30 ring-1 ring-primary/10"
    >
      <QueryState
        query={recommendationQuery}
        loading={<LoadingState rows={4} label="Loading recommendation" />}
        errorTitle="Could not load your recommendation"
        emptyIcon={Lightbulb}
        emptyTitle="No recommendation right now"
        emptyDescription="You meet every requirement for your current task. Optional challenges are in your learning plan."
      >
        {(recommendation) => <RecommendationDetails recommendation={recommendation} />}
      </QueryState>
    </ContextSection>
  )
}
