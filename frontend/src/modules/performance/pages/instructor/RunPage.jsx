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
import AgentActivityFeed from '../../assessment/AgentActivityFeed.jsx'
import PipelineFlow from '../../assessment/PipelineFlow.jsx'
import { PipelineSkeleton } from '../../assessment/Reveal.jsx'
import { useFillHeight } from '../../assessment/useFillHeight.js'
import { useRunEvents } from '../../assessment/useRunEvents.js'
import { RunPill } from '../../assessment/visuals.jsx'

const ACTIVE = ['queued', 'running', 'waiting_human']

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
  const results = useQuery({ queryKey: assessmentKeys.overview(teamId, run.data?.sprint_id), queryFn: () => assessmentApi.overview(teamId, run.data.sprint_id), enabled: Boolean(run.data) })
  const reviews = useQuery({ queryKey: [...assessmentKeys.reviews, 'run', runId, status], queryFn: () => assessmentApi.reviews('open'), enabled: status === 'waiting_human' })
  const [student, setStudent] = useState(null)
  const [selected, setSelected] = useState(null)
  const [replayAt, setReplayAt] = useState(null) // null: show everything; a number: show the first n events
  const [playing, setPlaying] = useState(false)
  const timer = useRef(null)
  const root = useRef(null)
  const fixed = useFillHeight(root) // on a wide screen the page is one fixed screen: the pipeline and the logs scroll on their own

  const current = status || run.data?.status
  const active = ACTIVE.includes(current)
  const names = useMemo(() => {
    const map = {}
    if (!results.data) return map
    if (Array.isArray(results.data.roster)) {
      for (const r of results.data.roster) {
        const sid = r.student_id || r.id
        const name = (r.names && r.names[0]) || r.name || (r.logins && r.logins[0]) || sid
        if (sid) map[sid] = name
      }
    }
    const rows = Array.isArray(results.data.rows)
      ? results.data.rows
      : Array.isArray(results.data)
        ? results.data
        : []
    for (const r of rows) {
      const sid = r.student_id || r.id
      const name = r.student?.name || r.name || sid
      if (sid) map[sid] = name
    }
    return map
  }, [results.data])
  const shown = replayAt == null ? events : events.slice(0, replayAt)
  const identityReview = (reviews.data || []).find((r) => r.run_id === runId && r.kind === 'identity_mapping')
  const sprintUrl = `/teams/${teamId}/performance/team/results`

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
    const text = await assessmentApi.runReport(runId)
    const url = URL.createObjectURL(new Blob([text], { type: 'text/markdown' }))
    Object.assign(document.createElement('a'), { href: url, download: `assessment-${runId}.md` }).click()
    URL.revokeObjectURL(url)
  }

  const took = run.data?.started_at && run.data?.finished_at ? (new Date(run.data.finished_at) - new Date(run.data.started_at)) / 1000 : null

  return (
    <div ref={root} style={fixed ? { height: fixed } : undefined} className={fixed ? 'flex flex-col gap-4 overflow-hidden' : 'space-y-5'}>
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" asChild aria-label="Back to the assessment"><Link to={sprintUrl}><ArrowLeft className="h-4 w-4" /></Link></Button>
          <div>
            <h1 className="flex items-center gap-3 text-lg font-semibold text-foreground">
              {run.data ? `${run.data.mode === 'final' ? 'Final assessment' : 'Snapshot'} of sprint ${run.data.sprint_id}` : 'Assessment run'}
              {current && <RunPill status={current} />}
            </h1>
            <p className="text-sm text-muted-foreground">
              {team.data?.name}{run.data && ` · started ${when(run.data.created_at)}`}{took != null && ` · took ${duration(took)}`}
              {active && <span className="ml-2">{mode === 'live' ? '· live' : mode === 'polling' ? '· updating every 2 s' : ''}</span>}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {active && <Button size="sm" variant="outline" onClick={cancel}><XCircle className="h-4 w-4" />Cancel</Button>}
          {!active && current && <Button size="sm" variant="outline" onClick={rerun}><RefreshCw className="h-4 w-4" />Re-evaluate</Button>}
          {run.data?.has_report && <Button size="sm" variant="outline" onClick={report}><FileText className="h-4 w-4" />Report</Button>}
        </div>
      </div>

      {current === 'failed' && run.data?.error && <p className="shrink-0 rounded-lg border border-l-2 border-l-rose-500 bg-card px-4 py-2.5 text-sm text-foreground"><span className="font-medium">The run failed.</span> <span className="text-muted-foreground">{run.data.error.message}</span></p>}

      {!active && events.length > 0 && (
        <Card className="shrink-0 flex-row flex-wrap items-center gap-3 px-3 py-2 shadow-none">
          <Button size="sm" variant={playing ? 'secondary' : 'outline'} onClick={() => { if (!playing && replayAt == null) setReplayAt(0); setPlaying(!playing) }}>{playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}{playing ? 'Pause' : 'Replay'}</Button>
          <input type="range" min="0" max={events.length} value={replayAt ?? events.length} onChange={(e) => { setPlaying(false); setReplayAt(Number(e.target.value) >= events.length ? null : Number(e.target.value)) }} className="min-w-48 flex-1 accent-primary" aria-label="Replay position" />
          <span className="w-28 text-right text-xs tabular-nums text-muted-foreground">{replayAt == null ? 'final state' : `event ${replayAt} of ${events.length}`}</span>
          <Button size="icon" variant="ghost" aria-label="Back to the final state" onClick={() => { setPlaying(false); setReplayAt(null) }}><RotateCcw className="h-4 w-4" /></Button>
        </Card>
      )}

      {graph.data ? (
        <div className="grid min-h-0 flex-1 gap-5 @4xl:grid-cols-[minmax(0,1fr)_440px] @4xl:grid-rows-[minmax(0,1fr)]">
          <section className="flex min-h-0 flex-col overflow-hidden rounded-xl border border-foreground/15 bg-card shadow-sm">
            <div className="shrink-0 border-b px-4 py-2.5"><h2 className="text-sm font-semibold text-foreground">Pipeline</h2></div>
            <div className="min-h-0 flex-1 overflow-y-auto bg-muted/40 px-4 py-4">
              <div className="max-w-3xl">
                <PipelineFlow topology={graph.data} events={shown} student={student} onStudent={setStudent} selected={selected} onSelect={setSelected} names={names} />
              </div>
            </div>
          </section>
          <div className="min-h-0 h-full overflow-hidden">
            <AgentActivityFeed
              events={shown}
              current={current}
              identityReview={identityReview}
              runId={runId}
              onReviewDone={() => qc.invalidateQueries({ queryKey: ['assessment'] })}
              names={names}
            />
          </div>
        </div>
      ) : <PipelineSkeleton />}
    </div>
  )
}
