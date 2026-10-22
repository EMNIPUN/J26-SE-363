import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ArrowRight, CheckCircle2, Clock, MessageSquareQuote, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import EmptyState from '@/shared/components/EmptyState.jsx'
import PageHeader from '@/shared/components/PageHeader.jsx'
import { showToast } from '@/shared/utils/toast.jsx'
import { assessmentApi } from '../../assessment/assessmentApi.js'
import { when } from '../../assessment/format.js'
import { PanelSkeleton } from '../../assessment/Reveal.jsx'

const waiting = (q) => q.status === 'open' || q.status === 'extended'
const FILTERS = [
  { id: 'waiting', label: 'Waiting', test: waiting },
  { id: 'answered', label: 'Answered', test: (q) => q.status === 'answered' },
  { id: 'missed', label: 'Missed', test: (q) => q.status === 'expired' },
  { id: 'all', label: 'All', test: () => true },
]

const sprintLabel = (id) => (/^sprint[-_ ]?\d+$/i.test(id) ? `Sprint ${id.match(/\d+/)[0]}` : String(id).replace(/[-_]/g, ' '))

function timeLeft(q) {
  const h = (new Date(q.extended_until || q.deadline_at) - Date.now()) / 36e5
  return h > 0 ? (h >= 48 ? `${Math.round(h / 24)} days` : `${Math.round(h)} hours`) : 'closed'
}

/** The small mark in front of a question: where it stands. */
function State({ q }) {
  if (q.status === 'answered') return <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" aria-label="Answered" />
  if (q.status === 'expired') return <XCircle className="h-4 w-4 shrink-0 text-rose-500" aria-label="Missed" />
  return <Clock className="h-4 w-4 shrink-0 text-amber-600" aria-label="Waiting for your answer" />
}

