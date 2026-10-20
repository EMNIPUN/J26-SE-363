import { useCallback, useState } from 'react'
import PropTypes from 'prop-types'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, CalendarRange, Medal, RefreshCw, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import EmptyState from '@/shared/components/EmptyState.jsx'
import { useConfirm } from '@/shared/utils/useConfirm.js'
import { showToast } from '@/shared/utils/toast.jsx'
import GithubIcon from '@/shared/github/GithubIcon.jsx'
import { useTeam } from '@/shared/hooks/useTeams.js'
import { assessmentApi, assessmentKeys } from '../../assessment/assessmentApi.js'
import { markBand, markText, styleOf } from '../../assessment/format.js'
import ResultView from '../../assessment/ResultView.jsx'
import { PanelSkeleton } from '../../assessment/Reveal.jsx'
import { Avatar } from '../../assessment/visuals.jsx'

function MarkDialog({ open, onClose, result, onSave }) {
  const [mark, setMark] = useState(result?.override?.mark ?? '')
  const [reason, setReason] = useState(result?.override?.reason ?? '')
  const ok = mark !== '' && Number(mark) >= 0 && Number(mark) <= 100 && reason.trim().length >= 10
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Set your own mark</DialogTitle>
          <DialogDescription>The agent predicted {markText(result?.mark)}. Your mark is shown to the student instead, and the prediction stays on record next to it.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-3">
          <label className="grid gap-1 text-sm">Mark (0 to 100)<Input type="number" min="0" max="100" value={mark} onChange={(e) => setMark(e.target.value)} /></label>
          <label className="grid gap-1 text-sm">Why<textarea className="min-h-24 rounded-md border bg-background p-2 text-sm" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="At least 10 characters. This is kept with the mark." /></label>
        </div>
        <DialogFooter>
          {result?.override?.mark != null && <Button variant="ghost" className="mr-auto" onClick={() => onSave(null, '')}>Use the prediction again</Button>}
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button disabled={!ok} onClick={() => onSave(Number(mark), reason)}>Save</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

const day = (iso) => (iso ? new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : '')
const ordinal = (n) => `${n}${['th', 'st', 'nd', 'rd'][n % 100 > 10 && n % 100 < 14 ? 0 : Math.min(n % 10, 4) % 4] || 'th'}`

/** The student as a person in this team: a large photo and name, which team and sprint this report is about, their GitHub account, and where they stand in the team. */
function Profile({ result, rows, teamName, sprint, sprintInfo, login, back, action }) {
  const marks = (rows || []).map((r) => ({ id: r.student_id, mark: r.effective_mark ?? r.mark })).filter((r) => r.mark != null).sort((a, b) => b.mark - a.mark)
  const mine = result.effective_mark ?? result.mark
  const rank = mine == null ? null : marks.findIndex((r) => r.id === result.student_id) + 1
  const average = marks.length ? marks.reduce((a, r) => a + r.mark, 0) / marks.length : null
  const gap = mine != null && average != null ? Math.round(mine - average) : null
  const chips = [
    teamName && { Icon: Users, text: teamName },
    { Icon: CalendarRange, text: `Sprint ${sprint}${sprintInfo ? ` · ${day(sprintInfo.start)} to ${day(sprintInfo.end)}` : ''}` },
    login && { Icon: GithubIcon, text: `@${login}` },
    rank > 0 && { Icon: Medal, text: `${ordinal(rank)} of ${marks.length} in the team${gap != null && marks.length > 1 ? ` · ${gap > 0 ? '+' : ''}${gap} vs the average` : ''}` },
  ].filter(Boolean)
  return (
    <section className="overflow-hidden rounded-2xl border bg-card shadow-sm">
      <div className="relative h-28 bg-gradient-to-r from-indigo-500 via-violet-500 to-sky-500 sm:h-32">
        <div className="absolute inset-0 opacity-30 [background-image:radial-gradient(white_1px,transparent_1px)] [background-size:18px_18px]" aria-hidden="true" />
        <Button variant="secondary" size="sm" asChild className="absolute left-4 top-4 bg-white/90 text-foreground backdrop-blur hover:bg-white"><Link to={back}><ArrowLeft className="h-4 w-4" />Team results</Link></Button>
        {action && <div className="absolute right-4 top-4">{action}</div>}
      </div>
      <div className="flex flex-col gap-5 px-6 pb-6 sm:flex-row sm:items-end sm:gap-6">
        <div className="-mt-14 shrink-0 sm:-mt-16"><div className="rounded-full bg-card p-1.5 shadow-lg ring-1 ring-border"><Avatar name={result.student?.name} picture={result.student?.picture} size={112} /></div></div>
        <div className="min-w-0 flex-1 space-y-3 sm:pb-1">
          <div>
            <h1 className="truncate text-3xl font-bold tracking-tight text-foreground sm:text-4xl">{result.student?.name}</h1>
            <p className="mt-1 text-sm text-muted-foreground">Assessment report</p>
          </div>
          <ul className="flex flex-wrap gap-2">
            {chips.map((c) => <li key={c.text} className="inline-flex items-center gap-1.5 rounded-full border bg-muted/40 px-3 py-1 text-xs font-medium text-foreground"><c.Icon className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />{c.text}</li>)}
          </ul>
        </div>
        <div className="shrink-0 rounded-2xl border bg-muted/30 px-5 py-3 text-center sm:mb-1">
          <p className={`text-4xl font-bold tabular-nums leading-none ${styleOf(markBand(mine)).text}`}>{markText(mine)}</p>
          <p className="mt-1 text-[11px] uppercase tracking-wide text-muted-foreground">predicted mark</p>
        </div>
      </div>
    </section>
  )
}
Profile.propTypes = { result: PropTypes.object, rows: PropTypes.array, teamName: PropTypes.string, sprint: PropTypes.string, sprintInfo: PropTypes.object, login: PropTypes.string, back: PropTypes.string, action: PropTypes.node }

/** One student for the lecturer: the mark and why, the evidence behind each factor, what the agent checked, and the lecturer's own mark. */
export default function StudentAssessment() {
  const { teamId, studentId } = useParams()
  const [params] = useSearchParams()
  const sprint = params.get('sprint') || ''
  const qc = useQueryClient()
  const confirm = useConfirm()
  const [dialog, setDialog] = useState(false)
  // The day by day view and the code questions are only asked for when their part of the page is about to be seen.
  const [seen, setSeen] = useState({})
  const onSeen = useCallback((name) => { if (name) setSeen((s) => (s[name] ? s : { ...s, [name]: true })) }, [])
  const results = useQuery({ queryKey: assessmentKeys.results(teamId, sprint), queryFn: () => assessmentApi.results(teamId, sprint), enabled: Boolean(sprint) })
  const result = results.data?.find((r) => r.student_id === studentId)
  const traj = useQuery({ queryKey: assessmentKeys.trajectory(teamId, sprint, studentId), queryFn: () => assessmentApi.trajectory(teamId, sprint, studentId), enabled: Boolean(result) && Boolean(seen.trajectory) })
  const quiz = useQuery({ queryKey: assessmentKeys.quiz(teamId, sprint, studentId), queryFn: () => assessmentApi.quiz(teamId, sprint, studentId), enabled: Boolean(result) && Boolean(seen.quiz) })
  const runs = useQuery({ queryKey: assessmentKeys.runs(teamId, sprint), queryFn: () => assessmentApi.runs(teamId, sprint), enabled: Boolean(sprint) })
  const team = useTeam(teamId)
  const tracking = useQuery({ queryKey: assessmentKeys.tracking(teamId), queryFn: () => assessmentApi.tracking(teamId), retry: false })
  const readiness = useQuery({ queryKey: assessmentKeys.readiness(teamId), queryFn: () => assessmentApi.readiness(teamId) })
  const weights = runs.data?.find((r) => r.summary?.method)?.summary.method.weights
  const latest = runs.data?.[0]
  const back = `/teams/${teamId}/performance/team/results?sprint=${encodeURIComponent(sprint)}`

  const save = async (mark, reason) => {
    try {
      await assessmentApi.setMark(teamId, sprint, studentId, { mark, reason })
      showToast.success(mark == null ? 'The prediction is used again' : 'Your mark is saved')
      setDialog(false)
      qc.invalidateQueries({ queryKey: ['assessment', teamId] })
    } catch (e) {
      showToast.error(e.message)
    }
  }
  const evaluateAgain = async () => {
    const ok = await confirm({ title: `Evaluate ${result.student?.name} again?`, description: 'The whole team is assessed again from the repository as it is now (the agent works on a team at a time). Earlier results stay available.', confirmText: 'Evaluate again' })
    if (!ok) return
    try {
      await assessmentApi.rerun(latest.id)
      showToast.success('Started again')
      qc.invalidateQueries({ queryKey: ['assessment', teamId] })
    } catch (e) {
      showToast.error(e.message)
    }
  }

  if (results.isPending) {
    return (
      <div className="space-y-8" aria-busy="true">
        <div className="flex items-center gap-4"><span className="h-12 w-12 animate-pulse rounded-full bg-muted" /><span className="h-5 w-48 animate-pulse rounded bg-muted" /></div>
        <PanelSkeleton height={200} title={false} />
        <PanelSkeleton height={160} />
        <PanelSkeleton height={220} />
      </div>
    )
  }
  if (!result) return <EmptyState title="No result for this student" description="There is no result for this student in this sprint yet." actionLabel="Back to the team" onAction={() => window.history.back()} />

  return (
    <div className="space-y-6">
      <Profile
        result={result} rows={results.data} teamName={team.data?.name} sprint={sprint} sprintInfo={tracking.data?.config?.sprints?.find((x) => x.id === sprint)}
        login={readiness.data?.members?.find((m) => m.user_id === studentId)?.login} back={back}
        action={latest && !['queued', 'running', 'waiting_human'].includes(latest.status) ? <Button variant="secondary" onClick={evaluateAgain}><RefreshCw className="h-4 w-4" />Re-evaluate</Button> : null}
      />
      <ResultView result={result} weights={weights} mode="lecturer" trajectory={traj.data} quiz={quiz.data} quizLoading={quiz.isPending} questionsHref={`/teams/${teamId}/performance/students/${studentId}/questions?sprint=${encodeURIComponent(sprint)}`} onSetMark={() => setDialog(true)} onSeen={onSeen} />
      {dialog && <MarkDialog open onClose={() => setDialog(false)} result={result} onSave={save} />}
    </div>
  )
}
