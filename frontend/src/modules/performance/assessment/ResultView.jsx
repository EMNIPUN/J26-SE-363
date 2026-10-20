import { useRef, useState } from 'react'
import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { CartesianGrid, Area, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { AlertTriangle, ArrowRight, BarChart3, ChevronDown, Gauge, History, Info, Layers, LineChart, MessageSquareQuote, MinusCircle, PenLine, Radar, ShieldCheck, Sparkles, TrendingDown, TrendingUp } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { contributions, explainFactor, explainMark, FACTORS, factorState, markBand, markText, questionsOf, quizSummary, score100, styleOf, when } from './format.js'
import FactorRadar from './FactorRadar.jsx'
import Panel, { InfoTip } from './Panel.jsx'
import Reveal, { PanelSkeleton } from './Reveal.jsx'
import SprintHistory from './SprintHistory.jsx'
import { useContainerWidth } from './useContainerWidth.js'
import { ContributionBar, FactorBar, ScoreRing, StatusPill } from './visuals.jsx'

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

/**
 * Cards of different heights in columns that are filled from the top, each card going to the shortest column so far, so there are no gaps between rows and no card is stretched.
 * Each item has a rough height (`weight`); a card keeps its column when it opens, so nothing jumps. The number of columns follows the width the page has, not the window.
 */
function Masonry({ items }) {
  const box = useRef(null)
  const width = useContainerWidth(box)
  const n = width >= 1180 ? 3 : width >= 760 ? 2 : 1
  const columns = Array.from({ length: n }, () => ({ height: 0, nodes: [] }))
  items.forEach((item) => {
    const shortest = columns.reduce((best, c) => (c.height < best.height ? c : best), columns[0])
    shortest.nodes.push(item.node)
    shortest.height += item.weight
  })
  return (
    <div ref={box} className="flex items-start gap-4">
      {columns.map((c, i) => <div key={i} className="flex min-w-0 flex-1 flex-col gap-4">{c.nodes}</div>)}
    </div>
  )
}
Masonry.propTypes = { items: PropTypes.array }

/** One factor, short when closed (the score and one line) and full when open (why, what it is based on, what it measures, how far to trust it). */
function FactorCard({ meta, result, block, part, index, open, onToggle }) {
  const state = factorState(result)
  const reasons = (block?.reasons || []).filter(Boolean)
  const warnings = block?.warnings || []
  const id = `factor-${meta.id}`
  return (
    <Card className="animate-fade-rise gap-3.5 p-5" style={{ animationDelay: `${index * 90}ms` }}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="text-base font-semibold text-foreground">{meta.label}</h4>
            {result?.provisional && state.kind === 'scored' && <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">to date</span>}
          </div>
          <p className="truncate text-xs text-muted-foreground">{meta.question}</p>
        </div>
        <button
          type="button" onClick={onToggle} aria-expanded={open} aria-controls={id} aria-label={`${open ? 'Hide' : 'Show'} the explanation of ${meta.label}`}
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-muted-foreground transition-all hover:border-primary/50 hover:bg-primary/5 hover:text-primary ${open ? 'border-primary/40 bg-primary/5 text-primary' : ''}`}
        >
          <ChevronDown className={`h-4 w-4 transition-transform duration-300 ${open ? 'rotate-180' : ''}`} aria-hidden="true" />
        </button>
      </div>

      <FactorBar result={result} />
      {reasons[0] && <p className="line-clamp-2 text-sm leading-snug text-foreground/85">{reasons[0]}</p>}
      {warnings[0] && <p className="flex items-start gap-1.5 rounded-lg bg-amber-50 px-2.5 py-1.5 text-xs text-amber-800 dark:bg-amber-950/30 dark:text-amber-300"><AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" /><span className="line-clamp-1">{warnings[0]}{warnings.length > 1 ? ` (+${warnings.length - 1})` : ''}</span></p>}

      <div id={id}>
        <Collapse open={open}>
          <dl className="space-y-3.5 border-t pt-4 text-sm">
            <div><dt className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">In short</dt><dd className="mt-1 leading-relaxed text-foreground">{explainFactor(meta, result, part)}</dd></div>
            {reasons.length > 1 && (
              <div>
                <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Based on</dt>
                <dd className="mt-1"><ul className="space-y-1">{reasons.slice(1).map((r, i) => <li key={i} className="flex gap-2 text-foreground/90"><span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-muted-foreground/60" />{r}</li>)}</ul></dd>
              </div>
            )}
            {warnings.length > 1 && <div><dt className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Notes</dt><dd className="mt-1 space-y-1 text-amber-800 dark:text-amber-300">{warnings.slice(1).map((w, i) => <p key={i}>{w}</p>)}</dd></div>}
            <div><dt className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Measures</dt><dd className="mt-1 leading-relaxed text-muted-foreground">{meta.measures}</dd></div>
            {block?.how_much_to_trust && <div><dt className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">How far to trust it</dt><dd className="mt-1 leading-relaxed text-muted-foreground">{block.how_much_to_trust}</dd></div>}
          </dl>
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
  if (rows.length < 2) return <p className="rounded-lg bg-muted/50 p-4 text-sm text-muted-foreground">Needs at least two snapshots. One is taken every night while the sprint runs.</p>
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

const KIND = {
  strong: { Icon: TrendingUp, cls: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-300 dark:border-emerald-900' },
  weak: { Icon: TrendingDown, cls: 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/30 dark:text-rose-300 dark:border-rose-900' },
  flag: { Icon: AlertTriangle, cls: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/30 dark:text-amber-300 dark:border-amber-900' },
  out: { Icon: MinusCircle, cls: 'bg-slate-50 text-slate-600 border-slate-200 dark:bg-slate-900/40 dark:text-slate-300 dark:border-slate-800' },
  override: { Icon: PenLine, cls: 'bg-violet-50 text-violet-700 border-violet-200 dark:bg-violet-950/30 dark:text-violet-300 dark:border-violet-900' },
  range: { Icon: Info, cls: 'bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-950/30 dark:text-sky-300 dark:border-sky-900' },
  pattern: { Icon: Gauge, cls: 'bg-violet-50 text-violet-700 border-violet-200 dark:bg-violet-950/30 dark:text-violet-300 dark:border-violet-900' },
  provisional: { Icon: Info, cls: 'bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-950/30 dark:text-sky-300 dark:border-sky-900' },
}

function Line2({ line }) {
  const k = KIND[line.kind] || KIND.range
  return (
    <li className={`flex items-start gap-3 rounded-xl border px-3.5 py-2.5 ${k.cls}`}>
      <k.Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <div className="min-w-0 text-sm leading-snug"><span className="block text-[11px] font-semibold uppercase tracking-wide opacity-80">{line.lead}</span><span className="font-medium text-foreground">{line.text}</span></div>
    </li>
  )
}
Line2.propTypes = { line: PropTypes.object }

/** Why this student got this mark: the headline and the three things that matter most; everything else is one click away. */
function WhyThisMark({ result, weights }) {
  const [more, setMore] = useState(false)
  const { headline, key, more: rest } = explainMark(result, weights)
  const summary = result.justification?.summary
  if (!key.length && !summary) return null
  return (
    <div className="space-y-4">
      <p className="text-xl font-semibold leading-snug tracking-tight text-foreground">{headline}</p>
      <ul className="space-y-2">{key.map((l) => <Line2 key={l.kind} line={l} />)}</ul>
      {(rest.length > 0 || summary) && (
        <div>
          <button type="button" onClick={() => setMore(!more)} aria-expanded={more} className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline">
            <ChevronDown className={`h-4 w-4 transition-transform ${more ? 'rotate-180' : ''}`} aria-hidden="true" />{more ? 'Less detail' : `More detail (${rest.length + (summary ? 1 : 0)})`}
          </button>
          <Collapse open={more}>
            <div className="space-y-2 pt-3">
              <ul className="space-y-2">{rest.map((l) => <Line2 key={l.kind} line={l} />)}</ul>
              {summary && <p className="rounded-lg bg-muted/40 p-3 text-sm leading-relaxed text-muted-foreground">{summary}</p>}
            </div>
          </Collapse>
        </div>
      )}
    </div>
  )
}
WhyThisMark.propTypes = { result: PropTypes.object, weights: PropTypes.object }

/** The code check in a card: how it went in five numbers, and a way into the full list of questions, which has its own page. */
function QuestionsCard({ quiz, href, loading }) {
  const questions = questionsOf(quiz)
  if (loading) return <div className="h-24 animate-pulse rounded-xl bg-muted" aria-busy="true" />
  if (!questions.length) return <p className="rounded-lg bg-muted/50 p-4 text-sm text-muted-foreground">Not asked yet. It is asked in the final assessment.</p>
  const s = quizSummary(questions)
  const stats = [
    { label: 'Questions', value: s.total },
    { label: 'Answered', value: s.answered },
    { label: 'Waiting', value: s.open },
    { label: 'Missed', value: s.expired },
    { label: 'Average', value: s.average == null ? '-' : `${s.average.toFixed(1)}/5` },
  ]
  return (
    <div className="space-y-4">
      <dl className="grid grid-cols-3 gap-2.5 @2xl:grid-cols-5">
        {stats.map((x) => (
          <div key={x.label} className="rounded-xl border bg-muted/30 px-3 py-2.5">
            <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">{x.label}</dt>
            <dd className="mt-0.5 text-xl font-semibold tabular-nums text-foreground">{x.value}</dd>
          </div>
        ))}
      </dl>
      <Link to={href} className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3.5 py-2 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90">
        Open all {s.total} questions<ArrowRight className="h-4 w-4" aria-hidden="true" />
      </Link>
    </div>
  )
}
QuestionsCard.propTypes = { quiz: PropTypes.object, href: PropTypes.string, loading: PropTypes.bool }

/** What to look at first, as four short pills instead of a paragraph. */
function AtAGlance({ parts, flags, outCount }) {
  const top = [...parts].sort((a, b) => b.score - a.score)[0]
  const low = [...parts].sort((a, b) => a.score - b.score)[0]
  const items = [
    top && { Icon: TrendingUp, label: 'Strongest', value: `${top.label} ${score100(top.score)}`, cls: 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-300' },
    low && low !== top && { Icon: TrendingDown, label: 'Weakest', value: `${low.label} ${score100(low.score)}`, cls: 'border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-300' },
    flags > 0 && { Icon: AlertTriangle, label: 'To check', value: `${flags} point${flags === 1 ? '' : 's'}`, cls: 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-300' },
    outCount > 0 && { Icon: MinusCircle, label: 'Left out', value: `${outCount} factor${outCount === 1 ? '' : 's'}`, cls: 'border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-800 dark:bg-slate-900/40 dark:text-slate-300' },
  ].filter(Boolean)
  return (
    <ul className="flex flex-wrap gap-2">
      {items.map((i) => (
        <li key={i.label} className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm ${i.cls}`}>
          <i.Icon className="h-4 w-4 shrink-0" aria-hidden="true" /><span className="opacity-80">{i.label}</span><span className="font-semibold">{i.value}</span>
        </li>
      ))}
    </ul>
  )
}
AtAGlance.propTypes = { parts: PropTypes.array, flags: PropTypes.number, outCount: PropTypes.number }

