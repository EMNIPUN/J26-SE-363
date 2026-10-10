import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import EmptyState from '../../../shared/components/EmptyState.jsx'
import PageHeader from '../../../shared/components/PageHeader.jsx'
import { useTeamPath } from '../../../shared/hooks/useTeamPath.js'
import { CONCEPTS } from '../data/tutorWorkspace.js'
import SampleBanner from '../components/SampleBanner.jsx'
import { tutorWorkspaceService } from '../services/tutorWorkspaceService.js'

export default function Progress() {
  const team = useTeamPath()
  const [workspace, setWorkspace] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reloadKey, setReloadKey] = useState(0)

  const load = () => {
    setLoading(true)
    setError(null)
    setReloadKey((value) => value + 1)
  }

  useEffect(() => {
    let live = true
    tutorWorkspaceService
      .getProjectContext()
      .then((data) => {
        if (!live) return
        setWorkspace(data)
        setError(null)
        setLoading(false)
      })
      .catch((err) => {
        if (!live) return
        setError(err.message || 'Progress could not be loaded.')
        setLoading(false)
      })
    return () => {
      live = false
    }
  }, [reloadKey])

  const estimates = workspace?.estimates || []
  const byStatus = (status) => estimates.filter((item) => item.status === status)
  const completedExercises = (workspace?.exercises || []).filter((item) => item.status === 'Submitted')
  const recentConcepts = estimates
    .filter((item) => item.evidence.length > 0)
    .map((item) => CONCEPTS[item.conceptId]?.label)

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={['AI Tutor', 'Progress & Results']}
        title="Progress and results"
        description="Evidence on file, and the competency snapshot the sample service returned. Opening a reading is not counted as competency."
      />
      <SampleBanner />
      {loading && <p className="text-sm text-muted-foreground">Loading progress…</p>}
      {error && <EmptyState title="Progress unavailable" description={error} actionLabel="Try again" onAction={load} />}
      {workspace && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <SummaryCard label="Exercises submitted" value={String(completedExercises.length)} />
            <SummaryCard label="Assessment attempts" value={String(workspace.attempts.length)} />
            <SummaryCard label="Concepts with evidence" value={String(recentConcepts.length)} />
            <SummaryCard label="Demonstrated" value={labels(byStatus('Demonstrated'))} />
            <SummaryCard label="Developing" value={labels(byStatus('Developing'))} />
            <SummaryCard label="Needs attention" value={labels(byStatus('Needs Attention'))} />
            <SummaryCard label="Insufficient evidence" value={labels(byStatus('Insufficient Evidence'))} />
          </div>

          <Card className="p-5">
            <h2 className="text-sm font-semibold">Competency over time</h2>
            {workspace.competencyHistory.length === 0 ? (
              <p className="mt-2 text-sm text-muted-foreground">
                No historical competency series was returned. The figures above are one sample snapshot, not a trend.
              </p>
            ) : null}
          </Card>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="p-5">
              <h2 className="text-sm font-semibold">Evidence history</h2>
              <ul className="mt-3 space-y-3">
                {workspace.evidence.map((item) => (
                  <li key={item.id} className="border-b border-border pb-3 last:border-0 last:pb-0">
                    <p className="text-sm font-medium">{item.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {item.kind} · {item.when} · {CONCEPTS[item.conceptId]?.label}
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">{item.detail}</p>
                  </li>
                ))}
              </ul>
            </Card>
            <Card className="p-5">
              <h2 className="text-sm font-semibold">Recommendation history</h2>
              <ul className="mt-3 space-y-3">
                {workspace.recommendationHistory.map((item) => (
                  <li key={item.id} className="border-b border-border pb-3 last:border-0 last:pb-0">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium">{item.intervention}</p>
                      <span className="text-xs text-muted-foreground">{item.completed ? 'Completed' : 'Open'}</span>
                    </div>
                    <p className="text-xs text-muted-foreground">{CONCEPTS[item.conceptId]?.label}</p>
                    <p className="mt-1 text-sm text-muted-foreground">{item.reason}</p>
                    <p className="mt-1 text-xs text-muted-foreground">Follow-up: {item.followUp}</p>
                  </li>
                ))}
              </ul>
            </Card>
          </div>

          <Card className="space-y-3 p-5">
            <h2 className="text-sm font-semibold">What the snapshot is based on</h2>
            <p className="text-sm leading-relaxed text-muted-foreground">{workspace.explanation}</p>
            <Button asChild variant="outline" size="sm">
              <Link to={team('/tutor/guidance')}>Back to sprint guidance</Link>
            </Button>
          </Card>
        </>
      )}
    </div>
  )
}

function labels(items) {
  if (!items.length) return 'None in this snapshot'
  return items.map((item) => CONCEPTS[item.conceptId]?.label).join(', ')
}

function SummaryCard({ label, value }) {
  return (
    <Card className="p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold leading-snug">{value}</p>
    </Card>
  )
}
