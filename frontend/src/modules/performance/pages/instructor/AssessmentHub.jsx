import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Activity, GitBranch, Play, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import Badge from '@/shared/components/Badge.jsx'
import PageHeader from '@/shared/components/PageHeader.jsx'
import { assessmentApi } from '../../assessment/assessmentApi.js'
import TrackingForm from '../../assessment/TrackingForm.jsx'
import ReviewQueue from '../../assessment/ReviewQueue.jsx'
import StudentResultPanel from '../../assessment/StudentResultPanel.jsx'
import { FACTOR_LABEL } from '../../assessment/factorLabels.js'

const STATUS_TONE = { final: 'success', provisional: 'primary', pending_review: 'warning' }
const RUN_TONE = { queued: 'neutral', running: 'primary', waiting_human: 'warning', succeeded: 'success', failed: 'danger', cancelled: 'neutral' }
const COLUMNS = ['effort', 'consistency', 'requirement_fulfillment', 'collaboration', 'task_complexity', 'code_ownership']

function cell(f) {
  if (!f) return '–'
  if (f.status === 'completed' && f.score != null) return `${f.score.toFixed(2)}${f.provisional ? '*' : ''}`
  return { not_available: 'n/a', pending: 'pending', fallback: 'failed' }[f.status] || f.status
}

