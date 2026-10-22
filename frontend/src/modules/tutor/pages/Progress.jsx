import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { Play, Route } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import EmptyState from '../../../shared/components/EmptyState.jsx'
import PageHeader from '../../../shared/components/PageHeader.jsx'
import { useTeamPath } from '../../../shared/hooks/useTeamPath.js'
import BktMasteryCard from '../components/BktMasteryCard.jsx'
import LivePipelineBanner from '../components/LivePipelineBanner.jsx'
import { tutorApi } from '../services/tutorApi.js'

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

export default function Progress() {
  const team = useTeamPath()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [payload, setPayload] = useState(null)

  const runAnalysis = useCallback(() => {
    setLoading(true)
    setError(null)
    tutorApi
      .estimateCompetency({})
      .then((body) => {
        // apiClient already unwraps axios response.data
        if (body?.status && body.status !== 'completed') {
          setError(body.error?.message || `Status: ${body.status}`)
          setPayload(body)
          return
        }
        setPayload(body)
      })
      .catch((err) => {
        setError(err.message || 'Progress could not be loaded.')
        setPayload(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const result = payload?.result || {}
  const estimates = enrichEstimates(result)
  const withEvidence = estimates.filter((item) => (item.observation_count || 0) > 0)
  const unknown = estimates.filter((item) => item.mastery_probability == null)

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={['AI Tutor', 'Progress & Results']}
        title="Progress and results"
        description="Concept-level BKT mastery from chronological MCP attempts with Boolean is_correct. Learning views are not used as competency."
        actions={
          <Button onClick={runAnalysis} loading={loading} disabled={loading}>
            <Play className="h-4 w-4" />
            Refresh analysis
          </Button>
        }
      />
      <LivePipelineBanner mode="live" />

      {loading && <p className="text-sm text-muted-foreground">Refreshing competency estimates…</p>}
      {error && (
        <EmptyState title="Progress unavailable" description={error} actionLabel="Try again" onAction={runAnalysis} />
      )}

      {!payload && !loading && !error && (
        <Card className="p-6">
          <p className="text-sm text-muted-foreground">
            Run analysis to load live mastery estimates, or open{' '}
            <Link className="underline" to={team('/tutor/guidance')}>
              Sprint guidance
            </Link>{' '}
            first.
          </p>
          <Button className="mt-3" onClick={runAnalysis}>
            <Play className="h-4 w-4" />
            Run analysis
          </Button>
        </Card>
      )}

      {payload?.status === 'completed' && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <SummaryCard label="Concepts tracked" value={String(estimates.length)} />
            <SummaryCard label="With observations" value={String(withEvidence.length)} />
            <SummaryCard label="Unknown (no evidence)" value={String(unknown.length)} />
            <SummaryCard
              label="Required-concept evidence"
              value={String(result.performance_evidence_count ?? 0)}
            />
          </div>

          <Card className="p-4">
            <p className="text-xs text-muted-foreground">
              Research note: mastery uses baseline BKT parameters (not trained). Missing usable
              evidence returns null mastery — never coerced to zero.
            </p>
          </Card>

          <div className="flex justify-end">
            <Button asChild variant="outline" size="sm">
              <Link to={team('/tutor/guidance')}>
                <Route className="h-3.5 w-3.5" />
                Back to guidance
              </Link>
            </Button>
          </div>

          <div className="grid gap-3 lg:grid-cols-2">
            {estimates.map((estimate) => (
              <BktMasteryCard key={estimate.concept_id} estimate={estimate} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}

function SummaryCard({ label, value }) {
  return (
    <Card className="p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </Card>
  )
}
