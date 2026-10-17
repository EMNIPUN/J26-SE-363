import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { BellOff, CheckCheck, Clock, X } from 'lucide-react'
import PageHeader from '../../../shared/components/PageHeader.jsx'
import EmptyState from '../../../shared/components/EmptyState.jsx'
import { showToast } from '../../../shared/utils/toast.jsx'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import AgentChip from '../components/AgentChip.jsx'
import { AGENTS, INITIAL_NUDGES } from '../data/mockTutorData.js'

const FILTERS = [
  { key: 'all', label: 'All', match: () => true },
  { key: 'unread', label: 'Unread', match: (n) => n.unread },
  { key: 'check', label: 'Learning checks', match: (n) => n.type === 'check' },
  { key: 'sprint', label: 'Sprint', match: (n) => n.type === 'sprint' },
  { key: 'momentum', label: 'Momentum', match: (n) => n.type === 'momentum' },
]

export default function Nudges() {
  const { teamId } = useParams()
  const [nudges, setNudges] = useState(INITIAL_NUDGES)
  const [filter, setFilter] = useState('all')

  const activeFilter = FILTERS.find((f) => f.key === filter) || FILTERS[0]
  const visible = nudges.filter(activeFilter.match)
  const unreadCount = nudges.filter((n) => n.unread).length

  const markRead = (id) =>
    setNudges((prev) => prev.map((n) => (n.id === id ? { ...n, unread: false } : n)))

  const markAllRead = () => {
    setNudges((prev) => prev.map((n) => ({ ...n, unread: false })))
    showToast.success('All nudges marked as read')
  }

  const remove = (nudge, verb) => {
    setNudges((prev) => prev.filter((n) => n.id !== nudge.id))
    showToast.info(verb === 'snooze' ? 'Snoozed until tomorrow' : 'Nudge dismissed', {
      description: nudge.title,
      action: {
        label: 'Undo',
        onClick: () =>
          setNudges((prev) => {
            if (prev.some((n) => n.id === nudge.id)) return prev
            const order = INITIAL_NUDGES.map((n) => n.id)
            return [...prev, nudge].sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id))
          }),
      },
    })
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Nudges"
        breadcrumb={['Tutor Agent', 'Nudges']}
        description="Timely suggestions from your Tutor Agent when a deadline is at risk, a learning check is due, or your momentum changes."
        actions={
          <Button variant="outline" size="lg" onClick={markAllRead} disabled={unreadCount === 0}>
            <CheckCheck className="h-4 w-4" />
            Mark all read
          </Button>
        }
      />

      <Tabs value={filter} onValueChange={setFilter}>
        <TabsList className="h-auto flex-wrap justify-start">
          {FILTERS.map((f) => {
            const count = nudges.filter(f.match).length
            return (
              <TabsTrigger key={f.key} value={f.key} className="gap-1.5">
                {f.label}
                <span className="rounded-full bg-muted-foreground/15 px-1.5 text-[10px] tabular-nums">{count}</span>
              </TabsTrigger>
            )
          })}
        </TabsList>
      </Tabs>

      {visible.length === 0 ? (
        <EmptyState
          icon={BellOff}
          title={filter === 'all' ? 'You’re all caught up' : `No ${activeFilter.label.toLowerCase()} nudges`}
          description="New nudges appear here when the Tutor Agent spots something worth your attention."
        />
      ) : (
        <ul className="space-y-3">
          {visible.map((n) => {
            const AgentIcon = (AGENTS[n.agent] || AGENTS.learning).icon
            return (
              <li
                key={n.id}
                className={`relative flex flex-col gap-4 rounded-xl border bg-card p-5 card-elevated transition-colors sm:flex-row sm:items-start ${
                  n.unread ? 'border-primary/30' : 'border-border/60'
                }`}
              >
                {n.unread && (
                  <span className="absolute left-0 top-5 h-8 w-1 rounded-r-full bg-primary" aria-hidden="true" />
                )}
                <span
                  className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${(AGENTS[n.agent] || AGENTS.learning).tone}`}
                >
                  <AgentIcon className="h-5 w-5" />
                </span>

                <div className="min-w-0 flex-1 pr-8">
                  <div className="flex flex-wrap items-center gap-2">
                    <AgentChip agent={n.agent} />
                    <span className="text-xs text-muted-foreground">{n.time}</span>
                    {n.unread && (
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-primary">New</span>
                    )}
                  </div>
                  <h2 className="mt-1.5 text-sm font-semibold text-foreground">{n.title}</h2>
                  <p className="mt-0.5 text-sm text-muted-foreground">{n.message}</p>

                  <div className="mt-4 flex flex-wrap items-center gap-2">
                    <Button asChild size="sm" onClick={() => markRead(n.id)}>
                      <Link to={`/teams/${teamId}/tutor/chat?prompt=${encodeURIComponent(n.action.prompt)}`}>
                        {n.action.label}
                      </Link>
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => remove(n, 'snooze')}>
                      <Clock className="h-3.5 w-3.5" />
                      Snooze
                    </Button>
                    {n.unread && (
                      <Button variant="ghost" size="sm" onClick={() => markRead(n.id)}>
                        Mark as read
                      </Button>
                    )}
                  </div>
                </div>

                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="absolute right-3 top-3 text-muted-foreground"
                  onClick={() => remove(n, 'dismiss')}
                  aria-label={`Dismiss: ${n.title}`}
                >
                  <X className="h-4 w-4" />
                </Button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
