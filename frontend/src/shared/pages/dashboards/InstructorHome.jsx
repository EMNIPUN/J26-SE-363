import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  Ban,
  BookOpen,
  Eye,
  FolderKanban,
  Gavel,
  GraduationCap,
  MessageCircle,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'
import { useAuth } from '../../auth/useAuth.js'
import { useScope } from '../../context/useScope.js'
import { getGreeting, getShortName, formatToday } from '../../utils/greeting.js'
import { openAiPanel } from '../../utils/aiPanel.js'
import { usePlanningData } from '../../../modules/planning/context/usePlanningData.js'
import { buildLecturerSummary, DATA_SOURCE_NOTE } from '../../services/lecturerDashboard.js'
import Card from '../../components/Card.jsx'
import Badge from '../../components/Badge.jsx'
import EmptyState from '../../components/EmptyState.jsx'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

const DISMISS_KEY = 'selvia-lecturer-dismissed'
const STATUS_TONE = { 'On Track': 'success', 'Needs Attention': 'warning', 'At Risk': 'danger' }
const ATTENTION_ICON = {
  decision: Gavel,
  blocker: Ban,
  quality: Eye,
  security: ShieldAlert,
  support: Sparkles,
}
const CHAT_SUGGESTIONS = [
  'Which groups have blocked sprint tasks?',
  'Which groups are below the quality gate?',
  'What is waiting for my decision?',
]

function readDismissed() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(DISMISS_KEY) || '[]')
    return Array.isArray(saved) ? saved : []
  } catch {
    return []
  }
}

function SummaryCard({ icon: Icon, title, linkLabel, to, children }) {
  return (
    <Card className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Icon className="h-4 w-4" aria-hidden="true" />
        </span>
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
      </div>
      <div className="flex-1 space-y-3 text-sm">{children}</div>
      {to && (
        <Link
          to={to}
          className="inline-flex items-center gap-1 self-start rounded-sm text-sm font-medium text-primary outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring"
        >
          {linkLabel}
          <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
        </Link>
      )}
    </Card>
  )
}

function Stat({ label, value, tone }) {
  const toneClass =
    tone === 'warning'
      ? 'text-amber-700 dark:text-amber-400'
      : tone === 'danger'
        ? 'text-destructive'
        : tone === 'success'
          ? 'text-emerald-700 dark:text-emerald-400'
          : 'text-foreground'
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className={`text-lg font-semibold tabular-nums ${toneClass}`}>{value}</dd>
    </div>
  )
}

