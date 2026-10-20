import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, FileText, Pause, Play, RefreshCw, RotateCcw, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useConfirm } from '@/shared/utils/useConfirm.js'
import { showToast } from '@/shared/utils/toast.jsx'
import { useTeam } from '@/shared/hooks/useTeams.js'
import { assessmentApi, assessmentKeys } from '../../assessment/assessmentApi.js'
import { duration, when } from '../../assessment/format.js'
import IdentityMapForm from '../../assessment/IdentityMapForm.jsx'
import PipelineFlow from '../../assessment/PipelineFlow.jsx'
import { useRunEvents } from '../../assessment/useRunEvents.js'
import { RunPill } from '../../assessment/visuals.jsx'

const LEVEL = { error: 'text-rose-600', warn: 'text-amber-600', info: 'text-foreground' }
const ACTIVE = ['queued', 'running', 'waiting_human']

function Drawer({ path, events, names, onClose }) {
  const who = path.startsWith('student:') ? path.slice(8, path.indexOf('/')) : null
  const mine = events.filter((e) => e.node_path === path || e.node_path.startsWith(`${path}/`))
  return (
    <Card className="gap-3 p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-foreground">{path.split('/').pop().replace(/_/g, ' ')}</p>
          <p className="truncate text-xs text-muted-foreground">{who ? names?.[who] || who : 'team run'}</p>
        </div>
        <Button size="sm" variant="ghost" onClick={onClose}>Close</Button>
      </div>
      {mine.length === 0 && <p className="text-xs text-muted-foreground">Nothing has happened in this step yet.</p>}
      <ol className="max-h-[28rem] space-y-1.5 overflow-auto pr-1 font-mono text-[11px] leading-relaxed">
        {mine.map((e) => (
          <li key={e.seq} className="flex gap-2">
            <span className="shrink-0 text-muted-foreground">{String(e.ts).slice(11, 19)}</span>
            <span className={`min-w-0 break-words ${LEVEL[e.level] || ''}`}>{e.type !== 'log' && <span className="mr-1 rounded bg-muted px-1 text-muted-foreground">{e.type.replace('node_', '')}</span>}{e.message}</span>
          </li>
        ))}
      </ol>
    </Card>
  )
}

/**
 * One run, seen as a flow. A live run lights up as it goes; a finished run opens on its final state and can be replayed from the first event.
 * Only lecturers and administrators of the team can open it (the API refuses everyone else).
 */
