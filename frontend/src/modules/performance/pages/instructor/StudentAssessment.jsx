import { useCallback, useState } from 'react'
import PropTypes from 'prop-types'
import { Link, useParams } from 'react-router-dom'
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
import { PanelSkeleton, ProfileSkeleton } from '../../assessment/Reveal.jsx'
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
/** The student as a person in this team: a large photo and name, which team and sprint this report is about, their GitHub account, and where they stand in the team. */
function Profile({ result, rows, teamName, sprint, sprintInfo, sprints = [], onSprintChange, login, back, action }) {
  const marks = (rows || []).map((r) => ({ id: r.student_id || r.id, mark: r.effective_mark ?? r.mark })).filter((r) => r.mark != null).sort((a, b) => b.mark - a.mark)
  const mine = result.effective_mark ?? result.mark
  const overall = result.scope === 'overall'  // the final mark: the average over every sprint
  const rank = mine == null || !overall ? null : marks.findIndex((r) => r.id === result.student_id) + 1  // the team's marks are final marks too
  const average = marks.length ? marks.reduce((a, r) => a + r.mark, 0) / marks.length : null
  const gap = mine != null && average != null ? Math.round(mine - average) : null
  const chips = [
    teamName && { Icon: Users, text: teamName },
    login && { Icon: GithubIcon, text: `@${login}` },
    rank > 0 && { Icon: Medal, text: `${ordinal(rank)} of ${marks.length} in the team${gap != null && marks.length > 1 ? ` · ${gap > 0 ? '+' : ''}${gap} vs the average` : ''}` },
  ].filter(Boolean)
  return (
    <section className="overflow-hidden rounded-2xl border bg-card shadow-sm">
      <div className="relative h-28 bg-gradient-to-r from-indigo-500 via-violet-500 to-sky-500 @xl:h-32">
        <div className="absolute inset-0 opacity-30 [background-image:radial-gradient(white_1px,transparent_1px)] [background-size:18px_18px]" aria-hidden="true" />
        <Button variant="secondary" size="sm" asChild className="absolute left-4 top-4 bg-white/90 text-slate-900 backdrop-blur hover:bg-white hover:text-slate-900"><Link to={back}><ArrowLeft className="h-4 w-4" />Team results</Link></Button>
        {action && <div className="absolute right-4 top-4">{action}</div>}
      </div>
      <div className="flex flex-col gap-5 px-6 pb-6 @xl:flex-row @xl:items-end @xl:gap-6">
        <div className="-mt-14 shrink-0 @xl:-mt-16"><div className="rounded-full bg-card p-1.5 shadow-lg ring-1 ring-border"><Avatar name={result.student?.name} picture={result.student?.picture} size={112} /></div></div>
        <div className="min-w-0 flex-1 space-y-3 @xl:pb-1">
          <div>
            <h1 className="text-2xl font-bold leading-tight tracking-tight text-foreground @xl:text-3xl">{result.student?.name}</h1>
            <p className="mt-1 text-sm text-muted-foreground">Assessment report</p>
          </div>
          <ul className="flex flex-wrap items-center gap-2">
            {sprints.length > 0 ? (
              <li className="inline-flex items-center gap-1.5 rounded-full border bg-muted/40 px-3 py-1 text-xs font-medium text-foreground">
                <CalendarRange className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                <span className="text-muted-foreground">Sprint:</span>
                <select
                  value={overall ? '' : sprint}
                  onChange={(e) => onSprintChange?.(e.target.value)}
                  className="bg-transparent font-semibold cursor-pointer border-none outline-none text-foreground py-0"
                  aria-label="Select sprint"
                >
                  <option value="" className="bg-popover text-popover-foreground">Overall (all sprints)</option>
                  {sprints.map((s) => (
                    <option key={s.id} value={s.id} className="bg-popover text-popover-foreground">
                      {s.id}
                    </option>
                  ))}
                </select>
                {!overall && sprintInfo && <span className="text-muted-foreground text-[11px] ml-1">· {day(sprintInfo.start)} to {day(sprintInfo.end)}</span>}
              </li>
            ) : (
              <li className="inline-flex items-center gap-1.5 rounded-full border bg-muted/40 px-3 py-1 text-xs font-medium text-foreground">
                <CalendarRange className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                Sprint {sprint}{sprintInfo ? ` · ${day(sprintInfo.start)} to ${day(sprintInfo.end)}` : ''}
              </li>
            )}
            {chips.map((c) => <li key={c.text} className="inline-flex items-center gap-1.5 rounded-full border bg-muted/40 px-3 py-1 text-xs font-medium text-foreground"><c.Icon className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />{c.text}</li>)}
          </ul>
        </div>
        <div className="shrink-0 rounded-2xl border bg-muted/30 px-5 py-3 text-center @xl:mb-1">
          <p className={`text-3xl font-bold tabular-nums leading-none ${styleOf(markBand(mine)).text}`}>{markText(mine)}</p>
          <p className="mt-1 text-[11px] uppercase tracking-wide text-muted-foreground">{overall ? 'final mark' : 'predicted mark'}</p>
        </div>
      </div>
    </section>
  )
}
Profile.propTypes = { result: PropTypes.object, rows: PropTypes.array, teamName: PropTypes.string, sprint: PropTypes.string, sprintInfo: PropTypes.object, sprints: PropTypes.array, onSprintChange: PropTypes.func, login: PropTypes.string, back: PropTypes.string, action: PropTypes.node }

