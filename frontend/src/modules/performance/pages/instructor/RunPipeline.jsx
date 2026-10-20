import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, FileText, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import Badge from '@/shared/components/Badge.jsx'
import PageHeader from '@/shared/components/PageHeader.jsx'
import { assessmentApi } from '../../assessment/assessmentApi.js'
import { useRunEvents } from '../../assessment/useRunEvents.js'
import { nodeStates, studentsIn } from '../../assessment/pipelineModel.js'
import PipelineCanvas from '../../assessment/PipelineCanvas.jsx'
import IdentityMapForm from '../../assessment/IdentityMapForm.jsx'

const TONE = { queued: 'neutral', running: 'primary', waiting_human: 'warning', succeeded: 'success', failed: 'danger', cancelled: 'neutral' }
const LEVEL = { error: 'text-destructive', warn: 'text-amber-600', info: 'text-foreground' }

function NodeDrawer({ path, events, onClose }) {
  const mine = events.filter((e) => e.node_path === path || e.node_path.startsWith(`${path}/`))
  return (
    <aside className="rounded-xl border bg-card p-4 space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold break-all">{path}</h3>
        <Button size="sm" variant="ghost" onClick={onClose}>Close</Button>
      </div>
      {mine.length === 0 && <p className="text-xs text-muted-foreground">Nothing has happened in this node yet.</p>}
      <ol className="max-h-80 overflow-auto space-y-1 font-mono text-xs">
        {mine.map((e) => (
          <li key={e.seq} className="flex gap-2">
            <span className="text-muted-foreground shrink-0">{String(e.ts).slice(11, 19)}</span>
            <span className="shrink-0 w-20 text-muted-foreground">{e.type}</span>
            <span className={LEVEL[e.level] || ''}>{e.message}</span>
          </li>
        ))}
      </ol>
    </aside>
  )
}

export default function RunPipeline() {
  const { runId } = useParams()
  const client = useQueryClient()
  const graph = useQuery({ queryKey: ['perf-graph'], queryFn: assessmentApi.graph, staleTime: Infinity })
  const { events, status, mode } = useRunEvents(runId)
  const run = useQuery({ queryKey: ['perf-run', runId, status], queryFn: () => assessmentApi.run(runId) })
  const reviews = useQuery({ queryKey: ['perf-reviews-run', runId, status], queryFn: () => assessmentApi.reviews('open'), enabled: status === 'waiting_human' })
  const [student, setStudent] = useState(null)
  const [selected, setSelected] = useState(null)

  const states = useMemo(() => nodeStates(events), [events])
  const students = useMemo(() => studentsIn(events), [events])
  const lane = student || students[0]?.id || null
  const identityReview = (reviews.data || []).find((r) => r.run_id === runId && r.kind === 'identity_mapping')
  const current = status || run.data?.status

  const cancel = async () => {
    await assessmentApi.cancelRun(runId)
    client.invalidateQueries({ queryKey: ['perf-run'] })
  }
  const report = async () => {
    const text = await assessmentApi.report(runId)
    const url = URL.createObjectURL(new Blob([text], { type: 'text/markdown' }))
    Object.assign(document.createElement('a'), { href: url, download: `assessment-${runId}.md` }).click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Assessment run"
        description={run.data ? `Team ${run.data.team_ref}, sprint ${run.data.sprint_id}, ${run.data.mode === 'final' ? 'final' : 'provisional snapshot'}` : ''}
        actions={
          <>
            <Badge tone={TONE[current] || 'neutral'}>{current?.replace('_', ' ') || 'loading'}</Badge>
            <Badge tone="neutral">{mode === 'live' ? 'live' : mode === 'polling' ? 'updating every 2 s' : mode}</Badge>
            {['queued', 'running', 'waiting_human'].includes(current) && <Button size="sm" variant="outline" onClick={cancel}><XCircle className="h-4 w-4" /> Cancel</Button>}
            {current === 'succeeded' && <Button size="sm" variant="outline" onClick={report}><FileText className="h-4 w-4" /> Report</Button>}
            <Button size="sm" variant="ghost" asChild><Link to="../assessment"><ArrowLeft className="h-4 w-4" /> Back</Link></Button>
          </>
        }
      />
      {current === 'waiting_human' && identityReview && <IdentityMapForm runId={runId} review={identityReview} onDone={() => client.invalidateQueries({ queryKey: ['perf-run'] })} />}
      {current === 'failed' && run.data?.error && <p className="rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm">The run failed: {run.data.error.type}: {run.data.error.message}</p>}
      {graph.data ? (
        <div className="grid gap-5 xl:grid-cols-[1fr_380px]">
          <PipelineCanvas
            topology={graph.data}
            states={states}
            student={lane}
            selected={selected}
            onSelect={(path) => setSelected(path)}
            studentPicker={
              students.length > 0 && (
                <select className="rounded-md border bg-background px-2 py-1 text-xs" value={lane || ''} onChange={(e) => setStudent(e.target.value)}>
                  {students.map((s) => <option key={s.id} value={s.id}>{s.id}{s.state === 'done' ? ' (done)' : s.state === 'failed' ? ' (failed)' : ''}</option>)}
                </select>
              )
            }
          />
          <div className="space-y-3 xl:sticky xl:top-4 self-start">
            {selected ? <NodeDrawer path={selected} events={events} onClose={() => setSelected(null)} /> : <p className="text-sm text-muted-foreground">Click a node to see its log.</p>}
            <div className="rounded-xl border bg-card p-3">
              <h3 className="text-sm font-semibold mb-1">Latest</h3>
              <ol className="space-y-1 text-xs font-mono max-h-64 overflow-auto">
                {events.filter((e) => e.type === 'log').slice(-12).reverse().map((e) => <li key={e.seq}><span className="text-muted-foreground">{e.node_path.split('/').pop()}</span> {e.message}</li>)}
              </ol>
            </div>
          </div>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">Loading the pipeline…</p>
      )}
    </div>
  )
}