/** Jump to a part of the page. It stays in view while scrolling. */
function JumpBar({ items }) {
  const go = (id) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  return (
    <nav aria-label="Sections of this report" className="sticky top-0 z-20 -mx-1 flex gap-1 overflow-x-auto rounded-xl border bg-card/90 p-1 shadow-sm backdrop-blur">
      {items.map((i) => <button key={i.id} type="button" onClick={() => go(i.id)} className="shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground">{i.label}</button>)}
    </nav>
  )
}
JumpBar.propTypes = { items: PropTypes.array }

const column = (id, node) => <div key={id} className="mb-6 break-inside-avoid">{node}</div>

/**
 * One student's assessment as a dashboard of separate sections: the mark and what to look at first; a jump bar; the factor radar, the points to check, how the mark is made and the sprint by sprint view
 * in balanced columns; the reason for the mark; every factor; the code questions and what the agent checked; day by day.
 * The page is meant to be scanned: short lead words and numbers show first, and the longer explanations sit behind an "i" or a "more" button.
 * `mode` "lecturer" adds the sprint by sprint view, the code questions, what the agent investigated and the lecturer's own mark; "student" shows only the student's own feedback.
 * The parts come in one after another with a skeleton in their place, and the later ones only when they are about to be seen (`onSeen` tells the page, so it asks the server for their data then).
 * Columns follow the width of the workspace (container queries), so the page holds together when the AI chat opens beside it.
 */
