import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Repeat } from 'lucide-react'
import { cn } from '@/lib/utils'
import ContextSection from '../layout/ContextSection.jsx'
import QueryState from '../common/QueryState.jsx'
import LoadingState from '../common/LoadingState.jsx'
import { useLearningLoop } from '../../hooks/useLearning.js'
import { useTutorPaths } from '../../utils/tutorPaths.js'
import { LOOP_STEP_ICONS, LOOP_STEP_STATUS, getMeta } from '../../utils/statusMeta.js'

function LoopStep({ step, index }) {
  const status = getMeta(LOOP_STEP_STATUS, step.status)
  const StepIcon = LOOP_STEP_ICONS[step.id]
  const StatusIcon = status.icon
  const isCurrent = step.status === 'current'
  const isMuted = step.status === 'upcoming' || step.status === 'skipped'

  return (
    <li
      aria-current={isCurrent ? 'step' : undefined}
      className={cn(
        'flex w-40 shrink-0 snap-start flex-col gap-1 rounded-lg border px-3 py-2 @2xl:w-auto @2xl:min-w-0',
        isCurrent ? 'border-primary/50 bg-primary/5 ring-1 ring-primary/15' : 'border-border/60 bg-card',
      )}
    >
      <div className="flex items-center gap-1.5">
        <span className="text-[10px] font-semibold tabular-nums text-muted-foreground" aria-hidden="true">
          {index + 1}
        </span>
        {StepIcon && (
          <StepIcon className={cn('h-3.5 w-3.5', isMuted ? 'text-muted-foreground' : 'text-primary')} aria-hidden="true" />
        )}
        <span className={cn('min-w-0 flex-1 truncate text-xs font-semibold', isMuted ? 'text-muted-foreground' : 'text-foreground')}>
          {step.label}
        </span>
        {StatusIcon && <StatusIcon className={cn('h-3.5 w-3.5 shrink-0', status.iconClass)} aria-hidden="true" />}
        <span className="sr-only">({status.label})</span>
      </div>
      <p className="line-clamp-2 text-[11px] leading-snug text-muted-foreground">{step.detail}</p>
    </li>
  )
}

function LoopSteps({ loop }) {
  const paths = useTutorPaths()
  const scrollerRef = useRef(null)

  // On narrow screens the steps form a horizontal strip; bring the current
  // step into view without scrolling the page.
  useEffect(() => {
    const scroller = scrollerRef.current
    const current = scroller?.querySelector('[aria-current="step"]')
    if (scroller && current && scroller.scrollWidth > scroller.clientWidth) {
      scroller.scrollLeft = current.offsetLeft - scroller.offsetLeft - 8
    }
  }, [loop])

  return (
    <div className="space-y-3">
      <div
        ref={scrollerRef}
        role="region"
        aria-label="Learning loop steps"
        tabIndex={0}
        className="relative -mx-1 overflow-x-auto px-1 pb-3 focus-visible:outline-2 focus-visible:outline-ring @2xl:overflow-visible @2xl:pb-1"
      >
        <ol className="flex snap-x gap-2 @2xl:grid @2xl:grid-cols-[repeat(auto-fill,minmax(10.5rem,1fr))]">
          {loop.steps.map((step, index) => (
            <LoopStep key={step.id} step={step} index={index} />
          ))}
        </ol>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted-foreground">
        <p className="flex items-center gap-1.5">
          <Repeat className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
          After every result the Tutor recalculates your gaps and recommends again
          {loop.focusConcept ? `, currently focusing on ${loop.focusConcept.name}` : ''}.
        </p>
        {loop.latestAssessmentId && (
          <Link
            to={paths.results(loop.latestAssessmentId)}
            className="flex items-center gap-1 font-medium text-primary hover:underline"
          >
            Latest result
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        )}
      </div>
    </div>
  )
}

export default function LearningLoop() {
  const loopQuery = useLearningLoop()

  return (
    <ContextSection
      icon={Repeat}
      title="Your Adaptive Learning Loop"
      description="From your current task to your next recommendation"
    >
      <QueryState
        query={loopQuery}
        isEmpty={(data) => !data?.steps?.length}
        loading={<LoadingState rows={3} label="Loading your learning loop" />}
        errorTitle="Could not load your learning loop"
      >
        {(loop) => <LoopSteps loop={loop} />}
      </QueryState>
    </ContextSection>
  )
}
