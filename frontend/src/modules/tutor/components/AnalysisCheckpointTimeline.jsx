import { Check, Circle, Clock, Loader2, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import BktMasteryCard from './BktMasteryCard.jsx'
import LearningEvidencePanel from './LearningEvidencePanel.jsx'
import StudentSprintTaskBoard from './StudentSprintTaskBoard.jsx'

/** @typedef {'pending' | 'preparing' | 'running' | 'done' | 'failed' | 'upcoming'} CheckpointStatus */

export const ANALYSIS_CHECKPOINTS = [
  {
    id: 'context',
    title: 'Sprint context',
    hint: 'Your project and sprint tasks are loaded.',
  },
  {
    id: 'knowledge',
    title: 'Required knowledge',
    hint: 'Finding the concepts each sprint task needs.',
  },
  {
    id: 'evidence',
    title: 'Learning evidence',
    hint: 'Collecting exercise and assessment-answer evidence from SLAP.',
  },
  {
    id: 'competency',
    title: 'Competency (BKT)',
    hint: 'Estimating mastery from chronological evidence.',
  },
  {
    id: 'recommendation',
    title: 'Learning recommendation',
    hint: 'Adaptive next-step guidance — planned after PP1.',
    upcoming: true,
  },
]

const STATUS_LABEL = {
  pending: 'Not started',
  preparing: 'Preparing',
  running: 'In progress',
  done: 'Completed',
  failed: 'Needs attention',
  upcoming: 'Coming next',
}

function statusTone(status) {
  switch (status) {
    case 'done':
      return {
        node: 'border-emerald-600 bg-emerald-600 text-white',
        label: 'text-emerald-700 dark:text-emerald-400',
        line: 'bg-emerald-500/70',
      }
    case 'running':
    case 'preparing':
      return {
        node: 'border-primary bg-primary text-primary-foreground',
        label: 'text-primary',
        line: 'bg-primary/40',
      }
    case 'failed':
      return {
        node: 'border-destructive bg-destructive text-destructive-foreground',
        label: 'text-destructive',
        line: 'bg-destructive/40',
      }
    case 'upcoming':
      return {
        node: 'border-dashed border-muted-foreground/40 bg-muted/50 text-muted-foreground',
        label: 'text-muted-foreground',
        line: 'bg-border',
      }
    default:
      return {
        node: 'border-border bg-muted text-muted-foreground',
        label: 'text-muted-foreground',
        line: 'bg-border',
      }
  }
}

function StatusIcon({ status }) {
  if (status === 'done') return <Check className="h-3.5 w-3.5" aria-hidden="true" strokeWidth={2.5} />
  if (status === 'failed') return <X className="h-3.5 w-3.5" aria-hidden="true" strokeWidth={2.5} />
  if (status === 'upcoming') return <Clock className="h-3.5 w-3.5" aria-hidden="true" />
  if (status === 'running' || status === 'preparing') {
    return <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
  }
  return <Circle className="h-2.5 w-2.5 fill-current" aria-hidden="true" />
}

function CheckpointDetailPanel({
  selectedId,
  statuses,
  analysisResult,
  estimates,
  teamPath,
  loading,
}) {
  const step = ANALYSIS_CHECKPOINTS.find((item) => item.id === selectedId) || ANALYSIS_CHECKPOINTS[0]
  const status = statuses[step.id] || (step.upcoming ? 'upcoming' : 'pending')
  const knowledge = analysisResult?.required_knowledge
  const knowledgeTasks = knowledge?.tasks || []
  const evidenceCount = analysisResult?.performance_evidence_count
  const performanceEvidence = analysisResult?.performance_evidence || []
  const normalizedEvidence = analysisResult?.normalized_evidence || []

  return (
    <div
      className="mt-5 rounded-2xl bg-muted/25 px-4 py-5 sm:px-5"
      aria-live="polite"
      aria-label={`${step.title} details`}
    >
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h3 className="text-base font-semibold text-foreground">{step.title}</h3>
          <p className="text-xs text-muted-foreground">
            {STATUS_LABEL[status]} · tap another checkpoint above to switch
          </p>
        </div>
      </div>

      {selectedId === 'context' && <StudentSprintTaskBoard />}

      {selectedId === 'knowledge' && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Concepts your sprint tasks depend on — so the tutor knows what to check next.
          </p>
          {status === 'pending' ||
          status === 'preparing' ||
          (status === 'running' && !knowledgeTasks.length) ? (
            <p className="rounded-xl bg-card px-4 py-3 text-sm text-muted-foreground">
              {loading || status === 'running' || status === 'preparing'
                ? 'Identifying required concepts for your sprint tasks…'
                : 'Run analysis to discover which course concepts each of your tasks requires.'}
            </p>
          ) : null}
          {knowledgeTasks.length > 0 ? (
            <div className="space-y-3">
              {knowledgeTasks.map((task) => (
                <article key={task.task_id} className="rounded-2xl bg-card px-4 py-4 shadow-xs">
                  <h4 className="text-sm font-semibold text-foreground">
                    {task.task_title || task.task_id}
                  </h4>
                  <ul className="mt-3 space-y-3">
                    {(task.required_concepts || []).map((concept) => (
                      <li
                        key={concept.concept_id}
                        className="border-l-2 border-primary/40 pl-3 text-sm text-muted-foreground"
                      >
                        <span className="font-semibold text-foreground">
                          {concept.concept_name || concept.concept_id}
                        </span>
                        {concept.selection_role ? (
                          <span className="ml-2 text-xs text-muted-foreground">
                            {concept.selection_role.replaceAll('_', ' ')}
                          </span>
                        ) : null}
                        {concept.reason ? (
                          <span className="mt-1 block leading-relaxed">{concept.reason}</span>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </article>
              ))}
            </div>
          ) : status === 'done' || status === 'failed' ? (
            <p className="text-sm text-muted-foreground">No required concepts were returned.</p>
          ) : null}
        </div>
      )}

      {selectedId === 'evidence' && (
        <LearningEvidencePanel
          evidenceCount={evidenceCount}
          performanceEvidence={performanceEvidence}
          normalizedEvidence={normalizedEvidence}
          requiredKnowledge={knowledge}
          loading={loading}
          status={status}
        />
      )}

      {selectedId === 'competency' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm text-muted-foreground">
              How ready you look on each required concept (baseline BKT).
            </p>
            {estimates?.length > 0 && teamPath ? (
              <Button asChild variant="outline" size="sm">
                <Link to={teamPath('/tutor/progress')}>Open progress view</Link>
              </Button>
            ) : null}
          </div>
          {estimates?.length > 0 ? (
            <div className="grid gap-3 lg:grid-cols-2">
              {estimates.map((estimate) => (
                <BktMasteryCard key={estimate.concept_id} estimate={estimate} />
              ))}
            </div>
          ) : loading || status === 'running' || status === 'preparing' ? (
            <p className="rounded-xl bg-card px-4 py-3 text-sm text-muted-foreground">
              Estimating mastery with baseline BKT…
            </p>
          ) : (
            <p className="rounded-xl bg-card px-4 py-3 text-sm text-muted-foreground">
              Run analysis to see BKT mastery for each required concept.
            </p>
          )}
        </div>
      )}

      {selectedId === 'recommendation' && (
        <div className="rounded-2xl bg-card px-4 py-5 shadow-xs">
          <p className="text-sm font-semibold text-foreground">Coming after PP1</p>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            The Adaptive Decision Engine will suggest your next learning step (explain, practice,
            assess, or nudge) and explain why — based on competency and your sprint tasks.
          </p>
        </div>
      )}
    </div>
  )
}

/**
 * Horizontal checkpoint timeline + detail panel for the selected step.
 */
export default function AnalysisCheckpointTimeline({
  statuses,
  activeMessage,
  selectedId = 'context',
  onSelect,
  analysisResult = null,
  estimates = [],
  teamPath = null,
  loading = false,
}) {
  return (
    <section
      className="rounded-xl border border-border bg-card px-4 py-4 sm:px-5"
      aria-label="Analysis checkpoints"
    >
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-foreground">Analysis checkpoints</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Select a checkpoint to inspect its details.
          </p>
        </div>
        {activeMessage ? (
          <p className="text-xs font-medium text-foreground" role="status" aria-live="polite">
            {activeMessage}
          </p>
        ) : null}
      </div>

      <ol className="grid gap-4 sm:grid-cols-5 sm:gap-0">
        {ANALYSIS_CHECKPOINTS.map((step, index) => {
          const status = statuses[step.id] || (step.upcoming ? 'upcoming' : 'pending')
          const tone = statusTone(status)
          const isLast = index === ANALYSIS_CHECKPOINTS.length - 1
          const prevStatus = index > 0 ? statuses[ANALYSIS_CHECKPOINTS[index - 1].id] : null
          const prevDone = prevStatus === 'done'
          const lineActive =
            prevDone ||
            status === 'done' ||
            status === 'running' ||
            status === 'preparing'
          const selected = selectedId === step.id

          return (
            <li key={step.id} className="relative flex gap-3 sm:flex-col sm:items-center sm:px-1.5">
              {!isLast && (
                <span
                  className={`pointer-events-none absolute left-[15px] top-8 hidden h-[calc(100%-2rem)] w-px sm:left-[calc(50%+16px)] sm:top-[15px] sm:block sm:h-px sm:w-[calc(100%-32px)] ${
                    lineActive && status !== 'upcoming' ? tone.line : 'bg-border'
                  }`}
                  aria-hidden="true"
                />
              )}

              <button
                type="button"
                onClick={() => onSelect?.(step.id)}
                className="relative z-[1] flex w-full flex-col items-start gap-2 rounded-lg px-1 py-1 text-left outline-none transition hover:opacity-90 sm:items-center"
                aria-pressed={selected}
                aria-current={selected ? 'step' : undefined}
              >
                <span
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 transition ${tone.node} ${
                    selected
                      ? 'outline outline-2 outline-offset-2 outline-primary'
                      : ''
                  }`}
                >
                  <StatusIcon status={status} />
                </span>

                <div className="min-w-0 sm:text-center">
                  <p
                    className={`text-sm ${
                      selected ? 'font-semibold text-foreground' : 'font-medium text-foreground'
                    }`}
                  >
                    {step.title}
                  </p>
                  <p className={`mt-0.5 text-[11px] font-medium ${tone.label}`}>
                    {STATUS_LABEL[status]}
                  </p>
                  <p className="mt-1 hidden text-xs text-muted-foreground sm:mx-auto sm:block sm:max-w-[10.5rem]">
                    {step.hint}
                  </p>
                </div>
              </button>
            </li>
          )
        })}
      </ol>

      <CheckpointDetailPanel
        selectedId={selectedId}
        statuses={statuses}
        analysisResult={analysisResult}
        estimates={estimates}
        teamPath={teamPath}
        loading={loading}
      />
    </section>
  )
}

/** Idle: sprint context ready; recommendation reserved for post-PP1. */
export function idleCheckpointStatuses() {
  return {
    context: 'done',
    knowledge: 'pending',
    evidence: 'pending',
    competency: 'pending',
    recommendation: 'upcoming',
  }
}

/**
 * PP1 success: pipeline checkpoints done; learning recommendation stays upcoming.
 */
export function completedCheckpointStatuses() {
  return {
    context: 'done',
    knowledge: 'done',
    evidence: 'done',
    competency: 'done',
    recommendation: 'upcoming',
  }
}

/**
 * Mark the active stage failed; keep earlier stages done.
 * Learning recommendation stays upcoming (not implemented in PP1).
 * @param {string} failedId
 */
export function failedCheckpointStatuses(failedId) {
  const order = ANALYSIS_CHECKPOINTS.map((s) => s.id).filter((id) => id !== 'recommendation')
  const failAt = Math.max(0, order.indexOf(failedId))
  /** @type {Record<string, CheckpointStatus>} */
  const next = { recommendation: 'upcoming' }
  order.forEach((id, i) => {
    if (i < failAt) next[id] = 'done'
    else if (i === failAt) next[id] = 'failed'
    else next[id] = 'pending'
  })
  return next
}
