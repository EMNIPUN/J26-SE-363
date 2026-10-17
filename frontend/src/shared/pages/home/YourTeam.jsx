import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'

const leaderLine = (team) => {
  if (team.my_role === 'leader') return 'You lead this team'
  return team.leader ? `Led by ${team.leader.name}` : 'No leader yet'
}

/** A student's team for the current term: one way in to its workspace. */
export default function YourTeam({ teams }) {
  return teams.map((team) => (
    <Card key={team.id} className="flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <p className="text-xs font-medium text-muted-foreground">
          Your team{team.term ? ` · ${team.term}` : ''}
        </p>
        <h2 className="truncate text-lg font-semibold text-foreground">{team.name}</h2>
        <p className="truncate text-sm text-muted-foreground">
          {[team.project?.title, leaderLine(team)].filter(Boolean).join(' · ')}
        </p>
      </div>
      <Button asChild className="shrink-0">
        <Link to={`/teams/${team.code}`}>
          Open workspace
          <ArrowRight aria-hidden="true" />
        </Link>
      </Button>
    </Card>
  ))
}

YourTeam.propTypes = { teams: PropTypes.arrayOf(PropTypes.object).isRequired }
