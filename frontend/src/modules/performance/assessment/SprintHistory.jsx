import PropTypes from 'prop-types'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ArrowDownRight, ArrowUpRight, Info, Minus } from 'lucide-react'
import { band, markBand, markText, styleOf } from './format.js'
import { Skel } from './Reveal.jsx'

const COLORS = { effort: '#10b981', consistency: '#f59e0b', requirement_fulfillment: '#6366f1', collaboration: '#ec4899', task_complexity: '#0ea5e9' }

function Delta({ value }) {
  if (value == null || value === 0) return value === 0 ? <Minus className="h-3 w-3 text-muted-foreground" aria-label="no change" /> : null
  const up = value > 0
  const Icon = up ? ArrowUpRight : ArrowDownRight
  return <span className={`inline-flex items-center text-[11px] font-semibold tabular-nums ${up ? 'text-emerald-600' : 'text-rose-600'}`}><Icon className="h-3 w-3" aria-hidden="true" />{up ? '+' : ''}{value}</span>
}
Delta.propTypes = { value: PropTypes.number }

function Cell({ cell, current }) {
  if (cell.kind === 'loading') return <td className="px-3 py-3"><Skel className="mx-auto h-5 w-10" /></td>
  const tone = cell.score == null ? 'text-muted-foreground' : styleOf(band(cell.score / 100)).text
  return (
    <td className={`px-3 py-3 text-center ${current ? 'bg-primary/5' : ''}`}>
      {cell.score == null
        ? <span className="text-xs text-muted-foreground" title={cell.label}>{cell.kind === 'missing' ? '-' : 'n/a'}</span>
        : <span className="inline-flex flex-col items-center leading-tight"><span className={`text-base font-semibold tabular-nums ${tone}`}>{cell.score}</span><Delta value={cell.delta} /></span>}
    </td>
  )
}
Cell.propTypes = { cell: PropTypes.object, current: PropTypes.bool }

/**
 * Each factor's score in every sprint of the team, so a lecturer sees whether the student is improving, holding or slipping, and in what.
 * Code Ownership is not followed sprint by sprint, and says why.
 */
export default function SprintHistory({ history, current }) {
  const tracked = history.rows.filter((r) => r.tracked)
  const loose = history.rows.filter((r) => !r.tracked)
  const chart = history.sprints.map((id, i) => ({ sprint: id, mark: history.marks[i].mark == null ? null : Math.round(history.marks[i].mark), ...Object.fromEntries(tracked.map((r) => [r.id, r.cells[i].score])) }))

  return (
    <div className="space-y-6">
      {history.enough ? (
        <div className="h-64">
          <ResponsiveContainer>
            <LineChart data={chart} margin={{ top: 8, right: 16, bottom: 0, left: -8 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey="sprint" fontSize={11} /><YAxis domain={[0, 100]} fontSize={11} /><Tooltip /><Legend />
              <Line dataKey="mark" name="Predicted mark" stroke="#111827" strokeWidth={3} dot={{ r: 4 }} connectNulls />
              {tracked.map((r) => <Line key={r.id} dataKey={r.id} name={r.label} stroke={COLORS[r.id]} strokeWidth={2} dot={{ r: 3 }} connectNulls />)}
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : <p className="rounded-lg bg-muted/50 p-4 text-sm text-muted-foreground">Needs at least two sprints that have been assessed to show how the scores moved. The table fills in as they are.</p>}

      <div className="-mx-1 overflow-x-auto">
        <table className="w-full min-w-[420px] text-sm">
          <thead>
            <tr className="text-xs text-muted-foreground">
              <th className="px-3 pb-2 text-left font-medium">Factor</th>
              {history.sprints.map((id) => <th key={id} className={`px-3 pb-2 text-center font-medium ${id === current ? 'text-primary' : ''}`}>{id}{id === current && <span className="ml-1 rounded-full bg-primary/10 px-1.5 text-[10px]">this report</span>}</th>)}
            </tr>
          </thead>
          <tbody className="divide-y">
            <tr className="bg-muted/30">
              <td className="px-3 py-3 font-semibold text-foreground">Predicted mark</td>
              {history.marks.map((m) => m.loading ? <td key={m.sprint} className="px-3 py-3"><Skel className="mx-auto h-6 w-10" /></td> : (
                <td key={m.sprint} className={`px-3 py-3 text-center text-base font-semibold tabular-nums ${styleOf(markBand(m.mark)).text}`}>{markText(m.mark)}</td>
              ))}
            </tr>
            {tracked.map((r) => (
              <tr key={r.id}>
                <td className="px-3 py-3 text-foreground"><span className="mr-2 inline-block h-2 w-2 rounded-full" style={{ background: COLORS[r.id] }} />{r.label}</td>
                {r.cells.map((c) => <Cell key={c.sprint} cell={c} current={c.sprint === current} />)}
              </tr>
            ))}
            {loose.map((r) => (
              <tr key={r.id} className="bg-muted/20">
                <td className="px-3 py-3 text-foreground">{r.label}</td>
                <td colSpan={history.sprints.length} className="px-3 py-3 text-xs leading-relaxed text-muted-foreground"><span className="inline-flex items-start gap-1.5"><Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />Not followed sprint by sprint. {r.why}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
SprintHistory.propTypes = { history: PropTypes.object.isRequired, current: PropTypes.string }
