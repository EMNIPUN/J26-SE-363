import { useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, ChevronDown, FileCode2, MessageSquareQuote } from 'lucide-react'
import EmptyState from '@/shared/components/EmptyState.jsx'
import { assessmentApi, assessmentKeys } from '../../assessment/assessmentApi.js'
import { questionsOf, quizSummary, when } from '../../assessment/format.js'
import Reveal, { PanelSkeleton, StatRowSkeleton } from '../../assessment/Reveal.jsx'
import { Avatar } from '../../assessment/visuals.jsx'

const STATUS = {
  answered: { label: 'Answered', cls: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300' },
  open: { label: 'Waiting for the answer', cls: 'bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300' },
  extended: { label: 'Second answer window', cls: 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300' },
  expired: { label: 'Not answered: counts as 0', cls: 'bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300' },
}
const FILTERS = [
  { id: 'all', label: 'All', test: () => true },
  { id: 'answered', label: 'Answered', test: (q) => q.status === 'answered' },
  { id: 'open', label: 'Waiting', test: (q) => q.status === 'open' || q.status === 'extended' },
  { id: 'expired', label: 'Not answered', test: (q) => q.status === 'expired' },
]

function Rating({ value }) {
  if (value == null) return null
  return (
    <span className="inline-flex items-center gap-1.5 text-xs" title={`Rated ${Number(value).toFixed(1)} of 5`}>
      <span className="flex gap-0.5" aria-hidden="true">{[1, 2, 3, 4, 5].map((i) => <span key={i} className={`h-1.5 w-4 rounded-full ${Number(value) >= i - 0.25 ? 'bg-primary' : 'bg-muted'}`} />)}</span>
      <span className="font-semibold tabular-nums text-foreground">{Number(value).toFixed(1)}</span>
    </span>
  )
}

function Question({ q, open, onToggle }) {
  const status = STATUS[q.status] || { label: q.status, cls: 'bg-muted text-muted-foreground' }
  const id = `question-${q.n}`
  return (
    <article className="overflow-hidden rounded-2xl border bg-card shadow-sm">
      <button type="button" onClick={onToggle} aria-expanded={open} aria-controls={id} className="flex w-full items-center gap-4 px-5 py-4 text-left transition-colors hover:bg-muted/40">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-sm font-semibold tabular-nums text-primary">{q.n}</span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium text-foreground">{q.question}</span>
          <span className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1 font-mono"><FileCode2 className="h-3.5 w-3.5" aria-hidden="true" />{q.file_path}{q.line_range ? `, lines ${q.line_range[0]} to ${q.line_range[1]}` : ''}</span>
            <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${status.cls}`}>{status.label}</span>
          </span>
        </span>
        <span className="hidden shrink-0 @xl:block"><Rating value={q.rating} /></span>
        <ChevronDown className={`h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-300 ${open ? 'rotate-180' : ''}`} aria-hidden="true" />
      </button>
      <div id={id} className="grid transition-[grid-template-rows] duration-300 ease-out" style={{ gridTemplateRows: open ? '1fr' : '0fr' }}>
        <div className="min-h-0 overflow-hidden" aria-hidden={!open}>
          <div className="space-y-4 border-t bg-muted/20 px-5 py-5">
            <div>
              <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">The code</p>
              <pre className="max-h-64 overflow-auto rounded-xl bg-muted p-3 text-xs leading-relaxed">{q.snippet}</pre>
            </div>
            <div>
              <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">The question</p>
              <p className="text-sm font-medium leading-relaxed text-foreground">{q.question}</p>
            </div>
            <div>
              <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">The answer{q.status === 'answered' ? ` · ${when(q.answered_at)}${q.in_second_window ? ' · second window, capped at 50' : ''}` : ''}</p>
              {q.status === 'answered' ? <blockquote className="rounded-xl border-l-4 border-primary/50 bg-primary/5 p-3 text-sm leading-relaxed">{q.answer}</blockquote> : <p className="text-sm text-muted-foreground">{q.status === 'expired' ? 'No answer was given in time.' : 'No answer yet.'}</p>}
            </div>
            {q.rating != null && <p className="text-sm">Rated <span className="font-semibold">{Number(q.rating).toFixed(1)} of 5</span> by the answer scorer, which was checked on assistant-written answers only.</p>}
            {(q.warnings || []).map((w, i) => <p key={i} className="text-xs text-amber-700 dark:text-amber-400">{w}</p>)}
          </div>
        </div>
      </div>
    </article>
  )
}

/** All the code questions asked of one student, on a page of their own: there can be ten or more, so they are a list to scan, filter and open one at a time. */
export default function StudentQuestions() {
  const { teamId, studentId } = useParams()
  const [params] = useSearchParams()
  const sprint = params.get('sprint') || ''
  const results = useQuery({ queryKey: assessmentKeys.results(teamId, sprint), queryFn: () => assessmentApi.results(teamId, sprint), enabled: Boolean(sprint) })
  const quiz = useQuery({ queryKey: assessmentKeys.quiz(teamId, sprint, studentId), queryFn: () => assessmentApi.quiz(teamId, sprint, studentId), enabled: Boolean(sprint) })
  const [filter, setFilter] = useState('all')
  const [open, setOpen] = useState({})
  const questions = useMemo(() => questionsOf(quiz.data), [quiz.data])
  const summary = quizSummary(questions)
  const shown = questions.filter(FILTERS.find((f) => f.id === filter).test)
  const person = results.data?.find((r) => r.student_id === studentId)?.student
  const name = person?.name
  const back = `/teams/${teamId}/performance/students/${studentId}?sprint=${encodeURIComponent(sprint)}`
  const allOpen = shown.length > 0 && shown.every((q) => open[q.n])

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link to={back} aria-label="Back to the student" className="flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"><ArrowLeft className="h-4 w-4" /></Link>
          {name && <Avatar name={name} picture={person?.picture} size={44} />}
          <div>
            <h1 className="flex items-center gap-2 text-lg font-semibold tracking-tight text-foreground"><MessageSquareQuote className="h-5 w-5 text-primary" aria-hidden="true" />Code questions</h1>
            <p className="text-sm text-muted-foreground">{name ? `${name} · ` : ''}Sprint {sprint}</p>
          </div>
        </div>
      </div>

      {quiz.isPending ? (
        <div className="space-y-6"><StatRowSkeleton count={4} /><div className="space-y-3">{[0, 1, 2, 3].map((i) => <PanelSkeleton key={i} height={84} title={false} />)}</div></div>
      ) : questions.length === 0 ? (
        <EmptyState icon={MessageSquareQuote} title="No questions yet" description="The code questions are asked in the final assessment of the sprint." />
      ) : (
        <>
          <dl className="grid grid-cols-2 gap-3 @xl:grid-cols-5">
            {[['Questions', summary.total], ['Answered', summary.answered], ['Waiting', summary.open], ['Not answered', summary.expired], ['Average rating', summary.average == null ? '-' : `${summary.average.toFixed(1)} / 5`]].map(([label, value]) => (
              <div key={label} className="rounded-2xl border bg-card px-4 py-3 shadow-sm">
                <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</dt>
                <dd className="mt-0.5 text-lg font-semibold tabular-nums text-foreground">{value}</dd>
              </div>
            ))}
          </dl>

          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border bg-card px-3 py-2 shadow-sm">
            <div role="tablist" aria-label="Filter the questions" className="flex flex-wrap gap-1">
              {FILTERS.map((f) => {
                const count = questions.filter(f.test).length
                return (
                  <button key={f.id} type="button" role="tab" aria-selected={filter === f.id} onClick={() => setFilter(f.id)}
                    className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${filter === f.id ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:bg-accent hover:text-foreground'}`}>
                    {f.label} <span className={`ml-1 text-xs tabular-nums ${filter === f.id ? 'opacity-80' : 'opacity-60'}`}>{count}</span>
                  </button>
                )
              })}
            </div>
            <button type="button" onClick={() => setOpen(Object.fromEntries(shown.map((q) => [q.n, !allOpen])))} className="rounded-lg border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-primary/50 hover:text-primary">{allOpen ? 'Collapse all' : 'Expand all'}</button>
          </div>

          <div className="space-y-3">
            {shown.length === 0 && <p className="rounded-xl bg-muted/50 p-4 text-sm text-muted-foreground">No question matches this filter.</p>}
            {shown.map((q, i) => (
              <Reveal key={`${filter}-${q.n}`} lazy={i >= 6} compact delay={i < 6 ? i * 70 : 0} height={84}>
                <Question q={q} open={Boolean(open[q.n])} onToggle={() => setOpen((o) => ({ ...o, [q.n]: !o[q.n] }))} />
              </Reveal>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
