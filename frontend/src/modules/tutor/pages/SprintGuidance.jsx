import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChartColumn, MessageCircle, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import EmptyState from '../../../shared/components/EmptyState.jsx'
import PageHeader from '../../../shared/components/PageHeader.jsx'
import { useTeamPath } from '../../../shared/hooks/useTeamPath.js'
import AnalysisCheckpointTimeline, {
  completedCheckpointStatuses,
  failedCheckpointStatuses,
  idleCheckpointStatuses,
} from '../components/AnalysisCheckpointTimeline.jsx'
import LivePipelineBanner from '../components/LivePipelineBanner.jsx'
import { tutorApi } from '../services/tutorApi.js'

/** Soft stage advances while the single Core call is in flight (honest UX, not fake success). */
const UPCOMING_RECOMMENDATION = { recommendation: 'upcoming' }

const STAGE_PLAN = [
  {
    afterMs: 0,
    focus: 'knowledge',
    statuses: {
      context: 'done',
      knowledge: 'preparing',
      evidence: 'pending',
      competency: 'pending',
      ...UPCOMING_RECOMMENDATION,
    },
    message: 'Preparing required-knowledge identification…',
  },
  {
    afterMs: 2500,
    focus: 'knowledge',
    statuses: {
      context: 'done',
      knowledge: 'running',
      evidence: 'pending',
      competency: 'pending',
      ...UPCOMING_RECOMMENDATION,
    },
    message: 'Identifying concepts your sprint tasks need…',
  },
  {
    afterMs: 9000,
    focus: 'evidence',
    statuses: {
      context: 'done',
      knowledge: 'done',
      evidence: 'preparing',
      competency: 'pending',
      ...UPCOMING_RECOMMENDATION,
    },
    message: 'Required knowledge ready. Preparing evidence retrieval…',
  },
  {
    afterMs: 12000,
    focus: 'evidence',
    statuses: {
      context: 'done',
      knowledge: 'done',
      evidence: 'running',
      competency: 'pending',
      ...UPCOMING_RECOMMENDATION,
    },
    message: 'Collecting performance evidence from SLAP…',
  },
  {
    afterMs: 20000,
    focus: 'competency',
    statuses: {
      context: 'done',
      knowledge: 'done',
      evidence: 'done',
      competency: 'running',
      ...UPCOMING_RECOMMENDATION,
    },
    message: 'Estimating competency with BKT…',
  },
]

function enrichEstimates(result) {
  const estimates = result?.estimates || []
  const tasks = result?.required_knowledge?.tasks || []
  const names = {}
  for (const task of tasks) {
    for (const concept of task.required_concepts || []) {
      names[concept.concept_id] = concept.concept_name || concept.concept_id
    }
  }
  return estimates.map((item) => ({
    ...item,
    concept_name: names[item.concept_id] || item.concept_id,
  }))
}

function inferFailedStage(err) {
  const text = `${err?.message || ''} ${err?.detail || ''}`.toLowerCase()
  if (text.includes('mint') || text.includes('identity') || text.includes('token')) {
    return 'evidence'
  }
  if (text.includes('mcp') || text.includes('evidence')) return 'evidence'
  if (text.includes('neo4j') || text.includes('knowledge') || text.includes('openai')) {
    return 'knowledge'
  }
  return 'competency'
}

