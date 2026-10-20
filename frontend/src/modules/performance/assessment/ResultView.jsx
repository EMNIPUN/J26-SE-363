import { useState } from 'react'
import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { CartesianGrid, Area, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { AlertTriangle, ArrowRight, BarChart3, ChevronDown, Gauge, Info, Layers, LineChart, MessageSquareQuote, MinusCircle, PenLine, ShieldCheck, Sparkles, TrendingDown, TrendingUp } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { contributions, explainFactor, explainMark, FACTORS, factorState, markBand, markText, questionsOf, quizSummary, styleOf, when } from './format.js'
import Reveal from './Reveal.jsx'
import { ContributionBar, FactorBar, ScoreRing, StatusPill } from './visuals.jsx'

/** One clearly separated part of the page: its own box, a header with an icon, a title and what it is for, then the content. */
function Panel({ title, hint, icon: Icon, aside, tone = 'default', children }) {
  const chip = tone === 'warning' ? 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300' : 'bg-primary/10 text-primary'
  return (
    <section className="overflow-hidden rounded-2xl border bg-card shadow-sm">
      <header className="flex flex-wrap items-start gap-3 border-b bg-muted/40 px-5 py-4 sm:px-6">
        {Icon && <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${chip}`}><Icon className="h-[18px] w-[18px]" aria-hidden="true" /></span>}
        <div className="min-w-0 flex-1">
          <h3 className="text-base font-semibold tracking-tight text-foreground">{title}</h3>
          {hint && <p className="mt-0.5 text-sm leading-relaxed text-muted-foreground">{hint}</p>}
        </div>
        {aside}
      </header>
      <div className="p-5 sm:p-6">{children}</div>
    </section>
  )
}
Panel.propTypes = { title: PropTypes.string, hint: PropTypes.string, icon: PropTypes.elementType, aside: PropTypes.node, tone: PropTypes.string, children: PropTypes.node }

/** Opens and closes smoothly. The content stays in the page, so it can be found and read by assistive technology. */
function Collapse({ open, children }) {
  return (
    <div className="grid transition-[grid-template-rows] duration-300 ease-out" style={{ gridTemplateRows: open ? '1fr' : '0fr' }}>
      <div className="min-h-0 overflow-hidden" aria-hidden={!open}>{children}</div>
    </div>
  )
}
Collapse.propTypes = { open: PropTypes.bool, children: PropTypes.node }

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

/** One factor. The arrow opens the explanation: why this score, what it did to the mark, what it measures and how far to trust it. */
function FactorCard({ meta, result, block, part, index, open, onToggle }) {
  const state = factorState(result)
  const reasons = (block?.reasons || []).filter(Boolean)
  const id = `factor-${meta.id}`
  return (
    <Card className="animate-fade-rise gap-4 p-5" style={{ animationDelay: `${index * 90}ms` }}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="text-sm font-semibold text-foreground">{meta.label}</h4>
            {result?.provisional && state.kind === 'scored' && <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">to date</span>}
          </div>
          <p className="text-xs text-muted-foreground">{meta.question}</p>
        </div>
        <button
          type="button" onClick={onToggle} aria-expanded={open} aria-controls={id} aria-label={`${open ? 'Hide' : 'Show'} the explanation of ${meta.label}`}
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-muted-foreground transition-all hover:border-primary/50 hover:bg-primary/5 hover:text-primary ${open ? 'border-primary/40 bg-primary/5 text-primary' : ''}`}
        >
          <ChevronDown className={`h-4 w-4 transition-transform duration-300 ${open ? 'rotate-180' : ''}`} aria-hidden="true" />
        </button>
      </div>

      <FactorBar result={result} />
      {state.kind !== 'scored' && reasons[0] && <p className="text-xs leading-relaxed text-muted-foreground">{reasons[0]}</p>}
      {state.kind === 'scored' && reasons.length > 0 && (
        <ul className="space-y-1 text-sm text-foreground/90">
          {reasons.slice(0, 2).map((r, i) => <li key={i} className="flex gap-2"><span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-muted-foreground/60" />{r}</li>)}
        </ul>
      )}
      {(block?.warnings || []).length > 0 && (
        <ul className="space-y-1 rounded-lg bg-amber-50 p-2 text-xs text-amber-800 dark:bg-amber-950/30 dark:text-amber-300">
          {block.warnings.slice(0, 4).map((w, i) => <li key={i}>{w}</li>)}
        </ul>
      )}

      <div id={id}>
        <Collapse open={open}>
          <div className="space-y-3 border-t pt-4 text-sm">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">In short</p>
              <p className="mt-1 leading-relaxed text-foreground">{explainFactor(meta, result, part)}</p>
            </div>
            {reasons.length > 2 && (
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">What it is based on</p>
                <ul className="mt-1 space-y-1">{reasons.slice(2).map((r, i) => <li key={i} className="flex gap-2 text-foreground/90"><span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-muted-foreground/60" />{r}</li>)}</ul>
              </div>
            )}
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">What it measures</p>
              <p className="mt-1 leading-relaxed text-muted-foreground">{meta.measures}</p>
            </div>
            {block?.how_much_to_trust && (
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">How far to trust it</p>
                <p className="mt-1 leading-relaxed text-muted-foreground">{block.how_much_to_trust}</p>
              </div>
            )}
          </div>
        </Collapse>
      </div>
    </Card>
  )
}
FactorCard.propTypes = { meta: PropTypes.object, result: PropTypes.object, block: PropTypes.object, part: PropTypes.object, index: PropTypes.number, open: PropTypes.bool, onToggle: PropTypes.func }

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

const EXPLAIN_ICON = { strong: TrendingUp, weak: TrendingDown, out: MinusCircle, pattern: Gauge, range: Info, flag: AlertTriangle, override: PenLine }
const EXPLAIN_TONE = { strong: 'text-emerald-600', weak: 'text-rose-600', out: 'text-muted-foreground', pattern: 'text-violet-600', range: 'text-sky-600', flag: 'text-amber-600', override: 'text-violet-600' }

/** The overall explanation: why this student got this mark, in plain sentences. */
function WhyThisMark({ result, weights }) {
  const { headline, lines } = explainMark(result, weights)
  const j = result.justification || {}
  if (!lines.length && !j.summary) return null
  return (
    <div className="space-y-4">
      <p className="text-lg font-semibold leading-snug text-foreground">{headline}</p>
      {j.friendly_summary && <p className="leading-relaxed text-foreground/90">{j.friendly_summary}</p>}
      <ul className="space-y-2.5">
        {lines.map((l, i) => {
          const Icon = EXPLAIN_ICON[l.kind] || Info
          return (
            <li key={i} className="flex gap-3 rounded-xl bg-muted/40 p-3 text-sm leading-relaxed">
              <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${EXPLAIN_TONE[l.kind] || ''}`} aria-hidden="true" />
              <span>{l.text}</span>
            </li>
          )
        })}
      </ul>
      {j.summary && <p className="text-sm leading-relaxed text-muted-foreground">{j.summary}</p>}
    </div>
  )
}
WhyThisMark.propTypes = { result: PropTypes.object, weights: PropTypes.object }

/** The code check in a card: how it went and a way into the full list of questions, which has its own page. */
function QuestionsCard({ quiz, href, loading }) {
  const questions = questionsOf(quiz)
  if (loading) return <div className="h-24 animate-pulse rounded-xl bg-muted" aria-busy="true" />
  if (!questions.length) return <p className="rounded-lg bg-muted/50 p-4 text-sm text-muted-foreground">No code question has been asked for this sprint yet. It is asked in the final assessment.</p>
  const s = quizSummary(questions)
  const stats = [
    { label: 'Questions', value: s.total },
    { label: 'Answered', value: s.answered },
    { label: 'Waiting', value: s.open },
    { label: 'Not answered', value: s.expired },
    { label: 'Average rating', value: s.average == null ? '-' : `${s.average.toFixed(1)} / 5` },
  ]
  return (
    <div className="space-y-4">
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {stats.map((x) => (
          <div key={x.label} className="rounded-xl border bg-muted/30 px-3 py-2.5">
            <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">{x.label}</dt>
            <dd className="mt-0.5 text-lg font-semibold tabular-nums text-foreground">{x.value}</dd>
          </div>
        ))}
      </dl>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">Each question is about a function this student wrote. The answers are rated by the answer scorer, which was checked on assistant-written answers only.</p>
        <Link to={href} className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3.5 py-2 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90">
          Open all {s.total} questions<ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Link>
      </div>
    </div>
  )
}
QuestionsCard.propTypes = { quiz: PropTypes.object, href: PropTypes.string, loading: PropTypes.bool }

/**
 * One student's assessment, written for someone who has to act on it, in separate sections: the mark, what to check, how the mark is made, why this mark, each factor, the code questions, day by day, what the agent checked.
 * `mode` "lecturer" adds the code questions, what the agent investigated and the lecturer's own mark; "student" shows only the student's own feedback.
 * The parts come in one after another, and the later ones only when they are about to be seen (`onSeen` tells the page, so it asks the server for their data then).
 */
export default function ResultView({ result, weights, mode = 'lecturer', trajectory, quiz, quizLoading, questionsHref, onSetMark, onSeen }) {
  const [open, setOpen] = useState({})
  if (!result) return null
  const j = result.justification || {}
  const lecturer = mode === 'lecturer'
  const mark = result.effective_mark ?? result.mark
  const overridden = Boolean(result.override?.mark != null || result.overridden)
  const parts = contributions(result.factors, weights)
  const pattern = result.factors?.behavioral_pattern
  const audit = j.audit || {}
  const flags = j.flags || []
  const allOpen = FACTORS.every((f) => open[f.id])
  const setAll = (v) => setOpen(Object.fromEntries(FACTORS.map((f) => [f.id, v])))

  return (
    <div className="space-y-8">
      <Reveal delay={0} height={200}>
        <Card className="flex-col gap-6 overflow-hidden border-t-4 p-6 sm:flex-row sm:items-center" style={{ borderTopColor: styleOf(markBand(mark)).ring }}>
          <ScoreRing mark={mark} interval={overridden ? null : result.mark_interval} />
          <div className="min-w-0 flex-1 space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <StatusPill status={result.status} />
              {overridden && <span className="inline-flex items-center gap-1 rounded-md bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-700 dark:bg-violet-950 dark:text-violet-300"><PenLine className="h-3 w-3" />Set by the lecturer</span>}
            </div>
            {j.friendly_summary && <p className="text-base leading-relaxed text-foreground">{j.friendly_summary}</p>}
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
      </Reveal>

      {flags.length > 0 && (
        <Reveal delay={120} height={140}>
          <Panel title={lecturer ? 'Points to check' : 'Things your lecturer will look at'} icon={AlertTriangle} tone="warning">
            <div className="space-y-2">
              {flags.map((f, i) => (
                <div key={i} className="rounded-xl border border-amber-300/70 bg-amber-50 p-3 text-sm dark:border-amber-900 dark:bg-amber-950/30">
                  <p className="font-medium text-amber-900 dark:text-amber-200">{f.message}</p>
                  {f.reason && lecturer && <p className="mt-1 text-xs text-amber-800/80 dark:text-amber-300/80">The agent {f.action === 'escalate' ? 'is leaving this to you' : f.action === 'accept' ? 'considered it and let it stand' : 'looked at it'}: {f.reason}</p>}
                </div>
              ))}
            </div>
          </Panel>
        </Reveal>
      )}

      {parts.length > 0 && (
        <Reveal delay={220} height={200}>
          <Panel title="How the mark is made" hint={j.how_computed} icon={Layers}>
            <ContributionBar parts={parts} />
            {pattern?.applied && pattern.modifier !== 1 && <p className="mt-3 text-sm">The working pattern <span className="font-medium">{pattern.persona}</span> adjusted the total by a factor of {Number(pattern.modifier).toFixed(2)}.</p>}
          </Panel>
        </Reveal>
      )}

      <Reveal delay={320} height={220}>
        <Panel title="Why this mark" hint="The overall explanation, in plain sentences, taken from the factors below." icon={Sparkles}>
          <WhyThisMark result={result} weights={weights} />
        </Panel>
      </Reveal>

      <Reveal delay={420} height={320}>
        <Panel
          title="The factors" icon={BarChart3}
          hint="Each bar runs from 0 to 100. The lighter stretch is the range the score is likely to fall in; hatching means the sprint is still running. The arrow on a card explains it."
          aside={<button type="button" onClick={() => setAll(!allOpen)} className="rounded-lg border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-primary/50 hover:text-primary">{allOpen ? 'Collapse all' : 'Expand all'}</button>}
        >
          <div className="grid gap-4 md:grid-cols-2">
            {FACTORS.map((m, i) => (
              <FactorCard key={m.id} index={i} meta={m} result={result.factors?.[m.id]} block={j.factors?.[m.id]} part={parts.find((p) => p.id === m.id)} open={Boolean(open[m.id])} onToggle={() => setOpen((o) => ({ ...o, [m.id]: !o[m.id] }))} />
            ))}
            <Card className="animate-fade-rise gap-2 p-5 md:col-span-2" style={{ animationDelay: `${FACTORS.length * 90}ms` }}>
              <h4 className="text-sm font-semibold text-foreground">Working pattern</h4>
              <p className="text-sm">{pattern?.persona ? <span className="font-medium">{pattern.persona}</span> : <span className="text-muted-foreground">Not classified</span>}{pattern && !pattern.applied && <span className="ml-2 text-xs text-muted-foreground">shown as a tendency; it only adjusts the mark once the sprint is final</span>}</p>
              {(j.factors?.behavioral_pattern?.reasons || []).filter(Boolean).slice(0, 2).map((r, i) => <p key={i} className="text-xs text-muted-foreground">{r}</p>)}
            </Card>
          </div>
        </Panel>
      </Reveal>

      {lecturer && (
        <Reveal lazy name="quiz" onSeen={onSeen} delay={80} height={220}>
          <Panel title="The code questions" hint="Asked about functions the student wrote, to check they understand code with their name on it." icon={MessageSquareQuote}>
            <QuestionsCard quiz={quiz} href={questionsHref} loading={quizLoading} />
          </Panel>
        </Reveal>
      )}

      {(trajectory || onSeen) && (
        <Reveal lazy name="trajectory" onSeen={onSeen} delay={80} height={380}>
          <Panel title="Day by day" hint="How the predicted mark moved during the sprint." icon={LineChart}>
            {trajectory ? <Trajectory points={trajectory} /> : <div className="h-72 animate-pulse rounded-xl bg-muted" aria-busy="true" />}
          </Panel>
        </Reveal>
      )}

      {lecturer && (audit.actions?.length > 0 || audit.checked?.length > 0 || audit.summary) && (
        <Reveal lazy name="audit" onSeen={onSeen} delay={80} height={220}>
          <Panel title="What the agent checked" hint="Before settling the mark the agent checks its own results. It can leave a factor out; it cannot change a score." icon={ShieldCheck}>
            <div className="space-y-3 text-sm">
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
            </div>
          </Panel>
        </Reveal>
      )}
    </div>
  )
}
ResultView.propTypes = { result: PropTypes.object, weights: PropTypes.object, mode: PropTypes.string, trajectory: PropTypes.array, quiz: PropTypes.object, quizLoading: PropTypes.bool, questionsHref: PropTypes.string, onSetMark: PropTypes.func, onSeen: PropTypes.func }
