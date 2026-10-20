import { useState } from 'react'
import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { useQueries } from '@tanstack/react-query'
import { Area, CartesianGrid, ComposedChart, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Activity, AlertTriangle, ArrowDownRight, ArrowRight, ArrowUpRight, CalendarClock, Camera, CheckCircle2, LineChart as LineChartIcon, Minus, TrendingUp, Trophy, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { assessmentApi, assessmentKeys } from '../../../assessment/assessmentApi.js'
import { developmentModel, sprintProgress } from '../../../assessment/development.js'
import { FACTORS, markBand, styleOf, when } from '../../../assessment/format.js'
import Panel from '../../../assessment/Panel.jsx'
import { Avatar } from '../../../assessment/visuals.jsx'

const label = (day) => new Date(`${day}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
const FACTOR_COLORS = { effort: '#10b981', consistency: '#f59e0b', requirement_fulfillment: '#6366f1', collaboration: '#ec4899', task_complexity: '#0ea5e9', code_ownership: '#8b5cf6' }
const TREND = {
  rising: { text: 'Rising', cls: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300', Icon: ArrowUpRight },
  falling: { text: 'Falling', cls: 'bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300', Icon: ArrowDownRight },
  steady: { text: 'Steady', cls: 'bg-muted text-muted-foreground', Icon: Minus },
  none: { text: 'Not enough yet', cls: 'bg-muted text-muted-foreground', Icon: Minus },
}
const WARNING = { dropped: ArrowDownRight, low: AlertTriangle, uncertain: Activity }

function Stat({ icon: Icon, label: name, value, sub, tone }) {
  return (
    <Card className="flex-row items-center gap-4 p-4">
      <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${tone}`}><Icon className="h-5 w-5" aria-hidden="true" /></span>
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">{name}</p>
        <p className="truncate text-2xl font-semibold tabular-nums leading-tight text-foreground">{value}</p>
        {sub && <p className="truncate text-xs text-muted-foreground">{sub}</p>}
      </div>
    </Card>
  )
}
Stat.propTypes = { icon: PropTypes.elementType, label: PropTypes.string, value: PropTypes.node, sub: PropTypes.node, tone: PropTypes.string }

function Delta({ value, className = '' }) {
  if (value == null) return <span className={`text-muted-foreground ${className}`}>-</span>
  const n = Math.round(value)
  const up = n > 0
  const Icon = up ? ArrowUpRight : n < 0 ? ArrowDownRight : Minus
  return <span className={`inline-flex items-center gap-0.5 font-semibold tabular-nums ${up ? 'text-emerald-600' : n < 0 ? 'text-rose-600' : 'text-muted-foreground'} ${className}`}><Icon className="h-3.5 w-3.5" aria-hidden="true" />{up ? '+' : ''}{n}</span>
}
Delta.propTypes = { value: PropTypes.number, className: PropTypes.string }

function Spark({ points, color }) {
  const data = points.map((p) => ({ x: p.day, y: p.mark }))
  if (data.length < 2) return <span className="text-xs text-muted-foreground">-</span>
  return (
    <div className="h-8 w-28" aria-hidden="true">
      <ResponsiveContainer><LineChart data={data} margin={{ top: 4, right: 2, bottom: 4, left: 2 }}><YAxis domain={[0, 100]} hide /><Line dataKey="y" stroke={color} strokeWidth={2} dot={false} isAnimationActive={false} /></LineChart></ResponsiveContainer>
    </div>
  )
}
Spark.propTypes = { points: PropTypes.array, color: PropTypes.string }

function SprintBar({ progress, days, snapshots }) {
  if (!progress) return <p className="text-sm text-muted-foreground">The sprint dates are not set. Add them under Setup to see how far through the sprint the team is.</p>
  const state = progress.notStarted ? 'The sprint has not started.' : progress.over ? 'The sprint is over.' : `Day ${progress.day} of ${progress.days}.`
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-medium text-foreground">{state}</p>
        <p className="text-xs text-muted-foreground">{snapshots} snapshot{snapshots === 1 ? '' : 's'} so far. One is taken every night while the sprint runs.</p>
      </div>
      <div className="relative h-3 rounded-full bg-muted">
        <div className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all duration-700" style={{ width: `${Math.max(2, progress.share * 100)}%` }} />
        {days.map((d) => {
          const left = progress.start != null ? Math.max(0, Math.min(1, (new Date(`${d}T20:00:00`).getTime() - progress.start) / (progress.end - progress.start))) * 100 : null
          return left == null ? null : <span key={d} title={`Snapshot ${label(d)}`} className="absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-primary shadow dark:border-card" style={{ left: `${left}%` }} />
        })}
      </div>
    </div>
  )
}
SprintBar.propTypes = { progress: PropTypes.object, days: PropTypes.array, snapshots: PropTypes.number }