export default function SprintGuidance() {
  const team = useTeamPath()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [payload, setPayload] = useState(null)
  const [checkpointStatuses, setCheckpointStatuses] = useState(idleCheckpointStatuses)
  const [selectedCheckpoint, setSelectedCheckpoint] = useState('context')
  const [activeMessage, setActiveMessage] = useState(
    'Sprint context is ready. Select a checkpoint or click Run analysis.',
  )
  const timersRef = useRef([])
  const userPickedRef = useRef(false)

  const clearStageTimers = useCallback(() => {
    timersRef.current.forEach((id) => clearTimeout(id))
    timersRef.current = []
  }, [])

  useEffect(() => () => clearStageTimers(), [clearStageTimers])

  const startStageProgression = useCallback(() => {
    clearStageTimers()
    userPickedRef.current = false
    STAGE_PLAN.forEach((stage) => {
      const id = setTimeout(() => {
        setCheckpointStatuses(stage.statuses)
        setActiveMessage(stage.message)
        if (!userPickedRef.current) {
          setSelectedCheckpoint(stage.focus)
        }
      }, stage.afterMs)
      timersRef.current.push(id)
    })
  }, [clearStageTimers])

  const handleSelectCheckpoint = useCallback((id) => {
    userPickedRef.current = true
    setSelectedCheckpoint(id)
  }, [])

  const runAnalysis = useCallback(() => {
    setLoading(true)
    setError(null)
    setPayload(null)
    startStageProgression()

    tutorApi
      .estimateCompetency({})
      .then((body) => {
        clearStageTimers()
        if (body?.status && body.status !== 'completed') {
          const detail =
            body.error?.message ||
            body.result?.detail ||
            `Analysis finished with status: ${body.status}`
          setError(detail)
          setPayload(body)
          setCheckpointStatuses(failedCheckpointStatuses('competency'))
          setSelectedCheckpoint('competency')
          setActiveMessage('Analysis did not complete. You can try again.')
          return
        }
        setPayload(body)
        setCheckpointStatuses(completedCheckpointStatuses())
        if (!userPickedRef.current) {
          setSelectedCheckpoint('evidence')
        }
        const evidenceCount = body?.result?.performance_evidence_count ?? 0
        const conceptCount = (body?.result?.estimates || []).length
        setActiveMessage(
          `PP1 pipeline complete · ${conceptCount} concept estimate(s) · ${evidenceCount} evidence record(s). Learning recommendation comes after PP1.`,
        )
      })
      .catch((err) => {
        clearStageTimers()
        setError(err.message || 'Competency analysis failed.')
        setPayload(null)
        const failedId = inferFailedStage(err)
        setCheckpointStatuses(failedCheckpointStatuses(failedId))
        setSelectedCheckpoint(failedId)
        setActiveMessage('Something went wrong on a checkpoint. Try again when ready.')
      })
      .finally(() => setLoading(false))
  }, [clearStageTimers, startStageProgression])

  const result = payload?.result || {}
  const knowledge = result.required_knowledge
  const estimates = enrichEstimates(result)
  const showResults = payload?.status === 'completed'

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={['AI Tutor', 'Sprint Guidance']}
        title="Sprint guidance"
        description="Watch each checkpoint as the tutor identifies required knowledge, gathers evidence, and estimates mastery."
        actions={
          <Button onClick={runAnalysis} loading={loading} disabled={loading}>
            <Play className="h-4 w-4" />
            {showResults ? 'Run again' : 'Run analysis'}
          </Button>
        }
      />
      <LivePipelineBanner mode="live" />

      <AnalysisCheckpointTimeline
        statuses={checkpointStatuses}
        activeMessage={activeMessage}
        selectedId={selectedCheckpoint}
        onSelect={handleSelectCheckpoint}
        analysisResult={showResults ? result : null}
        estimates={showResults ? estimates : []}
        teamPath={team}
        loading={loading}
      />

      {loading && (
        <Card className="border-dashed p-4">
          <p className="text-sm text-muted-foreground" role="status">
            Analysis is running. The detail panel above follows the active checkpoint — you can also
            click any step to inspect it.
          </p>
        </Card>
      )}

      {error && (
        <EmptyState
          title="Analysis unavailable"
          description={error}
          actionLabel="Try again"
          onAction={runAnalysis}
        />
      )}

      {showResults && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="grid flex-1 gap-3 sm:grid-cols-3">
            <SummaryCard
              label="Course"
              value={knowledge?.course_code || knowledge?.course_id || '—'}
            />
            <SummaryCard
              label="Evidence records"
              value={String(result.performance_evidence_count ?? 0)}
            />
            <SummaryCard label="Concepts estimated" value={String(estimates.length)} />
          </div>
          <div className="flex gap-2">
            <Button asChild variant="outline" size="sm">
              <Link to={team('/tutor/chat')}>
                <MessageCircle className="h-3.5 w-3.5" />
                Chat
              </Link>
            </Button>
            <Button asChild variant="outline" size="sm">
              <Link to={team('/tutor/progress')}>
                <ChartColumn className="h-3.5 w-3.5" />
                Progress
              </Link>
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

function SummaryCard({ label, value }) {
  return (
    <Card className="p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold">{value}</p>
    </Card>
  )
}
