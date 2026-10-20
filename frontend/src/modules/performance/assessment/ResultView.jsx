import { useState } from 'react'
import PropTypes from 'prop-types'
import { CartesianGrid, Area, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { AlertTriangle, ChevronDown, Info, MessageSquareQuote, PenLine, ShieldCheck } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { contributions, FACTORS, factorState, markText, when } from './format.js'
import { ContributionBar, FactorBar, ScoreRing, StatusPill } from './visuals.jsx'

function Section({ title, hint, children, icon: Icon }) {
  return (
    <section className="space-y-3">
      <div>
        <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">{Icon && <Icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />}{title}</h3>
        {hint && <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>}
      </div>
      {children}
    </section>
  )
}
Section.propTypes = { title: PropTypes.string, hint: PropTypes.string, children: PropTypes.node, icon: PropTypes.elementType }

function Details({ summary, children }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="text-xs">
      <button type="button" onClick={() => setOpen(!open)} className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground" aria-expanded={open}>
        <ChevronDown className={`h-3.5 w-3.5 transition-transform ${open ? 'rotate-180' : ''}`} aria-hidden="true" />{summary}
      </button>
      {open && <div className="mt-1.5 space-y-1 text-muted-foreground">{children}</div>}
    </div>
  )
}
Details.propTypes = { summary: PropTypes.string, children: PropTypes.node }

