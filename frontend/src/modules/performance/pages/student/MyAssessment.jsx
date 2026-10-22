import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Hourglass, MessageSquareQuote } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import EmptyState from '@/shared/components/EmptyState.jsx'
import PageHeader from '@/shared/components/PageHeader.jsx'
import GithubIcon from '@/shared/github/GithubIcon.jsx'
import { githubKeys, githubService } from '@/shared/github/githubService.js'
import { assessmentApi } from '../../assessment/assessmentApi.js'
import ResultView from '../../assessment/ResultView.jsx'
import { PanelSkeleton } from '../../assessment/Reveal.jsx'

const sprintLabel = (id) => (/^sprint[-_ ]?\d+$/i.test(id) ? `Sprint ${id.match(/\d+/)[0]}` : String(id).replace(/[-_]/g, ' '))
const day = (iso) => (iso ? new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : '')

/** The signed-in student's own assessment, and nothing about anyone else. One tab for the final mark and one for each sprint of the team; only the chosen one is shown. */
export default function MyAssessment() {
  const { teamId } = useParams()
  const [params, setParams] = useSearchParams()
  const reports = useQuery({ queryKey: ['assessment', 'mine', 'reports', teamId], queryFn: () => assessmentApi.myReports(teamId), enabled: Boolean(teamId) })
  const waiting = useQuery({ queryKey: ['assessment', 'mine', 'quizzes', teamId, 'open'], queryFn: () => assessmentApi.myQuizzes(teamId, 'open'), enabled: Boolean(teamId) })
  const config = useQuery({ queryKey: githubKeys.config, queryFn: githubService.config })
  const github = useQuery({ queryKey: githubKeys.team(teamId), queryFn: () => githubService.team(teamId), enabled: Boolean(config.data?.configured) })
  const openCount = (waiting.data?.items || []).filter((q) => q.status === 'open' || q.status === 'extended').length
  const mine = github.data?.members?.[0]
  const needsConnect = github.data?.repo && mine && !mine.login

  const list = reports.data?.reports || []
  const sprints = (reports.data?.sprints?.length ? reports.data.sprints : list.map((r) => r.sprint)).filter(Boolean)
  const asked = params.get('sprint') || 'final'
  const tab = asked === 'final' || sprints.some((s) => s.id === asked) ? asked : 'final'   // an address with a sprint this team does not have opens the final mark
  const choose = (id) => setParams(id === 'final' ? {} : { sprint: id }, { replace: true })
  const sprint = sprints.find((s) => s.id === tab)
  const entry = list.find((r) => r.sprint?.id === tab)

  const tabs = [{ id: 'final', label: 'Final mark' }, ...sprints.map((s) => ({ id: s.id, label: sprintLabel(s.id) }))]
  const hasResult = (id) => id === 'final' ? Boolean(reports.data?.overall) : list.some((r) => r.sprint?.id === id && r.report)

  return (
    <div className="space-y-6">
      <PageHeader
        title="My assessment"
        description="Your final mark (the average of your sprints) and your predicted mark for each sprint, and why. It is a prediction made from your team's repository and Scrum board, to be checked by your lecturer. You see only your own."
        actions={(
          <Button asChild variant={openCount > 0 ? 'default' : 'outline'} size="sm">
            <Link to={`/teams/${teamId}/performance/my-assessment/questions`}>
              <MessageSquareQuote className="h-4 w-4" aria-hidden="true" />Code questions
              {openCount > 0 && <span className="ml-1 rounded-full bg-primary-foreground/20 px-1.5 text-[11px] tabular-nums">{openCount} waiting</span>}
            </Link>
          </Button>
        )}
      />
      {needsConnect && (
        <Card className="flex-row flex-wrap items-center justify-between gap-3 border-amber-300/70 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/30">
          <div className="flex items-center gap-3 text-sm"><GithubIcon className="h-5 w-5 shrink-0" /><div><p className="font-medium">Connect your GitHub account to this team</p><p className="text-xs text-muted-foreground">Your assessment is matched to you through your GitHub account.</p></div></div>
          <Button size="sm" asChild><Link to={`/teams/${teamId}/members`}>Connect GitHub</Link></Button>
        </Card>
      )}

      {reports.isPending ? <div className="space-y-6" aria-busy="true"><PanelSkeleton height={190} title={false} /><PanelSkeleton height={380} /></div> : list.length === 0 && !reports.data?.overall ? (
        <EmptyState icon={Hourglass} title="No assessment yet" description="It appears here after your lecturer runs the first snapshot of your team's sprint." />
      ) : (
        <>
          <div role="tablist" aria-label="Final mark or one sprint" className="inline-flex max-w-full gap-0.5 overflow-x-auto rounded-lg bg-muted p-0.5">
            {tabs.map((t) => (
              <button key={t.id} type="button" role="tab" aria-selected={tab === t.id} onClick={() => choose(t.id)}
                className={`shrink-0 rounded-md px-3.5 py-1.5 text-sm transition-colors ${tab === t.id ? 'bg-card font-medium text-foreground shadow-sm' : hasResult(t.id) ? 'text-muted-foreground hover:text-foreground' : 'text-muted-foreground/60 hover:text-muted-foreground'}`}>
                {t.label}
              </button>
            ))}
          </div>

          {tab === 'final' ? (
            reports.data?.overall ? (
              <section className="space-y-3">
                <p className="text-xs text-muted-foreground">The average of your {reports.data.overall.sprints_counted} sprint{reports.data.overall.sprints_counted === 1 ? '' : 's'} so far. Pick a sprint above to read it on its own.</p>
                <ResultView result={reports.data.overall} mode="student" />
              </section>
            ) : <Card className="p-5 text-sm text-muted-foreground">There is no final mark yet: your lecturer is still checking your first result.</Card>
          ) : (
            <section className="space-y-3">
              {sprint?.start && <p className="text-xs text-muted-foreground">{sprintLabel(sprint.id)} · {day(sprint.start)} to {day(sprint.end)}</p>}
              {!entry ? (
                <Card className="p-5 text-sm text-muted-foreground">{sprint?.state === 'upcoming' ? 'This sprint has not started yet.' : sprint?.state === 'current' ? 'This sprint is still running. A result appears after your lecturer runs a snapshot.' : 'There is no assessment for this sprint yet.'}</Card>
              ) : entry.status === 'under_review' || !entry.report ? (
                <Card className="p-5 text-sm">Your lecturer is checking this result before it is shown to you.</Card>
              ) : <ResultView key={tab} result={entry.report} mode="student" />}
            </section>
          )}
        </>
      )}
    </div>
  )
}
