import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Plus, Search, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '../../auth/useAuth.js'
import {
  useAcceptInvitation,
  useDeclineInvitation,
  useMyInvitations,
  useMyTeams,
} from '../../hooks/useTeams.js'
import EmptyState from '../../components/EmptyState.jsx'
import { NextSteps, ProfileCard } from './HomeAside.jsx'
import HomeStats from './HomeStats.jsx'
import InvitationList from './InvitationList.jsx'
import { TeamCards, TeamsTable } from './TeamLists.jsx'

const SEARCH_FROM = 6 // a search box only helps once the list is long

function greeting() {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}

function Loading() {
  return (
    <div className="grid gap-3" aria-busy="true">
      <Skeleton className="h-12 w-full" />
      <Skeleton className="h-12 w-full" />
      <Skeleton className="h-12 w-full" />
    </div>
  )
}

function matches(team, query) {
  const text = [team.name, team.code, team.project?.title, team.term].join(' ').toLowerCase()
  return text.includes(query.toLowerCase())
}

/**
 * The page a person lands on after signing in: who they are, what needs an answer, and their teams.
 * It is the account level of the app, so it has a top bar. Inside a team the sidebar workspace
 * takes over (DashboardShell).
 */
export default function HomePage() {
  const { user, account } = useAuth()
  const navigate = useNavigate()
  const canCreate = user.role === 'instructor' // only lecturers create teams
  const isStaff = canCreate || user.role === 'admin'
  const teams = useMyTeams()
  const invitations = useMyInvitations()
  const accept = useAcceptInvitation()
  const decline = useDeclineInvitation()
  const [query, setQuery] = useState('')

  const visible = useMemo(
    () => (teams.data ?? []).filter((team) => matches(team, query.trim())),
    [teams.data, query],
  )
  const busyId = accept.isPending ? accept.variables : decline.isPending ? decline.variables : null
  const waiting = invitations.data ?? []
  const firstName = user.name?.split(' ')[0]

  return (
    <div className="grid gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            {greeting()}
            {firstName ? `, ${firstName}` : ''}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {isStaff ? 'Here is how your teams are doing.' : 'Here is what is happening in your teams.'}
          </p>
        </div>
        {canCreate && (
          <Button asChild>
            <Link to="/teams/new">
              <Plus className="h-4 w-4" aria-hidden="true" />
              Create team
            </Link>
          </Button>
        )}
      </div>

      {waiting.length > 0 && (
        <InvitationList
          invitations={waiting}
          busyId={busyId}
          onAccept={accept.mutate}
          onDecline={decline.mutate}
        />
      )}

      <HomeStats
        teams={teams.data ?? []}
        invitations={waiting.length}
        isStaff={isStaff}
        loading={teams.isPending}
      />

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <section className="grid gap-4" aria-labelledby="teams-heading">
          <div className="flex items-center justify-between gap-3">
            <h2 id="teams-heading" className="text-base font-semibold text-foreground">
              Your teams
            </h2>
            {teams.isSuccess && teams.data.length >= SEARCH_FROM && (
              <div className="relative w-full max-w-56">
                <Search
                  className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                  aria-hidden="true"
                />
                <Input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search teams"
                  aria-label="Search teams"
                  className="pl-8"
                />
              </div>
            )}
          </div>

          {teams.isPending && <Loading />}

          {teams.isError && (
            <Card className="items-start gap-3 p-4">
              <p className="text-sm text-destructive">Your teams could not be loaded.</p>
              <Button variant="outline" onClick={() => teams.refetch()}>
                Try again
              </Button>
            </Card>
          )}

          {/* A student with an invitation waiting needs no "no team yet" message below it. */}
          {teams.isSuccess &&
            teams.data.length === 0 &&
            (canCreate || waiting.length === 0) &&
            (canCreate ? (
              <EmptyState
                icon={Users}
                title="No teams yet"
                description="Create a team, then invite its students and any other lecturers."
                actionLabel="Create team"
                onAction={() => navigate('/teams/new')}
              />
            ) : (
              <EmptyState
                icon={Users}
                title="You are not in a team yet"
                description={`Your lecturer invites you by email. When they invite ${user.email || 'your address'}, the invitation appears here.`}
              />
            ))}

          {teams.isSuccess && teams.data.length > 0 && (
            visible.length === 0 ? (
              <p className="text-sm text-muted-foreground">No team matches that search.</p>
            ) : isStaff ? (
              <TeamsTable teams={visible} />
            ) : (
              <TeamCards teams={visible} />
            )
          )}
        </section>

        <aside className="grid gap-4">
          {canCreate && teams.isSuccess && <NextSteps teams={teams.data} />}
          <ProfileCard user={user} profile={account?.profile} />
        </aside>
      </div>
    </div>
  )
}
