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
import { needsAttention, profileChecklist, splitByTerm } from '../../utils/teams.js'
import AvailableStudents from './AvailableStudents.jsx'
import DraftTeams from './DraftTeams.jsx'
import EarlierTerms from './EarlierTerms.jsx'
import HomeStats from './HomeStats.jsx'
import InvitationList from './InvitationList.jsx'
import NeedsAttention from './NeedsAttention.jsx'
import ProfileChecklist from './ProfileChecklist.jsx'
import RecentTeams from './RecentTeams.jsx'
import TeamList from './TeamList.jsx'
import { StudentTeamsTable } from './TeamLists.jsx'
import WaitingForReply from './WaitingForReply.jsx'

const SHOWN = 6 // the rest are on the Teams page

function greeting() {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}

/**
 * The page a person lands on after signing in. It is about the person and all their teams
 * together: what needs an answer, where their teams stand, and what to do next. What happens
 * inside one team is in that team's workspace (DashboardShell).
 */
export default function HomePage() {
  const { user, account } = useAuth()
  const canCreate = user.role === 'instructor' // only lecturers create teams
  const isStaff = canCreate || user.role === 'admin'
  const isStudent = user.role === 'student'
  const teams = useMyTeams()
  const invitations = useMyInvitations()
  const accept = useAcceptInvitation()
  const decline = useDeclineInvitation()

  const busy = accept.isPending
    ? { id: accept.variables, action: 'accept' }
    : decline.isPending
      ? { id: decline.variables, action: 'decline' }
      : null
  const waiting = invitations.data ?? []
  const all = teams.data ?? []
  const { latest, current, earlier } = splitByTerm(all)
  const drafts = all.filter((team) => team.status === 'pending')
  const settled = current.filter((team) => team.status !== 'pending')
  const past = earlier.filter((team) => team.status !== 'pending')
  const attention = needsAttention(all, isStaff)
  const profileOpen = profileChecklist(account, user.role).some((item) => !item.done)
  const hasAside = attention.length > 0 || profileOpen
  const firstName = user.name?.split(' ')[0]

  // A student's current team and past teams are two tables; a lecturer's teams are one table.
  const showTeams = teams.isPending || teams.isError || all.length === 0 || (!isStudent && settled.length > 0)

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
          busy={busy}
          onAccept={accept.mutate}
          onDecline={decline.mutate}
        />
      )}

      <HomeStats
        teams={all}
        invitations={waiting.length}
        isStaff={isStaff}
        loading={teams.isPending}
        term={latest}
      />

      <RecentTeams teams={all} />

      <div
        className={`grid items-start gap-6 ${hasAside ? 'lg:grid-cols-[minmax(0,1fr)_22rem]' : ''}`}
      >
        <div className="grid gap-6">
          {canCreate && <DraftTeams teams={drafts} />}

          {isStudent && settled.length > 0 && (
            <section className="grid gap-4" aria-labelledby="current-heading">
              <h2 id="current-heading" className="text-base font-semibold text-foreground">
                Your team{latest ? ` · ${latest}` : ''}
              </h2>
              <StudentTeamsTable teams={settled} />
            </section>
          )}

          {showTeams && (
            <section className="grid gap-4" aria-labelledby="teams-heading">
              <div className="flex items-center justify-between gap-3">
                <h2 id="teams-heading" className="text-base font-semibold text-foreground">
                  Your teams{latest ? ` · ${latest}` : ''}
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
                visible={isStudent ? [] : settled.slice(0, SHOWN)}
                isStaff={isStaff}
                canCreate={canCreate}
                email={user.email}
                hasInvitations={waiting.length > 0}
              />
            </section>
          )}

          {isStudent && past.length > 0 && (
            <section className="grid gap-4" aria-labelledby="past-heading">
              <h2 id="past-heading" className="text-base font-semibold text-foreground">
                Past teams
              </h2>
              <StudentTeamsTable teams={past} />
            </section>
          )}
          {!isStudent && <EarlierTerms teams={past} />}

          {canCreate && <AvailableStudents teams={all} defaultTerm={latest} />}
          {canCreate && <WaitingForReply />}
        </div>

        {hasAside && (
          <aside className="grid gap-4">
            {attention.length > 0 && <NeedsAttention items={attention} />}
            <ProfileChecklist account={account} role={user.role} />
          </aside>
        )}
      </div>
    </div>
  )
}
