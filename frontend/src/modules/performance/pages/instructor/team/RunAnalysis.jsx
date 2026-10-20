import PropTypes from 'prop-types'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card } from '@/components/ui/card'
import { BarChart3, CheckCircle2, Clock, History, Timer, Users } from 'lucide-react'
import { duration, when } from '../../../assessment/format.js'
import Panel from '../../../assessment/Panel.jsx'
import { runStats } from '../../../assessment/runStats.js'
import { RunPill } from '../../../assessment/visuals.jsx'

const COLOR = { succeeded: '#10b981', completed: '#10b981', finished: '#10b981', failed: '#f43f5e', cancelled: '#94a3b8', running: '#6366f1', waiting_human: '#f59e0b' }

function Stat({ icon: Icon, label, value, sub, tone }) {
  return (
    <Card className="flex-row items-center gap-4 p-4">
      <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${tone}`}><Icon className="h-5 w-5" aria-hidden="true" /></span>
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">{label}</p>
        <div className="truncate text-2xl font-semibold tabular-nums leading-tight text-foreground">{value}</div>
        {sub && <p className="truncate text-xs text-muted-foreground">{sub}</p>}
      </div>
    </Card>
  )
}
Stat.propTypes = { icon: PropTypes.elementType, label: PropTypes.string, value: PropTypes.node, sub: PropTypes.node, tone: PropTypes.string }

/** The runs of a team at a glance: how many and how they ended, how long they take, the latest one, and a chart of the time each run took. */
export default function RunAnalysis({ runs }) {
  const s = runStats(runs)
  if (!s.total) return null
  const rate = s.successRate == null ? '-' : `${Math.round(s.successRate * 100)}%`
  const parts = [
    { label: 'Succeeded', n: s.succeeded, cls: 'bg-emerald-500' },
    { label: 'Failed', n: s.failed, cls: 'bg-rose-500' },
    { label: 'Cancelled', n: s.cancelled, cls: 'bg-slate-400' },
    { label: 'In progress', n: s.active, cls: 'bg-indigo-500' },
  ].filter((p) => p.n > 0)

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat icon={History} tone="bg-indigo-100 text-indigo-600 dark:bg-indigo-950" label="Runs" value={s.total} sub={`${s.snapshots} snapshot${s.snapshots === 1 ? '' : 's'} · ${s.finals} final`} />
        <Stat icon={CheckCircle2} tone={s.failed ? 'bg-amber-100 text-amber-600 dark:bg-amber-950' : 'bg-emerald-100 text-emerald-600 dark:bg-emerald-950'} label="Success rate" value={rate} sub={s.failed ? `${s.failed} failed` : s.succeeded ? 'None failed' : 'Nothing has finished yet'} />
        <Stat icon={Timer} tone="bg-sky-100 text-sky-600 dark:bg-sky-950" label="Average time" value={s.averageSeconds == null ? '-' : duration(s.averageSeconds)} sub={s.fastestSeconds != null ? `Fastest ${duration(s.fastestSeconds)} · slowest ${duration(s.slowestSeconds)}` : 'After the first finished run'} />
        <Stat icon={Clock} tone="bg-violet-100 text-violet-600 dark:bg-violet-950" label="Latest run" value={<RunPill status={s.latest.status} />} sub={`${when(s.latest.created_at)}${s.students != null ? ` · ${s.students} students` : ''}`} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <Panel title="How long each run took" icon={BarChart3} hint="Oldest on the left. The colour is how the run ended.">
          {s.durations.length === 0 ? <p className="text-sm text-muted-foreground">No run has finished yet.</p> : (
            <div className="h-56">
              <ResponsiveContainer>
                <BarChart data={s.durations} margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.3} vertical={false} />
                  <XAxis dataKey="n" fontSize={11} tickFormatter={(n) => `#${n}`} /><YAxis fontSize={11} tickFormatter={(v) => `${Math.round(v / 60)}m`} />
                  <Tooltip formatter={(v) => [duration(v), 'Took']} labelFormatter={(n, items) => items?.[0]?.payload?.label || `Run ${n}`} />
                  <Bar dataKey="seconds" radius={[6, 6, 0, 0]}>{s.durations.map((d) => <Cell key={d.id} fill={COLOR[d.status] || '#6366f1'} />)}</Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Panel>

        <Panel title="How they ended" icon={Users} hint="Every run of this team, all sprints.">
          <div className="space-y-4">
            <div className="flex h-3 overflow-hidden rounded-full bg-muted" role="img" aria-label={parts.map((p) => `${p.n} ${p.label.toLowerCase()}`).join(', ')}>
              {parts.map((p) => <span key={p.label} className={p.cls} style={{ width: `${(p.n / s.total) * 100}%` }} />)}
            </div>
            <ul className="space-y-2 text-sm">
              {parts.map((p) => <li key={p.label} className="flex items-center gap-2"><span className={`h-2.5 w-2.5 rounded-full ${p.cls}`} /><span className="flex-1 text-foreground">{p.label}</span><span className="tabular-nums text-muted-foreground">{p.n}</span></li>)}
            </ul>
          </div>
        </Panel>
      </div>
    </div>
  )
}
RunAnalysis.propTypes = { runs: PropTypes.array }
