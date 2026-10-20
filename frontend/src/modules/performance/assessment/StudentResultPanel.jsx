import { CartesianGrid, Area, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import Badge from '@/shared/components/Badge.jsx'

const BAND_TONE = { low: 'danger', medium: 'warning', high: 'success' }
const STATUS_TEXT = { not_available: 'not available', pending: 'pending', fallback: 'failed' }

/** The development view: the provisional mark day by day with its plausible range, and the factor scores. */
export function Trajectory({ points }) {
  const rows = (points || []).map((p) => ({
    day: new Date(p.as_of).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    mark: p.mark, range: p.mark_interval ? [p.mark_interval[0], p.mark_interval[1]] : null,
    ...Object.fromEntries(Object.entries(p.factors || {}).filter(([, f]) => f?.score != null).map(([k, f]) => [k, Math.round(f.score * 100)])),
  }))
  if (rows.length < 2) return <p className="text-sm text-muted-foreground">The day-by-day view needs at least two snapshots. A snapshot is taken every night while the sprint runs.</p>
  return (
    <div className="h-72">
      <ResponsiveContainer>
        <ComposedChart data={rows}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis dataKey="day" fontSize={11} />
          <YAxis domain={[0, 100]} fontSize={11} />
          <Tooltip />
          <Legend />
          <Area dataKey="range" name="Plausible range" stroke="none" fill="oklch(0.7 0.12 270)" fillOpacity={0.18} />
          <Line dataKey="mark" name="Predicted mark" stroke="oklch(0.5 0.19 280)" strokeWidth={2.5} dot />
          <Line dataKey="effort" name="Effort (x100)" stroke="oklch(0.65 0.15 160)" dot={false} />
          <Line dataKey="consistency" name="Consistency (x100)" stroke="oklch(0.7 0.15 80)" dot={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

function FactorCard({ block }) {
  const score = block.score
  return (
    <div className="rounded-xl border bg-card p-4 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <h4 className="font-semibold text-sm">{block.title}</h4>
        {score != null ? <Badge tone={BAND_TONE[block.band] || 'neutral'}>{score.toFixed(2)} {block.band}</Badge> : <Badge tone="neutral">{STATUS_TEXT[block.status] || block.status || 'adjustment'}</Badge>}
      </div>
      {block.interval && <p className="text-xs text-muted-foreground">plausible {block.interval[0].toFixed(2)} to {block.interval[1].toFixed(2)}{block.provisional ? ', provisional' : ''}</p>}
      <ul className="list-disc pl-4 text-sm space-y-0.5">{(block.reasons || []).filter(Boolean).map((r, i) => <li key={i}>{r}</li>)}</ul>
      {(block.warnings || []).length > 0 && <ul className="text-xs text-amber-700 dark:text-amber-400 space-y-0.5">{block.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>}
      {block.how_much_to_trust && <details className="text-xs text-muted-foreground"><summary className="cursor-pointer">How far to trust this</summary><p className="mt-1">{block.how_much_to_trust}</p></details>}
    </div>
  )
}

/** One student's result: mark, why, per-factor justification, flags. `result` is a row of /results (lecturer) or /me/results (student). */
export default function StudentResultPanel({ result, trajectory }) {
  if (!result) return null
  const j = result.justification || {}
  const mark = result.effective_mark ?? result.mark
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end gap-4">
        <div>
          <p className="text-xs text-muted-foreground">Predicted mark{result.override || result.overridden ? ' (set by the lecturer)' : ''}</p>
          <p className="text-4xl font-bold tracking-tight">{mark == null ? 'n/a' : Math.round(mark)}<span className="text-lg text-muted-foreground"> / 100</span></p>
          {result.mark_interval && <p className="text-xs text-muted-foreground">plausible range {Math.round(result.mark_interval[0])} to {Math.round(result.mark_interval[1])}</p>}
        </div>
        <Badge tone={result.status === 'final' ? 'success' : result.status === 'pending_review' ? 'warning' : 'primary'}>{String(result.status).replace('_', ' ')}</Badge>
      </div>
      {j.friendly_summary && <p className="text-sm">{j.friendly_summary}</p>}
      <p className="text-sm text-muted-foreground">{j.summary}</p>
      {(j.flags || []).length > 0 && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm dark:bg-amber-950/30 space-y-1">
          <p className="font-medium">Points to check</p>
          <ul className="list-disc pl-4">{j.flags.map((f, i) => <li key={i}>{f.message}{f.action ? ` — ${f.action}${f.reason ? `: ${f.reason}` : ''}` : ''}</li>)}</ul>
        </div>
      )}
      <div className="grid gap-3 md:grid-cols-2">{Object.entries(j.factors || {}).map(([k, b]) => <FactorCard key={k} block={b} />)}</div>
      {j.how_computed && <p className="text-xs text-muted-foreground">{j.how_computed}</p>}
      {trajectory && <section><h3 className="text-sm font-semibold mb-2">Day by day</h3><Trajectory points={trajectory} /></section>}
      {(j.caveats || []).map((c, i) => <p key={i} className="text-xs text-muted-foreground italic">{c}</p>)}
    </div>
  )
}