export default function ResultView({ result, weights, mode = 'lecturer', trajectory, quiz, quizLoading, questionsHref, history, average, currentSprint, onSetMark, onSeen }) {
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
  const hasAudit = audit.actions?.length > 0 || audit.checked?.length > 0 || audit.summary
  const showHistory = lecturer && Boolean(history)
  const jump = [
    { id: 'sec-profile', label: 'Factor profile' },
    showHistory && { id: 'sec-history', label: 'Sprint by sprint' },
    { id: 'sec-why', label: 'Why this mark' },
    { id: 'sec-factors', label: 'Factors' },
    lecturer && { id: 'sec-questions', label: 'Code questions' },
    (trajectory || onSeen) && { id: 'sec-day', label: 'Day by day' },
  ].filter(Boolean)

  return (
    <div className="space-y-6">
      <Reveal delay={0} height={200}>
        <Card className="flex-col gap-6 overflow-hidden border-t-4 p-6 @xl:flex-row @xl:items-center" style={{ borderTopColor: styleOf(markBand(mark)).ring }}>
          <ScoreRing mark={mark} interval={overridden ? null : result.mark_interval} />
          <div className="min-w-0 flex-1 space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <StatusPill status={result.status} />
              {overridden && <span className="inline-flex items-center gap-1 rounded-md bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-700 dark:bg-violet-950 dark:text-violet-300"><PenLine className="h-3 w-3" />Set by the lecturer</span>}
              <InfoTip label="this mark">{lecturer ? 'A prediction to support your decision, not a grade. ' : 'A prediction from your repository and board, to be checked by your lecturer. '}{(j.caveats || [])[0]}</InfoTip>
            </div>
            {j.friendly_summary && <p className="max-w-prose text-lg font-medium leading-snug text-foreground">{j.friendly_summary}</p>}
            <AtAGlance parts={parts} flags={flags.length} outCount={FACTORS.length - parts.length} />
            {overridden && lecturer && result.override?.mark != null && (
              <p className="rounded-lg bg-violet-50 p-3 text-sm dark:bg-violet-950/30">
                <span className="font-semibold">Your mark: {markText(result.override.mark)}</span> <span className="text-muted-foreground">(the agent predicted {markText(result.mark)})</span>. {result.override.reason}
                <span className="block text-xs text-muted-foreground">{result.override.by_name}, {when(result.override.at)}</span>
              </p>
            )}
            {lecturer && onSetMark && <button type="button" onClick={onSetMark} className="text-sm font-medium text-primary hover:underline">{overridden ? 'Change the mark' : 'Set a different mark'}</button>}
          </div>
        </Card>
      </Reveal>

      <JumpBar items={jump} />

      <div className="@4xl:columns-2 @4xl:gap-6">
        {column('profile', (
          <Reveal id="sec-profile" delay={120} height={420}>
            <Panel title="Factor profile" icon={Radar} hint="You against the team average" info="Every factor on one chart, from 0 at the centre to 100 at the edge. The dashed shape is the team average. A factor with no score is left out of the mark, not counted as zero.">
              <FactorRadar result={result} average={average} />
            </Panel>
          </Reveal>
        ))}
        {flags.length > 0 && column('flags', (
          <Reveal delay={200} height={140}>
            <Panel title={lecturer ? 'Points to check' : 'Your lecturer will look at'} icon={AlertTriangle} tone="warning" hint={`${flags.length} thing${flags.length === 1 ? '' : 's'} to look at`}>
              <div className="space-y-2">
                {flags.map((f, i) => (
                  <div key={i} className="rounded-xl border border-amber-300/70 bg-amber-50 p-3 dark:border-amber-900 dark:bg-amber-950/30">
                    <p className="text-sm font-semibold text-amber-900 dark:text-amber-200">{f.message}</p>
                    {f.reason && lecturer && <p className="mt-1 text-xs text-amber-800/80 dark:text-amber-300/80"><span className="font-medium">Agent:</span> {f.action === 'escalate' ? 'left it to you' : f.action === 'accept' ? 'let it stand' : 'looked at it'}. {f.reason}</p>}
                  </div>
                ))}
              </div>
            </Panel>
          </Reveal>
        ))}
        {parts.length > 0 && column('how', (
          <Reveal delay={300} height={200}>
            <Panel title="How the mark is made" icon={Layers} hint="Points each factor adds" info={j.how_computed}>
              <ContributionBar parts={parts} />
              {pattern?.applied && pattern.modifier !== 1 && <p className="mt-3 text-sm">Pattern <span className="font-medium">{pattern.persona}</span>: total adjusted by {Number(pattern.modifier).toFixed(2)}.</p>}
            </Panel>
          </Reveal>
        ))}
        {showHistory && column('history', (
          <Reveal id="sec-history" lazy name="history" onSeen={onSeen} delay={80} height={420}>
            <Panel title="Sprint by sprint" icon={History} hint="Each factor, every sprint" info="Each factor's score in every sprint, and how much it moved since the sprint before. Code Ownership is not followed this way: it is a few questions at the end of a sprint.">
              <SprintHistory history={history} current={currentSprint} />
            </Panel>
          </Reveal>
        ))}
        {column('why', (
          <Reveal id="sec-why" delay={400} height={260}>
            <Panel title="Why this mark" icon={Sparkles} hint="In plain words" info="Taken from the factors below. Nothing here is guessed.">
              <WhyThisMark result={result} weights={weights} />
            </Panel>
          </Reveal>
        ))}
      </div>

      <Reveal id="sec-factors" delay={200} height={320}>
        <Panel
          title="The factors" icon={BarChart3} hint="Open a card for the detail"
          info="Each bar runs from 0 to 100. The lighter stretch is the range the score is likely to fall in; hatching means the sprint is still running. The arrow on a card opens its explanation."
          aside={<button type="button" onClick={() => setAll(!allOpen)} className="rounded-lg border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-primary/50 hover:text-primary">{allOpen ? 'Collapse all' : 'Expand all'}</button>}
        >
          <Masonry
            items={[
              ...FACTORS.map((m, i) => {
                const reasons = (j.factors?.[m.id]?.reasons || []).filter(Boolean)
                return {
                  key: m.id,
                  weight: 170 + (reasons[0] ? 40 : 0) + ((j.factors?.[m.id]?.warnings || []).length ? 44 : 0),
                  node: <FactorCard key={m.id} index={i} meta={m} result={result.factors?.[m.id]} block={j.factors?.[m.id]} part={parts.find((p) => p.id === m.id)} open={Boolean(open[m.id])} onToggle={() => setOpen((o) => ({ ...o, [m.id]: !o[m.id] }))} />,
                }
              }),
              {
                key: 'pattern', weight: 120,
                node: (
                  <Card key="pattern" className="animate-fade-rise gap-2 p-5" style={{ animationDelay: `${FACTORS.length * 90}ms` }}>
                    <h4 className="text-base font-semibold text-foreground">Working pattern</h4>
                    <p className="text-sm">{pattern?.persona ? <span className="font-medium">{pattern.persona}</span> : <span className="text-muted-foreground">Not classified</span>}{pattern && !pattern.applied && <span className="mt-1 block text-xs text-muted-foreground">A tendency for now. It counts once the sprint is final.</span>}</p>
                    {(j.factors?.behavioral_pattern?.reasons || []).filter(Boolean).slice(0, 1).map((r, i) => <p key={i} className="line-clamp-2 text-xs text-muted-foreground">{r}</p>)}
                  </Card>
                ),
              },
            ]}
          />
        </Panel>
      </Reveal>

      {lecturer && (
        <div className="@4xl:columns-2 @4xl:gap-6">
          {column('quiz', (
            <Reveal id="sec-questions" lazy name="quiz" onSeen={onSeen} delay={80} height={220}>
              <Panel title="The code questions" icon={MessageSquareQuote} hint="About code the student wrote" info="Questions about functions this student wrote, to check they understand code with their name on it. The answers are rated by the answer scorer, which was checked on assistant-written answers only.">
                <QuestionsCard quiz={quiz} href={questionsHref} loading={quizLoading} />
              </Panel>
            </Reveal>
          ))}
          {hasAudit && column('audit', (
            <Reveal lazy name="audit" onSeen={onSeen} delay={80} height={220}>
              <Panel title="What the agent checked" icon={ShieldCheck} hint="Its own results, checked" info="Before settling the mark the agent checks its own results. It can leave a factor out; it cannot change a score.">
                <div className="space-y-3 text-sm">
                  {audit.summary && <p className="font-medium text-foreground">{audit.summary}</p>}
                  {(audit.left_out && Object.keys(audit.left_out).length > 0) && (
                    <ul className="space-y-1">{Object.entries(audit.left_out).map(([k, why]) => <li key={k} className="rounded-lg bg-muted p-2 text-xs"><span className="font-medium">{k.replace(/_/g, ' ')}</span> left out: {why}</li>)}</ul>
                  )}
                  {(audit.actions || []).map((a) => <p key={a.id} className="text-xs text-muted-foreground"><span className="font-medium text-foreground">{a.factor.replace(/_/g, ' ')}</span>: {a.action}. {a.reason}</p>)}
                  {(audit.checked || []).length > 0 && (
                    <Details summary={`${audit.checked.length} look-ups it made`}>
                      <ul className="space-y-1 font-mono">{audit.checked.map((c, i) => <li key={i}><span className="text-foreground">{c.tool}</span> {c.result}</li>)}</ul>
                    </Details>
                  )}
                  {audit.model && <p className="text-[11px] text-muted-foreground">Model: {audit.model}</p>}
                </div>
              </Panel>
            </Reveal>
          ))}
        </div>
      )}

      {(trajectory || onSeen) && (
        <Reveal id="sec-day" lazy name="trajectory" onSeen={onSeen} delay={80} height={380}>
          <Panel title="Day by day" icon={LineChart} hint="Predicted mark during the sprint">
            {trajectory ? <Trajectory points={trajectory} /> : <PanelSkeleton height={280} title={false} />}
          </Panel>
        </Reveal>
      )}
    </div>
  )
}
ResultView.propTypes = { result: PropTypes.object, weights: PropTypes.object, mode: PropTypes.string, trajectory: PropTypes.array, quiz: PropTypes.object, quizLoading: PropTypes.bool, questionsHref: PropTypes.string, history: PropTypes.object, average: PropTypes.object, currentSprint: PropTypes.string, onSetMark: PropTypes.func, onSeen: PropTypes.func }
