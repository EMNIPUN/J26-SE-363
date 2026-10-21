import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { AlertTriangle, ArrowDownRight, ArrowRight, ArrowUpRight, Camera, CheckCircle2, Minus, TrendingUp, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import Panel from '../../../assessment/Panel.jsx'
import { ChartSkeleton, PanelSkeleton, Stagger, StatRowSkeleton, TableSkeleton } from '../../../assessment/Reveal.jsx'
import { Avatar } from '../../../assessment/visuals.jsx'
import { markBand, styleOf } from '../../../assessment/format.js'

const TREND = {
  rising: { text: 'Rising', cls: 'bg-emerald-100 text-emerald-700', Icon: ArrowUpRight },
  falling: { text: 'Falling', cls: 'bg-rose-100 text-rose-700', Icon: ArrowDownRight },
  steady: { text: 'Steady', cls: 'bg-muted text-muted-foreground', Icon: Minus },
  none: { text: 'Not enough yet', cls: 'bg-muted text-muted-foreground', Icon: Minus },
}
const label = (day) => new Date(`${day}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

function Stat({ icon: Icon, label: name, value, sub }) {
  return <Card className="flex-row items-center gap-4 p-4"><span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary"><Icon className="h-5 w-5" /></span><div><p className="text-xs text-muted-foreground">{name}</p><p className="text-xl font-semibold tabular-nums">{value}</p>{sub && <p className="text-xs text-muted-foreground">{sub}</p>}</div></Card>
}
Stat.propTypes = { icon: PropTypes.elementType, label: PropTypes.string, value: PropTypes.node, sub: PropTypes.node }

export default function DevelopmentTab({ development, loading, base, canRun, onSnapshot }) {
  if (loading) return <div className="space-y-6" aria-busy="true"><StatRowSkeleton /><PanelSkeleton height={110} /><ChartSkeleton height={300} /><TableSkeleton rows={4} columns={6} /></div>
  const d = development || {}
  const students = d.students || []
  const chart = (d.chart || []).map((p) => ({ ...p, band: p.low != null && p.high != null ? [p.low, p.high] : null, ...Object.fromEntries(Object.entries(p.marks || {}).map(([id, mark]) => [id, mark])) }))
  const enough = chart.length > 1
  const href = (id) => `${base}/students/${id}`
  return (
    <Stagger className="space-y-6" step={100}>
      <div className="grid gap-4 @xl:grid-cols-2 @5xl:grid-cols-4">
        <Stat icon={Users} label="Team average now" value={d.kpis?.team_average ?? '-'} sub={d.kpis?.team_change != null ? `${d.kpis.team_change > 0 ? '+' : ''}${d.kpis.team_change} since first snapshot` : 'No comparison yet'} />
        <Stat icon={Camera} label="Snapshots" value={d.kpis?.snapshots ?? 0} sub={d.kpis?.last_snapshot_at ? `Last one ${new Date(d.kpis.last_snapshot_at).toLocaleString()}` : 'None yet'} />
        <Stat icon={TrendingUp} label="Most improved" value={d.kpis?.most_improved?.first_name || '-'} sub={d.kpis?.most_improved ? `+${d.kpis.most_improved.change} points` : 'Nobody has risen yet'} />
        <Stat icon={AlertTriangle} label="Below 40" value={d.kpis?.below_40 ?? 0} sub={d.kpis?.below_40 ? 'Worth a conversation' : 'Nobody is at risk'} />
      </div>
      <Panel title="Where the sprint is" hint="The server supplies the sprint progress and snapshot positions.">
        <p className="text-sm font-medium">{d.progress?.state === 'current' ? `Day ${d.progress.day} of ${d.progress.days}.` : d.progress?.state === 'finished' ? 'The sprint is over.' : 'The sprint has not started.'}</p>
        <div className="relative mt-3 h-3 rounded-full bg-muted"><div className="absolute inset-y-0 left-0 rounded-full bg-primary" style={{ width: `${Math.max(2, (d.progress?.share || 0) * 100)}%` }} /></div>
      </Panel>
      <Panel title="Predicted mark, day by day" icon={TrendingUp} hint="The server computes averages, ranges and student series.">
        {!enough ? <p className="rounded-lg bg-muted/50 p-4 text-sm text-muted-foreground">At least two snapshots are needed to draw a line.</p> : <div className="h-80"><ResponsiveContainer><ComposedChart data={chart}><CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis dataKey="day" tickFormatter={label} fontSize={11} /><YAxis domain={[0, 100]} fontSize={11} /><Tooltip /><Area dataKey="band" name="Lowest to highest" stroke="none" fill="#6366f1" fillOpacity={0.12} /><Line dataKey="average" name="Team average" stroke="#111827" strokeWidth={3} dot /></ComposedChart></ResponsiveContainer></div>}
      </Panel>
      <Panel title="Each student's movement" icon={Users}>
        <div className="overflow-x-auto"><table className="w-full min-w-[620px] text-sm"><thead><tr className="text-left text-xs text-muted-foreground"><th className="p-2">Student</th><th className="p-2">Over the sprint</th><th className="p-2 text-right">First</th><th className="p-2 text-right">Latest</th><th className="p-2 text-right">Change</th><th className="p-2">Trend</th><th /></tr></thead><tbody className="divide-y">{students.map((s) => { const tr = TREND[s.trend] || TREND.none; return <tr key={s.student_id}><td className="p-2"><div className="flex items-center gap-3"><Avatar name={s.name} picture={s.picture} size={32} /><span>{s.name}</span></div></td><td className="p-2 text-xs text-muted-foreground">{(s.spark || []).join(' → ') || '-'}</td><td className="p-2 text-right">{s.first ?? '-'}</td><td className={`p-2 text-right font-semibold ${styleOf(markBand(s.latest)).text}`}>{s.latest ?? '-'}</td><td className="p-2 text-right">{s.change > 0 ? '+' : ''}{s.change ?? '-'}</td><td className="p-2"><span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs ${tr.cls}`}><tr.Icon className="h-3 w-3" />{tr.text}</span></td><td className="p-2 text-right"><Link to={s.href || href(s.student_id)} className="text-xs text-primary"><ArrowRight className="h-4 w-4" /></Link></td></tr> })}</tbody></table></div>
      </Panel>
      <Panel title="Worth a look" icon={AlertTriangle}>
        {(d.warnings || []).length === 0 ? <p className="flex items-center gap-2 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-800"><CheckCircle2 className="h-4 w-4" />Nothing stands out in the snapshots so far.</p> : <ul className="space-y-2">{d.warnings.map((w) => <li key={`${w.student_id}-${w.kind}`} className="flex items-center gap-2 rounded-xl border p-3 text-sm"><AlertTriangle className="h-4 w-4 text-amber-600" />{w.text}<Link className="ml-auto text-xs text-primary" to={href(w.student_id)}>Open</Link></li>)}</ul>}
        {onSnapshot && <Button className="mt-4" disabled={!canRun} onClick={onSnapshot}><Camera className="h-4 w-4" />Take a snapshot now</Button>}
      </Panel>
    </Stagger>
  )
}
DevelopmentTab.propTypes = { development: PropTypes.object, loading: PropTypes.bool, sprint: PropTypes.string, base: PropTypes.string, canRun: PropTypes.bool, onSnapshot: PropTypes.func }
