import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  BookOpen,
  CalendarClock,
  Circle,
  KanbanSquare,
  MessageCircle,
  Sparkles,
} from 'lucide-react'
import { useAuth } from '../../auth/useAuth.js'
import { useScope } from '../../context/useScope.js'
import { getModule } from '../../constants/modules.js'
import { getGreeting, getShortName, formatToday } from '../../utils/greeting.js'
import { usePlanningData } from '../../../modules/planning/context/usePlanningData.js'
import { computeStageStats, getNextAction, STAGE_ORDER } from '../../../modules/planning/stageStats.js'
import { ACTIVITY_FEED } from '../../../modules/planning/data/mockData.js'
import { formatRelativeTime } from '../../../modules/planning/utils.js'
import ComponentLinkGrid from '../../components/ComponentLinkGrid.jsx'
import Card from '../../components/Card.jsx'
import EmptyState from '../../components/EmptyState.jsx'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'

const TASK_ORDER = { Blocked: 0, 'In Progress': 1, Todo: 2 }
const TASK_LABEL = { Blocked: 'Blocked', 'In Progress': 'In progress', Todo: 'Not started' }

function tutorUrl(team, prompt) {
  return team(`/tutor/chat?prompt=${encodeURIComponent(prompt)}`)
}

export default function StudentHome() {
  const { user } = useAuth()
  const { selectedGroup } = useScope()
  const { requirements, userStories, estimations, kanbanTasks, projectInfo, activityLog } = usePlanningData()
  const [today] = useState(() => Date.now())

  const team = (path) => `/teams/${selectedGroup?.code}${path}`
  const stats = computeStageStats({ requirements, userStories, estimations, kanbanTasks })
  const nextAction = getNextAction(stats)
  const stages = STAGE_ORDER.map((key) => stats[key])
  const activeStage = stages.find((stage) => stage.to === nextAction.to) || stages[0]

  const openTasks = [...kanbanTasks]
    .filter((task) => task.status !== 'Done')
    .sort((a, b) => (TASK_ORDER[a.status] ?? 9) - (TASK_ORDER[b.status] ?? 9))

  const doneCount = kanbanTasks.filter((task) => task.status === 'Done').length
  const sprintProgress = kanbanTasks.length ? Math.round((doneCount / kanbanTasks.length) * 100) : 0

  const sprintEnd = new Date(projectInfo.sprintEndDate)
  const daysLeft = Math.ceil((sprintEnd.getTime() - today) / 86400000)
  const sprintTiming =
    daysLeft > 1
      ? `${daysLeft} days left in ${projectInfo.sprintName}`
      : daysLeft === 1
        ? `${projectInfo.sprintName} ends tomorrow`
        : daysLeft === 0
          ? `${projectInfo.sprintName} ends today`
          : `${projectInfo.sprintName} ended ${sprintEnd.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`

  const timeByText = Object.fromEntries(ACTIVITY_FEED.map((item) => [item.text, item.time]))
  const updates = activityLog.slice(0, 3)

  const quickLinks = ['planning', 'tutor', 'performance', 'security'].map((key) => {
    const mod = getModule(key)
    const destinations = {
      planning: '/planning/dashboard',
      tutor: '/tutor/guidance',
      performance: '/performance/my-progress',
      security: '/security/dashboard',
    }
    return {
      key: mod.key,
      label: mod.label,
      icon: mod.icon,
      tagline: mod.tagline,
      to: team(destinations[key]),
    }
  })

  const nextPrompt = `I'm stuck on this next step: ${nextAction.text}. Explain what I should do, and what I need to understand first.`

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-medium text-muted-foreground">{formatToday()}</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-foreground">
            {getGreeting()}, {getShortName(user?.name)}
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            {selectedGroup?.name} · {projectInfo.sprintName} of {projectInfo.totalSprints} · {sprintTiming}.
            Start with one step. The rest of the sprint can wait.
          </p>
        </div>
        <Button asChild variant="outline" size="lg" className="shrink-0 self-start">
          <Link to={team('/planning/sprint-management')}>
            <KanbanSquare className="h-4 w-4" />
            Sprint board
          </Link>
        </Button>
      </div>

      <section
        aria-labelledby="next-action-heading"
        className="rounded-xl border border-primary/25 bg-card p-5 shadow-xs sm:p-6"
      >
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-start gap-4 min-w-0">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground">
              <CalendarClock className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <p id="next-action-heading" className="text-xs font-semibold uppercase tracking-wider text-primary">
                Do this next
              </p>
              <p className="mt-1 text-lg font-semibold text-foreground">{nextAction.text}</p>
              <p className="mt-1 text-sm text-muted-foreground">
                {activeStage?.label} · {activeStage?.caption}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 shrink-0">
            <Button asChild size="lg">
              <Link to={team(nextAction.to)}>
                Continue
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link to={tutorUrl(team, nextPrompt)}>
                <Sparkles className="h-4 w-4" />
                Ask the tutor
              </Link>
            </Button>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 gap-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-foreground">Open sprint tasks</h2>
              <p className="text-sm text-muted-foreground">Each task can open the board or a tutor explanation.</p>
            </div>
            <span className="text-xs font-medium text-muted-foreground shrink-0">
              {doneCount}/{kanbanTasks.length || 0} done
            </span>
          </div>
          {kanbanTasks.length > 0 && (
            <Progress value={sprintProgress} className="h-1.5" aria-label="Sprint tasks completed" />
          )}
          {openTasks.length === 0 ? (
            <EmptyState
              card={false}
              icon={Circle}
              title={kanbanTasks.length === 0 ? 'No sprint tasks yet' : 'You are clear for now'}
              description={
                kanbanTasks.length === 0
                  ? 'Tasks appear here once stories move onto the sprint board.'
                  : 'Every task on this board is done. Check the next recommended step if the pipeline still has work.'
              }
            />
          ) : (
            <ul className="divide-y divide-border">
              {openTasks.map((task) => {
                const prompt = `I'm working on the sprint task "${task.title}". What should I understand before I continue?`
                return (
                  <li key={task.id} className="flex flex-col gap-3 py-3 sm:flex-row sm:items-center sm:justify-between">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-foreground">{task.title}</p>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {TASK_LABEL[task.status] || task.status}
                        {task.requirementId ? ` · ${task.requirementId}` : ''}
                        {task.blockedReason ? ` · ${task.blockedReason}` : ''}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2 shrink-0">
                      <Button asChild variant="outline" size="sm">
                        <Link to={team('/planning/sprint-management')}>Open</Link>
                      </Button>
                      <Button asChild variant="ghost" size="sm">
                        <Link to={tutorUrl(team, prompt)}>
                          <MessageCircle className="h-3.5 w-3.5" />
                          Ask tutor
                        </Link>
                      </Button>
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
          {openTasks.length === 0 && (
            <Button asChild variant="outline" size="sm">
              <Link to={team('/planning/sprint-management')}>Open sprint board</Link>
            </Button>
          )}
        </Card>

        <Card className="gap-4">
          <div>
            <h2 className="text-base font-semibold text-foreground">Recent updates</h2>
            <p className="text-sm text-muted-foreground">From your planning workspace.</p>
          </div>
          {updates.length === 0 ? (
            <EmptyState
              card={false}
              title="No updates yet"
              description="Quality checks, estimates, and tutor notes will show up here."
            />
          ) : (
            <ul className="space-y-3">
              {updates.map((item) => (
                <li key={item.id} className="text-sm">
                  <p className="text-foreground">{item.text}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {timeByText[item.text] || formatRelativeTime(item.timestamp)}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <section aria-labelledby="pipeline-heading">
        <h2 id="pipeline-heading" className="text-base font-semibold text-foreground">
          Where the project stands
        </h2>
        <p className="mt-1 mb-3 text-sm text-muted-foreground">
          These four stages use the same progress as the planning workspace.
        </p>
        <ol className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {stages.map((stage, index) => (
            <li key={stage.key}>
              <Link
                to={team(stage.to)}
                className="flex h-full flex-col rounded-xl border border-border/60 bg-card p-4 outline-none transition-colors hover:border-primary/40 focus-visible:ring-2 focus-visible:ring-ring"
              >
                <span className="text-xs font-medium text-muted-foreground">Step {index + 1}</span>
                <span className="mt-1 text-sm font-semibold text-foreground">{stage.label}</span>
                <span className="mt-2 text-sm tabular-nums text-foreground">{stage.percent}%</span>
                <span className="mt-1 text-xs text-muted-foreground">{stage.caption}</span>
              </Link>
            </li>
          ))}
        </ol>
      </section>

      <section>
        <div className="mb-4 flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-base font-semibold text-foreground">Workspaces</h2>
        </div>
        <ComponentLinkGrid items={quickLinks} />
      </section>
    </div>
  )
}
