import { Link } from 'react-router-dom'
import { ArrowRight, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuth } from '../../auth/useAuth.js'
import {
  useAcceptInvitation,
  useDeclineInvitation,
  useMyInvitations,
  useMyTeams,
} from '../../hooks/useTeams.js'
import HomeStats from './HomeStats.jsx'
import InvitationList from './InvitationList.jsx'
import NeedsAttention from './NeedsAttention.jsx'
import TeamList from './TeamList.jsx'
import { needsAttention } from '../../utils/teams.js'

const SHOWN = 6 // the rest are on the Teams page

function greeting() {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}

/**
 * The page a person lands on after signing in: what needs an answer, a few numbers, and their
 * teams. The full list is on the Teams page. Inside a team the sidebar workspace takes over.
 */
export default function HomePage() {
  const { user } = useAuth()
  const canCreate = user.role === 'instructor' // only lecturers create teams
  const isStaff = canCreate || user.role === 'admin'
  const teams = useMyTeams()
  const invitations = useMyInvitations()
  const accept = useAcceptInvitation()
  const decline = useDeclineInvitation()

  const busyId = accept.isPending ? accept.variables : decline.isPending ? decline.variables : null
  const waiting = invitations.data ?? []
  const all = teams.data ?? []
  const attention = needsAttention(all, isStaff)
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

      <HomeStats teams={all} invitations={waiting.length} isStaff={isStaff} loading={teams.isPending} />

      <div className={`grid items-start gap-6 ${attention.length > 0 ? 'lg:grid-cols-[minmax(0,1fr)_22rem]' : ''}`}>
        <section className="grid gap-4" aria-labelledby="teams-heading">
          <div className="flex items-center justify-between gap-3">
            <h2 id="teams-heading" className="text-base font-semibold text-foreground">
              Your teams
            </h2>
            {all.length > SHOWN && (
              <Link
                to="/teams"
                className="flex items-center gap-1 text-sm font-medium text-primary hover:underline"
              >
                View all {all.length}
                <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
              </Link>
            )}
          </div>
          <TeamList
            teamsQuery={teams}
            visible={all.slice(0, SHOWN)}
            isStaff={isStaff}
            canCreate={canCreate}
            email={user.email}
            hasInvitations={waiting.length > 0}
          />
        </section>

        {attention.length > 0 && <NeedsAttention items={attention} />}
      </div>
    </div>
  )
}
