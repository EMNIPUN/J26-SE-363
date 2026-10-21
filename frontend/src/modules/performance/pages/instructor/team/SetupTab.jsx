import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { ArrowRight, BookOpenCheck, CheckCircle2, CircleDashed, ClipboardList, GitBranch, History, KanbanSquare, MessageSquareQuote, Moon, Scale, ShieldCheck, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import Badge from '@/shared/components/Badge.jsx'
import GithubIcon from '@/shared/github/GithubIcon.jsx'
import { MEMBER_STATE } from '@/shared/github/githubService.js'
import { when } from '../../../assessment/format.js'
import Panel from '../../../assessment/Panel.jsx'
import { PanelSkeleton, Stagger } from '../../../assessment/Reveal.jsx'
import { Avatar, RunPill } from '../../../assessment/visuals.jsx'

const DONE = ['succeeded', 'completed', 'finished']

function Check({ ok, partial, label, detail, action }) {
  return (
    <li className="flex items-start gap-3 rounded-xl border p-3.5">
      <span className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${ok ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-950' : partial ? 'bg-amber-100 text-amber-600 dark:bg-amber-950' : 'bg-muted text-muted-foreground'}`}>
        {ok ? <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> : <CircleDashed className="h-4 w-4" aria-hidden="true" />}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-foreground">{label}</p>
        <p className="truncate text-xs text-muted-foreground">{detail}</p>
      </div>
      {!ok && action}
    </li>
  )
}
Check.propTypes = { ok: PropTypes.bool, partial: PropTypes.bool, label: PropTypes.string, detail: PropTypes.string, action: PropTypes.node }

const STEPS = [
  { Icon: Moon, title: 'Every night: a snapshot', text: 'While the sprint runs, every student is assessed from the repository as it is. The marks are provisional and carry a wide range early on.' },
  { Icon: ClipboardList, title: 'At the end: the final assessment', text: 'Start it from the page header once the sprint is over. It is the run that counts, and it also asks each student questions about code they wrote.' },
  { Icon: MessageSquareQuote, title: 'The code questions', text: 'Students answer in 48 hours, with a second window of 48 hours where the best score is 50. An unanswered question counts as 0.' },
  { Icon: ShieldCheck, title: 'Your review', text: 'Anything the agent could not settle, such as unmatched commits or a factor that failed, waits in Reviews. You accept, set your own mark with a reason, or run it again.' },
  { Icon: Users, title: 'What students see', text: 'Each student sees only their own predicted mark and feedback. A result that is under review stays hidden from them until you have decided.' },
]

/**
 * The team's assessment setup, read only: whether everything the agent needs is in place, who is connected, what it reads, how a sprint is assessed, the weights in use and the latest runs.
 * The repository and the people come from GitHub (the team leader links them); the sprints and tasks come from the team's Scrum board.
 */
export default function SetupTab({ setup, loading, membersPath, base }) {
  if (loading) return <div className="space-y-6" aria-busy="true"><PanelSkeleton height={230} /><PanelSkeleton height={260} /><PanelSkeleton height={190} /></div>
  const members = setup?.members || []
  const ready = members.filter((m) => m.state === 'ready').length
  const sprints = setup?.sprints || []
  const finished = (setup?.recent_runs || []).some((r) => DONE.includes(r.status))
  const weights = setup?.weights
  const link = <Button size="sm" variant="outline" asChild><Link to={membersPath}>Open</Link></Button>
  const checks = [
    { label: 'Repository linked', ok: Boolean(setup?.repo), detail: setup?.repo || 'The team leader links it through GitHub', action: link },
    { label: 'Students connected to GitHub', ok: members.length > 0 && ready === members.length, partial: ready > 0, detail: members.length ? `${ready} of ${members.length} can write to the repository` : 'No students in the team yet', action: link },
    { label: 'Scrum board linked', ok: Boolean(setup?.board_ref), detail: setup?.board_ref ? `Board ${setup.board_ref}: tasks and acceptance criteria are read from it` : 'Tasks and acceptance criteria are read from the team\'s Scrum board' },
    { label: 'Sprints known', ok: sprints.length > 0, detail: sprints.length ? `${sprints.length} sprint${sprints.length === 1 ? '' : 's'} from the Scrum board` : 'They come from the Scrum board once it has sprints' },
    { label: 'Assessed at least once', ok: finished, detail: finished ? 'A run has finished for this team' : 'Start a snapshot from the page header' },
  ]
  const passed = checks.filter((c) => c.ok).length

  return (
    <Stagger className="space-y-6" step={110}>
      <Panel
        title="Ready to assess?" icon={BookOpenCheck} hint="What the agent needs before it can assess this team."
        aside={<Badge tone={setup?.ready ? 'success' : 'warning'}>{setup?.ready ? 'Ready to assess' : 'Not ready'}</Badge>}
      >
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-2.5 flex-1 gap-1" aria-hidden="true">{checks.map((c, i) => <span key={i} className={`flex-1 rounded-full transition-colors ${c.ok ? 'bg-emerald-500' : c.partial ? 'bg-amber-400' : 'bg-muted'}`} />)}</div>
          <span className="text-sm font-medium tabular-nums text-foreground">{passed} of {checks.length}</span>
        </div>
        {(setup?.blockers || []).map((b) => <p key={b} className="mb-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950/30 dark:text-amber-200">{b}</p>)}
        <ul className="grid gap-3 @2xl:grid-cols-2">{checks.map((c) => <Check key={c.label} {...c} />)}</ul>
      </Panel>

      <Panel
        title="Repository and people" icon={GitBranch} hint="Linked by the team leader through GitHub. Nobody types a roster."
        aside={<Button variant="outline" size="sm" asChild><Link to={membersPath}>Manage the GitHub link</Link></Button>}
      >
        {setup?.repo && <p className="mb-4 inline-flex items-center gap-2 rounded-lg bg-muted/60 px-3 py-1.5 font-mono text-sm"><GithubIcon className="h-4 w-4" />{setup.repo}</p>}
        <ul className="grid gap-3 @2xl:grid-cols-2">
          {members.map((m) => {
            const s = MEMBER_STATE[m.state] || MEMBER_STATE.not_connected
            return (
              <li key={m.user_id} className="flex items-center gap-3 rounded-xl border p-3.5">
                <Avatar name={m.name} picture={m.picture} size={44} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">{m.name}{m.is_leader && <span className="ml-2 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">Leader</span>}</p>
                  <p className="truncate font-mono text-xs text-muted-foreground">{m.login ? `@${m.login}` : 'No GitHub account connected'}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{s.help}</p>
                </div>
                <Badge tone={s.tone} title={s.help}>{s.label}</Badge>
              </li>
            )
          })}
          {members.length === 0 && <li className="text-sm text-muted-foreground">No students in the team yet.</li>}
        </ul>
        {(setup?.notes || []).length > 0 && <p className="mt-4 text-xs text-muted-foreground">{setup.notes.length} member{setup.notes.length > 1 ? 's' : ''} can still be assessed, but commits that cannot be matched to them will be sent to you to map.</p>}
      </Panel>

      <Panel title="What the agent reads" icon={KanbanSquare} hint="Only these. It never runs a student's code.">
        <div className="grid gap-3 @2xl:grid-cols-3">
          {[
            { Icon: GitBranch, title: 'The repository', lines: ['Commits, with their authors, times and changed lines', 'Pull requests, reviews and comments', 'The code around each change, read only'] },
            { Icon: KanbanSquare, title: 'The Scrum board', lines: ['Each task, who it is assigned to and its status', 'The acceptance criteria of each task', 'Story points and the sprint dates'] },
            { Icon: MessageSquareQuote, title: 'The students', lines: ['Their answers to the code questions', 'Which GitHub account is theirs, as GitHub confirmed it', 'Nothing from private messages or other tools'] },
          ].map((c) => (
            <div key={c.title} className="rounded-xl border bg-muted/20 p-4">
              <p className="flex items-center gap-2 text-sm font-semibold text-foreground"><c.Icon className="h-4 w-4 text-primary" aria-hidden="true" />{c.title}</p>
              <ul className="mt-2 space-y-1.5 text-xs text-muted-foreground">{c.lines.map((l) => <li key={l} className="flex gap-2"><span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-muted-foreground/60" />{l}</li>)}</ul>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="How a sprint is assessed" icon={ClipboardList} hint="From the first snapshot to what the students see.">
        <ol className="relative space-y-5">
          {STEPS.map((s, i) => (
            <li key={s.title} className="relative flex gap-4">
              {i < STEPS.length - 1 && <span className="absolute left-[17px] top-9 h-[calc(100%-0.5rem)] w-px bg-border" aria-hidden="true" />}
              <span className="relative z-10 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border bg-card text-primary shadow-sm"><s.Icon className="h-4 w-4" aria-hidden="true" /></span>
              <div className="min-w-0 pt-0.5"><p className="text-sm font-semibold text-foreground">{s.title}</p><p className="mt-0.5 text-sm leading-relaxed text-muted-foreground">{s.text}</p></div>
            </li>
          ))}
        </ol>
      </Panel>

      <div className="grid gap-6 @4xl:grid-cols-2">
        <Panel title="Weights in use" icon={Scale} hint="How much each factor counts towards the mark." aside={<Button variant="ghost" size="sm" asChild><Link to={`${base}/method`}>Method<ArrowRight className="h-3.5 w-3.5" /></Link></Button>}>
          {weights ? (
            <ul className="space-y-3">
              {Object.entries(weights).sort((a, b) => b[1] - a[1]).map(([k, w]) => (
                <li key={k} className="space-y-1">
                  <div className="flex justify-between text-sm"><span className="text-foreground">{k}</span><span className="tabular-nums text-muted-foreground">{Math.round(w * 100)}%</span></div>
                  <div className="h-2 rounded-full bg-muted"><div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500" style={{ width: `${w * 100 / Math.max(...Object.values(weights))}%` }} /></div>
                </li>
              ))}
            </ul>
          ) : <p className="text-sm text-muted-foreground">The weights are shown here after the first run. A factor that cannot be measured is left out and its weight is shared among the others.</p>}
        </Panel>

        <Panel title="Recent runs" icon={History} hint="The latest assessments of this team.">
          {(setup?.recent_runs || []).length === 0 ? <p className="text-sm text-muted-foreground">No assessment has run for this team yet.</p> : (
            <ul className="space-y-2">
              {setup.recent_runs.slice(0, 4).map((r) => (
                <li key={r.id} className="flex items-center gap-3 rounded-xl border p-3">
                  <RunPill status={r.status} />
                  <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium text-foreground">{r.mode === 'final' ? 'Final assessment' : 'Snapshot'} <span className="font-normal text-muted-foreground">of {r.sprint_id}</span></p><p className="text-xs text-muted-foreground">{when(r.created_at)}</p></div>
                  <Button size="sm" variant="ghost" asChild><Link to={`${base}/runs/${r.id}`}>Open</Link></Button>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </Stagger>
  )
}
SetupTab.propTypes = { setup: PropTypes.object, loading: PropTypes.bool, membersPath: PropTypes.string, base: PropTypes.string }