/** One question: the code it is about, the question, and (while it is open) the box for the answer. */
function Question({ quiz, onSent, onNext, hasNext }) {
  const [answer, setAnswer] = useState('')
  const [busy, setBusy] = useState(false)
  const open = waiting(quiz)
  const send = async () => {
    setBusy(true)
    try {
      const r = await assessmentApi.answerQuiz(quiz.id, answer)
      showToast.success(r.in_second_window ? 'Answer sent. It came in the second window, so the highest score for it is 50.' : 'Answer sent. Thank you.')
      setAnswer('')
      onSent()
    } catch (e) {
      showToast.error(e.message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <Card className="gap-4 p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-foreground">{sprintLabel(quiz.sprint_id)} · question {quiz.n} of {quiz.of}</h2>
        {open && <span className="inline-flex items-center gap-1 text-xs text-muted-foreground"><Clock className="h-3.5 w-3.5" aria-hidden="true" />{quiz.status === 'extended' ? 'Second window, ' : ''}{timeLeft(quiz)} left</span>}
        {quiz.status === 'answered' && <span className="text-xs text-emerald-700 dark:text-emerald-400">Answered {when(quiz.answered_at)}</span>}
        {quiz.status === 'expired' && <span className="text-xs text-rose-600">Not answered in time</span>}
      </div>
      <p className="font-mono text-xs text-muted-foreground">{quiz.file_path}{quiz.line_range ? `, lines ${quiz.line_range[0]} to ${quiz.line_range[1]}` : ''}</p>
      <pre className="max-h-72 overflow-auto rounded-lg bg-muted p-3 text-xs leading-relaxed">{quiz.snippet}</pre>
      <p className="text-sm font-medium text-foreground">{quiz.question}</p>
      {open ? (
        <>
          <Textarea rows={6} value={answer} onChange={(e) => setAnswer(e.target.value)} placeholder="Explain in your own words." />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="max-w-xl text-xs text-muted-foreground">This checks that you understand code with your name on it. Answer from what you know. Copying the code or the question lowers the score.</p>
            <Button disabled={busy || answer.trim().length < 5} onClick={send}>Send my answer</Button>
          </div>
        </>
      ) : (
        <p className="rounded-lg bg-muted/50 p-3 text-sm text-muted-foreground">{quiz.status === 'answered' ? 'Your answer was sent and is being rated. It counts towards your Code Ownership score.' : 'The time for this question is over.'}</p>
      )}
      {hasNext && <div className="flex justify-end"><Button variant="ghost" size="sm" onClick={onNext}>Next question<ArrowRight className="h-4 w-4" /></Button></div>}
    </Card>
  )
}

/** The code questions of the signed-in student: all of them in one place, so the assessment page stays about the results. */
export default function MyQuestions() {
  const { teamId } = useParams()
  const qc = useQueryClient()
  const quizzes = useQuery({ queryKey: ['assessment', 'mine', 'quizzes', teamId, 'all'], queryFn: () => assessmentApi.myQuizzes(teamId), enabled: Boolean(teamId) })
  const [filter, setFilter] = useState(null)   // null until the student picks one: it opens on "Waiting", or "All" when nothing waits
  const [sprint, setSprint] = useState('all')
  const [picked, setPicked] = useState(null)

  const items = useMemo(() => [...(quizzes.data?.items || [])].sort((a, b) => String(a.sprint_id).localeCompare(String(b.sprint_id)) || a.n - b.n), [quizzes.data])
  const sprints = useMemo(() => [...new Set(items.map((q) => q.sprint_id))], [items])
  const counts = Object.fromEntries(FILTERS.map((f) => [f.id, items.filter(f.test).length]))
  const active = filter || (counts.waiting > 0 ? 'waiting' : 'all')
  const test = FILTERS.find((f) => f.id === active).test
  const visible = items.filter((q) => test(q) && (sprint === 'all' || q.sprint_id === sprint))
  const index = Math.max(0, visible.findIndex((q) => q.id === picked))
  const current = visible[index]

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['assessment', 'mine', 'quizzes', teamId] })
    qc.invalidateQueries({ queryKey: ['assessment', 'mine', 'reports', teamId] })
  }
  const afterAnswer = () => {
    const next = visible.slice(index + 1).find(waiting)
    refresh()
    if (next) setPicked(next.id)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Code questions"
        description="Questions about code you wrote, to check that you understand it. Each one is open for a limited time; answer from what you know."
        actions={<Button variant="outline" size="sm" asChild><Link to={`/teams/${teamId}/performance/my-assessment`}><ArrowLeft className="h-4 w-4" />My assessment</Link></Button>}
      />

      {quizzes.isPending ? <div className="space-y-6" aria-busy="true"><PanelSkeleton height={120} title={false} /><PanelSkeleton height={380} /></div> : items.length === 0 ? (
        <EmptyState icon={MessageSquareQuote} title="No code questions yet" description="They are asked in the final assessment of each sprint. They appear here as soon as your lecturer has run it." />
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div role="tablist" aria-label="Which questions" className="inline-flex flex-wrap gap-0.5 rounded-lg bg-muted p-0.5">
              {FILTERS.map((f) => (
                <button key={f.id} type="button" role="tab" aria-selected={active === f.id} onClick={() => { setFilter(f.id); setPicked(null) }}
                  className={`rounded-md px-3 py-1.5 text-xs transition-colors ${active === f.id ? 'bg-card font-medium text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}>
                  {f.label} <span className="tabular-nums text-muted-foreground">{counts[f.id]}</span>
                </button>
              ))}
            </div>
            {sprints.length > 1 && (
              <label className="flex items-center gap-2 text-xs text-muted-foreground">
                Sprint
                <select value={sprint} onChange={(e) => { setSprint(e.target.value); setPicked(null) }} className="rounded-lg border bg-background px-2 py-1.5 text-xs font-medium text-foreground">
                  <option value="all">All sprints</option>
                  {sprints.map((id) => <option key={id} value={id}>{sprintLabel(id)}</option>)}
                </select>
              </label>
            )}
          </div>

          {visible.length === 0 ? (
            <Card className="p-5 text-sm text-muted-foreground">{active === 'waiting' ? 'Nothing is waiting for your answer. Well done.' : 'No questions here.'}</Card>
          ) : (
            <div className="grid items-start gap-5 @3xl:grid-cols-[18rem_minmax(0,1fr)]">
              <Card className="max-h-[34rem] gap-0 overflow-y-auto p-1.5">
                <ul>
                  {visible.map((q, i) => (
                    <li key={q.id}>
                      {(i === 0 || visible[i - 1].sprint_id !== q.sprint_id) && <p className="px-2.5 pb-1 pt-2.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{sprintLabel(q.sprint_id)}</p>}
                      <button type="button" onClick={() => setPicked(q.id)} aria-current={q.id === current?.id}
                        className={`flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-sm transition-colors ${q.id === current?.id ? 'bg-muted font-medium text-foreground' : 'text-foreground/80 hover:bg-muted/60'}`}>
                        <State q={q} />
                        <span className="min-w-0 flex-1 truncate">Question {q.n} of {q.of}</span>
                        {waiting(q) && <span className="shrink-0 text-[11px] text-muted-foreground">{timeLeft(q)}</span>}
                      </button>
                    </li>
                  ))}
                </ul>
              </Card>
              {current && <Question key={current.id} quiz={current} onSent={afterAnswer} onNext={() => setPicked(visible[index + 1].id)} hasNext={index < visible.length - 1} />}
            </div>
          )}
        </>
      )}
    </div>
  )
}