function FactorCard({ meta, result, block }) {
  const state = factorState(result)
  const reasons = (block?.reasons || []).filter(Boolean)
  return (
    <Card className="gap-3 p-4">
      <div>
        <div className="flex items-start justify-between gap-2">
          <h4 className="text-sm font-semibold text-foreground">{meta.label}</h4>
          {result?.provisional && state.kind === 'scored' && <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">to date</span>}
        </div>
        <p className="text-xs text-muted-foreground">{meta.question}</p>
      </div>
      <FactorBar result={result} />
      {state.kind !== 'scored' && reasons[0] && <p className="text-xs text-muted-foreground">{reasons[0]}</p>}
      {state.kind === 'scored' && reasons.length > 0 && (
        <ul className="space-y-1 text-sm text-foreground/90">
          {reasons.slice(0, 4).map((r, i) => <li key={i} className="flex gap-2"><span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-muted-foreground/60" />{r}</li>)}
        </ul>
      )}
      {(block?.warnings || []).length > 0 && (
        <ul className="space-y-1 rounded-lg bg-amber-50 p-2 text-xs text-amber-800 dark:bg-amber-950/30 dark:text-amber-300">
          {block.warnings.slice(0, 4).map((w, i) => <li key={i}>{w}</li>)}
        </ul>
      )}
      <Details summary="What this measures and how far to trust it">
        <p>{meta.measures}</p>
        {block?.how_much_to_trust && <p>{block.how_much_to_trust}</p>}
      </Details>
    </Card>
  )
}
FactorCard.propTypes = { meta: PropTypes.object, result: PropTypes.object, block: PropTypes.object }

function Trajectory({ points }) {
  const rows = (points || []).map((p) => ({
    day: new Date(p.as_of).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    mark: p.mark, range: p.mark_interval ? [p.mark_interval[0], p.mark_interval[1]] : null,
    ...Object.fromEntries(Object.entries(p.factors || {}).filter(([, f]) => f?.score != null).map(([k, f]) => [k, Math.round(f.score * 100)])),
  }))
  if (rows.length < 2) return <p className="rounded-lg bg-muted/50 p-4 text-sm text-muted-foreground">The day by day view needs at least two snapshots. One is taken every night while the sprint runs, and each Snapshot you start adds a point.</p>
  return (
    <div className="h-72">
      <ResponsiveContainer>
        <ComposedChart data={rows}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis dataKey="day" fontSize={11} /><YAxis domain={[0, 100]} fontSize={11} /><Tooltip /><Legend />
          <Area dataKey="range" name="Likely range" stroke="none" fill="#6366f1" fillOpacity={0.15} />
          <Line dataKey="mark" name="Predicted mark" stroke="#4f46e5" strokeWidth={2.5} dot />
          <Line dataKey="effort" name="Effort" stroke="#10b981" dot={false} />
          <Line dataKey="consistency" name="Consistency" stroke="#f59e0b" dot={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
Trajectory.propTypes = { points: PropTypes.array }

function Quiz({ quiz }) {
  if (!quiz) return <p className="rounded-lg bg-muted/50 p-4 text-sm text-muted-foreground">No code question has been asked for this sprint yet. It is asked in the final assessment.</p>
  const answered = quiz.status === 'answered'
  return (
    <Card className="gap-3 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <span className="font-mono">{quiz.file_path}{quiz.line_range ? `, lines ${quiz.line_range[0]} to ${quiz.line_range[1]}` : ''}</span>
        <span>{{ open: 'Waiting for the answer', extended: 'Second answer window', answered: `Answered ${when(quiz.answered_at)}${quiz.in_second_window ? ' (second window: capped at 50)' : ''}`, expired: 'Not answered: counts as 0' }[quiz.status]}</span>
      </div>
      <pre className="max-h-56 overflow-auto rounded-lg bg-muted p-3 text-xs leading-relaxed">{quiz.snippet}</pre>
      <p className="text-sm font-medium text-foreground">{quiz.question}</p>
      {answered ? (
        <blockquote className="rounded-lg border-l-4 border-primary/50 bg-primary/5 p-3 text-sm">{quiz.answer}</blockquote>
      ) : <p className="text-sm text-muted-foreground">No answer yet.</p>}
      {answered && quiz.rating != null && <p className="text-sm">Rated <span className="font-semibold">{Number(quiz.rating).toFixed(1)} of 5</span> by the answer scorer, which was checked on assistant-written answers only.</p>}
      {(quiz.warnings || []).map((w, i) => <p key={i} className="text-xs text-amber-700">{w}</p>)}
    </Card>
  )
}
Quiz.propTypes = { quiz: PropTypes.object }

/**
 * One student's assessment, written for someone who has to act on it: the mark and how sure we are, why, what to check, then each factor with its evidence.
 * `mode` "lecturer" adds what the agent investigated, the code question and answer, and the lecturer's own mark; "student" shows only the student's own feedback.
 */
export default function ResultView({ result, weights, mode = 'lecturer', trajectory, quiz, onSetMark }) {
  if (!result) return null
  const j = result.justification || {}
  const lecturer = mode === 'lecturer'
  const mark = result.effective_mark ?? result.mark
  const overridden = Boolean(result.override?.mark != null || result.overridden)
  const parts = contributions(result.factors, weights)
  const pattern = result.factors?.behavioral_pattern
  const audit = j.audit || {}
  const flags = j.flags || []

  return (
    <div className="space-y-8">
      <Card className="flex-col gap-6 p-6 sm:flex-row sm:items-center">
        <ScoreRing mark={mark} interval={overridden ? null : result.mark_interval} />
        <div className="min-w-0 flex-1 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <StatusPill status={result.status} />
            {overridden && <span className="inline-flex items-center gap-1 rounded-md bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-700 dark:bg-violet-950 dark:text-violet-300"><PenLine className="h-3 w-3" />Set by the lecturer</span>}
          </div>
          {j.friendly_summary && <p className="text-base leading-relaxed text-foreground">{j.friendly_summary}</p>}
          <p className="text-sm leading-relaxed text-muted-foreground">{j.summary}</p>
          {overridden && lecturer && result.override?.mark != null && (
            <p className="rounded-lg bg-violet-50 p-3 text-sm dark:bg-violet-950/30">
              <span className="font-medium">Your mark: {markText(result.override.mark)}.</span> The agent predicted {markText(result.mark)}. {result.override.reason}
              <span className="block text-xs text-muted-foreground">{result.override.by_name}, {when(result.override.at)}</span>
            </p>
          )}
          {lecturer && onSetMark && <button type="button" onClick={onSetMark} className="text-sm font-medium text-primary hover:underline">{overridden ? 'Change the mark' : 'Set a different mark'}</button>}
          <p className="flex items-start gap-1.5 text-xs text-muted-foreground"><Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />{lecturer ? 'This is a prediction to support your decision, not a grade. ' : 'This is a prediction from your repository and board, to be checked by your lecturer. '}{(j.caveats || [])[0]}</p>
        </div>
      </Card>

      {flags.length > 0 && (
        <Section title={lecturer ? 'Points to check' : 'Things your lecturer will look at'} icon={AlertTriangle}>
          <div className="space-y-2">
            {flags.map((f, i) => (
              <div key={i} className="rounded-xl border border-amber-300/70 bg-amber-50 p-3 text-sm dark:border-amber-900 dark:bg-amber-950/30">
                <p className="font-medium text-amber-900 dark:text-amber-200">{f.message}</p>
                {f.reason && lecturer && <p className="mt-1 text-xs text-amber-800/80 dark:text-amber-300/80">The agent {f.action === 'escalate' ? 'is leaving this to you' : f.action === 'accept' ? 'considered it and let it stand' : 'looked at it'}: {f.reason}</p>}
              </div>
            ))}
          </div>
        </Section>
      )}

      {parts.length > 0 && (
        <Section title="How the mark is made" hint={j.how_computed}>
          <ContributionBar parts={parts} />
          {pattern?.applied && pattern.modifier !== 1 && <p className="text-sm">The working pattern <span className="font-medium">{pattern.persona}</span> adjusted the total by a factor of {Number(pattern.modifier).toFixed(2)}.</p>}
        </Section>
      )}

      <Section title="The factors" hint="Each bar runs from 0 to 100. The lighter stretch is the range the score is likely to fall in; hatching means the sprint is still running.">
        <div className="grid gap-3 md:grid-cols-2">
          {FACTORS.map((m) => <FactorCard key={m.id} meta={m} result={result.factors?.[m.id]} block={j.factors?.[m.id]} />)}
          <Card className="gap-2 p-4 md:col-span-2">
            <h4 className="text-sm font-semibold text-foreground">Working pattern</h4>
            <p className="text-sm">{pattern?.persona ? <span className="font-medium">{pattern.persona}</span> : <span className="text-muted-foreground">Not classified</span>}{pattern && !pattern.applied && <span className="ml-2 text-xs text-muted-foreground">shown as a tendency; it only adjusts the mark once the sprint is final</span>}</p>
            {(j.factors?.behavioral_pattern?.reasons || []).filter(Boolean).slice(0, 2).map((r, i) => <p key={i} className="text-xs text-muted-foreground">{r}</p>)}
          </Card>
        </div>
      </Section>

      {lecturer && (
        <Section title="The code question" hint="Asked about a function the student wrote, to check they understand code with their name on it." icon={MessageSquareQuote}>
          <Quiz quiz={quiz} />
        </Section>
      )}

      {trajectory && (
        <Section title="Day by day" hint="How the predicted mark moved during the sprint.">
          <Card className="p-4"><Trajectory points={trajectory} /></Card>
        </Section>
      )}

      {lecturer && (audit.actions?.length > 0 || audit.checked?.length > 0 || audit.summary) && (
        <Section title="What the agent checked" hint="Before settling the mark the agent checks its own results. It can leave a factor out; it cannot change a score." icon={ShieldCheck}>
          <Card className="gap-3 p-4 text-sm">
            {audit.summary && <p>{audit.summary}</p>}
            {(audit.left_out && Object.keys(audit.left_out).length > 0) && (
              <ul className="space-y-1">{Object.entries(audit.left_out).map(([k, why]) => <li key={k} className="rounded-lg bg-muted p-2 text-xs"><span className="font-medium">{k.replace(/_/g, ' ')}</span> left out of the mark: {why}</li>)}</ul>
            )}
            {(audit.checked || []).length > 0 && (
              <Details summary={`${audit.checked.length} look-ups it made`}>
                <ul className="space-y-1 font-mono">{audit.checked.map((c, i) => <li key={i}><span className="text-foreground">{c.tool}</span> {c.result}</li>)}</ul>
              </Details>
            )}
            {(audit.actions || []).map((a) => <p key={a.id} className="text-xs text-muted-foreground"><span className="font-medium text-foreground">{a.factor.replace(/_/g, ' ')}</span>: {a.action}. {a.reason}</p>)}
            {audit.model && <p className="text-[11px] text-muted-foreground">Reasoning model: {audit.model}</p>}
          </Card>
        </Section>
      )}
    </div>
  )
}
ResultView.propTypes = { result: PropTypes.object, weights: PropTypes.object, mode: PropTypes.string, trajectory: PropTypes.array, quiz: PropTypes.object, onSetMark: PropTypes.func }