export default function RunPage() {
  const { teamId, runId } = useParams()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const confirm = useConfirm()
  const team = useTeam(teamId)
  const graph = useQuery({ queryKey: assessmentKeys.graph, queryFn: assessmentApi.graph, staleTime: Infinity })
  const { events, status, mode } = useRunEvents(runId)
  const run = useQuery({ queryKey: [...assessmentKeys.run(runId), status], queryFn: () => assessmentApi.run(runId) })
  const results = useQuery({ queryKey: assessmentKeys.results(teamId, run.data?.sprint_id), queryFn: () => assessmentApi.results(teamId, run.data.sprint_id), enabled: Boolean(run.data) })
  const reviews = useQuery({ queryKey: [...assessmentKeys.reviews, 'run', runId, status], queryFn: () => assessmentApi.reviews('open'), enabled: status === 'waiting_human' })
  const [student, setStudent] = useState(null)
  const [selected, setSelected] = useState(null)
  const [replayAt, setReplayAt] = useState(null) // null: show everything; a number: show the first n events
  const [playing, setPlaying] = useState(false)
  const timer = useRef(null)

  const current = status || run.data?.status
  const active = ACTIVE.includes(current)
  const names = useMemo(() => Object.fromEntries((results.data || []).map((r) => [r.student_id, r.student?.name])), [results.data])
  const shown = replayAt == null ? events : events.slice(0, replayAt)
  const identityReview = (reviews.data || []).find((r) => r.run_id === runId && r.kind === 'identity_mapping')
  const sprintUrl = `/teams/${teamId}/performance/assessment?sprint=${encodeURIComponent(run.data?.sprint_id || '')}`

  useEffect(() => {
    if (!playing) return undefined
    timer.current = setInterval(() => setReplayAt((n) => {
      const next = (n ?? 0) + Math.max(1, Math.ceil(events.length / 120))
      if (next >= events.length) { setPlaying(false); return null }
      return next
    }), 120)
    return () => clearInterval(timer.current)
  }, [playing, events.length])

  const cancel = async () => {
    await assessmentApi.cancelRun(runId)
    qc.invalidateQueries({ queryKey: ['assessment'] })
  }
  const rerun = async () => {
    const ok = await confirm({ title: 'Evaluate again?', description: 'A new run of the same kind starts from the repository as it is now. This run stays as it is.', confirmText: 'Evaluate again' })
    if (!ok) return
    try {
      const r = await assessmentApi.rerun(runId)
      showToast.success('Started')
      qc.invalidateQueries({ queryKey: ['assessment'] })
      navigate(`/teams/${teamId}/performance/runs/${r.run_id}`)
    } catch (e) {
      showToast.error(e.message)
    }
  }
  const report = async () => {
    const text = await assessmentApi.report(runId)
    const url = URL.createObjectURL(new Blob([text], { type: 'text/markdown' }))
    Object.assign(document.createElement('a'), { href: url, download: `assessment-${runId}.md` }).click()
    URL.revokeObjectURL(url)
  }

  const took = run.data?.started_at && run.data?.finished_at ? (new Date(run.data.finished_at) - new Date(run.data.started_at)) / 1000 : null

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" asChild aria-label="Back to the assessment"><Link to={sprintUrl}><ArrowLeft className="h-4 w-4" /></Link></Button>
          <div>
            <h1 className="flex items-center gap-3 text-xl font-semibold tracking-tight text-foreground">
              {run.data ? `${run.data.mode === 'final' ? 'Final assessment' : 'Snapshot'} of sprint ${run.data.sprint_id}` : 'Assessment run'}
              {current && <RunPill status={current} />}
            </h1>
            <p className="text-sm text-muted-foreground">
              {team.data?.name}{run.data && ` · started ${when(run.data.created_at)}`}{took != null && ` · took ${duration(took)}`}
              {active && <span className="ml-2 text-primary">{mode === 'live' ? '· live' : mode === 'polling' ? '· updating every 2 s' : ''}</span>}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {active && <Button size="sm" variant="outline" onClick={cancel}><XCircle className="h-4 w-4" />Cancel</Button>}
          {!active && current && <Button size="sm" variant="outline" onClick={rerun}><RefreshCw className="h-4 w-4" />Re-evaluate</Button>}
          {run.data?.has_report && <Button size="sm" variant="outline" onClick={report}><FileText className="h-4 w-4" />Report</Button>}
        </div>
      </div>

      {current === 'waiting_human' && identityReview && <IdentityMapForm runId={runId} review={identityReview} onDone={() => qc.invalidateQueries({ queryKey: ['assessment'] })} />}
      {current === 'failed' && run.data?.error && <p className="rounded-xl border border-rose-300 bg-rose-50 p-3 text-sm text-rose-900 dark:bg-rose-950/30 dark:text-rose-200">The run failed: {run.data.error.message}</p>}

      {!active && events.length > 0 && (
        <Card className="flex-row flex-wrap items-center gap-3 p-3">
          <Button size="sm" variant={playing ? 'secondary' : 'outline'} onClick={() => { if (!playing && replayAt == null) setReplayAt(0); setPlaying(!playing) }}>{playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}{playing ? 'Pause' : 'Replay'}</Button>
          <input type="range" min="0" max={events.length} value={replayAt ?? events.length} onChange={(e) => { setPlaying(false); setReplayAt(Number(e.target.value) >= events.length ? null : Number(e.target.value)) }} className="min-w-48 flex-1 accent-primary" aria-label="Replay position" />
          <span className="w-28 text-right text-xs tabular-nums text-muted-foreground">{replayAt == null ? 'final state' : `event ${replayAt} of ${events.length}`}</span>
          <Button size="icon" variant="ghost" aria-label="Back to the final state" onClick={() => { setPlaying(false); setReplayAt(null) }}><RotateCcw className="h-4 w-4" /></Button>
        </Card>
      )}

      {graph.data ? (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="max-w-3xl"><PipelineFlow topology={graph.data} events={shown} student={student} onStudent={setStudent} selected={selected} onSelect={setSelected} names={names} /></div>
          <div className="space-y-4 xl:sticky xl:top-4 xl:self-start">
            {selected ? <Drawer path={selected} events={shown} names={names} onClose={() => setSelected(null)} /> : <Card className="p-4 text-sm text-muted-foreground">Choose a step to read what it did, line by line.</Card>}
            <Card className="gap-2 p-4">
              <h3 className="text-sm font-semibold">Latest</h3>
              <ol className="max-h-72 space-y-1 overflow-auto font-mono text-[11px]">
                {shown.filter((e) => e.type === 'log').slice(-12).reverse().map((e) => <li key={e.seq} className="flex gap-2"><span className="shrink-0 text-muted-foreground">{e.node_path.split('/').pop().replace(/_/g, ' ')}</span><span className={`min-w-0 break-words ${LEVEL[e.level] || ''}`}>{e.message}</span></li>)}
              </ol>
            </Card>
          </div>
        </div>
      ) : <div className="h-64 animate-pulse rounded-xl bg-muted" aria-busy="true" />}
    </div>
  )
}
