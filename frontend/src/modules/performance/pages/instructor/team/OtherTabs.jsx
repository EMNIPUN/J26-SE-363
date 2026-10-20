import { useState } from 'react'
import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { CheckCircle2, FileText, GitBranch, History, Play, Plus, RefreshCw, Trash2, Workflow } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import EmptyState from '@/shared/components/EmptyState.jsx'
import { showToast } from '@/shared/utils/toast.jsx'
import { MEMBER_STATE } from '@/shared/github/githubService.js'
import Badge from '@/shared/components/Badge.jsx'
import { assessmentApi, assessmentKeys } from '../../../assessment/assessmentApi.js'
import { duration, when } from '../../../assessment/format.js'
import { Avatar, RunPill } from '../../../assessment/visuals.jsx'

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ec4899', '#0ea5e9', '#8b5cf6', '#ef4444', '#14b8a6']

/** The predicted mark of every student over the days of the sprint. */
export function DevelopmentTab({ team, sprint, rows }) {
  const queries = useQueries({ queries: (rows || []).map((r) => ({ queryKey: assessmentKeys.trajectory(team, sprint, r.student_id), queryFn: () => assessmentApi.trajectory(team, sprint, r.student_id) })) })
  if (!rows?.length) return <EmptyState icon={History} title="Nothing to plot yet" description="The development view fills in as snapshots are taken during the sprint." />
  const byDay = new Map()
  queries.forEach((q, i) => (q.data || []).forEach((p) => {
    const day = new Date(p.as_of).toISOString().slice(0, 10)
    byDay.set(day, { ...(byDay.get(day) || { day }), [rows[i].student?.name || rows[i].student_id]: p.mark == null ? null : Math.round(p.mark) })
  }))
  const data = [...byDay.values()].sort((a, b) => a.day.localeCompare(b.day))
  return (
    <Card className="gap-3 p-5">
      <div>
        <h3 className="text-sm font-semibold text-foreground">Predicted mark during the sprint</h3>
        <p className="text-xs text-muted-foreground">Each point is one snapshot. Early points rest on little evidence and move a lot; the line settles as the sprint goes on.</p>
      </div>
      {data.length < 2 ? <p className="rounded-lg bg-muted/50 p-4 text-sm text-muted-foreground">At least two snapshots are needed. One is taken every night while the sprint runs.</p> : (
        <div className="h-80">
          <ResponsiveContainer>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis dataKey="day" fontSize={11} /><YAxis domain={[0, 100]} fontSize={11} /><Tooltip /><Legend />
              {rows.map((r, i) => <Line key={r.student_id} dataKey={r.student?.name || r.student_id} stroke={COLORS[i % COLORS.length]} strokeWidth={2.2} connectNulls dot />)}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  )
}
DevelopmentTab.propTypes = { team: PropTypes.string, sprint: PropTypes.string, rows: PropTypes.array }

export function RunsTab({ runs, loading, base, onRerun, onReport, busy }) {
  if (loading) return <div className="h-32 animate-pulse rounded-xl bg-muted" />
  if (!runs?.length) return <EmptyState icon={Workflow} title="No assessment has run for this sprint" description="Start a snapshot or a final assessment above. You can watch each run live and open it again afterwards." />
  return (
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
  if (q.isPending) return <div className="h-32 animate-pulse rounded-xl bg-muted" />
  if (!list.length) return <EmptyState icon={CheckCircle2} title="Nothing waiting for you" description="When the agent finds something it cannot settle itself, for example work that looks higher than the student understands, it appears here." />
  return <div className="space-y-3">{list.map((r) => <ReviewItem key={r.id} review={r} onChanged={() => { qc.invalidateQueries({ queryKey: assessmentKeys.reviews }); qc.invalidateQueries({ queryKey: ['assessment'] }) }} />)}</div>
}
ReviewsTab.propTypes = { team: PropTypes.string }

const blank = () => ({ id: '', start: '', end: '' })

export function SetupTab({ team, tracking, readiness, membersPath }) {
  const qc = useQueryClient()
  const cfg = tracking?.config || {}
  const [sprints, setSprints] = useState(cfg.sprints?.length ? cfg.sprints : [blank()])
  const [release, setRelease] = useState(cfg.release_to_students ?? true)
  const [board, setBoard] = useState(tracking?.board_ref || team)
  const [saving, setSaving] = useState(false)
  const set = (i, k, v) => setSprints(sprints.map((s, j) => (j === i ? { ...s, [k]: v } : s)))
  const valid = sprints.every((s) => !s.id || (s.start && s.end && s.start <= s.end))

  const save = async () => {
    setSaving(true)
    try {
      await assessmentApi.saveSettings(team, { board_ref: board || null, release_to_students: release, sprints: sprints.filter((s) => s.id && s.start && s.end) })
      showToast.success('Saved')
      qc.invalidateQueries({ queryKey: ['assessment', team] })
    } catch (e) {
      showToast.error(e.message)
    } finally {
      setSaving(false)
    }
  }
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <Card className="gap-4 p-5">
        <div className="flex items-start justify-between gap-3">
          <div><h3 className="flex items-center gap-2 text-sm font-semibold"><GitBranch className="h-4 w-4" />Repository and people</h3><p className="text-xs text-muted-foreground">Linked by the team leader through GitHub. Nobody types a roster.</p></div>
          {readiness && <Badge tone={readiness.ready ? 'success' : 'warning'}>{readiness.ready ? 'Ready to assess' : 'Not ready'}</Badge>}
        </div>
        {readiness?.repo && <p className="font-mono text-sm">{readiness.repo}</p>}
        {(readiness?.blockers || []).map((b) => <p key={b} className="rounded-lg bg-amber-50 p-2 text-sm text-amber-900 dark:bg-amber-950/30 dark:text-amber-200">{b}</p>)}
        <ul className="divide-y rounded-lg border">
          {(readiness?.members || []).map((m) => {
            const s = MEMBER_STATE[m.state] || MEMBER_STATE.not_connected
            return <li key={m.user_id} className="flex items-center gap-3 px-3 py-2 text-sm"><Avatar name={m.name} size={28} /><span className="flex-1">{m.name}{m.login && <span className="ml-2 font-mono text-xs text-muted-foreground">@{m.login}</span>}</span><Badge tone={s.tone} title={s.help}>{s.label}</Badge></li>
          })}
        </ul>
        {(readiness?.notes || []).length > 0 && <p className="text-xs text-muted-foreground">{readiness.notes.length} member{readiness.notes.length > 1 ? 's' : ''} can still be assessed, but commits that cannot be matched to them will be sent to you to map.</p>}
        <Button variant="outline" size="sm" asChild className="w-fit"><Link to={membersPath}>Manage the GitHub link</Link></Button>
      </Card>

      <Card className="gap-4 p-5">
        <div><h3 className="text-sm font-semibold">Sprints</h3><p className="text-xs text-muted-foreground">The sprint id must match the id on the Scrum board.</p></div>
        <div className="space-y-2">
          {sprints.map((s, i) => (
            <div key={i} className="grid grid-cols-[1.2fr_1fr_1fr_auto] items-center gap-2">
              <Input aria-label="Sprint id" placeholder="Sprint id" value={s.id} onChange={(e) => set(i, 'id', e.target.value)} />
              <Input aria-label="Start" type="date" value={s.start} onChange={(e) => set(i, 'start', e.target.value)} />
              <Input aria-label="End" type="date" value={s.end} onChange={(e) => set(i, 'end', e.target.value)} />
              <Button size="icon" variant="ghost" aria-label="Remove sprint" onClick={() => setSprints(sprints.filter((_, j) => j !== i))}><Trash2 className="h-4 w-4" /></Button>
            </div>
          ))}
          <Button size="sm" variant="outline" onClick={() => setSprints([...sprints, blank()])}><Plus className="h-4 w-4" />Add a sprint</Button>
        </div>
        <label className="grid gap-1 text-sm">Scrum board id<Input value={board} onChange={(e) => setBoard(e.target.value)} placeholder={team} /></label>
        <label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" checked={release} onChange={(e) => setRelease(e.target.checked)} /><span>Students can see their own predicted mark and feedback<span className="block text-xs text-muted-foreground">Results under review are hidden from them until you have decided.</span></span></label>
        <Button onClick={save} disabled={saving || !valid} className="w-fit"><Play className="h-4 w-4" />Save settings</Button>
        {!valid && <p className="text-xs text-rose-600">A sprint must end on or after the day it starts.</p>}
      </Card>
    </div>
  )
}
SetupTab.propTypes = { team: PropTypes.string, tracking: PropTypes.object, readiness: PropTypes.object, membersPath: PropTypes.string }

