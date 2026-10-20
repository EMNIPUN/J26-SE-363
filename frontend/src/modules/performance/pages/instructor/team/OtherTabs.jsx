import { useState } from 'react'
import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, FileText, History, RefreshCw, Workflow } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import EmptyState from '@/shared/components/EmptyState.jsx'
import { showToast } from '@/shared/utils/toast.jsx'
import { assessmentApi, assessmentKeys } from '../../../assessment/assessmentApi.js'
import { duration, when } from '../../../assessment/format.js'
import Panel from '../../../assessment/Panel.jsx'
import { RunPill } from '../../../assessment/visuals.jsx'
import { ChartSkeleton, ListSkeleton, Stagger, StatRowSkeleton } from '../../../assessment/Reveal.jsx'
import RunAnalysis from './RunAnalysis.jsx'

export function RunsTab({ runs, loading, base, onRerun, onReport, busy }) {
  if (loading) return <div className="space-y-6" aria-busy="true"><StatRowSkeleton /><ChartSkeleton height={220} /><ListSkeleton rows={4} /></div>
  if (!runs?.length) return <EmptyState icon={Workflow} title="No assessment has run for this sprint" description="Start a snapshot or a final assessment above. You can watch each run live and open it again afterwards." />
  return (
    <Stagger className="space-y-6">
      <RunAnalysis runs={runs} />
      <Panel title="All runs" icon={History} hint="Newest first. Open one to see its pipeline, read its report or run it again.">
    <div className="space-y-2">
      {runs.map((r) => {
        const took = r.started_at && r.finished_at ? (new Date(r.finished_at) - new Date(r.started_at)) / 1000 : null
        const active = ['queued', 'running', 'waiting_human'].includes(r.status)
        return (
          <Card key={r.id} className="flex-row flex-wrap items-center gap-x-4 gap-y-2 p-4">
            <RunPill status={r.status} />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-foreground">{r.mode === 'final' ? 'Final assessment' : 'Snapshot'} <span className="font-normal text-muted-foreground">of sprint {r.sprint_id}</span></p>
              <p className="text-xs text-muted-foreground">{when(r.created_at)}{took != null && ` · took ${duration(took)}`}{r.requested_by === 'schedule' && ' · scheduled'}{r.summary?.students != null && ` · ${r.summary.students} students`}</p>
              {r.error && <p className="text-xs text-rose-600">{r.error.message}</p>}
            </div>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" asChild><Link to={`${base}/runs/${r.id}`}><Workflow className="h-4 w-4" />{active ? 'Watch live' : 'Open pipeline'}</Link></Button>
              {r.has_report && <Button size="sm" variant="ghost" onClick={() => onReport(r.id)}><FileText className="h-4 w-4" />Report</Button>}
              {!active && <Button size="sm" variant="ghost" disabled={busy} onClick={() => onRerun(r)}><RefreshCw className="h-4 w-4" />Re-evaluate</Button>}
            </div>
          </Card>
        )
      })}
    </div>
      </Panel>
    </Stagger>
  )
}
RunsTab.propTypes = { runs: PropTypes.array, loading: PropTypes.bool, base: PropTypes.string, onRerun: PropTypes.func, onReport: PropTypes.func, busy: PropTypes.bool }

function ReviewItem({ review, onChanged }) {
  const [mark, setMark] = useState('')
  const [reason, setReason] = useState('')
  const [open, setOpen] = useState(false)
  const act = async (decision) => {
    await assessmentApi.decide(review.id, decision === 'override' ? { decision, mark: Number(mark), reason } : { decision, reason })
    showToast.success(decision === 'override' ? 'Mark set' : decision === 'rerun' ? 'Assessment started again' : 'Accepted')
    onChanged()
  }
  return (
    <Card className="gap-3 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <span className="font-medium">{review.kind === 'identity_mapping' ? 'Some commits could not be matched to a student' : 'The agent wants a person to look at this'}</span>
        <Link to={`../runs/${review.run_id}`} className="text-xs text-primary hover:underline">Open the run</Link>
      </div>
      <p className="text-sm text-muted-foreground">{review.reason}</p>
      {review.kind === 'identity_mapping' ? <p className="text-xs text-muted-foreground">Answer this on the run page; the run is waiting for it.</p> : open ? (
        <div className="flex flex-wrap items-center gap-2">
          <Input className="w-24" type="number" min="0" max="100" placeholder="Mark" value={mark} onChange={(e) => setMark(e.target.value)} />
          <Input className="min-w-56 flex-1" placeholder="Why (at least 10 characters)" value={reason} onChange={(e) => setReason(e.target.value)} />
          <Button size="sm" disabled={!mark || reason.trim().length < 10} onClick={() => act('override')}>Set mark</Button>
          <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={() => act('accept')}><CheckCircle2 className="h-4 w-4" />Accept the prediction</Button>
          <Button size="sm" variant="outline" onClick={() => setOpen(true)}>Set my own mark</Button>
          <Button size="sm" variant="outline" onClick={() => act('rerun')}>Run again</Button>
        </div>
      )}
    </Card>
  )
}
ReviewItem.propTypes = { review: PropTypes.object, onChanged: PropTypes.func }

export function ReviewsTab({ team }) {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: assessmentKeys.reviews, queryFn: () => assessmentApi.reviews('open') })
  const list = (q.data || []).filter((r) => r.team_ref.toLowerCase() === String(team).toLowerCase())
  if (q.isPending) return <ListSkeleton rows={3} />
  if (!list.length) return <EmptyState icon={CheckCircle2} title="Nothing waiting for you" description="When the agent finds something it cannot settle itself, for example work that looks higher than the student understands, it appears here." />
  return <Stagger className="space-y-3" step={80}>{list.map((r) => <ReviewItem key={r.id} review={r} onChanged={() => { qc.invalidateQueries({ queryKey: assessmentKeys.reviews }); qc.invalidateQueries({ queryKey: ['assessment'] }) }} />)}</Stagger>
}
ReviewsTab.propTypes = { team: PropTypes.string }

