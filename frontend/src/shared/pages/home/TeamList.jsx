import PropTypes from 'prop-types'
import { useNavigate } from 'react-router-dom'
import { Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import EmptyState from '../../components/EmptyState.jsx'
import { TeamCards, TeamsTable } from './TeamLists.jsx'

function Loading() {
  return (
    <div className="grid gap-3" aria-busy="true">
      <Skeleton className="h-12 w-full" />
      <Skeleton className="h-12 w-full" />
      <Skeleton className="h-12 w-full" />
    </div>
  )
}

/**
 * The teams from `useMyTeams`, in every state: loading, failed, none yet, no match, or the list
 * (a table for lecturers, cards for students). `visible` is the list after any search or filter.
 */
export default function TeamList({ teamsQuery, visible, isStaff, canCreate, email, hasInvitations }) {
  const navigate = useNavigate()

  if (teamsQuery.isPending) return <Loading />

  if (teamsQuery.isError) {
    return (
      <Card className="items-start gap-3 p-4">
        <p className="text-sm text-destructive">Your teams could not be loaded.</p>
        <Button variant="outline" loading={teamsQuery.isFetching} onClick={() => teamsQuery.refetch()}>
          Try again
        </Button>
      </Card>
    )
  }

  if (teamsQuery.data.length === 0) {
    // A student with an invitation waiting needs no "no team yet" message next to it.
    if (!canCreate && hasInvitations) return null
    return canCreate ? (
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
        description={`Your lecturer invites you by email. When they invite ${email || 'your address'}, the invitation appears here.`}
      />
    )
  }

  if (visible.length === 0) {
    return <p className="text-sm text-muted-foreground">No team matches that search.</p>
  }
  return isStaff ? <TeamsTable teams={visible} /> : <TeamCards teams={visible} />
}

TeamList.propTypes = {
  teamsQuery: PropTypes.shape({
    isPending: PropTypes.bool,
    isError: PropTypes.bool,
    isFetching: PropTypes.bool,
    data: PropTypes.array,
    refetch: PropTypes.func,
  }).isRequired,
  visible: PropTypes.arrayOf(PropTypes.object).isRequired,
  isStaff: PropTypes.bool.isRequired,
  canCreate: PropTypes.bool.isRequired,
  email: PropTypes.string,
  hasInvitations: PropTypes.bool,
}