/** One student for the lecturer: the mark and why, the evidence behind each factor, what the agent checked, and the lecturer's own mark. */
export default function StudentAssessment() {
  const { teamId, studentId } = useParams()
  const [sprintParam, setSprintParam] = useState('')  // the sprint on screen is kept here, not in the address; empty means the latest one with a result
  const qc = useQueryClient()
  const confirm = useConfirm()
  const [dialog, setDialog] = useState(false)
  const [seen, setSeen] = useState({})
  const onSeen = useCallback((name) => { if (name) setSeen((s) => (s[name] ? s : { ...s, [name]: true })) }, [])

  const report = useQuery({
    queryKey: assessmentKeys.report(teamId, sprintParam, studentId),
    queryFn: () => assessmentApi.report(teamId, sprintParam, studentId),
    enabled: Boolean(studentId),
  })
  const result = report.data
  const sprint = sprintParam || result?.sprint_id || ''

  const overview = useQuery({ queryKey: assessmentKeys.overview(teamId, sprint), queryFn: () => assessmentApi.overview(teamId, sprint), enabled: Boolean(sprint) })
  // day by day over every sprint, not only the one on screen
  const traj = useQuery({ queryKey: assessmentKeys.trajectoryAll(teamId, studentId), queryFn: () => assessmentApi.trajectoryAll(teamId, studentId), enabled: Boolean(result) && Boolean(seen.trajectory) })
  const histQuery = useQuery({ queryKey: assessmentKeys.history(teamId, studentId), queryFn: () => assessmentApi.history(teamId, studentId), enabled: Boolean(result) })
  const quiz = useQuery({ queryKey: assessmentKeys.questions(teamId, sprint, studentId), queryFn: () => assessmentApi.questions(teamId, sprint, studentId), enabled: Boolean(result) && Boolean(seen.quiz) })
  const runs = useQuery({ queryKey: assessmentKeys.runs(teamId, sprint), queryFn: () => assessmentApi.runs(teamId, sprint), enabled: Boolean(sprint) })
  const team = useTeam(teamId)
  const tracking = useQuery({ queryKey: assessmentKeys.setup(teamId, sprint), queryFn: () => assessmentApi.setup(teamId, sprint), retry: false })
  const readiness = tracking

  const sprints = tracking.data?.sprints || result?.all_sprints || overview.data?.sprints || []
  const history = result?.history || histQuery.data || null
  const latest = runs.data?.[0]
  const back = `/teams/${teamId}/performance/team/results`

  const onSprintChange = (newSprint) => {
    setSprintParam(newSprint)
  }

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

  if (report.isPending || (sprint && overview.isPending)) {
    return (
      <div className="space-y-6" aria-busy="true">
        <ProfileSkeleton />
        <PanelSkeleton height={190} title={false} />
        <div className="grid gap-6 @5xl:grid-cols-12"><div className="@5xl:col-span-7"><PanelSkeleton height={380} /></div><div className="space-y-6 @5xl:col-span-5"><PanelSkeleton height={150} /><PanelSkeleton height={220} /></div></div>
      </div>
    )
  }
  if (!result) return <EmptyState title="No result for this student" description="There is no result for this student in this sprint yet." actionLabel="Back to the team" onAction={() => window.history.back()} />

  return (
    <div className="space-y-6">
      <Profile
        result={result}
        rows={overview.data?.rows || []}
        teamName={team.data?.name}
        sprint={sprint}
        sprintInfo={sprints.find((x) => x.id === sprint)}
        sprints={sprints}
        onSprintChange={onSprintChange}
        login={readiness.data?.members?.find((m) => m.user_id === studentId)?.login}
        back={back}
        action={latest && !['queued', 'running', 'waiting_human'].includes(latest.status) ? <Button variant="secondary" onClick={evaluateAgain}><RefreshCw className="h-4 w-4" />Re-evaluate</Button> : null}
      />
      {result.scope === 'overall' && (
        <p className="rounded-lg border bg-card px-4 py-2.5 text-xs text-muted-foreground">
          Final result: the mark and the factor scores are the average of {result.sprints_counted} sprint{result.sprints_counted === 1 ? '' : 's'}. The agent's brief, reasons and checks below are from {result.narrative_sprint}; pick a sprint above to read another one.
        </p>
      )}
      <ResultView result={result} mode="lecturer" average={result.team_average} trajectory={Array.isArray(traj.data) ? traj.data : null} quiz={quiz.data} quizLoading={quiz.isPending} history={history} currentSprint={result.scope === 'overall' ? '' : sprint} questionsHref={`/teams/${teamId}/performance/students/${studentId}/questions`} onSetMark={result.scope === 'overall' ? undefined : () => setDialog(true)} onSeen={onSeen} />
      {dialog && <MarkDialog open onClose={() => setDialog(false)} result={result} onSave={save} />}
    </div>
  )
}
