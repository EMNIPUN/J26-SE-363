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
import PageHeader from '../../components/PageHeader.jsx'
import InvitationList from './InvitationList.jsx'
import { TeamCards, TeamsTable } from './TeamLists.jsx'

const SEARCH_FROM = 6 // a search box only helps once the list is long

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

export default function HomePage() {
  const { user } = useAuth()
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

  return (
    <div className="grid gap-6">
      <PageHeader
        title="Teams"
        description={isStaff ? 'The teams you supervise.' : 'The teams you are part of.'}
        actions={
          canCreate && (
            <Button asChild>
              <Link to="/teams/new">
                <Plus className="h-4 w-4" aria-hidden="true" />
                Create team
              </Link>
            </Button>
          )
        }
      />

      {waiting.length > 0 && (
        <InvitationList
          invitations={waiting}
          busyId={busyId}
          onAccept={accept.mutate}
          onDecline={decline.mutate}
        />
      )}

      {teams.isPending && <Loading />}

      {teams.isError && (
        <Card className="items-start gap-3 p-4">
          <p className="text-sm text-destructive">Your teams could not be loaded.</p>
          <Button variant="outline" onClick={() => teams.refetch()}>
            Try again
          </Button>
        </Card>
      )}

      {/* A student with an invitation waiting needs no "no team yet" message above it. */}
      {teams.isSuccess && teams.data.length === 0 && (canCreate || waiting.length === 0) && (
        canCreate ? (
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
        )
      )}

      {teams.isSuccess && teams.data.length > 0 && (
        <div className="grid gap-4">
          {teams.data.length >= SEARCH_FROM && (
            <div className="relative max-w-sm">
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
          {visible.length === 0 ? (
            <p className="text-sm text-muted-foreground">No team matches that search.</p>
          ) : isStaff ? (
            <TeamsTable teams={visible} />
          ) : (
            <TeamCards teams={visible} />
          )}
        </div>
      )}
    </div>
  )
}