function Results({ team, sprint }) {
  const results = useQuery({ queryKey: ['perf-results', team, sprint], queryFn: () => assessmentApi.results(team, sprint), refetchInterval: 15000 })
  const [open, setOpen] = useState(null)
  const traj = useQuery({ queryKey: ['perf-traj', team, sprint, open], queryFn: () => assessmentApi.trajectory(team, sprint, open), enabled: Boolean(open) })
  if (!results.data?.length) return <p className="text-sm text-muted-foreground">No results yet for this sprint. Start a snapshot or a final run.</p>
  const selected = results.data.find((r) => r.student_id === open)
  return (
    <div className="space-y-4">
      <div className="overflow-auto rounded-xl border bg-card">
        <table className="w-full text-sm">
          <thead className="text-xs text-muted-foreground">
            <tr className="border-b">
              <th className="p-2 text-left">Student</th><th className="p-2 text-right">Mark</th><th className="p-2 text-right">Range</th><th className="p-2">Status</th>
              {COLUMNS.map((c) => <th key={c} className="p-2 text-right whitespace-nowrap">{FACTOR_LABEL[c]}</th>)}
            </tr>
          </thead>
          <tbody>
            {results.data.map((r) => (
              <tr key={r.student_id} className={`border-b last:border-0 cursor-pointer hover:bg-accent/50 ${open === r.student_id ? 'bg-accent/60' : ''}`} onClick={() => setOpen(open === r.student_id ? null : r.student_id)}>
                <td className="p-2 font-medium">{r.student_id}</td>
                <td className="p-2 text-right font-semibold">{r.effective_mark == null ? 'n/a' : Math.round(r.effective_mark)}{r.override ? ' ✎' : ''}</td>
                <td className="p-2 text-right text-muted-foreground">{r.mark_interval ? `${Math.round(r.mark_interval[0])}–${Math.round(r.mark_interval[1])}` : ''}</td>
                <td className="p-2 text-center"><Badge tone={STATUS_TONE[r.status]}>{r.status.replace('_', ' ')}</Badge></td>
                {COLUMNS.map((c) => <td key={c} className="p-2 text-right tabular-nums">{cell(r.factors?.[c])}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-muted-foreground">* provisional · n/a: could not be measured and left out of the mark · pending: waiting for the student&apos;s answer to the code question · ✎ mark set by you</p>
      {selected && <div className="rounded-xl border bg-card p-5"><StudentResultPanel result={selected} trajectory={traj.data} /></div>}
    </div>
  )
}

function Team({ team, onStopped }) {
  const client = useQueryClient()
  const info = useQuery({ queryKey: ['perf-tracking', team], queryFn: () => assessmentApi.tracking(team) })
  const sprints = info.data?.config?.sprints || []
  const [sprint, setSprint] = useState('')
  const [editing, setEditing] = useState(false)
  const current = sprint || sprints[sprints.length - 1]?.id || ''
  const runs = useQuery({ queryKey: ['perf-runs', team, current], queryFn: () => assessmentApi.runs(team, current || undefined), refetchInterval: 5000 })

  const start = async (mode) => {
    if (!current) return toast.error('Add a sprint to this team first')
    const r = await assessmentApi.startRun(team, current, mode)
    toast.success(`${mode === 'final' ? 'Final' : 'Snapshot'} run queued`)
    client.invalidateQueries({ queryKey: ['perf-runs'] })
    return r
  }
  if (info.isLoading) return null
  if (editing) return <TrackingForm initial={info.data} onSaved={() => { setEditing(false); client.invalidateQueries({ queryKey: ['perf-tracking'] }) }} />

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="primary"><GitBranch className="h-3 w-3" />{info.data.repo_url.replace('https://', '')}</Badge>
        <Badge tone={info.data.status === 'active' ? 'success' : 'neutral'}>{info.data.status}</Badge>
        {info.data.config?.last_sync && <span className="text-xs text-muted-foreground">last sync {new Date(info.data.config.last_sync.at).toLocaleString()}</span>}
        <select className="ml-auto rounded-md border bg-background px-2 py-1 text-sm" value={current} onChange={(e) => setSprint(e.target.value)}>
          {sprints.map((s) => <option key={s.id} value={s.id}>{s.id}</option>)}
        </select>
        <Button size="sm" variant="outline" onClick={async () => { await assessmentApi.sync(team); toast.success('Sync queued') }}><RefreshCw className="h-4 w-4" /> Sync now</Button>
        <Button size="sm" variant="outline" onClick={() => start('snapshot')}><Activity className="h-4 w-4" /> Snapshot</Button>
        <Button size="sm" onClick={() => start('final')}><Play className="h-4 w-4" /> Final run</Button>
        <Button size="sm" variant="ghost" onClick={() => setEditing(true)}>Edit tracking</Button>
        <Button size="sm" variant="ghost" onClick={async () => { await assessmentApi.stopTracking(team); onStopped() }}>Stop</Button>
      </div>

      <section className="space-y-2">
        <h2 className="text-sm font-semibold">Runs</h2>
        {runs.data?.length ? (
          <ul className="divide-y rounded-xl border bg-card text-sm">
            {runs.data.slice(0, 8).map((r) => (
              <li key={r.id} className="flex items-center gap-3 p-2.5">
                <Badge tone={RUN_TONE[r.status]}>{r.status.replace('_', ' ')}</Badge>
                <span>{r.mode === 'final' ? 'Final' : 'Snapshot'} · {r.sprint_id}</span>
                <span className="text-xs text-muted-foreground">{new Date(r.created_at).toLocaleString()}</span>
                <Link className="ml-auto text-primary underline text-xs" to={`../runs/${r.id}`}>Watch the pipeline</Link>
              </li>
            ))}
          </ul>
        ) : <p className="text-sm text-muted-foreground">No run yet.</p>}
      </section>

      <section className="space-y-2"><h2 className="text-sm font-semibold">Results</h2>{current ? <Results team={team} sprint={current} /> : null}</section>
      <section className="space-y-2"><h2 className="text-sm font-semibold">Needs your review</h2><ReviewQueue team={team} /></section>
    </div>
  )
}

export default function AssessmentHub() {
  const client = useQueryClient()
  const teams = useQuery({ queryKey: ['perf-teams'], queryFn: assessmentApi.teams })
  const [team, setTeam] = useState(null)
  const [adding, setAdding] = useState(false)
  const list = teams.data || []
  const chosen = team || list.find((t) => t.status === 'active')?.team_ref || null

  return (
    <div className="space-y-6">
      <PageHeader
        title="Assessment agent"
        description="Give the agent a team's repository and Scrum board. It follows the sprint, assesses every student with the seven factors, checks its own results and explains each mark."
        actions={
          <>
            <select className="rounded-md border bg-background px-2 py-1.5 text-sm" value={chosen || ''} onChange={(e) => { setTeam(e.target.value); setAdding(false) }}>
              {list.map((t) => <option key={t.team_ref} value={t.team_ref}>{t.team_ref}{t.status !== 'active' ? ` (${t.status})` : ''}</option>)}
            </select>
            <Button size="sm" onClick={() => setAdding(true)}>Track a team</Button>
          </>
        }
      />
      {adding || (!teams.isLoading && !list.length)
        ? <TrackingForm onSaved={(t) => { setAdding(false); setTeam(t); client.invalidateQueries({ queryKey: ['perf-teams'] }) }} />
        : chosen && <Team key={chosen} team={chosen} onStopped={() => { setTeam(null); client.invalidateQueries({ queryKey: ['perf-teams'] }) }} />}
    </div>
  )
}