export default function InstructorHome() {
  const { user } = useAuth()
  const { selectedGroup, teamStudents } = useScope()
  const planning = usePlanningData()
  const [dismissed, setDismissed] = useState(readDismissed)

  const summary = useMemo(
    () =>
      buildLecturerSummary({
        planning: {
          requirements: planning.requirements,
          userStories: planning.userStories,
          estimations: planning.estimations,
          kanbanTasks: planning.kanbanTasks,
        },
        teamStudents,
      }),
    [planning.requirements, planning.userStories, planning.estimations, planning.kanbanTasks, teamStudents],
  )

  const team = (path) => `/teams/${selectedGroup?.code}${path}`
  const visible = summary.attention.filter((item) => !dismissed.includes(item.id))
  const { projects, groups, progress, requirements, security, learning } = summary

  const dismiss = (id) => {
    setDismissed((prev) => {
      const next = prev.includes(id) ? prev : [...prev, id]
      try {
        sessionStorage.setItem(DISMISS_KEY, JSON.stringify(next))
      } catch {
        // ignore storage errors
      }
      return next
    })
  }

  const restore = () => {
    setDismissed([])
    try {
      sessionStorage.removeItem(DISMISS_KEY)
    } catch {
      // ignore storage errors
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <p className="text-xs font-medium text-muted-foreground">{formatToday()}</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight text-foreground">
          {getGreeting()}, {getShortName(user?.name)}
        </h1>
        <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
          {projects.count} projects · {visible.length} item{visible.length === 1 ? '' : 's'} need your attention ·{' '}
          {requirements.groupsBelowGate} below the quality gate. {DATA_SOURCE_NOTE}
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <section aria-labelledby="attention-heading" className="xl:col-span-2">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <h2 id="attention-heading" className="text-base font-semibold text-foreground">
                Needs your attention
              </h2>
              <p className="text-sm text-muted-foreground">
                Observed items come from project records. Inferred items are signals, not facts. Students do not see this list.
              </p>
            </div>
            {dismissed.length > 0 && (
              <Button variant="ghost" size="sm" onClick={restore}>
                Restore hidden ({dismissed.length})
              </Button>
            )}
          </div>

          {visible.length === 0 ? (
            <EmptyState
              icon={Gavel}
              title="Nothing is waiting"
              description="Escalated planning cases, blocked sprint tasks, groups under the quality gate, open critical findings, and support signals will show up here."
            />
          ) : (
            <ul className="space-y-3">
              {visible.map((item) => {
                const Icon = ATTENTION_ICON[item.type] || Eye
                return (
                  <li key={item.id} className="rounded-xl border border-border/60 bg-card p-4 shadow-xs">
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <Icon className="h-4 w-4" aria-hidden="true" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge tone={item.kind === 'Observed' ? 'primary' : 'warning'}>{item.kind}</Badge>
                          <h3 className="text-sm font-semibold text-foreground">{item.title}</h3>
                        </div>
                        <p className="mt-1 text-sm text-muted-foreground">{item.detail}</p>
                        <p className="mt-2 text-xs text-muted-foreground">{item.evidence}</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          <Button asChild size="sm">
                            <Link to={team(item.path)}>
                              {item.cta}
                              <ArrowRight className="h-3.5 w-3.5" />
                            </Link>
                          </Button>
                          {item.dismissible && (
                            <Button variant="ghost" size="sm" onClick={() => dismiss(item.id)}>
                              Dismiss signal
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </section>

        <div className="space-y-6">
          <Card className="space-y-4">
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <MessageCircle className="h-4 w-4" aria-hidden="true" />
              </span>
              <h2 className="text-sm font-semibold text-foreground">Ask SELVIA</h2>
            </div>
            <p className="text-sm text-muted-foreground">
              Opens the AI chat beside this page. It is not connected to project data yet, so it will say so rather than invent an answer.
            </p>
            <div className="flex flex-col gap-2">
              {CHAT_SUGGESTIONS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => openAiPanel(prompt)}
                  className="rounded-lg border border-border px-3 py-2 text-left text-sm outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {prompt}
                </button>
              ))}
            </div>
            <Button type="button" className="w-full" onClick={() => openAiPanel()}>
              Open SELVIA chat
            </Button>
          </Card>

          <SummaryCard icon={FolderKanban} title="Project overview" linkLabel="All projects" to={team('/planning/instructor/projects')}>
            <dl className="grid grid-cols-2 gap-3">
              <Stat label="Active projects" value={projects.count} />
              <Stat label="Students on groups" value={projects.students} />
            </dl>
            <p className="text-xs text-muted-foreground">Batches: {projects.batches.join(', ')}</p>
            {projects.milestone ? (
              <p className="text-sm text-muted-foreground">
                {projects.milestone.groupName} is in {projects.milestone.sprintName} of {projects.milestone.totalSprints}, ending{' '}
                {new Date(projects.milestone.sprintEndDate).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}.
                Milestones are recorded for this group only.
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">No milestones are recorded yet.</p>
            )}
          </SummaryCard>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <SummaryCard
          icon={BookOpen}
          title="Project progress"
          linkLabel="Planning overview"
          to={team('/planning/instructor/dashboard')}
        >
          {progress ? (
            <>
              <p className="text-xs text-muted-foreground">
                {progress.groupName} is the group with a live planning board.
              </p>
              <ul className="space-y-2">
                {progress.stages.map((stage) => (
                  <li key={stage.key}>
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-foreground">{stage.label}</span>
                      <span className="tabular-nums text-muted-foreground">{stage.percent}%</span>
                    </div>
                    <Progress value={stage.percent} className="mt-1 h-1.5" aria-label={`${stage.label} ${stage.percent}%`} />
                  </li>
                ))}
              </ul>
              <p className="text-sm text-muted-foreground">
                {progress.outstandingCount} of {progress.totalTasks} sprint tasks still open
                {progress.blockedCount > 0 ? `, ${progress.blockedCount} blocked` : ''}.
              </p>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">No group has a live planning board yet.</p>
          )}
        </SummaryCard>

        <SummaryCard
          icon={ShieldCheck}
          title="Requirement quality"
          linkLabel="Planning decisions"
          to={team('/planning/instructor/arbitration')}
        >
          <dl className="grid grid-cols-3 gap-3">
            <Stat label="Passing" value={requirements.passing} tone="success" />
            <Stat label="Needs review" value={requirements.review} tone="warning" />
            <Stat label="Failing" value={requirements.failing} tone={requirements.failing ? 'danger' : undefined} />
          </dl>
          <p className="text-sm text-muted-foreground">
            {requirements.total} requirements checked for {requirements.groupName}.{' '}
            {requirements.groupsBelowGate} group{requirements.groupsBelowGate === 1 ? '' : 's'} sit below the {requirements.threshold}% gate.
          </p>
        </SummaryCard>

        <SummaryCard icon={ShieldAlert} title="Security findings" linkLabel="Security overview" to={team('/security/dashboard')}>
          <dl className="grid grid-cols-4 gap-3">
            <Stat label="Open" value={security.open} tone={security.open ? 'warning' : undefined} />
            <Stat label="In review" value={security.review} />
            <Stat label="Learning check" value={security.learning} />
            <Stat label="Closed" value={security.closed} tone="success" />
          </dl>
          <p className="text-sm text-muted-foreground">
            {security.criticalOpen > 0
              ? `${security.criticalOpen} critical finding${security.criticalOpen === 1 ? ' is' : 's are'} not closed yet.`
              : 'No critical finding is open.'}{' '}
            Counts come from the loaded findings, not a new scan.
          </p>
        </SummaryCard>

        <SummaryCard
          icon={GraduationCap}
          title="Learning & student support"
          linkLabel="Student evidence"
          to={team('/performance/students')}
        >
          <p className="text-sm text-muted-foreground">
            Explanation scores are on file for {learning.explanationScoresOnFile} of {learning.teamStudentCount} students in{' '}
            {selectedGroup?.code}.
          </p>
          <div className="rounded-lg border border-border bg-muted/30 p-3">
            <p className="text-xs font-medium text-foreground">Tutor evidence (sample learner)</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {learning.needsAttention} concepts need attention, {learning.developing} developing, and {learning.insufficient} without
              enough evidence. {learning.attempts} assessment attempt{learning.attempts === 1 ? '' : 's'} on file.
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              One sample record. Class-wide learning analytics are not connected yet.
            </p>
          </div>
        </SummaryCard>
      </div>

      <Card className="p-0 gap-0 overflow-hidden">
        <div className="flex flex-wrap items-end justify-between gap-3 px-6 pt-5 pb-3">
          <div>
            <h2 className="text-base font-semibold text-foreground">Groups & students</h2>
            <p className="text-sm text-muted-foreground">
              Sorted by quality-gate score. Status is the value stored on each project, not a new prediction.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(groups.statusCounts).map(([status, count]) => (
              <Badge key={status} tone={STATUS_TONE[status] || 'neutral'}>
                {status}: {count}
              </Badge>
            ))}
          </div>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="pl-6">Group</TableHead>
              <TableHead className="w-[90px]">Members</TableHead>
              <TableHead className="w-[180px]">Quality gate</TableHead>
              <TableHead className="w-[110px]">Open reviews</TableHead>
              <TableHead className="w-[140px]">Recorded status</TableHead>
              <TableHead className="w-[80px] pr-6 text-right">
                <span className="sr-only">Actions</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {groups.list.map((group) => (
              <TableRow key={group.id}>
                <TableCell className="pl-6">
                  <p className="font-medium text-foreground">{group.name}</p>
                  <p className="max-w-[260px] truncate text-xs text-muted-foreground">{group.project}</p>
                </TableCell>
                <TableCell className="tabular-nums">{group.members}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Progress value={group.qualityGate} className="h-1.5 w-20" aria-label={`${group.name} quality gate`} />
                    <span className="text-xs font-medium tabular-nums text-foreground">{group.qualityGate}%</span>
                  </div>
                </TableCell>
                <TableCell className="tabular-nums">{group.openArbitrations}</TableCell>
                <TableCell>
                  <Badge tone={STATUS_TONE[group.status] || 'neutral'}>{group.status}</Badge>
                </TableCell>
                <TableCell className="pr-6 text-right">
                  <Button asChild variant="ghost" size="sm">
                    <Link to={team(`/planning/instructor/groups/${group.id}`)} aria-label={`Open ${group.name}`}>
                      Open
                    </Link>
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <p className="border-t border-border px-6 py-3 text-xs text-muted-foreground">
          {groups.teamStudentCount} student profiles in {selectedGroup?.code}
          {groups.inferredCount > 0 ? `, ${groups.inferredCount} with an inferred check-in signal` : ''}.{' '}
          <Link to={team('/performance/students')} className="font-medium text-primary hover:underline">
            Open student evidence
          </Link>
        </p>
      </Card>
    </div>
  )
}
