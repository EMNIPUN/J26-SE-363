import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  Bot,
  CalendarClock,
  ClipboardCheck,
  Gauge,
  KanbanSquare,
  MessageCircle,
  ShieldAlert,
  Sparkles,
} from 'lucide-react'
import { useAuth } from '../../auth/useAuth.js'
import { useScope } from '../../context/useScope.js'
import { getModule } from '../../constants/modules.js'
import { getGreeting, getShortName, formatToday } from '../../utils/greeting.js'
import StatCard from '../../components/StatCard.jsx'
import ComponentLinkGrid from '../../components/ComponentLinkGrid.jsx'
import Card from '../../components/Card.jsx'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Progress } from '@/components/ui/progress'

const INITIAL_TASKS = [
  { id: 't1', label: 'Submit requirement decomposition', due: 'Done', done: true, path: '/planning/requirements/decomposition' },
  { id: 't2', label: 'Review open DART arbitration flags', due: 'Due tomorrow', done: false, path: '/planning/dashboard' },
  { id: 't3', label: 'Fix flagged security findings', due: 'Due in 3 days', done: false, path: '/security/remediation' },
  { id: 't4', label: 'Complete JWT authentication quiz', due: 'Due in 4 days', done: false, path: '/tutor/activity/act-quiz-jwt' },
]

const ACTIVITY = [
  {
    id: 'a1',
    icon: ClipboardCheck,
    tone: 'bg-primary/10 text-primary',
    text: (
      <>
        SRS Quality Gate re-scored <strong className="font-semibold">REQ-014</strong> — now passing.
      </>
    ),
    time: '2 hours ago',
    path: '/planning/requirements/srs-quality',
  },
  {
    id: 'a2',
    icon: Bot,
    tone: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400',
    text: 'AI Tutor recommended a coding exercise on JWT validation middleware.',
    time: 'Yesterday',
    path: '/tutor/activity/act-ex-jwt-middleware',
  },
  {
    id: 'a3',
    icon: ShieldAlert,
    tone: 'bg-destructive/10 text-destructive',
    text: (
      <>
        AEGIS flagged a hardcoded secret in{' '}
        <code className="rounded bg-muted px-1.5 py-0.5 text-xs">config.py</code>.
      </>
    ),
    time: '2 days ago',
    path: '/security/scan-report',
  },
]

export default function StudentHome() {
  const { user } = useAuth()
  const { selectedGroup } = useScope()
  const [tasks, setTasks] = useState(INITIAL_TASKS)

  const team = (path) => `/teams/${selectedGroup?.code}${path}`
  const completed = tasks.filter((t) => t.done).length
  const progress = Math.round((completed / tasks.length) * 100)

  const quickLinks = [
    { ...getModule('planning'), to: team('/planning/dashboard') },
    { ...getModule('performance'), to: team('/performance/my-progress') },
    { ...getModule('tutor'), to: team('/tutor/chat') },
    { ...getModule('security'), to: team('/security/dashboard') },
  ]

  const toggleTask = (id) =>
    setTasks((prev) => prev.map((t) => (t.id === id ? { ...t, done: !t.done } : t)))

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-medium text-muted-foreground">{formatToday()}</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-foreground">
            {getGreeting()}, {getShortName(user.name)}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground truncate">
            {selectedGroup?.name} · Sprint 4 of 6 · Here&apos;s what needs your attention today.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <Button asChild variant="outline" size="lg">
            <Link to={team('/planning/sprint-management')}>
              <KanbanSquare className="h-4 w-4" />
              Sprint board
            </Link>
          </Button>
          <Button asChild size="lg">
            <Link to={team('/tutor/chat')}>
              <Sparkles className="h-4 w-4" />
              Ask AI Tutor
            </Link>
          </Button>
        </div>
      </div>

      <Link
        to={team('/planning/sprint-management')}
        className="group flex flex-col gap-4 rounded-xl border border-primary/20 bg-primary/5 p-5 sm:flex-row sm:items-center sm:justify-between outline-none focus-visible:ring-2 focus-visible:ring-ring transition-colors hover:bg-primary/10"
      >
        <div className="flex items-start gap-4 min-w-0">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <CalendarClock className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wider text-primary">Up next</p>
            <p className="mt-0.5 text-base font-semibold text-foreground">Sprint 4 review with your supervisor</p>
            <p className="text-sm text-muted-foreground">Friday, 10:00 AM · 3 days left to finish open tasks</p>
          </div>
        </div>
        <span className="inline-flex items-center gap-1.5 text-sm font-medium text-primary shrink-0">
          View sprint
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
        </span>
      </Link>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={ClipboardCheck} label="Quality gate score" value="86%" trend="+4% this sprint" tone="success" />
        <StatCard icon={Gauge} label="My contribution score" value="7.8 / 10" trend="Team average 7.4" tone="primary" />
        <StatCard icon={MessageCircle} label="Tutor sessions" value="12" trend="3 this week" tone="primary" />
        <StatCard icon={ShieldAlert} label="Open security findings" value="3" trend="1 critical" tone="warning" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-foreground">Recent activity</h2>
            <span className="text-xs text-muted-foreground">Across all components</span>
          </div>
          <ul className="divide-y divide-border">
            {ACTIVITY.map((item) => {
              const Icon = item.icon
              return (
                <li key={item.id}>
                  <Link
                    to={team(item.path)}
                    className="group -mx-2 flex items-start gap-3 rounded-lg px-2 py-3 transition-colors hover:bg-muted/60 outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${item.tone}`}>
                      <Icon className="h-4 w-4" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm text-foreground">{item.text}</span>
                      <span className="mt-0.5 block text-xs text-muted-foreground">{item.time}</span>
                    </span>
                    <ArrowRight className="mt-2 h-4 w-4 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                  </Link>
                </li>
              )
            })}
          </ul>
        </Card>

        <Card className="gap-4">
          <div>
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-foreground">Sprint checklist</h2>
              <span className="text-xs font-medium text-muted-foreground">
                {completed}/{tasks.length} done
              </span>
            </div>
            <Progress value={progress} className="mt-3 h-1.5" aria-label="Sprint checklist progress" />
          </div>
          <ul className="space-y-1">
            {tasks.map((task) => (
              <li key={task.id} className="flex items-start gap-3 rounded-lg px-2 py-2 -mx-2 hover:bg-muted/60 transition-colors">
                <Checkbox
                  id={`task-${task.id}`}
                  checked={task.done}
                  onCheckedChange={() => toggleTask(task.id)}
                  className="mt-0.5"
                />
                <div className="min-w-0 flex-1">
                  <label
                    htmlFor={`task-${task.id}`}
                    className={`block text-sm cursor-pointer ${task.done ? 'text-muted-foreground line-through' : 'text-foreground'}`}
                  >
                    {task.label}
                  </label>
                  <span className="text-xs text-muted-foreground">{task.done ? 'Completed' : task.due}</span>
                </div>
                {!task.done && (
                  <Link
                    to={team(task.path)}
                    className="text-xs font-medium text-primary hover:underline shrink-0 mt-0.5"
                    aria-label={`Open: ${task.label}`}
                  >
                    Open
                  </Link>
                )}
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <section>
        <div className="flex items-baseline justify-between mb-4 gap-4">
          <h2 className="text-xl font-bold tracking-tight text-foreground">Project components</h2>
          <p className="text-xs text-muted-foreground hidden sm:block">Jump back into any part of your project</p>
        </div>
        <ComponentLinkGrid items={quickLinks} />
      </section>
    </div>
  )
}
