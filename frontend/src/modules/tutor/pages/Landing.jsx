import { Link, useParams } from 'react-router-dom'
import { ArrowRight, BellRing, MessageCircle, Sparkles } from 'lucide-react'
import PageHeader from '../../../shared/components/PageHeader.jsx'
import Card from '../../../shared/components/Card.jsx'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import AgentChip from '../components/AgentChip.jsx'
import {
  CONCEPTS,
  INITIAL_NUDGES,
  MOMENTUM,
  SESSIONS,
  SPRINT_GUIDANCE,
} from '../data/mockTutorData.js'

const WEEKDAYS = ['M', 'T', 'W', 'T', 'F', 'S', 'S']

function masteryTone(value) {
  if (value >= 75) return 'text-emerald-600 dark:text-emerald-400'
  if (value >= 50) return 'text-foreground'
  return 'text-amber-600 dark:text-amber-400'
}

export default function Landing() {
  const { teamId } = useParams()
  const base = `/teams/${teamId}/tutor`
  const chatWith = (prompt) => `${base}/chat?prompt=${encodeURIComponent(prompt)}`
  const unreadNudges = INITIAL_NUDGES.filter((n) => n.unread)

  return (
    <div className="space-y-6">
      <PageHeader
        title="Adaptive Tutor"
        breadcrumb={['Adaptive Tutor', 'Suggestions']}
        description="Help that starts from your sprint. These suggestions use the sample project until the tutor is connected to your live tasks. Nothing here is a grade."
        actions={
          <>
            <Button asChild variant="outline" size="lg">
              <Link to={`${base}/nudges`}>
                <BellRing className="h-4 w-4" />
                Nudges
                {unreadNudges.length > 0 && (
                  <span className="ml-0.5 rounded-full bg-primary px-1.5 text-[10px] font-semibold text-primary-foreground">
                    {unreadNudges.length}
                  </span>
                )}
              </Link>
            </Button>
            <Button asChild size="lg">
              <Link to={`${base}/chat`}>
                <Sparkles className="h-4 w-4" />
                Start a session
              </Link>
            </Button>
          </>
        }
      />

      <Card className="gap-4">
        <div>
          <h2 className="text-base font-semibold text-foreground">Suggested for this sprint</h2>
          <p className="text-sm text-muted-foreground">
            Start with the item that matches the task you are doing. Discuss opens a practice conversation, not an assessment.
          </p>
        </div>
        <ul className="space-y-2">
          {SPRINT_GUIDANCE.map((item) => (
            <li
              key={item.id}
              className="flex flex-col gap-3 rounded-lg border border-border/60 p-4 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="min-w-0">
                <AgentChip agent={item.agent} />
                <p className="mt-2 text-sm font-medium text-foreground">{item.title}</p>
                <p className="mt-0.5 text-sm text-muted-foreground">{item.detail}</p>
              </div>
              <Button asChild variant="outline" size="sm" className="shrink-0 self-start sm:self-center">
                <Link to={chatWith(item.prompt)}>
                  <MessageCircle className="h-3.5 w-3.5" />
                  Discuss
                </Link>
              </Button>
            </li>
          ))}
        </ul>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="gap-5">
          <div>
            <h2 className="text-base font-semibold text-foreground">Practice rhythm</h2>
            <p className="text-sm text-muted-foreground">A sample week, shown until real study activity is connected.</p>
          </div>

          <div>
            <p className="mb-2 text-xs font-medium text-muted-foreground">Active days this week</p>
            <div className="flex gap-1.5">
              {MOMENTUM.streakDays.map((active, idx) => (
                <div key={idx} className="flex flex-1 flex-col items-center gap-1">
                  <span
                    className={`h-7 w-full rounded-md ${active ? 'bg-primary' : 'bg-muted border border-border/60'}`}
                    aria-label={`${WEEKDAYS[idx]}: ${active ? 'active' : 'inactive'}`}
                  />
                  <span className="text-[10px] text-muted-foreground">{WEEKDAYS[idx]}</span>
                </div>
              ))}
            </div>
          </div>

          <dl className="grid grid-cols-2 gap-2 border-t border-border pt-4 text-center">
            <div>
              <dt className="text-xs text-muted-foreground">Sample sessions</dt>
              <dd className="text-lg font-semibold text-foreground">{MOMENTUM.sessionsThisWeek}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Checks in the sample</dt>
              <dd className="text-lg font-semibold text-foreground">
                {MOMENTUM.checksPassed}/{MOMENTUM.checksTotal}
              </dd>
            </div>
          </dl>
        </Card>

        <Card className="gap-4">
          <div>
            <h2 className="text-base font-semibold text-foreground">Concepts to revisit</h2>
            <p className="text-sm text-muted-foreground">Sample familiarity, not a ranking. Lower just means practice it next.</p>
          </div>
          <ul className="space-y-4">
            {CONCEPTS.map((c) => (
              <li key={c.id}>
                <div className="mb-1.5 flex items-center justify-between text-sm">
                  <span className="text-foreground">{c.label}</span>
                  <span className={`text-xs font-semibold tabular-nums ${masteryTone(c.mastery)}`}>{c.mastery}%</span>
                </div>
                <Progress value={c.mastery} className="h-1.5" aria-label={`${c.label} mastery`} />
              </li>
            ))}
          </ul>
        </Card>

        <Card className="gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-foreground">Latest nudges</h2>
            <Link to={`${base}/nudges`} className="text-xs font-medium text-primary hover:underline">
              View all
            </Link>
          </div>
          <ul className="space-y-2">
            {INITIAL_NUDGES.slice(0, 3).map((n) => (
              <li key={n.id}>
                <Link
                  to={`${base}/nudges`}
                  className="flex items-start gap-3 rounded-lg p-2 -mx-2 transition-colors hover:bg-muted/60 outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <span
                    className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.unread ? 'bg-primary' : 'bg-transparent'}`}
                    aria-label={n.unread ? 'Unread' : undefined}
                  />
                  <span className="min-w-0">
                    <span className="block text-sm font-medium text-foreground">{n.title}</span>
                    <span className="block text-xs text-muted-foreground">{n.time}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </Card>

        <Card className="gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-foreground">Recent sessions</h2>
            <Link to={`${base}/chat`} className="text-xs font-medium text-primary hover:underline">
              Open chat
            </Link>
          </div>
          <ul className="space-y-1">
            {SESSIONS.slice(0, 3).map((s) => (
              <li key={s.id}>
                <Link
                  to={`${base}/chat?session=${s.id}`}
                  className="group flex items-center justify-between gap-3 rounded-lg p-2 -mx-2 transition-colors hover:bg-muted/60 outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium text-foreground">{s.title}</span>
                    <span className="block text-xs text-muted-foreground">
                      {s.when} · {s.messages} messages
                    </span>
                  </span>
                  <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  )
}
