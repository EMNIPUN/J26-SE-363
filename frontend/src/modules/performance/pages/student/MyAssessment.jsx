import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import PageHeader from '@/shared/components/PageHeader.jsx'
import { assessmentApi } from '../../assessment/assessmentApi.js'
import StudentResultPanel from '../../assessment/StudentResultPanel.jsx'

function hoursLeft(q) {
  const end = new Date(q.extended_until || q.deadline_at)
  const h = (end - Date.now()) / 36e5
  return h > 0 ? (h >= 48 ? `${Math.round(h / 24)} days` : `${Math.round(h)} hours`) : 'closed'
}

function Quiz({ quiz, onDone }) {
  const [answer, setAnswer] = useState('')
  const [busy, setBusy] = useState(false)
  const send = async () => {
    setBusy(true)
    try {
      const r = await assessmentApi.answerQuiz(quiz.id, answer)
      toast.success(r.in_second_window ? 'Answer sent. It was given in the second window, so the highest score for it is 0.50.' : 'Answer sent. Thank you.')
      onDone()
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="rounded-xl border bg-card p-5 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold text-sm">A question about code you wrote · sprint {quiz.sprint_id}</h3>
        <span className="text-xs text-muted-foreground">{quiz.status === 'extended' ? 'Second window: ' : ''}time left: {hoursLeft(quiz)}</span>
      </div>
      <p className="text-xs text-muted-foreground font-mono">{quiz.file_path}{quiz.line_range ? `, lines ${quiz.line_range[0]}–${quiz.line_range[1]}` : ''}</p>
      <pre className="overflow-auto rounded-lg bg-muted p-3 text-xs">{quiz.snippet}</pre>
      <p className="text-sm font-medium">{quiz.question}</p>
      <Textarea rows={5} value={answer} onChange={(e) => setAnswer(e.target.value)} placeholder="Explain in your own words." />
      <Button disabled={busy || answer.trim().length < 5} onClick={send}>Send my answer</Button>
      <p className="text-xs text-muted-foreground">This checks that you understand code with your name on it. Answer from what you know; copying the code or the question will lower the score.</p>
    </div>
  )
}

export default function MyAssessment() {
  const client = useQueryClient()
  const results = useQuery({ queryKey: ['perf-my-results'], queryFn: assessmentApi.myResults })
  const quizzes = useQuery({ queryKey: ['perf-my-quizzes'], queryFn: assessmentApi.myQuizzes })
  const open = (quizzes.data || []).filter((q) => q.status === 'open' || q.status === 'extended')
  const refresh = () => { client.invalidateQueries({ queryKey: ['perf-my-quizzes'] }); client.invalidateQueries({ queryKey: ['perf-my-results'] }) }

  return (
    <div className="space-y-6">
      <PageHeader title="My assessment" description="Your predicted mark for each sprint and why. It is a prediction made from your repository and board, to be checked by your lecturer." />
      {open.map((q) => <Quiz key={q.id} quiz={q} onDone={refresh} />)}
      {(results.data || []).length === 0 && <p className="text-sm text-muted-foreground">No assessment is available for you yet. It appears here after the first snapshot of your team.</p>}
      {(results.data || []).map((r) => (
        <div key={`${r.team_ref}-${r.sprint_id}`} className="rounded-xl border bg-card p-5 space-y-3">
          <h2 className="font-semibold">Sprint {r.sprint_id}</h2>
          {r.status === 'under_review' ? <p className="text-sm">Your lecturer is checking this result before it is shown.</p> : <StudentResultPanel result={r} />}
        </div>
      ))}
    </div>
  )
}