/**
 * How the team developed during the sprint: where the sprint is, the key numbers, the team's predicted mark day by day with each student switchable on and off,
 * every student's movement, who is worth a look, and how each factor moved. All of it comes from the snapshots taken so far.
 */
export default function DevelopmentTab({ team, sprint, rows, sprintInfo, base, canRun, onSnapshot }) {
  const queries = useQueries({ queries: (rows || []).map((r) => ({ queryKey: assessmentKeys.trajectory(team, sprint, r.student_id), queryFn: () => assessmentApi.trajectory(team, sprint, r.student_id) })) })
  const loading = queries.some((q) => q.isPending)
  const [hidden, setHidden] = useState({})
  const series = queries.map((q) => q.data || [])
  const model = developmentModel(rows, series)
  const range = sprintProgress(sprintInfo)
  const progress = range && sprintInfo ? { ...range, start: new Date(`${sprintInfo.start}T00:00:00`).getTime(), end: new Date(`${sprintInfo.end}T23:59:59`).getTime() } : null
  const link = (id) => `${base}/students/${id}?sprint=${encodeURIComponent(sprint)}`

  if (!rows?.length) {
    return (
      <Panel title="Nothing to show yet" icon={LineChartIcon} hint="This view fills in as the team is assessed.">
        <div className="flex flex-col items-start gap-4">
          <ol className="space-y-2 text-sm text-muted-foreground">
            <li className="flex gap-3"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">1</span>A snapshot assesses every student from the repository as it is now. One is also taken every night while the sprint runs.</li>
            <li className="flex gap-3"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">2</span>Each snapshot adds a point for every student. With two or more points you see the lines move.</li>
            <li className="flex gap-3"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">3</span>Early points rest on little evidence and are wide; they narrow as the sprint goes on.</li>
          </ol>
          {onSnapshot && <Button disabled={!canRun} onClick={onSnapshot}><Camera className="h-4 w-4" />Take a snapshot now</Button>}
        </div>
      </Panel>
    )
  }
  if (loading) return <div className="space-y-4" aria-busy="true"><Skeleton className="h-24 w-full" /><Skeleton className="h-80 w-full" /></div>

  const t = model.team
  const shownStudents = model.students.filter((s) => !hidden[s.id])
  const enough = model.days.length >= 2

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat icon={Users} tone="bg-indigo-100 text-indigo-600 dark:bg-indigo-950" label="Team average now" value={t.latest ?? '-'} sub={t.change != null ? <span>Since the first snapshot <Delta value={t.change} /></span> : 'One snapshot so far'} />
        <Stat icon={Camera} tone="bg-sky-100 text-sky-600 dark:bg-sky-950" label="Snapshots" value={t.snapshots} sub={t.lastAt ? `Last one ${when(new Date(t.lastAt).toISOString())}` : 'None yet'} />
        <Stat icon={Trophy} tone="bg-emerald-100 text-emerald-600 dark:bg-emerald-950" label="Most improved" value={t.improved ? t.improved.name.split(' ')[0] : '-'} sub={t.improved ? `+${Math.round(t.improved.change)} points` : 'Nobody has risen 5 points yet'} />
        <Stat icon={AlertTriangle} tone={t.lowCount ? 'bg-rose-100 text-rose-600 dark:bg-rose-950' : 'bg-muted text-muted-foreground'} label="Below 40" value={t.lowCount} sub={t.lowCount ? 'Worth a conversation' : 'Nobody is at risk'} />
      </div>

      <Panel title="Where the sprint is" icon={CalendarClock} hint="The dots on the bar are the snapshots.">
        <SprintBar progress={progress} days={model.days} snapshots={t.snapshots} />
      </Panel>

      <Panel title="Predicted mark, day by day" icon={TrendingUp} hint="The heavy line is the team average and the shaded stretch is the lowest to the highest student. Switch students on and off to compare. Early points rest on little evidence and move a lot.">
        {!enough ? <p className="rounded-lg bg-muted/50 p-4 text-sm text-muted-foreground">At least two snapshots are needed to draw a line. One is taken every night while the sprint runs, and each Snapshot you start adds a point.</p> : (
          <>
            <div className="mb-4 flex flex-wrap gap-2" role="group" aria-label="Students shown">
              {model.students.map((s) => (
                <button key={s.id} type="button" aria-pressed={!hidden[s.id]} onClick={() => setHidden((h) => ({ ...h, [s.id]: !h[s.id] }))}
                  className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium transition-all ${hidden[s.id] ? 'text-muted-foreground opacity-60' : 'bg-card shadow-sm'}`}>
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: hidden[s.id] ? '#cbd5e1' : s.color }} />{s.name}
                </button>
              ))}
            </div>
            <div className="h-80">
              <ResponsiveContainer>
                <ComposedChart data={model.chart} margin={{ top: 8, right: 16, bottom: 0, left: -8 }}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                  <XAxis dataKey="day" tickFormatter={label} fontSize={11} /><YAxis domain={[0, 100]} fontSize={11} />
                  <Tooltip labelFormatter={label} />
                  <Area dataKey="band" name="Lowest to highest" stroke="none" fill="#6366f1" fillOpacity={0.12} connectNulls />
                  {shownStudents.map((s) => <Line key={s.id} dataKey={s.name} stroke={s.color} strokeWidth={1.8} strokeOpacity={0.85} dot={{ r: 2.5 }} connectNulls />)}
                  <Line dataKey="average" name="Team average" stroke="#111827" strokeWidth={3.2} dot={{ r: 4 }} connectNulls />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </Panel>

      <Panel title="Each student's movement" icon={Users} hint="First snapshot to latest. A change of 5 points or more counts as a rise or a fall.">
        <div className="-mx-1 overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="text-left text-xs text-muted-foreground">
                <th className="px-2 pb-2 font-medium">Student</th><th className="px-2 pb-2 font-medium">Over the sprint</th><th className="px-2 pb-2 text-right font-medium">First</th><th className="px-2 pb-2 text-right font-medium">Latest</th><th className="px-2 pb-2 text-right font-medium">Change</th><th className="px-2 pb-2 font-medium">Trend</th><th className="px-2 pb-2" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {model.students.map((s) => {
                const tr = TREND[s.trend]
                return (
                  <tr key={s.id} className="group">
                    <td className="px-2 py-3"><div className="flex items-center gap-3"><Avatar name={s.name} picture={s.picture} size={32} /><span className="font-medium text-foreground">{s.name}</span></div></td>
                    <td className="px-2 py-3"><Spark points={s.points} color={s.color} /></td>
                    <td className="px-2 py-3 text-right tabular-nums text-muted-foreground">{s.first == null ? '-' : Math.round(s.first)}</td>
                    <td className={`px-2 py-3 text-right text-base font-semibold tabular-nums ${styleOf(markBand(s.latest)).text}`}>{s.latest == null ? '-' : Math.round(s.latest)}</td>
                    <td className="px-2 py-3 text-right"><Delta value={s.change} /></td>
                    <td className="px-2 py-3"><span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${tr.cls}`}><tr.Icon className="h-3 w-3" aria-hidden="true" />{tr.text}</span></td>
                    <td className="px-2 py-3 text-right"><Link to={link(s.id)} className="inline-flex items-center gap-1 text-xs font-medium text-primary opacity-70 transition-opacity group-hover:opacity-100">Open<ArrowRight className="h-3.5 w-3.5" aria-hidden="true" /></Link></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="Worth a look" icon={AlertTriangle} tone={model.warnings.length ? 'warning' : 'default'} hint="Early warnings from the snapshots: a drop since the last one, a low mark, or a prediction that is still very uncertain.">
        {model.warnings.length === 0 ? (
          <p className="flex items-center gap-2 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-300"><CheckCircle2 className="h-4 w-4 shrink-0" aria-hidden="true" />Nothing stands out in the snapshots so far.</p>
        ) : (
          <ul className="space-y-2">
            {model.warnings.map((w, i) => {
              const Icon = WARNING[w.kind] || AlertTriangle
              return (
                <li key={i} className="flex items-start gap-3 rounded-xl border border-amber-300/70 bg-amber-50 p-3 text-sm dark:border-amber-900 dark:bg-amber-950/30">
                  <Icon className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" aria-hidden="true" />
                  <span className="min-w-0 flex-1 text-amber-950 dark:text-amber-200">{w.text}</span>
                  <Link to={link(w.id)} className="shrink-0 text-xs font-medium text-primary hover:underline">Open</Link>
                </li>
              )
            })}
          </ul>
        )}
      </Panel>

      <Panel title="Factors over time" icon={Activity} hint="The team average of each factor at every snapshot, from 0 to 100. A factor that cannot be measured yet has no line.">
        {!enough ? <p className="rounded-lg bg-muted/50 p-4 text-sm text-muted-foreground">Needs at least two snapshots.</p> : (
          <div className="h-72">
            <ResponsiveContainer>
              <LineChart data={model.factorsByDay} margin={{ top: 8, right: 16, bottom: 0, left: -8 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="day" tickFormatter={label} fontSize={11} /><YAxis domain={[0, 100]} fontSize={11} /><Tooltip labelFormatter={label} /><Legend />
                {FACTORS.map((f) => <Line key={f.id} dataKey={f.id} name={f.label} stroke={FACTOR_COLORS[f.id]} strokeWidth={2} dot={{ r: 2.5 }} connectNulls />)}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </Panel>
    </div>
  )
}
DevelopmentTab.propTypes = { team: PropTypes.string, sprint: PropTypes.string, rows: PropTypes.array, sprintInfo: PropTypes.object, base: PropTypes.string, canRun: PropTypes.bool, onSnapshot: PropTypes.func }
