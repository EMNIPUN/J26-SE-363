import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Hourglass, MessageSquareQuote } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import EmptyState from '@/shared/components/EmptyState.jsx'
import PageHeader from '@/shared/components/PageHeader.jsx'
import GithubIcon from '@/shared/github/GithubIcon.jsx'
import { githubKeys, githubService } from '@/shared/github/githubService.js'
import { showToast } from '@/shared/utils/toast.jsx'
import { assessmentApi } from '../../assessment/assessmentApi.js'
import ResultView from '../../assessment/ResultView.jsx'
import { PanelSkeleton } from '../../assessment/Reveal.jsx'

function hoursLeft(q) {
  const h = (new Date(q.extended_until || q.deadline_at) - Date.now()) / 36e5
  return h > 0 ? (h >= 48 ? `${Math.round(h / 24)} days` : `${Math.round(h)} hours`) : 'closed'
}

function Quiz({ quiz, onDone }) {
  const [answer, setAnswer] = useState('')
  const [busy, setBusy] = useState(false)
  const send = async () => {
    setBusy(true)
    try {
      const r = await assessmentApi.answerQuiz(quiz.id, answer)
      showToast.success(r.in_second_window ? 'Answer sent. It came in the second window, so the highest score for it is 50.' : 'Answer sent. Thank you.')
      onDone()
    } catch (e) {
      showToast.error(e.message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <Card className="gap-4 border-primary/30 p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="flex items-center gap-2 text-sm font-semibold"><MessageSquareQuote className="h-4 w-4 text-primary" aria-hidden="true" />A question about code you wrote · sprint {quiz.sprint_id}</h3>
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground"><Hourglass className="h-3.5 w-3.5" />{quiz.status === 'extended' ? 'Second window, ' : ''}{hoursLeft(quiz)} left</span>
      </div>
      <p className="font-mono text-xs text-muted-foreground">{quiz.file_path}{quiz.line_range ? `, lines ${quiz.line_range[0]} to ${quiz.line_range[1]}` : ''}</p>
      <pre className="max-h-64 overflow-auto rounded-lg bg-muted p-3 text-xs leading-relaxed">{quiz.snippet}</pre>
      <p className="text-sm font-medium text-foreground">{quiz.question}</p>
      <Textarea rows={5} value={answer} onChange={(e) => setAnswer(e.target.value)} placeholder="Explain in your own words." />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-xl text-xs text-muted-foreground">This checks that you understand code with your name on it. Answer from what you know. Copying the code or the question lowers the score.</p>
        <Button disabled={busy || answer.trim().length < 5} onClick={send}>Send my answer</Button>
      </div>
    </Card>
  )
}

/** The signed-in student's own assessment, and nothing about anyone else. */
export default function MyAssessment() {
  const { teamId } = useParams()
  const qc = useQueryClient()
  const reports = useQuery({ queryKey: ['assessment', 'mine', 'reports', teamId], queryFn: () => assessmentApi.myReports(teamId), enabled: Boolean(teamId) })
  const quizzes = useQuery({ queryKey: ['assessment', 'mine', 'quizzes', teamId], queryFn: () => assessmentApi.myQuizzes(teamId, 'open'), enabled: Boolean(teamId) })
  const config = useQuery({ queryKey: githubKeys.config, queryFn: githubService.config })
  const github = useQuery({ queryKey: githubKeys.team(teamId), queryFn: () => githubService.team(teamId), enabled: Boolean(config.data?.configured) })
  const open = (quizzes.data?.items || []).filter((q) => q.status === 'open' || q.status === 'extended')
  const mine = github.data?.members?.[0]
  const needsConnect = github.data?.repo && mine && !mine.login
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['assessment', 'mine', 'reports', teamId] })
    qc.invalidateQueries({ queryKey: ['assessment', 'mine', 'quizzes', teamId] })
  }

  return (
    <div className="space-y-6">
      <PageHeader title="My assessment" description="Your predicted mark for each sprint, and why. It is a prediction made from your team's repository and Scrum board, to be checked by your lecturer. You see only your own." />
      {needsConnect && (
        <Card className="flex-row flex-wrap items-center justify-between gap-3 border-amber-300/70 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/30">
          <div className="flex items-center gap-3 text-sm"><GithubIcon className="h-5 w-5 shrink-0" /><div><p className="font-medium">Connect your GitHub account to this team</p><p className="text-xs text-muted-foreground">Without it, your commits may not be matched to you and your assessment will be thinner.</p></div></div>
          <Button size="sm" asChild><Link to={`/teams/${teamId}/members`}>Connect GitHub</Link></Button>
        </Card>
      )}
      {open.map((q) => <Quiz key={q.id} quiz={q} onDone={refresh} />)}
      {reports.isPending ? <div className="space-y-6" aria-busy="true"><PanelSkeleton height={190} title={false} /><PanelSkeleton height={380} /></div> : (reports.data?.reports || []).length === 0 ? (
        <EmptyState icon={Hourglass} title="No assessment yet" description="It appears here after your lecturer runs the first snapshot of your team's sprint." />
      ) : (reports.data?.reports || []).map((r) => (
        <section key={`${r.team_ref}-${r.sprint_id}`} className="space-y-3">
          <h2 className="text-base font-semibold text-foreground">Sprint {r.sprint_id}</h2>
          {r.status === 'under_review' || !r.report ? <Card className="p-5 text-sm">Your lecturer is checking this result before it is shown to you.</Card> : <ResultView result={r.report} mode="student" />}
        </section>
      ))}
    </div>
  )
}
