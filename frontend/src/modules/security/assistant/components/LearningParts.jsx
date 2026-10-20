import { Link } from 'react-router-dom'
import { FlaskConical } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import Badge from '@/shared/components/Badge.jsx'
import { MockBadge } from './common.jsx'
import { MOCK_NOTICE, conceptRows, decisionLabel, decisionTone, learningSummary, scorePercent } from '../lib/format.js'

// The notice that must be on the page: nothing here is an assessment of a student.
export function MockNotice({ tutor }) {
  return (
    <div role="note" data-slot="mock-notice" className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
      <FlaskConical className="mt-0.5 h-4 w-4 shrink-0" />
      <span>
        <span className="font-semibold">MOCK. </span>
        {MOCK_NOTICE}
        {tutor?.label ? <span className="mt-1 block text-xs opacity-80">{tutor.label}</span> : null}
      </span>
    </div>
  )
}

// A simulated score against the threshold, always with the MOCK label next to it.
export function ScoreBar({ score, threshold }) {
  const pct = scorePercent(score)
  const passed = Number(score) >= Number(threshold)
  return (
    <div data-slot="score" className="flex flex-wrap items-center gap-2 text-xs">
      <div
        role="img"
        aria-label={`simulated score ${score} against the threshold ${threshold}`}
        className="relative h-2 w-40 overflow-hidden rounded-full bg-muted"
      >
        <div className={`h-full ${passed ? 'bg-emerald-500' : 'bg-amber-500'}`} style={{ width: `${pct}%` }} />
        <div className="absolute inset-y-0 w-0.5 bg-foreground/70" style={{ left: `${scorePercent(threshold)}%` }} />
      </div>
      <span className="font-semibold">{score}</span>
      <span className="text-muted-foreground">of threshold {threshold}</span>
      <MockBadge>MOCK score</MockBadge>
    </div>
  )
}

export function AttemptThread({ attempts, threshold }) {
  return (
    <ol data-slot="attempts" className="space-y-3">
      {attempts.map((a) => (
        <li key={a.attempt} data-attempt={a.attempt} className="rounded-lg border border-border p-3">
          <p className="mb-1 flex flex-wrap items-center gap-2 text-xs font-semibold text-muted-foreground">
            Question {a.attempt} · hint level {a.hint_level}
            <Badge tone={Number(a.score) >= Number(threshold) ? 'success' : 'warning'}>{a.result}</Badge>
          </p>
          <p className="mb-2 text-sm">{a.text}</p>
          <ScoreBar score={a.score} threshold={threshold} />
        </li>
      ))}
    </ol>
  )
}

export function LearningItem({ item, threshold, to }) {
  return (
    <li data-slot="learning-item" data-group={item.group_id} data-decision={item.decision} className="space-y-3 rounded-xl border border-border bg-card p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-semibold">{item.title}</p>
          <p className="text-xs text-muted-foreground">
            {item.category} · concept: {item.concept ?? 'none'}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {item.mine && <Badge tone="primary">mine</Badge>}
          <Badge tone={decisionTone(item.decision)}>{decisionLabel(item.decision)}</Badge>
          <MockBadge />
        </div>
      </div>
      {item.escalation_reason ? <p className="text-xs">Why it was escalated: {item.escalation_reason}</p> : null}
      <AttemptThread attempts={item.attempts} threshold={item.threshold ?? threshold} />
      {to ? (
        <Link to={to} className="text-xs text-primary hover:underline">
          Open the finding
        </Link>
      ) : null}
    </li>
  )
}

const STATS = [
  ['concepts', 'Concepts covered'],
  ['closed', 'Closed'],
  ['escalated', 'Escalated to the lecturer'],
  ['attempts', 'Questions asked'],
]

// Concepts covered, closed against escalated, and questions asked, for the checks listed below it.
export function LearningSummaryCard({ items, scope }) {
  const summary = learningSummary(items)
  return (
    <Card data-slot="learning-summary" className="gap-4 p-5">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-sm font-semibold">Summary: {scope}</h2>
        <MockBadge>MOCK results</MockBadge>
      </div>
      <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {STATS.map(([key, label]) => (
          <div key={key} data-stat={key}>
            <dt className="text-xs text-muted-foreground">{label}</dt>
            <dd className="text-2xl font-bold">{summary[key]}</dd>
          </div>
        ))}
      </dl>
      {items.length ? (
        <Table data-slot="concept-table">
          <TableHeader>
            <TableRow>
              <TableHead>Concept</TableHead>
              <TableHead className="text-right">Checks</TableHead>
              <TableHead className="text-right">Closed</TableHead>
              <TableHead className="text-right">Escalated</TableHead>
              <TableHead className="text-right">Questions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {conceptRows(items).map((r) => (
              <TableRow key={r.id} data-concept={r.id}>
                <TableCell className="font-medium">{r.concept}</TableCell>
                <TableCell className="text-right">{r.checks}</TableCell>
                <TableCell className="text-right">{r.closed}</TableCell>
                <TableCell className="text-right">{r.escalated}</TableCell>
                <TableCell className="text-right">{r.attempts}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : null}
    </Card>
  )
}
