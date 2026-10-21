import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { AlertTriangle, ChevronRight, Clock, Gauge, Users } from 'lucide-react'
import { Card } from '@/components/ui/card'
import EmptyState from '@/shared/components/EmptyState.jsx'
import { markBand, markText, rangeText, styleOf } from '../../../assessment/format.js'
import { PanelSkeleton, Stagger, StatRowSkeleton, TableSkeleton } from '../../../assessment/Reveal.jsx'
import { Avatar, FactorBar, StatusPill } from '../../../assessment/visuals.jsx'

function Stat({ icon: Icon, label, value, hint, tone }) {
  return (
    <Card className="flex-row items-center gap-4 p-4">
      <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${tone}`}><Icon className="h-5 w-5" aria-hidden="true" /></span>
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-xl font-semibold tabular-nums text-foreground">{value}</p>
        {hint && <p className="truncate text-xs text-muted-foreground">{hint}</p>}
      </div>
    </Card>
  )
}
Stat.propTypes = { icon: PropTypes.elementType, label: PropTypes.string, value: PropTypes.node, hint: PropTypes.string, tone: PropTypes.string }

/** Every student's mark on one line from 0 to 100: how far apart the team members are. */
function Spread({ rows }) {
  const marks = rows.filter((r) => r.effective_mark != null)
  if (marks.length < 2) return null
  return (
    <Card className="gap-3 p-5">
      <div>
        <h3 className="text-sm font-semibold text-foreground">How the work is spread</h3>
        <p className="text-xs text-muted-foreground">One dot per student. A wide gap inside a team is what this assessment exists to show.</p>
      </div>
      <div className="relative h-14">
        <div className="absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-gradient-to-r from-rose-200 via-amber-200 to-emerald-200 dark:from-rose-900 dark:via-amber-900 dark:to-emerald-900" />
        {marks.map((r, i) => (
          <div key={r.student_id} className="group absolute -translate-x-1/2" style={{ left: `${Math.max(2, Math.min(98, r.effective_mark))}%`, top: i % 2 ? 6 : 28 }}>
            <Avatar name={r.student?.name} picture={r.student?.picture} size={24} />
            <span className="pointer-events-none absolute left-1/2 top-full z-10 mt-1 hidden -translate-x-1/2 whitespace-nowrap rounded bg-foreground px-2 py-0.5 text-xs text-background group-hover:block">{r.student?.name}: {markText(r.effective_mark)}</span>
          </div>
        ))}
      </div>
      <div className="flex justify-between text-[11px] text-muted-foreground"><span>0</span><span>50</span><span>100</span></div>
    </Card>
  )
}
Spread.propTypes = { rows: PropTypes.array }

export default function ResultsTab({ overview, loading, base }) {
  if (loading) return <div className="space-y-5" aria-busy="true"><StatRowSkeleton /><TableSkeleton rows={4} columns={7} /><PanelSkeleton height={150} /></div>
  const rows = overview?.rows || []
  const factors = overview?.meta?.factors || []
  if (!rows.length) {
    return <EmptyState icon={Gauge} title="No results for this sprint yet" description="Start a snapshot to see where the team is now, or a final assessment when the sprint is over. The results appear here as soon as the agent has finished each student." />
  }
  const s = overview.kpis || {}
  const sorted = [...rows].sort((a, b) => (b.effective_mark ?? -1) - (a.effective_mark ?? -1))
  return (
    <Stagger className="space-y-5">
      <div className="grid gap-3 @xl:grid-cols-2 @5xl:grid-cols-4">
        <Stat icon={Users} label="Average mark" value={markText(s.average_mark)} hint={s.lowest != null ? `from ${markText(s.lowest)} to ${markText(s.highest)}` : ''} tone="bg-primary/10 text-primary" />
        <Stat icon={AlertTriangle} label="Need your review" value={s.need_review ?? 0} hint={s.flags ? `${s.flags} points to check` : 'nothing flagged'} tone="bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400" />
        <Stat icon={Clock} label="Waiting for a code answer" value={s.waiting_for_answer ?? 0} hint="marks are provisional until they answer" tone="bg-sky-50 text-sky-700 dark:bg-sky-950/40 dark:text-sky-400" />
        <Stat icon={Gauge} label="Provisional" value={s.provisional ?? 0} hint="can still change" tone="bg-violet-50 text-violet-700 dark:bg-violet-950/40 dark:text-violet-400" />
      </div>

      <Card className="gap-0 overflow-hidden p-0">
        <div className="hidden grid-cols-[minmax(0,1.4fr)_120px_minmax(0,3fr)_24px] items-center gap-4 border-b bg-muted/40 px-4 py-2 text-xs font-medium text-muted-foreground @2xl:grid">
          <span>Student</span><span>Mark</span>
          <span className="grid grid-cols-6 gap-3">{factors.map((f) => <span key={f.id} className="truncate" title={f.label}>{f.short || f.label}</span>)}</span><span />
        </div>
        <ul>
          {sorted.map((r) => {
            const st = styleOf(markBand(r.effective_mark))
            const flags = r.justification?.flags?.length || 0
            return (
              <li key={r.student_id} className="border-b last:border-0">
                <Link to={`${base}/students/${r.student_id}`} className="grid grid-cols-[minmax(0,1fr)] items-center gap-3 px-4 py-3 transition-colors hover:bg-accent/50 @2xl:grid-cols-[minmax(0,1.4fr)_120px_minmax(0,3fr)_24px] @2xl:gap-4">
                  <span className="flex min-w-0 items-center gap-3">
                    <Avatar name={r.student?.name} picture={r.student?.picture} />
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium text-foreground">{r.student?.name}</span>
                      <span className="mt-0.5 flex flex-wrap items-center gap-1.5"><StatusPill status={r.status} /><span className="text-xs text-muted-foreground">over {r.sprints_done} sprint{r.sprints_done === 1 ? '' : 's'}</span>{flags > 0 && <span className="inline-flex items-center gap-1 text-xs text-amber-600"><AlertTriangle className="h-3 w-3" />{flags}</span>}</span>
                    </span>
                  </span>
                  <span>
                    <span className={`text-xl font-semibold tabular-nums ${st.text}`}>{markText(r.effective_mark)}</span>
                    <span className="block text-xs text-muted-foreground">{rangeText(r.mark_interval)}</span>
                  </span>
                  <span className="grid min-w-0 grid-cols-2 gap-x-4 gap-y-2 @xl:grid-cols-3 @2xl:grid-cols-6 @2xl:gap-x-3">
                    {factors.map((f) => <span key={f.id} className="min-w-0"><span className="mb-0.5 block text-[10px] text-muted-foreground @2xl:hidden">{f.label}</span><FactorBar result={r.factors?.[f.id]} height={6} compact /></span>)}
                  </span>
                  <ChevronRight className="hidden h-4 w-4 text-muted-foreground @2xl:block" aria-hidden="true" />
                </Link>
              </li>
            )
          })}
        </ul>
      </Card>

      <Spread rows={rows} />
      <p className="text-xs text-muted-foreground">Marks and factor scores are the average over every sprint evaluated so far. Hatched bars are to date: a sprint is still running. A dashed bar means the factor could not be measured and is left out of the mark. Marks are predictions to support your decision. <Link to={`${base}/method`} className="font-medium text-primary hover:underline">How the marks are made, and the weights</Link>.</p>
    </Stagger>
  )
}
ResultsTab.propTypes = { overview: PropTypes.object, loading: PropTypes.bool, sprint: PropTypes.string, base: PropTypes.string }
