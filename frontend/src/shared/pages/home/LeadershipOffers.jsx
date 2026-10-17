import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { Crown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useRespondToLeadership } from '../../hooks/useTeams.js'

function Offer({ team }) {
  const respond = useRespondToLeadership(team.code)
  return (
    <li className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-w-0 items-center gap-3">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Crown className="h-4 w-4" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-foreground">
            You were offered team leadership of {team.name}
          </p>
          <p className="text-sm text-muted-foreground">
            You become the leader when you accept.{' '}
            <Link to={`/teams/${team.code}/members`} className="text-primary hover:underline">
              Open the team
            </Link>
          </p>
        </div>
      </div>
      <div className="flex shrink-0 gap-2">
        <Button
          variant="outline"
          loading={respond.isPending && respond.variables === false}
          disabled={respond.isPending}
          onClick={() => respond.mutate(false)}
        >
          Decline
        </Button>
        <Button
          loading={respond.isPending && respond.variables === true}
          disabled={respond.isPending}
          onClick={() => respond.mutate(true)}
        >
          Accept
        </Button>
      </div>
    </li>
  )
}

Offer.propTypes = { team: PropTypes.object.isRequired }

/** Leadership offers waiting for the student, to accept or decline without opening the team. */
export default function LeadershipOffers({ teams }) {
  const offered = teams.filter((team) => team.leadership_offer_to_me)
  if (offered.length === 0) return null
  return (
    <Card className="gap-0 border-primary/30 bg-primary/5 p-0">
      <ul className="divide-y divide-border">
        {offered.map((team) => (
          <Offer key={team.id} team={team} />
        ))}
      </ul>
    </Card>
  )
}

LeadershipOffers.propTypes = { teams: PropTypes.arrayOf(PropTypes.object).isRequired }
